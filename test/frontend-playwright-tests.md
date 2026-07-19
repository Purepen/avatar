# Phase 2 — Frontend Playwright test plan

Run: `cd backend && uv run pytest tests/test_frontend.py -v` against the running
app (uvicorn on :8000 serving the built frontend). Screenshots go to
`test/screenshots/` (deleted at cleanup).

## Visitor page — states matrix (docs/ux-flows.md)
- [x] First visit: intro hero + suggestion chips, composer **autofocused**, dark theme default
- [x] Dark + light screenshots, desktop (1280×800) + mobile (390×844)
- [x] Sending renders the visitor bubble (initials token, right-aligned) and clears + **re-focuses** the composer
- [x] Avatar reply streams: typing dots → tokens; tool-status line appears for tool calls and collapses to done-state
- [x] `Q2` → instant answer, `instant · Q2` tag, no model call
- [x] `?q=2` deep link auto-submits Q2 and strips the param from the URL
- [x] Suggestion chip click submits immediately
- [x] `Enter` sends, `Shift+Enter` makes a newline
- [x] Keep chat ON: reload restores the thread from the cookie
- [x] Reset: clears the view, new conversation_id, old thread stays in DB
- [x] Human message arrives via polling as the human bubble (photo, indigo ring, name-free "live" tag)
- [x] Rate-limit (21st message): friendly slow-down note (UI path; 429 exercised against the container in phase 3)
- [x] Theme toggle persists via localStorage

## Admin page
- [x] Logged-out gate renders (dark + light screenshots); wrong password shows error
- [x] Correct password opens the dashboard; session survives reload
- [x] Inbox: conversations most-recent first; unread dot; amber "Needs you" badge; active row highlight
- [x] Opening a thread clears unread + needs-attention (badge disappears)
- [x] Thread shows all three roles with correct identity (initials / robot+green / photo+indigo)
- [x] Admin reply appears in thread; visitor receives it via poll
- [x] "Mark resolved" clears the attention flag without a reply
- [x] `ArrowUp`/`ArrowDown` move between conversations
- [x] `Enter` sends, `Shift+Enter` newline in the admin composer
- [x] Mobile (390×844): master/detail — inbox fills screen, tapping opens thread, back control returns
- [x] Dark + light screenshots of the authed dashboard

## Cross-cutting
- [x] No gradients in chrome, no emoji, amber/red only as badges (visual review of screenshots)
- [x] Rings background texture renders on the visitor page
- [x] Links in replies are clickable markdown links

Result: **11/11 passed** (2026-07-18), screenshots in test/screenshots/.

## Added features (2026-07-18, second pass)
- [x] First-visit walkthrough: shows for a new browser (no cookie), 6 spotlight steps
      (name, keep chat, reset, theme, attention button, Qn/FAQ), Done/Skip both set the
      cookie, no re-show on reload
- [x] Attention toggle: neutral by default, amber when pressed, resets right after send;
      message flagged needs_attention; real Pushover fired; attention_push status line renders
- [x] Admin search reaches every message in a thread (search_blob), not just the preview
- [x] Search term highlighted in thread + previews, jumps to first hit, clears with search
- [x] Change-password modal opens from appbar, mismatch error inline, cancel closes
- [x] "Forgot password?" visible on the login gate (flow covered at API level)
