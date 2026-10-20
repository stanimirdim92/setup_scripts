# VERIFY FAIL — LD-503

LD-503 fails verification on one REQ-017 scenario. A second finding, against REQ-009, needs a spec decision. All other requirements pass, except a few partial items listed below. The backend returns correct results in every case I ran.

## Failing behaviour

**D-1 · REQ-017, "Restored URL with conflicting keys" → back to `/build`**
- **Steps:** load `/filters?srch_instagram_account_status=not_detected&srch_instagram_followers_min=100`.
- **Expected:** the dropdown shows No Account Detected, the follower field is disabled at its default, and the request has no `srch_instagram_followers_min`.
- **Actual:** the screen is correct, but the first results request still sends `srch_instagram_followers_min=100`. The rows are correct only because the backend ignores that key (REQ-004). The stale key disappears after the user's first change.
- **Cause, confirmed in code:** `resources/js/utils/advertiser/advertiserFiltersPage.url.ts:350-357` reads the account status. Nothing removes that platform's other keys when the value is `not_detected`.
- **Fix:** remove the conflicting keys in `readFiltersFromURL`, or in the page's first request. Add a test at the page level.

**D-2 · REQ-009, "Open state" and "Selected state" → `/spec` decision**
- **Figma:** `2001:12004`: the open trigger has a dark focus border. `2001:20571`: the selected value is dark normal text, and the label is 14px.
- **Built:** the label is 12px; the selected value is 12px muted grey; the open trigger's border is the same as when it is closed.
- **Conflict:** DEC-006 accepts the `CustomSelect` style, but the scenario text asks for the Figma style.
- **Decision needed:** accept the current style and reword the scenario, or send a styling task to `/build`.

## Evidence per requirement
- **REQ-001 PASS**, **REQ-002 PASS**, **REQ-003 PASS**, **REQ-004 PASS**, **REQ-005 PASS**, **REQ-006 PASS**, **REQ-007 PASS**
- **REQ-008 PARTIAL:** the EXPLAIN and one-query tests pass. The 1.5× timing on a production-size replica was not measured. That is T008 / DEC-001 and goes to you.
- **REQ-009 PARTIAL:** see D-2.
- **REQ-010 PASS**, **REQ-011 PASS**, **REQ-012 PASS**, **REQ-013 PASS**, **REQ-014 PASS**
- **REQ-015 PARTIAL:** the empty state was checked in the browser. The API-error overlay is covered by vitest only.
- **REQ-016 PASS**
- **REQ-017 FAIL:** see D-1.

## Commands and results
- `composer test -- --compact --filter=AdvertiserSocialAccountStatus` → 44 passed (180 assertions).
- `yarn test` → 650 passed. `yarn tsc --noEmit` → clean. `yarn lint` → blocked: the module `eslint-typescript6` is missing.
- Mutation probes: 20 mutants, 16 killed, 3 equivalent survivors.

## Browser setup
- A disposable database `ld503_qa`, schema copied read-only, 11 test businesses, dropped afterwards. App served with `php -S` and environment overrides for that process only, at 1440×960 in EN and DE.

## Test-only commit
- `4fb1c048` on `worktree-LD-503`: one test file, +16 lines, REQ-004 for three platforms.

## Handoff
1. **`/build`:** fix D-1 and add a page-level test. That production fix makes this verdict void, so `/test` must run again.
2. **`/spec`:** decide D-2.
3. **You:** do T008 and post the screenshots to LD-506 if you want them there.

VERIFY FAIL — REQ-017 (D-1) → `/build`; REQ-009 trigger style vs Figma (D-2) → `/spec`.
