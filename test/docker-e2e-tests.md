# Phase 3 — Docker end-to-end test plan

Run: `./scripts/start_pc.ps1` (stops any existing `avatar` container, rebuilds
the image, runs it with the root `.env` on :8000).

- [x] Image builds clean (frontend build stage + backend uv stage)
- [x] Container starts; `GET /api/config` → 200 with the owner name (health path)
- [x] `/` serves the visitor UI with assets (icons, avatar images, fonts load)
- [x] `/admin` serves the dashboard gate
- [x] Real chat: a question streams a live LLM reply (OpenRouter, `gpt-5.4-nano`)
- [x] `Q2` instant answer works in-container
- [x] `?q=2` deep link works in-container
- [x] Admin login works; inbox lists the test conversation; thread opens
- [x] Human reply from admin reaches the visitor page via polling (3-way loop)
- [x] Contact-capture: visitor asks to get in touch → Pushover notification fires → "Needs you" badge in admin → opening clears it
- [x] Multiple visitors with distinct conversation_ids stay isolated (two browser contexts)
- [x] Rate limit returns 429 in-container (21 rapid messages)
- [x] Container logs show no errors during all of the above
- [x] `./scripts/stop_pc.ps1` stops and removes the container

Result: **all passed** (2026-07-18): 17/17 Playwright vs container, isolation + 429 verified, logs clean, stop/start scripts proven.
