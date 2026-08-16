# Implementation Plan: LD-333 — Localize date/datetime format based on customer locale

## Context

Leadbuster (Laravel 13) renders all dates/datetimes in the German dotted format
(`DD.MM.YYYY`) for every customer, regardless of locale — flagged by the Seattle Times
account seeing European dates in the Google Ads section. The spec (`LD-333-SPEC.md`,
committed on `claude/dorfiles-claude-setup-d9odgz` in `stanimirdim92/setup_scripts`, parked
there temporarily per your instruction — move it into the Leadbuster repo before
implementation) resolved the product decisions: a locale → format map (`us`/`ca` →
`MM/DD/YYYY`, `gb`/fallback → `DD/MM/YYYY`, `de`/unmapped → `DD.MM.YYYY`, with matching
datetime variants — 12h AM/PM for `us`/`ca`, 24h for the rest), applied globally via
`Carbon::serializeUsing()` in the existing `Localization` middleware.

**Correction (post-push, before any implementation started):** the format was originally
going to key off `users.language`, assuming its values were country codes. You then found
ICI (a Canadian account) has `lang = en` in both `users` and `integrations` — `lang` drives
UI translation, not date-region formatting, and can't tell Canada apart from UK/US/generic
English. Fix: a new `integrations.date_locale` column, fully decoupled from `lang`. Account
level (`integrations`, not `users`) because the ticket's own AC says "**accounts** display
dates as..." and `users.integrationid` already relates users to that account entity. This
adds a migration task (Task 2 below) that didn't exist in the original plan.

**This session has no Leadbuster repo attached** — only `stanimirdim92/setup_scripts`. Task
1 (discovery) still gates everything else; the codebase-dependent unknowns stay explicit
rather than guessed at.

## Architecture Decisions

- New `integrations.date_locale` column (migration + one-time seed from Petya's ticket
  comment's account-code → country list) is the source of truth for date format — not
  `lang`/`language`, which stays untouched and keeps its existing translation-only role.
- One global `DateLocaleFormat` helper (static pattern lookup) is the single source of
  truth for both date-only and datetime patterns — keyed by `date_locale`, reused
  everywhere, per the spec.
- `Carbon::serializeUsing()` in `Localization::setupLocale()` is the one wiring point for
  every field returned as a raw Carbon instance — reads `date_locale` via
  `auth()?->user()?->integration?->date_locale`, confirmed safe given classic PHP-FPM (no
  Octane), so no cross-request state-leak mitigation needed.
- Fields that are date-only (no time shown) can't be distinguished from datetime fields by
  the global hook alone — those need an explicit `->format(DateLocaleFormat::datePattern(...))`
  call at their serialization point. Which of the 5 named Ads fields are date-only vs
  datetime is unknown until Task 1.
- Single workstream (`ld-333-date-locale`) — every task shares the same subsystem
  (locale-driven formatting) and forms one dependency chain (migration → helper →
  middleware wiring → per-field fixes → call-site sweep); none of it is independent enough
  to justify splitting across two `/build` executors per the `dispatching-parallel-agents`
  test.

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
    - Confirmed the actual `User` → `Integration` Eloquent relationship name, and existing
      migration-naming conventions in this repo
  - **Verification:** answers written back into the spec (or a discovery note) with
    file:line references; no code changed in this task.
  - **Dependencies:** None
  - **Workstream:** ld-333-date-locale
  - **Files touched:** none (read-only)
  - **Estimated scope:** XS — but blocking

### Checkpoint: After Task 1
- [ ] All open questions from `LD-333-SPEC.md` have concrete, sourced answers
- [ ] Review findings with human before writing any code — if the call-site inventory is
  large, re-slice Phase 4 below before proceeding (see Risks)

### Phase 1: Data foundation

- [ ] **Task 2: Migration — add and seed `integrations.date_locale`**
  - **Description:** New nullable string column on `integrations`, seeded via a one-time
    data migration from Petya's ticket-comment mapping (account codes → country: CGZ/CMH/
    DRM/FEM/PRN/UST/IRT/LVM/THL → `us`, ICI → `ca`, MHI/MHB → `gb`, everything else → `de`,
    or leave `null` to fall through to the default if this repo's convention prefers that
    over an explicit `de` seed — confirm with Task 1/human).
  - **Acceptance criteria:**
    - Migration adds `integrations.date_locale` (nullable string)
    - Seed data matches the account list from the ticket comment exactly
    - Existing `integrations.lang`/`users.language` untouched by the migration
  - **Verification:** migration runs clean on a fresh DB and against existing seed/test
    data; spot-check a couple of known accounts (e.g. ICI) end up with the right value
  - **Dependencies:** Task 1 (migration-naming convention, exact table/relationship names)
  - **Workstream:** ld-333-date-locale
  - **Files touched:** new migration file (path pending Task 1)
  - **Estimated scope:** S

