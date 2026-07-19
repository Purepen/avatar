"""Password management: hashing units, change-password, and the
Pushover-code reset flow.

Flow tests need the Supabase `settings` table (see README) and self-skip if
it hasn't been created. They restore env-password auth afterwards by deleting
the settings rows they wrote.
"""

import os
import time

import pytest
from postgrest.exceptions import APIError

from app import settings_store
from app.auth import hash_password, verify_password_hash
from app.db import get_client

pytestmark = pytest.mark.anyio


def settings_table_exists() -> bool:
    try:
        get_client().table("settings").select("key").limit(1).execute()
        return True
    except APIError:
        return False


needs_settings = pytest.mark.skipif(
    not settings_table_exists(),
    reason="settings table not created yet (see README)",
)


class TestHashing:
    def test_roundtrip(self):
        stored = hash_password("s3cret-password")
        assert verify_password_hash("s3cret-password", stored)
        assert not verify_password_hash("wrong", stored)

    def test_salted(self):
        assert hash_password("same") != hash_password("same")

    def test_malformed_stored_value(self):
        assert not verify_password_hash("x", "not-a-valid-hash")


@pytest.fixture()
def restore_env_auth():
    """After the test, drop stored auth so ADMIN_PASSWORD works again."""
    yield
    settings_store.delete_setting("admin_auth")
    settings_store.delete_setting("admin_reset")


@needs_settings
class TestChangePassword:
    async def test_change_rotates_password_and_sessions(
        self, client, restore_env_auth
    ):
        env_password = os.environ["ADMIN_PASSWORD"]
        r = await client.post("/admin/login", json={"password": env_password})
        assert r.status_code == 200
        old_cookie = client.cookies["avatar_admin"]

        r = await client.post(
            "/admin/change-password",
            json={"current_password": env_password, "new_password": "new-pass-123"},
        )
        assert r.status_code == 200

        # env password no longer valid; new one is
        r = await client.post("/admin/login", json={"password": env_password})
        assert r.status_code == 401
        r = await client.post("/admin/login", json={"password": "new-pass-123"})
        assert r.status_code == 200

        # the pre-change session token is dead (auth version bumped)
        client.cookies.set("avatar_admin", old_cookie)
        r = await client.get("/admin/session")
        assert r.status_code == 401

    async def test_change_requires_current_password(self, client, restore_env_auth):
        r = await client.post(
            "/admin/login", json={"password": os.environ["ADMIN_PASSWORD"]}
        )
        assert r.status_code == 200
        r = await client.post(
            "/admin/change-password",
            json={"current_password": "wrong", "new_password": "whatever-123"},
        )
        assert r.status_code == 401

    async def test_change_requires_login(self, client):
        r = await client.post(
            "/admin/change-password",
            json={"current_password": "a", "new_password": "whatever-123"},
        )
        assert r.status_code == 401


@needs_settings
class TestResetFlow:
    async def test_reset_with_seeded_code(self, client, restore_env_auth):
        # Seed the code directly (the real flow pushes it to the phone).
        settings_store.set_setting(
            "admin_reset",
            {
                "code_hash": hash_password("123456"),
                "expires": time.time() + 600,
                "attempts": 0,
            },
        )
        r = await client.post(
            "/admin/reset/confirm",
            json={"code": "999999", "new_password": "reset-pass-123"},
        )
        assert r.status_code == 401  # wrong code

        r = await client.post(
            "/admin/reset/confirm",
            json={"code": "123456", "new_password": "reset-pass-123"},
        )
        assert r.status_code == 200
        # signed in immediately, and the new password works
        r = await client.get("/admin/session")
        assert r.status_code == 200
        r = await client.post("/admin/login", json={"password": "reset-pass-123"})
        assert r.status_code == 200
        # code is single-use
        r = await client.post(
            "/admin/reset/confirm",
            json={"code": "123456", "new_password": "other-pass-123"},
        )
        assert r.status_code == 400

    async def test_expired_code_rejected(self, client, restore_env_auth):
        settings_store.set_setting(
            "admin_reset",
            {
                "code_hash": hash_password("222222"),
                "expires": time.time() - 1,
                "attempts": 0,
            },
        )
        r = await client.post(
            "/admin/reset/confirm",
            json={"code": "222222", "new_password": "reset-pass-123"},
        )
        assert r.status_code == 400
