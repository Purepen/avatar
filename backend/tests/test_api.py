"""API tests against the FastAPI app in-process (httpx ASGITransport).

LLM-marked tests make real OpenRouter calls on the cheap model and real
Supabase writes; conversation rows are deleted by the conversation_id fixture.
"""

import json
import os

import pytest

from app import db
from tests.conftest import collect_sse

pytestmark = pytest.mark.anyio

ADMIN_ROUTES = [
    ("GET", "/admin/session"),
    ("GET", "/admin/conversations"),
    ("GET", "/admin/conversations/00000000-0000-0000-0000-000000000001"),
    ("POST", "/admin/conversations/00000000-0000-0000-0000-000000000001/messages"),
    ("POST", "/admin/conversations/00000000-0000-0000-0000-000000000001/resolve"),
]


class TestAdminAuth:
    @pytest.mark.parametrize("method,path", ADMIN_ROUTES)
    async def test_admin_routes_reject_unauthenticated(self, client, method, path):
        r = await client.request(method, path, json={"content": "x"})
        assert r.status_code == 401

    async def test_wrong_password_rejected(self, client):
        r = await client.post("/admin/login", json={"password": "not-the-password"})
        assert r.status_code == 401
        assert "avatar_admin" not in r.cookies

    async def test_login_sets_httponly_cookie_and_grants_access(self, client):
        r = await client.post(
            "/admin/login", json={"password": os.environ["ADMIN_PASSWORD"]}
        )
        assert r.status_code == 200
        set_cookie = r.headers["set-cookie"]
        assert "avatar_admin=" in set_cookie
        assert "HttpOnly" in set_cookie
        r = await client.get("/admin/session")
        assert r.status_code == 200

    async def test_tampered_cookie_rejected(self, client):
        client.cookies.set("avatar_admin", "forged-token")
        r = await client.get("/admin/conversations")
        assert r.status_code == 401


class TestConfigEndpoint:
    async def test_config_returns_owner_name(self, client):
        r = await client.get("/api/config")
        assert r.status_code == 200
        assert r.json()["owner_name"] == os.environ["OWNER_NAME"]


class TestConversationFetch:
    async def test_empty_conversation(self, client, conversation_id):
        r = await client.get(f"/api/conversation/{conversation_id}")
        assert r.status_code == 200
        body = r.json()
        assert body["messages"] == []
        assert body["conversation_name"] is None

    async def test_after_id_returns_only_newer(self, client, conversation_id):
        first = db.insert_message(conversation_id, "visitor", "one", "T.T.")
        db.insert_message(conversation_id, "avatar", "two")
        r = await client.get(
            f"/api/conversation/{conversation_id}", params={"after_id": first["id"]}
        )
        msgs = r.json()["messages"]
        assert [m["content"] for m in msgs] == ["two"]

    async def test_name_derived_from_rows(self, client, conversation_id):
        db.insert_message(conversation_id, "visitor", "hello", "M.O.")
        r = await client.get(f"/api/conversation/{conversation_id}")
        assert r.json()["conversation_name"] == "M.O."


class TestInstantAnswer:
    async def test_q2_no_llm(self, client, conversation_id):
        """Qn returns the FAQ instantly; meta says instant; both rows persisted."""
        events = await collect_sse(
            client,
            {"conversation_id": conversation_id, "message": "Q2", "visitor_name": "T.T."},
        )
        names = [e for e, _ in events]
        assert names == ["visitor_message", "meta", "token", "done"]
        meta = json.loads(dict(events)["meta"])
        assert meta == {"mode": "instant", "faq_number": 2}
        token_text = json.loads([d for e, d in events if e == "token"][0])["text"]
        assert token_text.startswith("**Q2:**")
        rows = db.fetch_conversation(conversation_id)
        assert [r["role"] for r in rows] == ["visitor", "avatar"]
        assert rows[1]["content"] == token_text
        assert rows[1]["tool_calls"] == [{"tool": "instant_faq", "faq_number": 2}]

    async def test_out_of_range_qn_still_no_llm(self, client, conversation_id):
        events = await collect_sse(
            client, {"conversation_id": conversation_id, "message": "Q99"}
        )
        meta = json.loads(dict(events)["meta"])
        assert meta["mode"] == "instant"
        token_text = json.loads([d for e, d in events if e == "token"][0])["text"]
        assert "no FAQ number 99" in token_text


