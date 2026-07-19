# Phase 1 — Backend test plan

Run: `cd backend && uv run pytest -v` (48 tests; the two `llm`-marked tests make
real OpenRouter calls on `openai/gpt-5.4-nano`).

## Environment (`tests/test_supabase_connection.py`)
- [x] `.env` has a well-formed `SUPABASE_URL` and secret key
- [x] `messages` table reachable through the Data API
- [x] Insert/read/delete round-trip works with all expected columns

## Pure units (`tests/test_units.py`)
- [x] FAQ file loads; every row has `faq`, `question`, `answer`, `query`
- [x] `find_faq(n)` returns `**Qn:** {question}` + full answer
- [x] `find_faq` out-of-range returns a friendly miss (no crash)
- [x] `Qn` shortcut regex: `Q2`, `q2`, ` Q13 `, `Q02` match; `Q123`, `Q2 please`, prose, `q` don't
- [x] Truncation: >20,000 chars clamped with the SPEC note appended; ≤ limit untouched
- [x] Transcript builder: labelled roles in order, `Human (OWNER_NAME)` label, visitor-name line, task trailer
- [x] Rate limiter: 20 allowed then the 21st denied; other conversations unaffected
- [x] Session token round-trips; tampered token rejected
- [x] Required env vars present; knowledge.md + style.md load

## API (`tests/test_api.py`)
- [x] Every `/admin/*` route (session, inbox, thread, post, resolve) returns 401 unauthenticated
- [x] Wrong password → 401, no cookie; correct password → httpOnly cookie, routes open
- [x] Tampered session cookie → 401
- [x] `/api/config` returns the `OWNER_NAME` from env
- [x] Conversation fetch: empty, `after_id` incremental, name derived from rows
- [x] `Q2` instant path: SSE sequence `visitor_message → meta(instant) → token → done`, no LLM call, both rows persisted, `tool_calls` records `instant_faq`
- [x] Out-of-range `Q99`: still instant, no LLM call
- [x] Rate limit: 21st message in a minute → HTTP 429 before any DB write
- [x] Long message: stored AND streamed content is clamped with the note
- [x] Admin open-thread marks all rows read + clears `needs_attention` in one update…returning round trip (verified persisted)
- [x] Inbox lists conversations with name, unread count, needs_attention
- [x] Human post from admin inserts `role=human` and triggers NO avatar reply
- [x] Resolve clears `needs_attention` but not `read`
- [x] (llm) Real model: agent streams `meta(agent) → token* → done`, reply persisted
- [x] (llm) Real model: a human message posted from admin is honoured by the Avatar on the next visitor turn (discount-code recall test)

Result: **48/48 passed** (2026-07-18).

## Added features (2026-07-18, second pass) — tests/test_attention_and_search.py
- [x] attention=True: push fired, visitor row flagged + tool_calls recorded, SSE
      attention_push events, instant tag preserved on Qn; inbox surfaces the flag
- [x] attention absent: no flag, no tool_calls
- [x] inbox search_blob covers older messages, lowercased, capped

## Password management (2026-07-18) — tests/test_password.py
- [x] PBKDF2 hash round-trip; salted (two hashes differ); malformed stored value rejected
- [x] Change password: env password stops working, new works, pre-change session token dead
- [x] Change requires the correct current password (401 otherwise) and login (401 unauth)
- [x] Reset: wrong code 401, right code sets password + signs in, code single-use, expired rejected
