# Implementation Plan: LD-333 — Localize date/datetime format based on customer locale

## Context

Leadbuster (Laravel 13) renders all dates/datetimes in the German dotted format
(`DD.MM.YYYY`) for every customer, regardless of locale — flagged by the Seattle Times
account seeing European dates in the Google Ads section. The spec (`LD-333-SPEC.md`,
committed on `claude/dorfiles-claude-setup-d9odgz` in `stanimirdim92/setup_scripts`, parked
there temporarily per your instruction — move it into the Leadbuster repo before
implementation) already resolved the product decisions: a locale → format map keyed off
`users.language` (`us`/`ca` → `MM/DD/YYYY`, `gb`/`en` fallback → `DD/MM/YYYY`,
`de`/unmapped → `DD.MM.YYYY`, with matching datetime variants — 12h AM/PM for `us`/`ca`,
24h for the rest), applied globally via `Carbon::serializeUsing()` in the existing
`Localization` middleware, no new DB column.

**This session has no Leadbuster repo attached** — only `stanimirdim92/setup_scripts`. You
chose "no preference" on attaching it now, so this plan keeps the codebase-dependent
unknowns as an explicit first task rather than guessing. Everything downstream of Task 1 is
marked "pending Task 1" where it depends on facts only the real repo can confirm.

## Architecture Decisions

- One global `DateLocaleFormat` helper (static pattern lookup) is the single source of
  truth for both date-only and datetime patterns — reused everywhere, per the spec.
- `Carbon::serializeUsing()` in `Localization::setupLocale()` is the one wiring point for
  every field returned as a raw Carbon instance — confirmed safe given classic PHP-FPM (no
  Octane), so no cross-request state-leak mitigation needed.
- Fields that are date-only (no time shown) can't be distinguished from datetime fields by
  the global hook alone — those need an explicit `->format(DateLocaleFormat::datePattern(...))`
  call at their serialization point. Which of the 5 named Ads fields are date-only vs
  datetime is unknown until Task 1.
- Single workstream (`ld-333-date-locale`) — every task shares the same subsystem
  (locale-driven formatting) and forms one dependency chain (helper → middleware wiring →
  per-field fixes → call-site sweep); none of it is independent enough to justify splitting
  across two `/build` executors per the `dispatching-parallel-agents` test.

## Task List

### Phase 0: Discovery (blocks everything else)

- [ ] **Task 1: Resolve the spec's open questions against the real codebase**
  - **Description:** Read-only investigation once the Leadbuster repo is available.
    Answers every unknown Task 2+ depends on.
  - **Acceptance criteria:**
    - Test framework and exact commands confirmed (Pest vs PHPUnit; build/lint too)
    - Exact file(s) that serialize the 5 named Ads fields (Active Since, Last Shown Ad,
      Last New Ad, Published, Last Shown) identified, and each classified date-only vs
      datetime
    - Confirmed whether a `Carbon::serializeUsing()` call already exists elsewhere (needs
      replacing, not duplicating)
    - Full inventory of explicit `->toDateTimeString()` / `->toDateString()` / hardcoded
      `->format('d.m.Y'...)` call sites app-wide (you mentioned you already have such
      fields)
    - Confirmed no external consumer (export, webhook, third-party integration) parses
      these API date fields expecting a fixed/ISO format
    - Module test-directory convention confirmed (`Modules/Core/Tests/...` vs root `tests/`)
  - **Verification:** answers written back into the spec (or a discovery note) with
    file:line references; no code changed in this task.
  - **Dependencies:** None
  - **Workstream:** ld-333-date-locale
  - **Files touched:** none (read-only)
  - **Estimated scope:** XS — but blocking

### Checkpoint: After Task 1
- [ ] All six open questions from `LD-333-SPEC.md` have concrete, sourced answers
- [ ] Review findings with human before writing any code — if the call-site inventory is
  large, re-slice Phase 3 below before proceeding (see Risks)

### Phase 1: Foundation

- [ ] **Task 2: Add `DateLocaleFormat` + unit tests**
  - **Description:** New class holding the confirmed locale → pattern map (date and
    datetime variants), per `LD-333-SPEC.md`'s Code Style section.
  - **Acceptance criteria:**
    - `datePattern(?string $locale)` and `datetimePattern(?string $locale)` static methods,
      covering `us`/`ca`/`gb`/`en`/`de` plus unmapped fallback to `de`
    - Unit tests cover every mapped locale + the fallback, for both methods
  - **Verification:** confirmed test command from Task 1 passes for the new test file
  - **Dependencies:** Task 1 (file path / test-directory convention)
  - **Workstream:** ld-333-date-locale
  - **Files touched:** new `DateLocaleFormat` class, new unit test file (paths pending Task 1)
  - **Estimated scope:** S (1-2 files)

### Phase 2: Global wiring

