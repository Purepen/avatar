"""Phase-2 Playwright tests (test/frontend-playwright-tests.md).

Runs against the live app on http://127.0.0.1:8000 (uvicorn serving the built
frontend). Screenshots land in test/screenshots/. Conversations created here
are deleted in the module teardown.

Run: uv run pytest tests/test_frontend.py -v
"""

import os
import time
import uuid
from pathlib import Path

import pytest

from app import db

BASE = os.environ.get("AVATAR_BASE", "http://127.0.0.1:8000")
SHOTS = Path(__file__).resolve().parents[2] / "test" / "screenshots"
SHOTS.mkdir(parents=True, exist_ok=True)

DESKTOP = {"width": 1280, "height": 800}
MOBILE = {"width": 390, "height": 844}

_created: set[str] = set()


def track(page) -> None:
    """Remember the page's conversation id for cleanup."""
    cid = page.evaluate(
        "document.cookie.split('; ').find(r => r.startsWith('avatar_cid='))?.split('=')[1]"
    )
    if cid:
        _created.add(cid)


@pytest.fixture(scope="module", autouse=True)
def cleanup_conversations():
    yield
    client = db.get_client()
    for cid in _created:
        client.table("messages").delete().eq("conversation_id", cid).execute()


def suppress_tour(page) -> None:
    """Mark the browser as having seen the first-visit walkthrough."""
    page.context.add_cookies(
        [{"name": "avatar_tour", "value": "1", "url": BASE + "/"}]
    )


@pytest.fixture()
def visitor(page):
    page.set_viewport_size(DESKTOP)
    suppress_tour(page)
    page.goto(BASE + "/")
    page.wait_for_selector("#composerInput")
    # Mandatory-name gate: pre-fill so send() works for tests that aren't
    # specifically exercising the name gate itself; refocus the composer
    # afterwards so the "autofocus on load" assertion still holds.
    page.fill("#nameField", "T.T.")
    page.focus("#composerInput")
    yield page
    track(page)


def set_theme(page, theme: str) -> None:
    current = page.evaluate("document.documentElement.getAttribute('data-theme')")
    if current != theme:
        page.click("#themeToggle")


def send(page, text: str) -> None:
    page.fill("#composerInput", text)
    page.press("#composerInput", "Enter")


