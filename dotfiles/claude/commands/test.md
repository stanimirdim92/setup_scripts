---
description: Independently verify built work against acceptance criteria, regression risk, and the appropriate test levels
argument-hint: "[task number(s), ticket, commit range, or feature description]"
---

`/test` is the independent **VERIFY** gate after `/build`.

It does not replace the tests written during implementation. `/build` uses TDD
as developer feedback; `/test` independently checks whether the completed work
is actually correct and sufficiently covered. Dispatch `test-engineer` to do
that investigation — `/test` owns scope resolution and the
PASS/FAIL/BLOCKED verdict, not the file-by-file inspection itself.

## 0. Testing methodology

Invoke `skills/test-driven-development`. It owns the testing methodology this
gate uses:

- the Prove-It Pattern, for every defect this gate finds;
- test-level selection (Test Pyramid, test sizes);
- the good-test rules (state not interactions, DAMP over DRY, real
  implementations over mocks, arrange-act-assert, descriptive names);
- the anti-pattern list;
- its stack-discovery and verification discipline — repository-defined
  commands, never guessed generic ones.

Its RED-GREEN-REFACTOR loop and Iron Law ("no production code without a
failing test first") stay with `/build`'s executor. `/test` verifies work that
already exists; it must not become a second path that drives fresh production
code from tests. Where that implementation discipline and this gate's scope
conflict, this section wins.

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

`test-engineer` has no `Skill` tool (see `tools:` in its definition), so it
cannot invoke `test-driven-development` itself. When a packet depends on that
discipline, carry it as explicit constraints or a pointer to
`skills/test-driven-development/SKILL.md` — never as an instruction to invoke
the skill.

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

## 3. Test-change ownership

`/test` owns test-only changes needed to verify the selected scope.
`test-engineer` may add or correct tests, fixtures, and test configuration, but
must not modify production code.

When `/test` changes test files:

- run the relevant verification after the change;
- commit the test-only change separately with a clear `test:` commit message;
- report the commit and exact files changed;
- do not leave changes introduced by `/test` uncommitted when returning a final
  result.

If a new test exposes a production defect, preserve and commit the failing
reproduction test before returning the defect to `/build`. The failing commit is
intentional evidence for the BUILD handoff; `/build` owns the production fix and
restoring the affected verification to green.

Do not absorb a production fix into a "test-only" change. If a test requires a
production-code change to pass, that is a BUILD handoff.

## 4. Failure handling

If `test-engineer`'s report surfaces a production-code bug, apply the skill's
Prove-It Pattern up to the point of the fix:

1. preserve or add the failing reproduction test;
2. confirm it fails for the expected reason, not an incidental one;
3. report the production defect clearly;
4. return the fix to `/build`.

Steps 5 onward of the pattern (implement, confirm green, run the suite) belong
to `/build`, not here.

Do not turn `/test` into a second general implementation path.

After `/build` fixes the defect, rerun the affected verification.

If the failure is only in the test itself, fix the test, verify it, commit the
test-only correction, and continue.

If verification cannot reach a trustworthy product verdict because of an
environmental or capability problem, do not misreport it as a production
failure. Examples include unavailable credentials or services, a broken test
environment, missing required permissions, and unrelated pre-existing failures
that prevent the selected scope from being isolated. Report **VERIFY BLOCKED**
as described below.

## 5. Result

From `test-engineer`'s report, return one explicit verification result:

**VERIFY PASS**, **VERIFY FAIL**, or **VERIFY BLOCKED**

### VERIFY PASS

Requires:

- all acceptance criteria have verification evidence;
- required focused/regression checks pass;
- no known production defect remains in the verified scope;
- every test-only change introduced by `/test` is committed;
- the working tree is in the expected state, with no uncommitted change
  introduced by `/test`. Pre-existing unrelated changes must be identified, not
  silently included or cleaned up.

Report:

- acceptance criteria verified
- tests added or changed
- test-only commits created
- commands run and outcome
- relevant coverage gaps intentionally left out, if any
- final working-tree state

Then stop.

The next workflow stage is `/review`.

### VERIFY FAIL

Report:

- failing criterion or behavior
- reproduction/test evidence
- expected vs actual behavior
- exact handoff scope for `/build`
- failing reproduction commit
- final working-tree state

Do not proceed to `/review` until verification passes.

### VERIFY BLOCKED

Use this only when verification cannot produce trustworthy PASS/FAIL evidence
without an environmental change, additional authority, or resolution of an
unrelated pre-existing failure.

Report:

- the exact blocking condition;
- evidence that distinguishes it from a product defect;
- checks completed before the blocker;
- any test-only commits created;
- the smallest action or decision needed to unblock verification;
- final working-tree state.

Do not proceed to `/review`, and do not return the issue to `/build` unless the
blocker is itself caused by production code in the selected scope.
