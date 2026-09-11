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

Resolve the target per `../references/target-selection.md`, and announce it ("Using: <target>") before anything else.

Read the selected spec/plan and authoritative task packets from disk or the
plan's designated tracker. Require BUILD's complete message from one of the
valid sources in `../references/target-selection.md` §Gate handoffs. A fresh
session is valid when the user manually supplies that message. Check every
identity claim against git and available run evidence, not just its completion
label.

Before dispatch, record the selected scope, BUILD commit and any declared
uncommitted BUILD diff, current HEAD/tree, base revision, and any pre-existing
staged, unstaged, or untracked changes.
Reconcile differences from BUILD, accepting only declared passing test-only
changes; unexplained differences or changed production code block the pipeline
VERIFY gate. Check the plan's spec pin under `../references/plan-quality-gates.md`
§2 so verification uses the approved behavior for this candidate.

If BUILD evidence is missing, do not invent it or rerun implementation. An
explicitly requested standalone test investigation may still run against a
clearly identified target, but report its findings separately from pipeline
verification and return VERIFY BLOCKED for the missing BUILD evidence.

Resolve:

- acceptance criteria — pass the spec's enumerated `### Requirement:` /
  `#### Scenario:` list with its `REQ-###` ids, so coverage maps back
  requirement-by-requirement rather than file-by-file;
- implemented behavior;
- risk/regression surface;
- tests and commands `/build` already ran.

Prefer the handoff and pointers over re-reading the full implementation in the
main context. Detailed inspection belongs to the verifier.

If the candidate or intended scope cannot be determined, return **VERIFY
BLOCKED** rather than guessing.

## 2. Dispatch one test-engineer

Send `test-engineer` a bounded packet containing:

- candidate identity, baseline tree changes, and selected scope;
- acceptance criteria;
- implemented behavior;
- relevant regression risks;
- tests/commands already run;
- pointers to the changed code/tests when useful.

Include `required_skills`. Select `browser-testing-with-devtools` when an
in-scope claim depends on actual rendering, browser APIs, navigation, console,
or network behavior. The verifier invokes each selected skill before testing.
When a required browser capability is unavailable, return `VERIFY BLOCKED` for
that check; component tests cannot replace browser evidence.

Include relevant invariant and decision pointers. BUILD's results are prior
evidence, not the verifier's conclusion; the agent independently selects and
executes checks sufficient to establish the in-scope behavior.

Do not paste the full spec, plan, command methodology, or another agent's
transcript.

The verifier should:

- inspect the implementation and existing tests;
- prove each acceptance criterion has credible evidence;
- add missing test-only coverage when needed;
- check meaningful edge/error/regression cases;
- run the repository-defined focused and broader checks appropriate to the risk.
- run a repository-defined smoke check when the candidate changes a deployed
  runtime entrypoint or a critical end-to-end path. Do not invent a deployment
  target or mutate a shared environment to manufacture one.

## 3. Ownership

`/test` may create test-only changes: tests, fixtures, and test configuration.
It must not modify production code.

Passing test-only changes may be committed as a separate `test:` local commit.
No push, deploy, history rewrite, or unrelated change is authorized; local
tags are allowed but never pushed.

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

Before issuing PASS, reconcile the final tree with the recorded candidate:
only the declared, verified test-only changes may have been introduced.
Confirm the agent supplied executed evidence per requirement, not merely
recommended tests. Missing in-scope evidence cannot be labeled an intentional
coverage exclusion; obtain it or report why verification is blocked.

Report acceptance criteria verified **per `REQ-###`** — one line per
requirement in scope, with its evidence — plus tests changed, exact
commands/outcomes, test-only commits with their exact files, coverage gaps
intentionally left out, the BUILD candidate identity, and the resulting
branch/commits/diff/tree state. A requirement in scope with no evidence line is
a gap to report, not one to omit. Preserve evidence provenance in the summary:
inherited results and code reasoning must not become claims that the verifier
executed a check. Include their source/version and any remaining proof gap.

### VERIFY FAIL

Report the failing behavior/criterion with its `REQ-###`, reproduction evidence,
expected vs actual, and the exact handoff back to `/build`.

### VERIFY BLOCKED

Use when scope/candidate identity, missing handoff or required evidence,
environment, permissions, unavailable dependencies, or unrelated pre-existing
failures prevent trustworthy PASS/FAIL evidence. A reproduced production defect
is FAIL, not merely a coverage blocker; report any other blocked checks as well.

Report the blocker, checks completed, and the smallest action needed to unblock.

A production-code fix invalidates the previous VERIFY result and must go back
through `/build`.
