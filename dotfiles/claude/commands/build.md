---
description: Dispatch implementation for one or more planned tasks by workstream
argument-hint: "[task number(s) from docs/tasks/[TICKET]-todo.md, or a task description]"
---

Dispatch `executor` agents for implementation.

`/build` owns orchestration and integration. The executor owns implementation
discipline, tests, verification, and scoped local commits.

## 1. Resolve scope before dispatch

Read `docs/tasks/[TICKET]-todo.md` and the plan only as needed.

For each selected task resolve:

- outcome and acceptance criteria;
- dependencies;
- planned workstream;
- expected file/area scope;
- verification;
- required skills.

Honor `/plan`'s workstream assignment. For ad-hoc/legacy work with no assignment,
infer one using the same rules. If the recorded workstream conflicts with
dependencies or the task is materially ambiguous, stop before dispatch.

## 2. Dispatch by workstream

Use **one executor per workstream, not one per task**.

- first selected task in a workstream -> fresh named `executor`;
- later tasks in that workstream -> resume the same executor;
- tasks inside a workstream stay sequential and follow dependency order.

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
only for materially ambiguous/high-risk work where a wrong decision is expensive
to undo.

Never blind-retry. A retry needs new evidence, a code/config/environment change,
or a materially different hypothesis.

Do not broaden tools, permissions, scope, or external write authority for
convenience. Surface a genuine capability boundary.

## 3. Completion

Before `/build` completes ensure:

- all selected tasks are implemented;
- all selected workstreams are integrated;
- executor-required verification is green;
- scoped local commits are complete;
- the tree is in the expected state.

Report **BUILD COMPLETE** with:

- tasks/workstreams completed;
- commits created;
- exact verification commands and outcomes;
- directly required scope expansions;
- anything noticed but intentionally untouched;
- blockers, if any;
- current branch/tree state;
- actual run metrics when exposed: fresh executor dispatches, resumes,
  model-tier overrides, verification failures causing rework, human redirects,
  and required scope expansions.

Never estimate unavailable token/cost/time data.

Do not dispatch independent verifiers or reviewers here. The next stage is
`/review`; `/review` decides whether the separate `/test` gate is required for
this candidate.
