---
description: Dispatch implementation for one or more planned tasks by workstream
argument-hint: "[task number(s) from docs/tasks/[TICKET]-todo.md, or a task description]"
---

Dispatch `executor` agents for implementation.

`/build` owns orchestration and integration. The executor owns implementation
discipline, tests, verification, and scoped local commits.

## 1. Resolve scope before dispatch

Resolve the target per `../references/target-selection.md`, and announce it ("Using: <target>") before anything else.

Read `docs/tasks/[TICKET]-todo.md` and the plan only as needed.

For each selected task resolve:

- outcome and acceptance criteria;
- dependencies;
- planned workstream;
- expected file/area scope;
- verification;
- required skills.

Honor `/plan`'s workstream assignment. For ad-hoc/legacy work with no assignment,
infer one using the same rules. Stop before dispatch when the recorded workstream
conflicts with dependencies, or when the task is ambiguous — meaning you cannot
state the expected observable behavior from the packet and plan without
inventing a decision. Report what is missing instead of guessing.

## 2. Dispatch by workstream

Use **one executor per workstream, not one per task**.

- first selected task in a workstream -> fresh named `executor`;
- later tasks in that workstream -> resume the same executor;
- tasks inside a workstream stay sequential and follow dependency order.

### Checkpoints gate dependency-readiness

Honor every checkpoint recorded in the plan. A task ordered after a checkpoint
is not dependency-ready until that checkpoint's criteria have been executed and
passed — run them at the boundary; do not take an upstream executor's task
completion as the checkpoint result. This applies with force to
contract-separated workstreams: never dispatch the downstream workstream before
its named contract checkpoint passes, even when executors are idle and the work
"could start."

### Executor packet

Send only what is needed to start correctly:

- task/outcome;
- acceptance criteria;
- dependencies;
- workstream;
- expected scope;
- verification;
- `required_skills`;
- `is_last_selected_task_in_workstream: yes|no`;
- workstream verification command when applicable;
- useful pointers to project/module rules, one or two precedents, and any shared
  contract/invariant.

Prefer pointers over pasted documents. Do not dump the full spec, plan, project
rules, investigation transcript, or another agent's output.

### Skills

Every fresh executor receives:

```text
required_skills:
  - executor-development-discipline
```

That baseline is preloaded by the executor definition. Do not paste or invoke it
again.

Add a task-specific skill only when its methodology is materially required.
Typical examples:

- shared/public API or contract -> `api-and-interface-design`;
- compatibility/deprecation/migration -> `deprecation-and-migration`;
- auth, permissions, secrets, or sensitive trust boundary ->
  `security-and-hardening`.

The executor invokes only additional skills selected by `/build`.

### Parallelism

Default to sequential execution for token efficiency.

Use at most **2 concurrent executors** only when independent,
dependency-ready workstreams justify the wall-clock tradeoff. Every concurrent
writer must use `isolation: worktree`; never run two writing agents against the
same checkout.

Parallel workstreams still integrate sequentially in dependency order. After
each integration run affected checks; after all integrations run the combined
selected-scope verification.

Parallelism buys elapsed time, not fewer tokens.

### Model and retry policy

Use the executor's configured default model for routine work. Override upward
only for high-risk work where a wrong decision is expensive to undo — e.g.
irreversible migrations, concurrency/consistency invariants, security-sensitive
boundaries, or novel external contracts.

Never blind-retry. A retry needs new evidence, a code/config/environment change,
or a materially different hypothesis.

Do not broaden tools, permissions, scope, or external write authority for
convenience. Surface a genuine capability boundary.

### Executor blockers and conflicts

When an executor reports a blocker or a task-packet conflict (acceptance
criteria infeasible against the repository, contradicted by the code, or
requiring an absent decision):

- stop that workstream at the blocked task; do not re-dispatch the same task
  hoping for a different reading;
- continue other workstreams only if they do not depend on the blocked task or
  a checkpoint behind it;
- a behavior conflict is a `SPEC CONFLICT` — route it to the human toward
  `/spec`; a plan-level defect (wrong dependency, wrong workstream, missing
  verification command) routes toward `/plan`;
- record the blocker in the completion report.

## 3. Completion

`/build` ends in exactly one of two reports.

**BUILD COMPLETE** — only when all of the following hold:

- all selected tasks are implemented;
- all selected workstreams are integrated;
- every plan checkpoint in the selected scope was executed and passed;
- executor-required verification is green;
- scoped local commits are complete;
- the tree is in the expected state.

**BUILD BLOCKED** — in every other terminal state. Never report BUILD COMPLETE
with open blockers, skipped checkpoints, or unimplemented selected tasks.

Both reports include:

- tasks/workstreams completed, and (for BUILD BLOCKED) tasks blocked or not
  started, each with its blocker and the stage it routes to (`/spec`, `/plan`,
  or human decision);
- checkpoints executed and their outcomes;
- commits created;
- exact verification commands and outcomes;
- directly required scope expansions;
- anything noticed but intentionally untouched;
- current branch/tree state;
- actual run metrics when exposed: fresh executor dispatches, resumes,
  model-tier overrides, verification failures causing rework, human redirects,
  and required scope expansions.

Never estimate unavailable token/cost/time data.

Do not dispatch independent verifiers or reviewers here. The next stage is
`/review`; `/review` decides whether the separate `/test` gate is required for
this candidate.
