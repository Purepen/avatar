"""Tests for the composer attention toggle and full-thread admin search."""

import asyncio
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
            client,
            {"conversation_id": conversation_id, "message": "Q1", "visitor_name": "N.A."},
        )
        rows = db.fetch_conversation(conversation_id)
        assert rows[0]["needs_attention"] is False
        assert rows[0]["tool_calls"] is None


class TestNewConversationAlert:
    """First message of a brand-new conversation pushes an alert so the human
    knows to come watch/intercept; later messages in the same conversation
    don't repeat it (SPEC addition, 2026-08-02)."""

    async def test_first_message_pushes_new_conversation_alert(
        self, client, conversation_id, monkeypatch
    ):
        import app.routers.chat as chat_module

        calls: list[str] = []
        monkeypatch.setattr(
            chat_module, "push", lambda message, timeout=15: calls.append(message)
        )

        await collect_sse(
            client,
            {"conversation_id": conversation_id, "message": "Q1", "visitor_name": "N.C."},
        )
        # The push is fire-and-forget (must never delay the visitor's reply);
        # give the background task a moment to run before asserting on it.
        await asyncio.sleep(0.2)
        assert len(calls) == 1
        assert calls[0].startswith("[New conversation]")
        assert "N.C." in calls[0]

    async def test_second_message_does_not_repeat_alert(
        self, client, conversation_id, monkeypatch
    ):
        import app.routers.chat as chat_module

        calls: list[str] = []
        monkeypatch.setattr(
            chat_module, "push", lambda message, timeout=15: calls.append(message)
        )

        await collect_sse(
            client,
            {"conversation_id": conversation_id, "message": "Q1", "visitor_name": "S.M."},
        )
        await collect_sse(
            client,
            {"conversation_id": conversation_id, "message": "Q2", "visitor_name": "S.M."},
        )
        await asyncio.sleep(0.2)
        new_convo_calls = [c for c in calls if c.startswith("[New conversation]")]
        assert len(new_convo_calls) == 1

    async def test_alert_failure_does_not_break_the_chat(
        self, client, conversation_id, monkeypatch
    ):
        import app.routers.chat as chat_module

        def boom(message: str, timeout: int = 15) -> str:
            raise RuntimeError("pushover down")

        monkeypatch.setattr(chat_module, "push", boom)

        events = await collect_sse(
            client,
            {"conversation_id": conversation_id, "message": "Q1", "visitor_name": "A.F."},
        )
        assert [e for e, _ in events][-1] == "done"


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