### Phase 2: Format logic

- [ ] **Task 3: Add `DateLocaleFormat` + unit tests**
  - **Description:** New class holding the confirmed `date_locale` → pattern map (date and
    datetime variants), per `LD-333-SPEC.md`'s Code Style section.
  - **Acceptance criteria:**
    - `datePattern(?string $dateLocale)` and `datetimePattern(?string $dateLocale)` static
      methods, covering `us`/`ca`/`gb`/`de` plus null/unmapped fallback to `de`
    - Unit tests cover every mapped value + the fallback, for both methods
  - **Verification:** confirmed test command from Task 1 passes for the new test file
  - **Dependencies:** Task 1 (file path / test-directory convention)
  - **Workstream:** ld-333-date-locale
  - **Files touched:** new `DateLocaleFormat` class, new unit test file (paths pending Task 1)
  - **Estimated scope:** S (1-2 files)

### Phase 3: Global wiring

- [ ] **Task 4: Wire `Carbon::serializeUsing()` into `Localization::setupLocale()`**
  - **Description:** Add the `serializeUsing` call right after `$locale` (translation
    locale — untouched) is resolved, reading `$dateLocale` from
    `auth()?->user()?->integration?->date_locale` (relationship name confirmed by Task 1)
    and calling `DateLocaleFormat::datetimePattern($dateLocale)` as the default. Remove/
    replace any pre-existing `serializeUsing` call Task 1 found instead of leaving two
    competing definitions.
  - **Acceptance criteria:**
    - Existing `Carbon::setLocale()`/`Date::setLocale()`/etc. calls untouched — this is a
      presentation-only change, not a translation change
    - A feature test hitting one representative endpoint as a user on a `us`-account and a
      user on a `de`-account gets back correctly formatted strings
    - A feature test with two users of *different* `lang` under the *same* account gets
      back the *same* date format — proves this is account-level, not user-level
  - **Verification:** feature tests pass; manual smoke check on one endpoint
  - **Dependencies:** Task 2 (column exists), Task 3, Task 1 (existing-serializeUsing
    finding, relationship name)
  - **Workstream:** ld-333-date-locale
  - **Files touched:** `Modules/Core/Http/Middleware/Localization.php`, feature tests
  - **Estimated scope:** S

### Checkpoint: After Task 4
- [ ] Global default format is locale-aware end-to-end for any field returned as a raw
      Carbon instance, keyed by account not by user — confirm via the feature tests, not
      just reading the diff

### Phase 4: The 5 named Ads fields

- [ ] **Task 5: Fix date-only fields among the 5 named Ads fields**
  - **Description:** For whichever of Active Since / Last Shown Ad / Last New Ad /
    Published / Last Shown Task 1 classified as date-only, add an explicit
    `->format(DateLocaleFormat::datePattern($dateLocale))` call at its serialization point
    — the global hook alone defaults to the datetime pattern and would leave these wrong.
    Datetime-classified fields need no change here (already fixed by Task 4).
  - **Acceptance criteria:** every date-only field among the 5 renders per
    `LD-333-SPEC.md`'s Success Criteria table for both a `us`-account and a `de`-account
    test user
  - **Verification:** feature test per field (or one combined test), asserting exact
    strings; matches ticket AC (`08/02/2026` for US, `02.08.2026` for DE)
  - **Dependencies:** Task 1 (classification + exact file), Task 4
  - **Workstream:** ld-333-date-locale
  - **Files touched:** wherever these fields serialize (path pending Task 1) — likely 1
    Resource/Transformer class
  - **Estimated scope:** S–M, exact size pending Task 1

