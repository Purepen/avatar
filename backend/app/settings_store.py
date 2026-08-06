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


# ---- Per-conversation admin controls (pause the Avatar / block the visitor) ----
#
# Stored in the same key-value settings table under "conv_state:<conversation_id>"
# — no new table needed. Degrades to "both off" if the table is missing.

_CONV_STATE_PREFIX = "conv_state:"


def conversation_state(conversation_id: str) -> dict:
    value = get_setting(_CONV_STATE_PREFIX + conversation_id)
    return {
        "avatar_muted": bool(value and value.get("avatar_muted")),
        "visitor_blocked": bool(value and value.get("visitor_blocked")),
    }


def set_conversation_state(conversation_id: str, **updates: bool) -> dict:
    state = conversation_state(conversation_id)
    state.update(updates)
    set_setting(_CONV_STATE_PREFIX + conversation_id, state)
    return state


def all_conversation_states() -> dict[str, dict]:
    """Every conv_state row in one round-trip, keyed by conversation_id —
    used by the admin inbox so it doesn't fetch state per-conversation."""
    try:
        rows = (
            get_client()
            .table("settings")
            .select("key, value")
            .like("key", f"{_CONV_STATE_PREFIX}%")
            .execute()
            .data
        )
    except APIError:
        return {}
    return {row["key"][len(_CONV_STATE_PREFIX) :]: row["value"] for row in rows}
