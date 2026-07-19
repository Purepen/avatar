# Avatar — Project Roadmap

The living plan for Micheal Olaniyi's digital-twin platform. What's shipped, what's next, and ideas for later. Update this file as work progresses.

**Live site:** https://purepen.fly.dev · **Admin:** https://purepen.fly.dev/admin · Fly app `purepen` (region `lhr`), Supabase `eu-west-1`.

---

## Phase 1 — Core build (DONE, 2026-07-18)

- [x] **Backend** (FastAPI + OpenAI Agents SDK via OpenRouter): streaming chat over SSE with tool-status events, `Qn` instant FAQ answers (no LLM call), `?q=N` deep links, Pushover push tool, contact-capture flow, Supabase persistence, single-round-trip admin reads, signed httpOnly admin sessions, abuse guards (20k-char truncation + 20 msgs/min per conversation → HTTP 429)
- [x] **Frontend** (vanilla TypeScript + Vite, design-system tokens/components): visitor chat (keep-chat cookie, reset, theme toggle, autofocus rules, 10s→60s polling for human replies) and admin dashboard (inbox states, keyboard nav, mobile master/detail), dark + light, desktop + mobile
- [x] **Three-way conversation**: visitor ↔ avatar ↔ human; human replies from admin render as the indigo "live" bubble; avatar honours human messages next turn without reacting to them
- [x] **Docker**: multi-stage build, one container serving app + static UI; `scripts/start_pc.ps1|stop_pc.ps1|start_mac.sh|stop_mac.sh`
- [x] **Testing** (all plans in `test/`, all checked off): 56 backend pytest tests, 17 Playwright UI tests with screenshot review, Docker e2e phase (multi-visitor isolation, rate limit, logs), cleanup gate

## Phase 2 — Features beyond the SPEC (DONE, 2026-07-18)

- [x] **Attention button** (`.btn-attn`, added to the design system): visitor presses it → that message pings Micheal's phone directly via Pushover + flags "Needs you" in admin — no special wording needed
- [x] **First-visit walkthrough**: 6-step spotlight tour for new browsers (cookie-detected) covering name field, keep-chat, reset, theme, attention button, and Qn/FAQ shortcuts
- [x] **Admin search overhaul**: searches the full text of every conversation (not just previews), highlights matched words in the opened thread + sidebar, jumps to the first hit
- [x] **Admin password management**: change-password modal (rotates a PBKDF2 hash in the Supabase `settings` table, kills all other sessions — impersonation defence) and "Forgot password?" reset via a one-time 6-digit Pushover code. `.env` `ADMIN_PASSWORD` is the fallback; delete the `admin_auth` settings row to hard-reset

## Phase 3 — Personalization (DONE, 2026-07-19)

- [x] `knowledge/knowledge.md` rewritten for Micheal from the ai-portfolio project: bio, both current roles with real metrics, full career history, education (WorldQuant BASc ML, FUNAAB B.Sc Mathematics, FCE Osiele N.C.E), 18 certifications with credential links, projects, recommendations, links (phone numbers deliberately excluded for privacy)
- [x] `knowledge/style.md`: Ed's voice/structure kept, wrapped around Micheal — LinkedIn/GitHub/YouTube links, "Courses I've completed" section with credential links
- [x] `knowledge/faq.jsonl`: 20 questions in Micheal's voice (hire-me/rates/contact answers funnel into contact capture)
- [x] Frontend footer links → Micheal's LinkedIn + YouTube; avatar images already generated from Micheal's photo

## Phase 4 — Deployment (DONE, 2026-07-19)

- [x] fly.io app `purepen` in `lhr`, **scale-to-zero budget config** (`min_machines_running = 0`, shared-cpu-1x/1GB → expect well under $2/month; machine sleeps when idle, ~5s wake)
- [x] Secrets staged from `.env` (never in the image); smoke checks passed (health, pages, 401 gate, live streamed LLM reply)
- [x] Redeploy any time with `bash scripts/deploy.sh`

---

## Next up (near-term)

- [ ] **Put the project on GitHub.** The repo currently has NO git history (the template's git was removed). Do: `git init` → commit → push to a new GitHub repo. Double-check `.gitignore` covers `.env` before the first commit.
- [ ] **Strengthen credentials before sharing the link widely**: change the admin password via the new dashboard modal (current one is weak), and consider a longer random `SESSION_SECRET` in `.env` + re-run `deploy.sh`.
- [ ] **Owner walkthrough of admin on mobile**: log in from the phone, pin the tab; Pushover + mobile admin is the daily driver.
- [ ] **Verify the Pushover contact-capture loop once on production** (ask the twin to get in touch → check phone → reply from admin).
- [ ] **Watch first-week costs** in Fly dashboard → Billing → Usage, and OpenRouter usage page; confirm the scale-to-zero behaviour (machine shows `stopped` when idle).
- [ ] **Share smart links**: `https://purepen.fly.dev/?q=3` opens the chat and instantly answers "can I hire you" — great for LinkedIn posts / email signatures. Pick the `?q=N` links worth sharing.

## Soon (when ready)

- [ ] **Custom domain** (e.g. `avatar.<your-domain>` or `chat.purepen.dev`): buy/choose a domain, then `fly certs add` + a CNAME per DEPLOY.md §7. Also keeps the keep-chat cookie first-party if embedding.
- [ ] **Embed the twin in the AI portfolio site** (`C:\My files\Case_studies\ai-portfolio`, Next.js/Vercel): add a page or section with an `<iframe src="https://purepen.fly.dev">` — adapt `scripts/wordpress-embed.html` (the `?q=` passthrough logic works the same in a React component).
- [ ] **Refresh knowledge as things change**: new projects, new certs, new role → edit `knowledge/*.md|jsonl`, then `bash scripts/deploy.sh`. Treat the twin like a CV that must never go stale.
- [ ] **Record a YouTube demo** of the twin for @purepenworld2081 — it's itself a portfolio piece (multi-agent, SSE streaming, human-in-the-loop).

## Later / ideas

- [ ] **Production model upgrade**: switch `MODEL` to `openai/gpt-5.4-mini` (`fly secrets set -a purepen MODEL=openai/gpt-5.4-mini`) if nano's answer quality ever feels thin — costs more per message, still cheap at portfolio traffic.
- [ ] **Inbox at scale**: if conversations grow into the thousands, replace the Python-side inbox grouping with a Postgres view/RPC (API shape stays the same — noted in `backend/app/db.py`).
- [ ] **Scale up if traffic grows**: revert `fly.toml` to `min_machines_running = 1` + `shared-cpu-2x` (the always-on reference shape in DEPLOY.md); note the per-machine rate-limit caveat if running >1 machine.
- [ ] **Analytics**: lightweight visitor stats (conversations/day, FAQ hit counts, attention-button usage) — could be a small admin panel fed by the existing `messages` table.
- [ ] **Email digests**: a scheduled job that emails a daily summary of new conversations (needs an email service — none in the stack today; Pushover covers urgent pings).
- [ ] **Voice mode**: Micheal builds voice agents professionally — a talk-to-the-twin mode (Whisper in, TTS out) would be a flagship demo of exactly that skill.
- [ ] **Export/share conversation**: let a visitor email themselves the transcript (doubles as lead capture).

---

*Built with Claude Code from Ed Donner's Avatar SPEC. History: core build + extended features + full test program (2026-07-18); personalization + fly.io deployment (2026-07-19).*