### Checkpoint: After Task 5
- [ ] Ads Overview, list view, and Ad Detail View all show consistent formatting for all 5
      named fields, for both a US-account and a DE-account test user — matches ticket AC
      directly

### Phase 5: Remaining explicit call sites

- [ ] **Task 6: Convert the explicit `toDateTimeString()`/hardcoded-format call sites**
  - **Description:** Using Task 1's inventory, convert each remaining explicit call to go
    through `DateLocaleFormat` instead of a fixed format. Per the spec's "ask first"
    boundary: confirm with you before changing any field not named in the ticket or spec.
  - **Acceptance criteria:** no remaining `toDateTimeString(`/`toDateString(`/hardcoded
    `format('d.m.Y'...)` call on any in-scope field; each conversion has a matching test
  - **Verification:** regression grep comes back clean on in-scope fields; new/updated
    tests pass
  - **Dependencies:** Task 1 (inventory), Task 3
  - **Workstream:** ld-333-date-locale
  - **Files touched:** unknown count until Task 1 — **if the inventory is large, this task
    should be re-sliced into one task per cluster of call sites rather than done as one
    large task** (see Risks)
  - **Estimated scope:** unknown — flag for re-planning if L/XL once Task 1 completes

### Phase 6: Blast-radius check

- [ ] **Task 7: Confirm no external consumer breaks**
  - **Description:** Lightweight verification that nothing outside Leadbuster's own
    frontend (exports, webhooks, third-party integrations) parses these API date fields
    expecting a fixed/ISO format — the global `serializeUsing` hook changes output for
    every Carbon field, not just the ones named in the ticket.
  - **Acceptance criteria:** either confirmed nothing depends on the old format, or any
    such consumer is explicitly called out and excluded/handled
  - **Verification:** manual review of integration/export code paths found via grep
  - **Dependencies:** Task 4
  - **Workstream:** ld-333-date-locale
  - **Estimated scope:** XS

### Checkpoint: Complete
- [ ] All `LD-333-SPEC.md` Success Criteria met
- [ ] Full test suite green
- [ ] Manual smoke check on Ads Overview/Detail as both a US-account and DE-account test user
- [ ] Ready for review

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| No Leadbuster repo attached this session | High — blocks Task 1 onward | Attach the repo (or run `/build` in a session that has it) before starting; this plan is not executable as-is until then |
| Task 6's call-site inventory turns out large | Med — could balloon into an XL task | Task 1 must report the count; if more than ~5 files, re-slice Task 6 into per-cluster tasks before `/build` runs it |
| Date-only vs datetime split for the 5 named fields is unconfirmed | Med — Task 5 could be a no-op or a rewrite depending on the answer | Task 1 resolves this before Task 5 starts; don't guess |
| Global `serializeUsing` hook affects fields outside the ticket's stated scope | Low–Med — could silently change output an external consumer depends on | Task 7 checks this explicitly before calling the feature done |
| Migration seed data (Task 2) drifts from reality — other accounts besides the ones Petya listed may need a non-`de` value | Med — silently wrong format for an unlisted account | Confirm with human/product whether the ticket comment's list is exhaustive before seeding; unmapped defaults to `de` either way, matching "the rest are German" |

## Open Questions

Carried from `LD-333-SPEC.md`, all resolved by Task 1:
1. Test framework/commands
2. Exact serialization file(s) + date-only vs datetime classification for the 5 named fields
3. Module/test-directory convention for the new class
4. Full inventory of explicit format call sites
5. External consumers of these date fields
6. Whether a `Carbon::serializeUsing()` call already exists elsewhere
7. Actual `User` → `Integration` relationship name and nullability handling
8. Migration/column naming convention (`date_locale` vs alternatives)
9. Whether resolving `date_locale` per-request needs eager-loading/caching to avoid an
   extra query in the `Localization` middleware
