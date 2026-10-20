# BUILD BLOCKED — LD-503

The build is blocked by two owner decisions. All other planned work is integrated and its checks pass. Plan and spec are both Approved, and the spec is identical to its pin `293bfa7c`, so no re-pin was needed.

## Blockers

1. **T003, the EXPLAIN criterion (REQ-008).** The criterion asks MySQL to read the pivot table by `PRIMARY`. MySQL reads `ix_afp_profile_advertiser` instead (`type: index`, not `ALL`). The Slack note covers only the phpstan findings, not this, so I did not re-dispatch T003. Decide one of these, then the route is `/plan` or `/spec`:
   - accept the plan MySQL uses;
   - change the subquery;
   - change the criterion.
2. **CP-001 fails on `composer test -- --compact`.** The result is 186 failed, 584 passed (exit 2). All LD-503 tests pass. The failures are in files LD-503 does not touch: missing snapshot columns, the `name_search` generated column, FK drop errors, a test-DB guard, and Auth/Brevo tests. I ran the two search-path tests with `main`'s production files, and they failed the same way (7 failed). I did not run the full suite on `main`. So the other failures are sorted by cause only; I have not proven they are baseline. Decide: accept this red baseline, or fix it first outside LD-503.

T007 (the browser check, run by `/test`) and T008 (replica timing, done by the developer) wait on CP-001.

## Commits

- `c0105764` LD-503: clear phpstan findings in the account status tests
- `686cdd04` LD-503: record the CP-001 run and its blockers (in `docs/tasks/LD-503-open.md`)

## Branch state

Branch `worktree-LD-503` is at HEAD `686cdd04`, and the tree is clean. Next step: the two owner decisions above, then `/build LD-503` again for T003, and `/test` for T007.
