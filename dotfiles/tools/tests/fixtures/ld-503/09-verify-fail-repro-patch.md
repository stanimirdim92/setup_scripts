# VERIFY FAIL — LD-503

The candidate fails one REQ-017 scenario: a restored URL with conflicting keys. I ran the reproduction myself and it fails on the candidate.

## Failing criterion: REQ-017, "Restored URL with conflicting keys"

**Reproduction in the browser** (test-engineer, disposable DB, app on `127.0.0.1:8765`, 1440×960):
- Load `/filters?srch_instagram_account_status=not_detected&srch_instagram_followers_min=100&...`.
- The UI is correct: Instagram shows No Account Detected and the follower field is locked at its default.
- The first search request still sends `srch_instagram_followers_min=100`, and the URL also keeps it.

**Expected vs actual:**
- **Expected (spec):** the request has no `srch_instagram_followers_min`.
- **Actual:** the request sends the key. The results are still correct (6 rows) because the backend ignores the key under `not_detected` (DEC-005).

**Repro test:** `/tmp/ld503-qa/repro-REQ017-first-request.patch` adds one vitest case to `Filters.states.test.tsx`. I applied it and ran it: 1 failed, 9 passed. I then reverted it.

**Handoff to `/build`:**
- Make the first request after URL restore match the reset state.
- Use the patch above as the failing test.
- If the owner accepts "the UI resets and the backend ignores the key", send it to `/spec` instead.

## REQ-009 findings for `/spec` (visual, DEC-006)
1. **Open trigger:** it has no focused border. Figma `2001:12004` shows a purple ring.
2. **Selected value:** it renders in the muted placeholder colour. Figma `2001:20571` shows dark "normal text".
3. **Sliders:** frames `2001:20571` and `2001:24939` show the range sliders greyed out under Account Detected. The implementation keeps them enabled, as REQ-017 requires. A designer should confirm.

## Per requirement
- REQ-001 to REQ-007: pass (E). REQ-008: partial (T008 not runnable here). REQ-009: partial (E, browser). REQ-010 to REQ-016: pass (E). **REQ-017: FAIL (E).**

## Test-only commit (not on the candidate branch)
- `7f835cb4` is on `worktree-agent-aadf625559fe91dbb` and carries `Refs: LD-503`. Two test files. `/build` can cherry-pick it with the fix.

## Candidate and tree state
- `worktree-LD-503` is unchanged: HEAD `80b5751f`, tree clean, base `cfa80c89`.

Next step: send the REQ-017 defect to `/build`, and the three REQ-009 findings to `/spec`. Then run `/test` again, because a production fix makes this result invalid.