class TestAbuseGuards:
    async def test_rate_limit_429_before_any_write(self, client, conversation_id):
        from app import rate_limit

        for _ in range(20):
            assert rate_limit.allow(conversation_id)
        r = await client.post(
            "/api/chat",
            json={"conversation_id": conversation_id, "message": "hi"},
        )
        assert r.status_code == 429
        assert r.json() == {"error": "rate_limited"}
        assert db.fetch_conversation(conversation_id) == []

    async def test_long_message_truncated_stored(self, client, conversation_id):
        from app import config

        long_msg = "a" * 25_000
        events = await collect_sse(
            client, {"conversation_id": conversation_id, "message": long_msg + " Q2"}
        )
        # Not a Qn (long text), so agent mode — but we only check the stored visitor row
        stored = db.fetch_conversation(conversation_id)[0]
        assert stored["role"] == "visitor"
        assert len(stored["content"]) <= config.MAX_MESSAGE_CHARS + len(
            config.TRUNCATION_NOTE
        ) + 1
        assert stored["content"].endswith(config.TRUNCATION_NOTE)
        # the SSE visitor_message echoes the clamped text
        visitor_evt = json.loads(dict(events)["visitor_message"])
        assert visitor_evt["content"].endswith(config.TRUNCATION_NOTE)


class TestAdminFlows:
    async def test_open_thread_marks_read_and_clears_attention(
        self, admin_client, conversation_id
    ):
        db.insert_message(conversation_id, "visitor", "help me", "V.V.")
        db.insert_message(
            conversation_id, "avatar", "I pushed the human", needs_attention=True
        )
        r = await admin_client.get(f"/admin/conversations/{conversation_id}")
        assert r.status_code == 200
        msgs = r.json()["messages"]
        assert len(msgs) == 2
        assert all(m["read"] for m in msgs)
        assert all(not m["needs_attention"] for m in msgs)
        # verify persisted, not just the response
        rows = db.fetch_conversation(conversation_id)
        assert all(r["read"] and not r["needs_attention"] for r in rows)

    async def test_inbox_lists_conversation_with_states(
        self, admin_client, conversation_id
    ):
        db.insert_message(conversation_id, "visitor", "newest question", "I.B.")
        db.insert_message(
            conversation_id, "avatar", "pushed", needs_attention=True
        )
        r = await admin_client.get("/admin/conversations")
        assert r.status_code == 200
        entry = next(
            e for e in r.json() if e["conversation_id"] == conversation_id
        )
        assert entry["conversation_name"] == "I.B."
        assert entry["unread_count"] >= 1
        assert entry["needs_attention"] is True

    async def test_human_post_inserts_without_agent_reaction(
        self, admin_client, conversation_id
    ):
        db.insert_message(conversation_id, "visitor", "hello", "V.V.")
        r = await admin_client.post(
            f"/admin/conversations/{conversation_id}/messages",
            json={"content": "Hi, this is the real me."},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["role"] == "human"
        assert body["read"] is True
        rows = db.fetch_conversation(conversation_id)
        # exactly the visitor + human rows — no avatar reply was generated
        assert [row["role"] for row in rows] == ["visitor", "human"]

    async def test_resolve_clears_attention_only(self, admin_client, conversation_id):
        db.insert_message(
            conversation_id, "visitor", "urgent", "U.U.", needs_attention=True
        )
        r = await admin_client.post(
            f"/admin/conversations/{conversation_id}/resolve"
        )
        assert r.status_code == 200
        row = db.fetch_conversation(conversation_id)[0]
        assert row["needs_attention"] is False
        assert row["read"] is False  # resolve does NOT mark read


@pytest.mark.llm
class TestWithRealModel:
    async def test_agent_streams_reply(self, client, conversation_id):
        events = await collect_sse(
            client,
            {
                "conversation_id": conversation_id,
                "message": "In one short sentence, who are you?",
                "visitor_name": "T.T.",
            },
        )
        names = [e for e, _ in events]
        assert names[0] == "visitor_message"
        assert json.loads(dict(events)["meta"])["mode"] == "agent"
        assert names[-1] == "done"
        assert names.count("token") >= 1
        rows = db.fetch_conversation(conversation_id)
        assert [r["role"] for r in rows] == ["visitor", "avatar"]
        assert len(rows[1]["content"]) > 0

    async def test_human_message_visible_to_agent_next_turn(
        self, client, conversation_id
    ):
        """The human's admin post is in the transcript for the next visitor turn."""
        db.insert_message(conversation_id, "visitor", "Can I get a discount?", "D.D.")
        db.insert_message(
            conversation_id,
            "human",
            "Special for you: use code TWIN50 for 50% off.",
            read=True,
        )
        events = await collect_sse(
            client,
            {
                "conversation_id": conversation_id,
                "message": "What was that discount code again? Reply with just the code.",
            },
        )
        full_text = "".join(
            json.loads(d)["text"] for e, d in events if e == "token"
        )
        assert "TWIN50" in full_text
