# BUILD BLOCKED: LD-503

The backend filter is built and tested, but T003 is blocked. The `EXPLAIN` acceptance criterion for REQ-008 fails as written. The plan says to stop and report in this case, so I did not weaken the assertion or add an index.

## The blocker: T003 `EXPLAIN` criterion (REQ-008)

The criterion expects MySQL to read `facebook_profiles_advertisers` by its `PRIMARY` key for `srch_facebook_account_status=not_detected`.

What MySQL actually does:
- It runs the `NOT EXISTS` as a materialised anti-join.
- It reads the pivot with a full covering index scan on `ix_afp_profile_advertiser` (`type: index`). This is not `PRIMARY`, and it is not an `ALL` scan.
- The plan was the same with 300 advertisers and with 3,001 advertisers.

**Decision needed (routes to `/spec`, then `/plan`). My recommendation is option 1:**
1. Accept this plan. Amend the criterion to "no `ALL` scan; the pivot is read through an index". Let T008, the replica timing against the DEC-001 1.5× budget, decide performance.
2. Change the subquery shape, for example with an optimizer hint or a `LEFT JOIN … IS NULL`. This changes TD-001 and the shared subquery helper.

## Tasks

| Task | Status | Commit |
| --- | --- | --- |
| T001 | Done | `2058bdcd` |
| T002 | Done (tests only; T001 code already met every criterion) | `8fb178ad` |
| T003 | Blocked: 6 of 7 criteria proven and committed; `EXPLAIN` is not. Status stays `Pending`. | `84c5fb4a` |
| T004–T006 | Already Done before this run | — |
| T007, T008 | Not selected. T007 is the `/test` Playwright check; T008 is a developer replica timing. Both wait on CP-001. | — |

**Checkpoint CP-001 did not run.** T003 is not Done, so I did not run the full integrated suite.

## Verification

- `bin/worktree-test.sh --compact --filter=AdvertiserSocialAccount`: 40 passed (152 assertions).
- `vendor/bin/phpstan analyse`: 8 new `staticMethod.dynamicCall` findings. They use the same `$query->whereExists(...)` call as the existing code around them. Strictly, they fail the CP-001 item "no new findings". Please confirm you accept them.

## Candidate

- Repo: `/var/www/html/leadbuster/.claude/worktrees/LD-503`, branch `worktree-LD-503`
- Commits `453f5fa9..84c5fb4a`, HEAD `84c5fb4a`; the working tree is clean
- Spec pinned at `293bfa7c`, unchanged since the pin, so the plan was current.

**Next step:** decide on the `EXPLAIN` criterion. Then rerun `/build LD-503` to finish T003 and run CP-001.
