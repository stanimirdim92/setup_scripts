---
description: Independently verify built work when risk or explicit request warrants a separate verifier
argument-hint: "[task number(s), ticket, commit range, or feature description]"
---

`/test` is the optional independent **VERIFY** gate after `/build`.

`/build` already requires the implementing executor to test and verify its own
work. `/test` exists for a second, independent verification context when
`../references/verification-triggers.md` requires it or when the user explicitly
asks for it.

If `/test` is invoked for a low-risk change anyway, run it; do not refuse merely
because the trigger matrix would have allowed it to be skipped.

## 1. Resolve scope

Use the selected task/spec artifacts, the current branch/diff, and `/build`'s
completion handoff from the current conversation.

Resolve:

- acceptance criteria;
- implemented behavior;
- risk/regression surface;
- tests and commands `/build` already ran.

Prefer the handoff and pointers over re-reading the full implementation in the
main context. Detailed inspection belongs to the verifier.

If the candidate or intended scope cannot be determined, return **VERIFY
BLOCKED** rather than guessing.

## 2. Dispatch one test-engineer

Send `test-engineer` a bounded packet containing:

- acceptance criteria;
- implemented behavior;
- relevant regression risks;
- tests/commands already run;
- pointers to the changed code/tests when useful.

Do not paste the full spec, plan, command methodology, or another agent's
transcript.

The verifier should:

- inspect the implementation and existing tests;
- prove each acceptance criterion has credible evidence;
- add missing test-only coverage when needed;
- check meaningful edge/error/regression cases;
- run the repository-defined focused and broader checks appropriate to the risk.

## 3. Ownership

`/test` may create test-only changes: tests, fixtures, and test configuration.
It must not modify production code.

Passing test-only changes may be committed as a separate `test:` local commit.
No push, tag, deploy, history rewrite, or unrelated change is authorized.

If a new test proves a production defect:

1. preserve the reproduction as a patch/report artifact when useful;
2. restore only uncommitted test changes introduced by `/test`;
3. return the production fix to `/build`.

Do not turn `/test` into a second implementation path.

## 4. Result

Return exactly one result:

### VERIFY PASS

Requires all in-scope acceptance criteria to have credible evidence, required
checks to pass, no known production defect in scope, and any test-only changes
to be committed.

Report acceptance criteria verified, tests changed, exact commands/outcomes,
test-only commits with their exact files, coverage gaps intentionally left out,
the BUILD candidate identity, and the resulting branch/commits/diff/tree state.

### VERIFY FAIL

Report the failing behavior/criterion, reproduction evidence, expected vs actual,
and the exact handoff back to `/build`.

### VERIFY BLOCKED

Use only when environment, permissions, unavailable dependencies, or unrelated
pre-existing failures prevent trustworthy PASS/FAIL evidence.

Report the blocker, checks completed, and the smallest action needed to unblock.

A production-code fix invalidates the previous VERIFY result and must go back
through `/build`.
