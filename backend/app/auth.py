"""Admin session auth: signed httpOnly cookie via itsdangerous.

Passwords: ADMIN_PASSWORD from .env is the initial password. Once the admin
changes it from the dashboard, a PBKDF2 hash stored in the Supabase `settings`
table takes over (the env value stops working). Each change bumps an auth
version baked into every session token, so changing the password immediately
invalidates all existing sessions — the defence against a stolen cookie.
"""

import base64
import hashlib
import secrets

from fastapi import HTTPException, Request, Response
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from . import config, settings_store

_serializer = URLSafeTimedSerializer(config.SESSION_SECRET, salt="avatar-admin-session")

_PBKDF2_ITERATIONS = 200_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt, _PBKDF2_ITERATIONS
    )
    return f"{base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def verify_password_hash(password: str, stored: str) -> bool:
    try:
        salt_b64, digest_b64 = stored.split("$", 1)
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
    except (ValueError, TypeError):
        return False
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt, _PBKDF2_ITERATIONS
    )
    return secrets.compare_digest(digest, expected)


def _auth_state(use_cache: bool = True) -> tuple[str | None, int]:
    """(stored password hash or None, auth version)."""
    setting = settings_store.get_setting("admin_auth", use_cache=use_cache)
    if setting and setting.get("password_hash"):
        return setting["password_hash"], int(setting.get("version", 1))
    return None, 0


def check_admin_password(password: str) -> bool:
    """Verify against the stored hash if set, else the ADMIN_PASSWORD env var."""
    stored_hash, _ = _auth_state(use_cache=False)
    if stored_hash:
        return verify_password_hash(password, stored_hash)
    return bool(config.ADMIN_PASSWORD) and secrets.compare_digest(
        password, config.ADMIN_PASSWORD
    )


def set_admin_password(new_password: str) -> None:
    """Store a new password hash and bump the auth version (kills all sessions)."""
    _, version = _auth_state(use_cache=False)
    settings_store.set_setting(
        "admin_auth",
        {"password_hash": hash_password(new_password), "version": version + 1},
    )


def create_session_token() -> str:
    _, version = _auth_state()
    return _serializer.dumps({"admin": True, "v": version})


def set_session_cookie(response: Response) -> None:
    response.set_cookie(
        key=config.SESSION_COOKIE_NAME,
        value=create_session_token(),
        max_age=config.SESSION_MAX_AGE_SECONDS,
        httponly=True,
        secure=config.COOKIE_SECURE,
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=config.SESSION_COOKIE_NAME, path="/")


def require_admin(request: Request) -> None:
    """FastAPI dependency guarding every /admin/* API route."""
    token = request.cookies.get(config.SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        data = _serializer.loads(token, max_age=config.SESSION_MAX_AGE_SECONDS)
    except (BadSignature, SignatureExpired):
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    if not data.get("admin"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    _, current_version = _auth_state()
    if int(data.get("v", 0)) != current_version:
        raise HTTPException(status_code=401, detail="Session superseded")
