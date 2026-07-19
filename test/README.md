# Avatar — Test Program

Three test phases plus a final cleanup gate, per SPEC.md §Testing. Each plan is
a checkbox list, checked off as the tests are executed and pass.

| Phase | Plan | How it runs |
|---|---|---|
| 1 | [backend-unit-tests.md](backend-unit-tests.md) | `cd backend && uv run pytest` (in-process FastAPI; real Supabase; `-m llm` tests call the real model on `openai/gpt-5.4-nano`) |
| 2 | [frontend-playwright-tests.md](frontend-playwright-tests.md) | Playwright against the running app; screenshots in dark + light, desktop + mobile |
| 3 | [docker-e2e-tests.md](docker-e2e-tests.md) | Build the container with `scripts/start_pc.ps1` and smoke the full 3-way flow |
| — | [cleanup-checklist.md](cleanup-checklist.md) | Delete test conversations from Supabase and all screenshots |

Test conversations use random UUIDs and are removed either by the pytest
fixtures (phase 1) or by the cleanup checklist (phases 2–3).
