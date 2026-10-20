# BUILD BLOCKED — LD-503

Frontend tasks T004–T006 are done and merged. Backend T001 is stuck on a spec conflict, so T002, T003 and CP-001 have not run. You need to make two decisions.

## Decisions you need to make

1. **Spec conflict on REQ-001 (goes to `/spec`).** The spec requires HTTP 422 for an invalid account value. These routes return **HTTP 200** with an `errors` body instead. The cause is the shared `ValidationFailedOverride` trait, which returns 422 only for Inertia requests. I checked this in `Modules/Core/app/Concerns/ValidationFailedOverride.php`.
   - **My recommendation:** change REQ-001 to accept the existing 200 response. Every other key on index, search and export already behaves this way.
   - The alternative is to return 422 for the whole request. That changes a shared contract that the frontend may rely on.
2. **Schema snapshot drift.** The committed snapshot fingerprint (`61b4ec1f…`) no longer matches the local `leadbuster` DB (`066500a6…`). Until that is fixed, `composer test` refuses to run on any checkout. This blocks CP-001.
   - Should I refresh and commit it on `main`, or on this branch?

## Status per task

| Task | State |
| --- | --- |
| T001 | Blocked. The code is written but uncommitted in worktree `agent-a62c86f1d04bbf47b`. It passes 22 of 24 new tests; the 2 failures are the 422 checks, left as written. |
| T002, T003 | Not started; they depend on T001. |
| T004 | Done, `6981e5ff` |
| T005 | Done, `26c02884`. |
| T006 | Done, `f649fe6d`. No production change was needed. |
| CP-001 | Not run. |
| T007 | Goes to `/test` (Playwright browser checks). |
| T008 | Yours: replica timing, recorded in LD-504. |

## Verification

- **Frontend:** `yarn test` passed all 650 tests in 88 files. `tsc --noEmit` is clean.
- **Backend:** `composer test --filter=AdvertiserSocialAccountStatusFilterTest` gives 22 passed and 2 failed. phpstan and deptrac have not run.

## Branch state

- **Branch:** `worktree-LD-503`, fast-forwarded from `5ebff73d` to `f649fe6d`.
- **Spec pin:** `3e832161`, unchanged since the plan pinned it.
- **Working tree:** the only change is the untracked `docs/tasks/LD-503-open.md`.
