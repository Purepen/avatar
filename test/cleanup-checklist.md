# Final cleanup gate

Per SPEC.md §Testing: after testing completes, test artifacts must be removed.

- [x] All test conversation threads deleted from the Supabase `messages` table
      (pytest fixtures self-cleaned; Playwright module fixtures self-cleaned;
      remaining smoke-test thread deleted 2026-07-18). Two conversations from
      the owner's own manual browser trials ("tolu", "testet") were left for
      the owner to keep or clear.
- [x] `test/screenshots/` deleted
- [x] All checkboxes in the three phase plans checked off
- [x] Final visual pass: both screens verified great in dark + light, desktop +
      mobile (screenshots reviewed before deletion)

Result: **complete** (2026-07-18).
