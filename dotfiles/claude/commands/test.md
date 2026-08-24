---
description: Independently verify built work against acceptance criteria, regression risk, and the appropriate test levels
argument-hint: "[task number(s), ticket, commit range, or feature description]"
---

`/test` is the independent **VERIFY** gate after `/build`.

It does not replace the tests written during implementation. `/build` uses TDD
as developer feedback; `/test` independently checks whether the completed work
is actually correct and sufficiently covered. Dispatch `test-engineer` to do
that investigation — `/test` owns scope resolution and the PASS/FAIL verdict,
not the file-by-file inspection itself.

## 1. Resolve verification scope

Read the relevant task/spec context and determine:

- acceptance criteria
- implemented behavior
- risk areas
- tests already added by `/build`
- verification commands already run
- relevant regression surface

Resolve this from the task/spec/plan documents and `/build`'s own completion
report — not by re-reading the full implementation yourself. The detailed
inspection belongs to the dispatched `test-engineer` in step 2.

## 2. Dispatch test-engineer

Give `test-engineer` a bounded task packet: acceptance criteria, implemented
behavior and relevant regression surface, and tests/commands `/build` already
ran. Do not hand it the full spec or implementation plan — pointers, not the
whole document.

`test-engineer` already knows to test at the lowest level that captures the
behavior (its own "Test at the Right Level" rule) — `/test` doesn't need to
restate that here. It inspects the implementation and existing tests, proves
each acceptance criterion has verification evidence, adds missing tests
where needed, checks edge/error cases and regression-sensitive neighboring
behavior, and runs the repository's appropriate broader verification
(focused regression suite, integration/feature tests, E2E for critical
flows, build, type check, lint — using repository-defined commands, not
guessed generic ones). It reports back test coverage findings and
verification evidence; it does not decide the final verdict.

## 3. Failure handling

If `test-engineer`'s report surfaces a production-code bug:

1. preserve or add the failing reproduction test;
2. confirm it fails for the expected reason;
3. report the production defect clearly;
4. return the fix to `/build`.

Do not turn `/test` into a second general implementation path.

After `/build` fixes the defect, rerun the affected verification.

If the failure is only in the test itself, fix the test and continue.

## 4. Result

From `test-engineer`'s report, return one explicit verification result:

**VERIFY PASS** or **VERIFY FAIL**

### VERIFY PASS

Requires:

- all acceptance criteria have verification evidence;
- required focused/regression checks pass;
- no known production defect remains in the verified scope.

Report:

- acceptance criteria verified
- tests added or changed
- commands run and outcome
- relevant coverage gaps intentionally left out, if any

Then stop.

The next workflow stage is `/review`.

### VERIFY FAIL

Report:

- failing criterion or behavior
- reproduction/test evidence
- expected vs actual behavior
- exact handoff scope for `/build`

Do not proceed to `/review` until verification passes.