class TestVisitor:
    def test_first_visit_intro_focus_and_themes(self, visitor):
        page = visitor
        assert page.evaluate("document.activeElement?.id") == "composerInput"
        assert page.is_visible("#intro")
        assert page.locator(".chip").count() == 3
        assert page.evaluate(
            "document.documentElement.getAttribute('data-theme')"
        ) == "dark"
        page.screenshot(path=str(SHOTS / "visitor-first-dark-desktop.png"))
        set_theme(page, "light")
        page.screenshot(path=str(SHOTS / "visitor-first-light-desktop.png"))
        set_theme(page, "dark")
        page.set_viewport_size(MOBILE)
        page.screenshot(path=str(SHOTS / "visitor-first-dark-mobile.png"))

    def test_name_required_blocks_send(self, page):
        """No name/initials -> the message is not sent; the field shakes red
        and an inline instruction appears instead of a visitor bubble."""
        page.set_viewport_size(DESKTOP)
        suppress_tour(page)
        page.goto(BASE + "/")
        page.wait_for_selector("#composerInput")
        send(page, "Hello without a name")
        page.wait_for_selector(".sys-note", timeout=10_000)
        assert "name" in page.locator(".sys-note").inner_text().lower()
        assert page.locator(".msg--visitor").count() == 0
        assert "is-error" in (page.get_attribute(".name-field", "class") or "")
        page.screenshot(path=str(SHOTS / "visitor-name-required.png"))
        # filling the name and resending now works
        page.fill("#nameField", "Q.G.")
        send(page, "Q1")
        page.wait_for_selector(".msg--visitor", timeout=15_000)
        track(page)

    def test_reply_notice_visible(self, visitor):
        page = visitor
        assert page.is_visible("#replyNotice")
        assert len(page.locator("#replyNoticeText").inner_text()) > 0

    def test_q2_instant_answer(self, visitor):
        page = visitor
        send(page, "Q2")
        page.wait_for_selector(".msg--avatar .bubble strong", timeout=30_000)
        assert page.locator(".instant-tag").inner_text().lower() == "instant · q2"
        bubble = page.locator(".msg--avatar .bubble").inner_text()
        assert bubble.startswith("Q2:")
        assert page.is_hidden("#intro")
        # composer refocused after send
        assert page.evaluate("document.activeElement?.id") == "composerInput"
        page.screenshot(path=str(SHOTS / "visitor-q2-instant.png"))

    def test_deep_link_q2(self, page):
        page.set_viewport_size(DESKTOP)
        suppress_tour(page)
        page.goto(BASE + "/?q=2")
        page.wait_for_selector(".instant-tag", timeout=30_000)
        assert "?q=" not in page.url
        track(page)

    def test_shift_enter_newline_not_send(self, visitor):
        page = visitor
        page.fill("#composerInput", "line one")
        page.press("#composerInput", "Shift+Enter")
        page.type("#composerInput", "line two")
        assert page.locator(".msg--visitor").count() == 0
        assert "\n" in page.input_value("#composerInput")

    def test_keep_chat_restore_and_reset(self, visitor):
        page = visitor
        send(page, "Q1")
        page.wait_for_selector(".msg--avatar", timeout=30_000)
        # Wait for the send to fully finish (not just the bubble to appear)
        # before reloading, so the reply is actually persisted server-side —
        # reloading mid-stream races the in-flight write, same as a real user.
        page.wait_for_selector("#sendBtn:not([disabled])", timeout=30_000)
        track(page)
        page.reload()
        page.wait_for_selector(".msg--avatar", timeout=30_000)
        assert page.locator(".msg--visitor").count() == 1
        old_cid = page.evaluate(
            "document.cookie.split('; ').find(r => r.startsWith('avatar_cid='))?.split('=')[1]"
        )
        page.click("#resetBtn")
        assert page.is_visible("#intro")
        assert page.locator(".msg--visitor").count() == 0
        new_cid = page.evaluate(
            "document.cookie.split('; ').find(r => r.startsWith('avatar_cid='))?.split('=')[1]"
        )
        assert new_cid != old_cid

    @pytest.mark.llm
    def test_real_reply_streams(self, visitor):
        page = visitor
        send(page, "In one short sentence, who are you?")
        page.wait_for_selector(".msg--avatar .bubble p", timeout=120_000)
        # send button re-enables only when the stream fully completes
        page.wait_for_selector("#sendBtn:not([disabled])", timeout=120_000)
        text = page.locator(".msg--avatar .bubble").inner_text()
        assert len(text) > 10
        page.screenshot(path=str(SHOTS / "visitor-real-reply.png"))

    def test_human_message_arrives_via_poll(self, visitor):
        page = visitor
        send(page, "Q1")
        page.wait_for_selector(".msg--avatar", timeout=30_000)
        track(page)
        cid = page.evaluate(
            "document.cookie.split('; ').find(r => r.startsWith('avatar_cid='))?.split('=')[1]"
        )
        db.insert_message(cid, "human", "It's the real me — hello!", read=True)
        # 10s poll interval + real setup/network overhead under a full test
        # run needs more headroom than a bare 20s budget reliably gives —
        # generous on purpose, since every visitor test in this run fires a
        # real background Pushover call (new-conversation alert) that can
        # briefly contend for the same thread pool. Not a production
        # scenario: a single browser's 10s poll isn't racing anything there.
        page.wait_for_selector(".msg--human", timeout=45_000)
        assert "the human · live" in page.locator(".human-tag").inner_text().lower()
        page.screenshot(path=str(SHOTS / "visitor-human-moment.png"))
        set_theme(page, "light")
        page.screenshot(path=str(SHOTS / "visitor-human-moment-light.png"))
        set_theme(page, "dark")


class TestTourAndAttention:
    def test_tour_shows_once_for_new_browser(self, page):
        page.set_viewport_size(DESKTOP)
        page.goto(BASE + "/")  # no tour cookie — a brand-new browser
        page.wait_for_selector(".tour-overlay", timeout=15_000)
        page.screenshot(path=str(SHOTS / "visitor-tour-step1.png"))
        # walk all steps; the last click says Done and closes the tour
        for _ in range(10):
            if page.locator(".tour-overlay").count() == 0:
                break
            page.click("#tourNext")
        assert page.locator(".tour-overlay").count() == 0
        # cookie set — a reload must NOT re-show the tour
        page.reload()
        page.wait_for_selector("#composerInput")
        page.wait_for_timeout(500)
        assert page.locator(".tour-overlay").count() == 0
        track(page)

    def test_tour_skip_sets_cookie(self, page):
        page.set_viewport_size(DESKTOP)
        page.goto(BASE + "/")
        page.wait_for_selector(".tour-overlay", timeout=15_000)
        page.click("#tourSkip")
        assert page.locator(".tour-overlay").count() == 0
        cookies = {c["name"]: c["value"] for c in page.context.cookies()}
        assert cookies.get("avatar_tour") == "1"
        track(page)

    def test_attention_button_flow(self, visitor):
        page = visitor
        page.click("#attnBtn")
        assert "is-on" in (page.get_attribute("#attnBtn", "class") or "")
        page.screenshot(path=str(SHOTS / "visitor-attention-armed.png"))
        send(page, "Q1")
        page.wait_for_selector("#sendBtn:not([disabled])", timeout=60_000)
        # button reset immediately after the send
        assert "is-on" not in (page.get_attribute("#attnBtn", "class") or "")
        # the attention_push status line rendered
        assert page.locator(".tool-status", has_text="attention_push").count() >= 1
        cid = page.evaluate(
            "document.cookie.split('; ').find(r => r.startsWith('avatar_cid='))?.split('=')[1]"
        )
        rows = db.fetch_conversation(cid)
        assert rows[0]["needs_attention"] is True


