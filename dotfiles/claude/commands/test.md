---
description: Independently verify built work against acceptance criteria, regression risk, and the appropriate test levels
argument-hint: "[task number(s), ticket, commit range, or feature description]"
---

Invoke `skills/test-driven-development` for test-quality and test-level
discipline.

`/test` is the independent **VERIFY** gate after `/build`.

It does not replace the tests written during implementation. `/build` uses TDD
as developer feedback; `/test` independently checks whether the completed work
is actually correct and sufficiently covered.

## 1. Resolve verification scope

Read the relevant task/spec context and determine:

- acceptance criteria
- implemented behavior
- risk areas
- tests already added by `/build`
- verification commands already run
- relevant regression surface

Inspect the implementation and existing tests before adding new verification.

## 2. Verify at the right level

Use the lowest test level that proves the behavior with sufficient confidence:

```text
Pure logic, no I/O          → Unit
Crosses a boundary          → Integration / feature
Critical user flow          → E2E
```

Do not add E2E coverage when a lower-level test proves the same behavior.

Do not duplicate tests that already prove the acceptance criterion.

## 3. Verify the acceptance criteria

For every applicable acceptance criterion:

- identify the test or verification that proves it;
- run that verification;
- add missing tests when the current suite does not adequately prove it;
- check important edge/error cases;
- check regression-sensitive neighboring behavior.

Also run the repository's appropriate broader verification for the changed
surface, such as:

- focused regression suite
- integration/feature tests
- E2E for critical user flows
- build
- type check
- lint

Use repository-defined commands. Do not guess generic commands when the project
already defines them.

## 4. Failure handling

If verification exposes a production-code bug:

1. preserve or add the failing reproduction test;
2. confirm it fails for the expected reason;
3. report the production defect clearly;
4. return the fix to `/build`.

Do not turn `/test` into a second general implementation path.

After `/build` fixes the defect, rerun the affected verification.

If the failure is only in the test itself, fix the test and continue.

## 5. Result

Return one explicit verification result:

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
