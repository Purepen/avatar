"""Fast unit tests: no HTTP, no LLM. FAQ parsing, truncation, transcript,
rate limiter, auth token round-trip, config defaults."""

import pytest

from app import config
from app.routers.chat import _clamp
from app.tools.faq import FAQ_LOOKUP, FAQS, find_faq, parse_qn_shortcut
from app.transcript import build_task_prompt


class TestFaq:
    def test_faq_loaded(self):
        assert len(FAQS) > 10
        assert all({"faq", "question", "answer", "query"} <= set(f) for f in FAQS)

    def test_find_faq_returns_full_question_and_answer(self):
        faq = FAQS[1]
        text = find_faq(faq["faq"])
        assert text.startswith(f"**Q{faq['faq']}:** {faq['question']}")
        assert faq["answer"] in text

    def test_find_faq_out_of_range(self):
        text = find_faq(99)
        assert "no FAQ number 99" in text
        assert str(max(FAQ_LOOKUP)) in text

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("Q2", 2),
            ("q2", 2),
            (" Q13 ", 13),
            ("Q02", 2),
            ("Q123", None),  # three digits — not a shortcut
            ("Q2 please", None),
            ("What is Q2?", None),
            ("hello", None),
            ("q", None),
        ],
    )
    def test_parse_qn_shortcut(self, text, expected):
        assert parse_qn_shortcut(text) == expected


class TestClamp:
    def test_short_message_untouched(self):
        assert _clamp("hello") == "hello"

    def test_long_message_truncated_with_note(self):
        long = "x" * 25_000
        out = _clamp(long)
        assert out.startswith("x" * config.MAX_MESSAGE_CHARS)
        assert out.endswith(config.TRUNCATION_NOTE)
        assert len(out) <= config.MAX_MESSAGE_CHARS + len(config.TRUNCATION_NOTE) + 1

    def test_exact_limit_untouched(self):
        msg = "y" * config.MAX_MESSAGE_CHARS
        assert _clamp(msg) == msg


class TestTranscript:
    def test_labels_and_order(self):
        rows = [
            {"role": "visitor", "content": "hi there"},
            {"role": "avatar", "content": "hello!"},
            {"role": "human", "content": "I am here too"},
            {"role": "visitor", "content": "great"},
        ]
        prompt = build_task_prompt(rows, visitor_name="A.B.")
        assert "Visitor: hi there" in prompt
        assert "Avatar: hello!" in prompt
        assert f"Human ({config.OWNER_NAME}): I am here too" in prompt
        assert '"A.B."' in prompt
        assert prompt.index("hi there") < prompt.index("hello!") < prompt.index("great")
        assert prompt.rstrip().endswith("no role label prefix.")

    def test_no_visitor_name(self):
        prompt = build_task_prompt([{"role": "visitor", "content": "yo"}])
        assert "name/initials" not in prompt


class TestRateLimit:
    def test_twenty_allowed_then_denied(self):
        from app import rate_limit

        cid = "rate-limit-unit-test"
        results = [rate_limit.allow(cid) for _ in range(21)]
        assert all(results[:20])
        assert results[20] is False

    def test_other_conversation_unaffected(self):
        from app import rate_limit

        assert rate_limit.allow("a-different-conversation") is True


class TestAuth:
    def test_session_token_roundtrip(self):
        from app.auth import _serializer, create_session_token

        token = create_session_token()
        data = _serializer.loads(token, max_age=60)
        assert data["admin"] is True
        assert "v" in data  # auth version — bumped on password change

    def test_tampered_token_rejected(self):
        from itsdangerous import BadSignature

        from app.auth import _serializer, create_session_token

        token = create_session_token() + "x"
        with pytest.raises(BadSignature):
            _serializer.loads(token, max_age=60)


class TestConfig:
    def test_required_env_present(self):
        assert config.OPENROUTER_API_KEY
        assert config.ADMIN_PASSWORD
        assert config.SUPABASE_URL.startswith("https://")
        assert config.OWNER_NAME

    def test_knowledge_loaded(self):
        from app.knowledge_loader import KNOWLEDGE, STYLE

        assert len(KNOWLEDGE) > 200
        assert len(STYLE) > 100