- [ ] **Task 3: Wire `Carbon::serializeUsing()` into `Localization::setupLocale()`**
  - **Description:** Add the `serializeUsing` call right after `$locale` is resolved,
    calling `DateLocaleFormat::datetimePattern($locale)` as the default. Remove/replace any
    pre-existing `serializeUsing` call Task 1 found instead of leaving two competing
    definitions.
  - **Acceptance criteria:**
    - Existing `Carbon::setLocale()`/`Date::setLocale()`/etc. calls untouched — this is a
      presentation-only change, not a translation change
    - A feature test hitting one representative endpoint as a `us`-locale user and a
      `de`-locale user gets back correctly formatted strings
  - **Verification:** feature test passes; manual smoke check on one endpoint
  - **Dependencies:** Task 2, Task 1 (existing-serializeUsing finding)
  - **Workstream:** ld-333-date-locale
  - **Files touched:** `Modules/Core/Http/Middleware/Localization.php`, one feature test
  - **Estimated scope:** S

### Checkpoint: After Task 3
- [ ] Global default format is locale-aware end-to-end for any field returned as a raw
      Carbon instance — confirm via the feature test, not just reading the diff

### Phase 3: The 5 named Ads fields

- [ ] **Task 4: Fix date-only fields among the 5 named Ads fields**
  - **Description:** For whichever of Active Since / Last Shown Ad / Last New Ad /
    Published / Last Shown Task 1 classified as date-only, add an explicit
    `->format(DateLocaleFormat::datePattern($locale))` call at its serialization point —
    the global hook alone defaults to the datetime pattern and would leave these wrong.
    Datetime-classified fields need no change here (already fixed by Task 3).
  - **Acceptance criteria:** every date-only field among the 5 renders per
    `LD-333-SPEC.md`'s Success Criteria table for both a `us` and a `de` test account
  - **Verification:** feature test per field (or one combined test), asserting exact
    strings; matches ticket AC (`08/02/2026` for US, `02.08.2026` for DE)
  - **Dependencies:** Task 1 (classification + exact file), Task 3
  - **Workstream:** ld-333-date-locale
  - **Files touched:** wherever these fields serialize (path pending Task 1) — likely 1
    Resource/Transformer class
  - **Estimated scope:** S–M, exact size pending Task 1

### Checkpoint: After Task 4
- [ ] Ads Overview, list view, and Ad Detail View all show consistent formatting for all 5
      named fields, for both a US and a DE test account — matches ticket AC directly

### Phase 4: Remaining explicit call sites

- [ ] **Task 5: Convert the explicit `toDateTimeString()`/hardcoded-format call sites**
  - **Description:** Using Task 1's inventory, convert each remaining explicit call to go
    through `DateLocaleFormat` instead of a fixed format. Per the spec's "ask first"
    boundary: confirm with you before changing any field not named in the ticket or spec.
  - **Acceptance criteria:** no remaining `toDateTimeString(`/`toDateString(`/hardcoded
    `format('d.m.Y'...)` call on any in-scope field; each conversion has a matching test
  - **Verification:** regression grep comes back clean on in-scope fields; new/updated
    tests pass
  - **Dependencies:** Task 1 (inventory), Task 2
  - **Workstream:** ld-333-date-locale
  - **Files touched:** unknown count until Task 1 — **if the inventory is large, this task
    should be re-sliced into one task per cluster of call sites rather than done as one
    large task** (see Risks)
  - **Estimated scope:** unknown — flag for re-planning if L/XL once Task 1 completes

### Phase 5: Blast-radius check

- [ ] **Task 6: Confirm no external consumer breaks**
  - **Description:** Lightweight verification that nothing outside Leadbuster's own
    frontend (exports, webhooks, third-party integrations) parses these API date fields
    expecting a fixed/ISO format — the global `serializeUsing` hook changes output for
    every Carbon field, not just the ones named in the ticket.
  - **Acceptance criteria:** either confirmed nothing depends on the old format, or any
    such consumer is explicitly called out and excluded/handled
  - **Verification:** manual review of integration/export code paths found via grep
  - **Dependencies:** Task 3
  - **Workstream:** ld-333-date-locale
  - **Estimated scope:** XS

### Checkpoint: Complete
- [ ] All `LD-333-SPEC.md` Success Criteria met
- [ ] Full test suite green
- [ ] Manual smoke check on Ads Overview/Detail as both a `us` and `de` test account
- [ ] Ready for review

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| No Leadbuster repo attached this session | High — blocks Task 1 onward | Attach the repo (or run `/build` in a session that has it) before starting; this plan is not executable as-is until then |
| Task 5's call-site inventory turns out large | Med — could balloon into an XL task | Task 1 must report the count; if more than ~5 files, re-slice Task 5 into per-cluster tasks before `/build` runs it |
| Date-only vs datetime split for the 5 named fields is unconfirmed | Med — Task 4 could be a no-op or a rewrite depending on the answer | Task 1 resolves this before Task 4 starts; don't guess |
| Global `serializeUsing` hook affects fields outside the ticket's stated scope | Low–Med — could silently change output an external consumer depends on | Task 6 checks this explicitly before calling the feature done |

## Open Questions

Carried from `LD-333-SPEC.md`, all resolved by Task 1:
1. Test framework/commands
2. Exact serialization file(s) + date-only vs datetime classification for the 5 named fields
3. Module/test-directory convention for the new class
4. Full inventory of explicit format call sites
5. External consumers of these date fields
6. Whether a `Carbon::serializeUsing()` call already exists elsewhere
