# Todo: LD-333 — Localize date/datetime format based on customer locale

Workstream: `ld-333-date-locale` (single — see plan.md's Architecture Decisions)

- [ ] Task 1: Resolve the spec's open questions against the real codebase (discovery, read-only — **blocks all tasks below**)
- [ ] Task 2: Add `DateLocaleFormat` + unit tests
- [ ] Task 3: Wire `Carbon::serializeUsing()` into `Localization::setupLocale()`
- [ ] Task 4: Fix date-only fields among the 5 named Ads fields
- [ ] Task 5: Convert the explicit `toDateTimeString()`/hardcoded-format call sites
- [ ] Task 6: Confirm no external consumer breaks

Checkpoints: after Task 1 (discovery review — may re-slice Task 5), after Task 3 (global wiring verified end-to-end), after Task 4 (ticket AC met), final (all Success Criteria + full test suite).

Full detail, acceptance criteria, and verification steps per task: `tasks/plan.md`.
