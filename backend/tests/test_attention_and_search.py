"""Tests for the composer attention toggle and full-thread admin search."""

import json

import pytest

from app import db
from tests.conftest import collect_sse

pytestmark = pytest.mark.anyio


class TestAttentionToggle:
    async def test_attention_qn_pings_and_flags(self, client, conversation_id):
        """attention=True fires the push (real Pushover), flags the visitor row,
        and emits the attention_push status events — here on the no-LLM Qn path."""
        events = await collect_sse(
            client,
            {
                "conversation_id": conversation_id,
                "message": "Q1",
                "visitor_name": "A.T.",
                "attention": True,
            },
        )
        names = [e for e, _ in events]
        assert names == [
            "visitor_message",
            "meta",
            "tool_call",
            "tool_result",
            "token",
            "done",
        ]
        tool_evt = json.loads([d for e, d in events if e == "tool_call"][0])
        assert tool_evt == {"tool": "attention_push"}
        # instant tag preserved alongside the attention push
        assert json.loads(dict(events)["meta"])["mode"] == "instant"

        rows = db.fetch_conversation(conversation_id)
        visitor_row = rows[0]
        assert visitor_row["needs_attention"] is True
        assert visitor_row["tool_calls"] == [{"tool": "attention_request"}]

        # the flag surfaces in the admin inbox
        entry = next(
            e
            for e in db.fetch_admin_inbox()
            if e["conversation_id"] == conversation_id
        )
        assert entry["needs_attention"] is True

    async def test_no_attention_no_flag(self, client, conversation_id):
        await collect_sse(
            client, {"conversation_id": conversation_id, "message": "Q1"}
        )
        rows = db.fetch_conversation(conversation_id)
        assert rows[0]["needs_attention"] is False
        assert rows[0]["tool_calls"] is None


class TestInboxSearchBlob:
    async def test_search_blob_covers_older_messages(
        self, admin_client, conversation_id
    ):
        db.insert_message(
            conversation_id, "visitor", "My kubernetes cluster is on fire", "S.B."
        )
        db.insert_message(conversation_id, "avatar", "Let me help with that.")
        db.insert_message(conversation_id, "visitor", "thanks, that fixed it")

        r = await admin_client.get("/admin/conversations")
        entry = next(
            e for e in r.json() if e["conversation_id"] == conversation_id
        )
        # preview is the newest message; the blob still finds the oldest one
        assert "kubernetes" not in entry["preview"].lower()
        assert "kubernetes" in entry["search_blob"]
        assert entry["search_blob"] == entry["search_blob"].lower()
