# VERIFY PASS test-only commits may advance the BUILD candidate

**Decision.** `/review` treats `BUILD COMPLETE` as the production-code baseline,
not as an immutable final commit set. The current candidate may differ from that
baseline only through passing test-only commits that `/test` declared in a
`VERIFY PASS` for the exact candidate under review.

`/review` verifies that every accepted post-BUILD commit contains only tests,
fixtures, or test configuration. Any production change, undeclared commit,
stale VERIFY result, or unexplained working-tree delta remains `REVIEW BLOCKED`.

When an exact `VERIFY PASS` already exists, REVIEW records independent
verification as `PASS` even if the trigger matrix would not have required it.
This covers both required verification and a user-requested `/test` run.

**Why.** [0035](0035-independent-verify-made-risk-triggered.md) made VERIFY
conditional but kept `/test`'s authority to create passing test-only commits.
The compacted `/review` prompt simultaneously rejected every candidate change
after `BUILD COMPLETE`. A successful `/test` that added coverage therefore
created a candidate `/review` was required to block, leaving no valid path back
into REVIEW.

This clarifies [0033](0033-canonical-disposition-and-scoped-commit-authority.md):
candidate integrity invalidates undeclared or production changes after BUILD,
but a declared passing test-only commit is the intended output of the VERIFY
gate, not an implementation mutation.

**Rejected — forbid `/test` from committing tests.** That would avoid the
identity transition by discarding useful passing coverage and would reverse the
scoped commit authority already assigned to VERIFY.

**Rejected — accept any post-BUILD change when VERIFY passes.** VERIFY does not
own production implementation. Allowing production changes would create a
second BUILD path and let code bypass the executor's implementation contract.

**Rejected — require another `/build` after a test-only commit.** BUILD did not
author or need to re-authorize the passing test delta. Re-running it would add
another orchestration cycle without improving candidate identity.
