"""Admin API: login, password management, and the conversation
inbox/thread/reply/resolve routes.

Every route except login and the password-reset pair is guarded by the
require_admin dependency (signed httpOnly session cookie).
"""

import secrets
import time

from fastapi import APIRouter, Depends, HTTPException, Response

from .. import db, rate_limit, settings_store
from ..auth import (
    check_admin_password,
    clear_session_cookie,
    hash_password,
    require_admin,
    set_admin_password,
    set_session_cookie,
    verify_password_hash,
)
from ..models import (
    AdminMessageRequest,
    ChangePasswordRequest,
    ConversationResponse,
    InboxEntry,
    LoginRequest,
    Message,
    ResetConfirmRequest,
)
from ..tools.push import push

router = APIRouter()

protected = APIRouter(dependencies=[Depends(require_admin)])

RESET_CODE_TTL_SECONDS = 10 * 60
RESET_MAX_ATTEMPTS = 5


@router.post("/admin/login")
def login(request: LoginRequest, response: Response):
    if not check_admin_password(request.password):
        raise HTTPException(status_code=401, detail="Wrong password")
    set_session_cookie(response)
    return {"ok": True}


@protected.post("/admin/change-password")
def change_password(request: ChangePasswordRequest, response: Response):
    """Rotate the admin password (requires knowing the current one). All other
    sessions are invalidated; this browser gets a fresh cookie."""
    if not check_admin_password(request.current_password):
        raise HTTPException(status_code=401, detail="Current password is wrong")
    try:
        set_admin_password(request.new_password)
    except settings_store.SettingsUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    set_session_cookie(response)  # re-issue with the new auth version
    push("Your Avatar admin password was just changed from the dashboard.")
    return {"ok": True}


@router.post("/admin/reset/request")
def reset_request():
    """Send a one-time 6-digit reset code to the owner's phone (Pushover)."""
    if not rate_limit.allow_reset_request():
        raise HTTPException(status_code=429, detail="Too many reset requests")
    code = f"{secrets.randbelow(1_000_000):06d}"
    try:
        settings_store.set_setting(
            "admin_reset",
            {
                "code_hash": hash_password(code),
                "expires": time.time() + RESET_CODE_TTL_SECONDS,
                "attempts": 0,
            },
        )
    except settings_store.SettingsUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    push(f"Avatar admin password reset code: {code} (valid for 10 minutes)")
    return {"ok": True}


@router.post("/admin/reset/confirm")
def reset_confirm(request: ResetConfirmRequest, response: Response):
    """Verify the pushed code and set the new password."""
    reset = settings_store.get_setting("admin_reset", use_cache=False)
    if not reset or time.time() > reset.get("expires", 0):
        raise HTTPException(status_code=400, detail="No active reset code")
    if reset.get("attempts", 0) >= RESET_MAX_ATTEMPTS:
        settings_store.delete_setting("admin_reset")
        raise HTTPException(status_code=400, detail="Too many attempts")
    if not verify_password_hash(request.code, reset["code_hash"]):
        reset["attempts"] = reset.get("attempts", 0) + 1
        settings_store.set_setting("admin_reset", reset)
        raise HTTPException(status_code=401, detail="Wrong code")
    try:
        set_admin_password(request.new_password)
    except settings_store.SettingsUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    settings_store.delete_setting("admin_reset")
    set_session_cookie(response)
    push("Your Avatar admin password was just reset via a phone code.")
    return {"ok": True}


@router.post("/admin/logout")
def logout(response: Response):
    clear_session_cookie(response)
    return {"ok": True}


@protected.get("/admin/session")
def session_check():
    """Lets the frontend check whether an existing session cookie is valid."""
    return {"ok": True}


@protected.get("/admin/conversations", response_model=list[InboxEntry])
def inbox():
    return db.fetch_admin_inbox()


@protected.get(
    "/admin/conversations/{conversation_id}", response_model=ConversationResponse
)
def open_thread(conversation_id: str):
    """Opening a thread marks every row read + clears needs_attention and
    returns the updated rows — one Supabase round-trip (SPEC requirement).
    """
    rows = db.fetch_and_mark_read(conversation_id)
    return ConversationResponse(
        conversation_id=conversation_id,
        conversation_name=db.derive_conversation_name(rows),
        messages=rows,
    )


@protected.post(
    "/admin/conversations/{conversation_id}/messages", response_model=Message
)
def post_human_message(conversation_id: str, request: AdminMessageRequest):
    """Insert the owner's message. The Avatar does NOT react to it — it is
    simply part of the transcript the next time the visitor sends something.
    """
    row = db.insert_message(
        conversation_id=conversation_id,
        role="human",
        content=request.content,
        read=True,
    )
    return row


@protected.post("/admin/conversations/{conversation_id}/resolve")
def resolve(conversation_id: str):
    db.mark_resolved(conversation_id)
    return {"ok": True}


router.include_router(protected)
