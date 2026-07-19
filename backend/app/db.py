"""Supabase access: all reads/writes to the messages table.

Conversation reads are a single round-trip (SPEC requirement): opening a
thread in admin marks every row read + clears needs_attention via one
PostgREST "update ... returning" call that returns the updated rows.
"""

from datetime import datetime, timezone
from functools import lru_cache

import httpx
from supabase import Client, create_client
from supabase.client import ClientOptions

from . import config


@lru_cache(maxsize=1)
def get_client() -> Client:
    # Generous timeout: tolerates slow networks without failing mid-conversation
    options = ClientOptions(httpx_client=httpx.Client(timeout=60))
    return create_client(config.SUPABASE_URL, config.SUPABASE_KEY, options)


def insert_message(
    conversation_id: str,
    role: str,
    content: str,
    conversation_name: str | None = None,
    tool_calls: list | None = None,
    needs_attention: bool = False,
    read: bool = False,
) -> dict:
    """Insert one message row and return it."""
    row = {
        "conversation_id": conversation_id,
        "conversation_name": conversation_name,
        "role": role,
        "content": content,
        "tool_calls": tool_calls,
        "needs_attention": needs_attention,
        "read": read,
    }
    result = get_client().table("messages").insert(row).execute()
    return result.data[0]


def fetch_conversation(conversation_id: str, after_id: int | None = None) -> list[dict]:
    """All rows for a conversation in chronological order.

    With after_id, only rows newer than that id (the polling path).
    """
    query = (
        get_client()
        .table("messages")
        .select("*")
        .eq("conversation_id", conversation_id)
        .order("id")
    )
    if after_id is not None:
        query = query.gt("id", after_id)
    return query.execute().data


def fetch_and_mark_read(conversation_id: str) -> list[dict]:
    """Open a thread in admin: mark all rows read, clear needs_attention,
    and return the updated rows — one PostgREST round-trip.
    """
    result = (
        get_client()
        .table("messages")
        .update({"read": True, "needs_attention": False})
        .eq("conversation_id", conversation_id)
        .execute()
    )
    return sorted(result.data, key=lambda r: r["id"])


def mark_resolved(conversation_id: str) -> None:
    """Clear the needs_attention flag without touching anything else."""
    (
        get_client()
        .table("messages")
        .update({"needs_attention": False})
        .eq("conversation_id", conversation_id)
        .eq("needs_attention", True)
        .execute()
    )


def fetch_admin_inbox(limit_rows: int = 2000) -> list[dict]:
    """One entry per conversation for the admin sidebar, most recent first.

    Fetches a recent window of rows and groups in Python — fine at
    personal-site scale (a Postgres view could replace this later without
    changing the API shape).
    """
    rows = (
        get_client()
        .table("messages")
        .select(
            "id, conversation_id, conversation_name, role, content, "
            "needs_attention, read, created_at"
        )
        .order("id", desc=True)
        .limit(limit_rows)
        .execute()
        .data
    )
    conversations: dict[str, dict] = {}
    for row in rows:  # newest first
        cid = row["conversation_id"]
        convo = conversations.get(cid)
        if convo is None:
            convo = conversations[cid] = {
                "conversation_id": cid,
                "conversation_name": None,
                "last_message_at": row["created_at"],
                "last_role": row["role"],
                "preview": row["content"][:140],
                "message_count": 0,
                "unread_count": 0,
                "needs_attention": False,
                "search_blob": "",
            }
        convo["message_count"] += 1
        # Lowercased full-thread text (capped) so admin search reaches every
        # message, not just the latest preview.
        if len(convo["search_blob"]) < 4000:
            convo["search_blob"] += row["content"][:500].lower() + "\n"
        if row["conversation_name"] and not convo["conversation_name"]:
            convo["conversation_name"] = row["conversation_name"]
        if not row["read"] and row["role"] != "human":
            convo["unread_count"] += 1
        if row["needs_attention"]:
            convo["needs_attention"] = True
        # Prefer the visitor's latest line as the preview (inbox shows "what they said")
        if convo["preview"] == "" and row["content"]:
            convo["preview"] = row["content"][:140]
    return sorted(
        conversations.values(), key=lambda c: c["last_message_at"], reverse=True
    )


def derive_conversation_name(rows: list[dict]) -> str | None:
    """Conversation name from rows already loaded — no extra query."""
    for row in rows:
        if row.get("conversation_name"):
            return row["conversation_name"]
    return None


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
