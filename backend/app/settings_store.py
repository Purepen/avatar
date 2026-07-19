"""Key-value settings persisted in Supabase (the `settings` table).

Used for the admin password override + reset codes. The table is optional:
if it hasn't been created yet, reads return None and writes raise
SettingsUnavailable — the password features then fall back cleanly to the
ADMIN_PASSWORD env var.
"""

import time

from postgrest.exceptions import APIError

from .db import get_client


class SettingsUnavailable(Exception):
    """The settings table does not exist (or is not reachable)."""


_cache: dict[str, tuple[float, dict | None]] = {}
_TTL_SECONDS = 20.0


def get_setting(key: str, use_cache: bool = True) -> dict | None:
    if use_cache:
        hit = _cache.get(key)
        if hit and time.time() - hit[0] < _TTL_SECONDS:
            return hit[1]
    try:
        rows = (
            get_client()
            .table("settings")
            .select("value")
            .eq("key", key)
            .execute()
            .data
        )
        value = rows[0]["value"] if rows else None
    except APIError:
        value = None  # table missing — feature falls back to env password
    _cache[key] = (time.time(), value)
    return value


def set_setting(key: str, value: dict) -> None:
    try:
        get_client().table("settings").upsert({"key": key, "value": value}).execute()
    except APIError as exc:
        raise SettingsUnavailable(
            "The settings table is missing — run the CREATE TABLE from the README."
        ) from exc
    _cache[key] = (time.time(), value)


def delete_setting(key: str) -> None:
    try:
        get_client().table("settings").delete().eq("key", key).execute()
    except APIError:
        pass
    _cache[key] = (time.time(), None)