class TestAdmin:
    def login(self, page):
        import os

        page.set_viewport_size(DESKTOP)
        page.goto(BASE + "/admin")
        page.wait_for_selector("#loginGate:not([hidden]), #dashboard:not([hidden])")
        if page.is_visible("#loginGate"):
            page.fill("#passwordInput", os.environ["ADMIN_PASSWORD"])
            page.click("#loginBtn")
            page.wait_for_selector("#dashboard:not([hidden])", timeout=15_000)

    def test_gate_and_wrong_password(self, page):
        page.set_viewport_size(DESKTOP)
        page.context.clear_cookies()
        page.goto(BASE + "/admin")
        page.wait_for_selector("#loginGate:not([hidden])")
        page.screenshot(path=str(SHOTS / "admin-gate-dark.png"))
        page.fill("#passwordInput", "wrong-password")
        page.click("#loginBtn")
        page.wait_for_selector("#loginError:not([hidden])", timeout=10_000)
        assert page.is_visible("#loginGate")

    def test_login_inbox_thread_reply_resolve(self, page):
        # Seed: a conversation with attention flag, via API + direct insert
        cid = str(uuid.uuid4())
        _created.add(cid)
        db.insert_message(cid, "visitor", "Can I reach the real you?", "P.W.")
        db.insert_message(
            cid, "avatar", "I've pinged the human for you.", needs_attention=True
        )

        self.login(page)
        page.wait_for_selector(".convo-item", timeout=15_000)
        page.screenshot(path=str(SHOTS / "admin-inbox-dark.png"))

        row = page.locator(".convo-item.is-attention", has_text="P.W.").first
        assert row.count() == 1
        row.click()
        page.wait_for_selector(".msg--visitor", timeout=15_000)
        # attention flag shown for this thread, badge cleared in the inbox
        assert page.is_visible("#attnFlag")
        page.wait_for_function(
            "() => ![...document.querySelectorAll('.convo-item.is-attention')]"
            ".some(el => el.textContent.includes('P.W.'))",
            timeout=10_000,
        )
        rows = db.fetch_conversation(cid)
        assert all(r["read"] and not r["needs_attention"] for r in rows)

        # reply as the human
        page.fill("#composerInput", "Hi — real me here. Email me anytime.")
        page.press("#composerInput", "Enter")
        page.wait_for_selector(".msg--human", timeout=15_000)
        assert "you · sent to visitor" in page.locator(".human-tag").inner_text().lower()
        page.screenshot(path=str(SHOTS / "admin-thread-dark.png"))
        set_theme(page, "light")
        page.screenshot(path=str(SHOTS / "admin-thread-light.png"))
        set_theme(page, "dark")

        # mark resolved (no-op now but exercises the endpoint)
        page.click("#resolveBtn")
        page.wait_for_function(
            "document.getElementById('attnFlag').hidden === true", timeout=10_000
        )

    def test_search_finds_older_messages(self, page):
        cid = str(uuid.uuid4())
        _created.add(cid)
        db.insert_message(cid, "visitor", "My xylophone budget is huge", "X.Y.")
        db.insert_message(cid, "avatar", "Noted!")
        db.insert_message(cid, "visitor", "thanks a lot")

        self.login(page)
        page.wait_for_selector(".convo-item", timeout=15_000)
        page.fill("#searchInput", "xylophone")
        page.wait_for_function(
            "document.querySelectorAll('.convo-item').length === 1", timeout=10_000
        )
        assert "X.Y." in page.locator(".convo-item").first.inner_text()

        # opening the thread highlights the matches and jumps to the first hit
        page.locator(".convo-item").first.click()
        page.wait_for_selector("mark.search-hit", timeout=15_000)
        hit = page.locator("#threadInner mark.search-hit").first
        assert hit.inner_text().lower() == "xylophone"
        page.screenshot(path=str(SHOTS / "admin-search-highlight.png"))
        # clearing the search re-renders the thread without marks
        page.fill("#searchInput", "")
        page.wait_for_function(
            "document.querySelectorAll('#threadInner mark.search-hit').length === 0",
            timeout=10_000,
        )

    def test_arrow_key_navigation(self, page):
        cid_a, cid_b = str(uuid.uuid4()), str(uuid.uuid4())
        _created.update([cid_a, cid_b])
        db.insert_message(cid_a, "visitor", "first conversation", "A.A.")
        time.sleep(1.1)
        db.insert_message(cid_b, "visitor", "second conversation", "B.B.")

        self.login(page)
        page.wait_for_selector(".convo-item", timeout=15_000)
        page.locator(".convo-item").first.click()
        page.wait_for_selector(".msg--visitor", timeout=15_000)
        first_name = page.locator("#threadName").inner_text()
        page.keyboard.press("ArrowDown")
        page.wait_for_function(
            f"document.getElementById('threadName').textContent !== {first_name!r}",
            timeout=15_000,
        )
        page.keyboard.press("ArrowUp")
        page.wait_for_function(
            f"document.getElementById('threadName').textContent === {first_name!r}",
            timeout=15_000,
        )

    def test_change_password_modal(self, page):
        self.login(page)
        page.click("#changePwBtn")
        page.wait_for_selector("#pwModal:not([hidden])")
        page.screenshot(path=str(SHOTS / "admin-change-password.png"))
        # mismatched new passwords surface an inline error, no request made
        page.fill("#pwCurrent", "anything")
        page.fill("#pwNew", "new-pass-123")
        page.fill("#pwConfirm", "different-123")
        page.click("#pwSave")
        page.wait_for_selector("#pwError:not([hidden])")
        assert "match" in page.locator("#pwError").inner_text()
        page.click("#pwCancel")
        assert page.is_hidden("#pwModal")

    def test_forgot_password_gate_swaps_card(self, page):
        page.set_viewport_size(DESKTOP)
        page.context.clear_cookies()
        page.goto(BASE + "/admin")
        page.wait_for_selector("#loginGate:not([hidden])")
        assert page.is_visible("#forgotBtn")
        # (not clicking through — a real click sends a live Pushover code and
        # consumes the 3/hour budget; the API flow is covered in test_password)

    def test_mute_and_block_buttons_toggle(self, page):
        cid = str(uuid.uuid4())
        _created.add(cid)
        db.insert_message(cid, "visitor", "toggle button test", "T.B.")

        self.login(page)
        page.locator(".convo-item", has_text="T.B.").first.click()
        page.wait_for_selector(".msg--visitor", timeout=15_000)

        assert "is-on" not in (page.get_attribute("#muteBtn", "class") or "")
        page.click("#muteBtn")
        page.wait_for_selector("#muteBtn.is-on", timeout=10_000)
        assert page.is_visible("#mutedFlag")
        # the toggle survives a re-render of the inbox row (mini-flag shown)
        assert page.locator(".convo-item", has_text="T.B.").locator(".mini-flag--indigo").count() == 1
        page.screenshot(path=str(SHOTS / "admin-muted-thread.png"))
        page.click("#muteBtn")
        page.wait_for_function(
            "!document.getElementById('muteBtn').classList.contains('is-on')", timeout=10_000
        )
        assert page.is_hidden("#mutedFlag")

        assert "is-on" not in (page.get_attribute("#blockBtn", "class") or "")
        page.click("#blockBtn")
        page.wait_for_selector("#blockBtn.is-on", timeout=10_000)
        assert page.is_visible("#blockedFlag")
        assert page.locator(".convo-item", has_text="T.B.").locator(".mini-flag--danger").count() == 1
        page.screenshot(path=str(SHOTS / "admin-blocked-thread.png"))
        page.click("#blockBtn")
        page.wait_for_function(
            "!document.getElementById('blockBtn').classList.contains('is-on')", timeout=10_000
        )
        assert page.is_hidden("#blockedFlag")

    def test_mobile_master_detail(self, page):
        cid = str(uuid.uuid4())
        _created.add(cid)
        db.insert_message(cid, "visitor", "mobile flow test", "M.M.")

        self.login(page)
        page.set_viewport_size(MOBILE)
        page.wait_for_selector(".convo-item", timeout=15_000)
        # inbox fills the screen; main hidden
        assert page.locator(".main").evaluate("el => getComputedStyle(el).display") == "none"
        page.screenshot(path=str(SHOTS / "admin-mobile-inbox.png"))
        page.locator(".convo-item", has_text="M.M.").first.click()
        page.wait_for_selector(".msg--visitor", timeout=15_000)
        assert page.locator(".sidebar").evaluate("el => getComputedStyle(el).display") == "none"
        page.screenshot(path=str(SHOTS / "admin-mobile-thread.png"))
        page.click("#backBtn")
        assert page.locator(".main").evaluate("el => getComputedStyle(el).display") == "none"
