---
description: Dispatch execution for one or more planned tasks by workstream
argument-hint: "[task number(s) from docs/tasks/[TICKET]-todo.md, or a task description]"
---

Dispatch `executor` agents for implementation.

The executor owns incremental/TDD execution discipline.
`/build` owns implementation orchestration only.

## 1. Resolve before dispatching anything

Read `docs/tasks/[TICKET]-todo.md` and, when needed,
`docs/tasks/[TICKET]-plan.md`.

Resolve exactly which task(s) are in scope, including:

- acceptance criteria
- dependencies
- workstream
- likely file/area scope
- verification steps

If a task reference is ambiguous, resolve it before dispatching an executor.

Do not discover task scope inside a running executor.

### Workstream source of truth

Honor the workstream assignments produced by `/plan`.

Do not silently regroup planned tasks during `/build`.

If:

- a legacy or ad-hoc task has no workstream, infer one using the planning rules;
- a recorded workstream appears unsafe, contradictory, or inconsistent with
  task dependencies, stop and surface the discrepancy before dispatching.

`/plan` owns workstream classification. `/build` consumes and validates it.

## 2. Dispatch by workstream

Dispatch **one executor per workstream, not one executor per task**.

Tasks in the same workstream share implementation context and should reuse the
same executor whenever possible.

### Executor input contract

For every executor dispatch or resume provide:

- task
- acceptance criteria
- dependencies
- workstream
- expected scope
- verification
- `is_last_selected_task_in_workstream: yes|no`
- workstream verification command, when applicable
- task-local context pointers when useful:
  - applicable project/module rule files;
  - one or two closest precedent files;
  - shared contract or invariant the task must preserve.

### Context packet discipline

Give the executor the smallest packet that lets it start correctly.

Prefer pointers to authoritative files over pasted copies. Do not dump the full
spec, full plan, all project rules, another agent's transcript, or raw
investigation output into every executor. The executor can read a referenced
file when it actually needs it.

A task packet should answer:

> What outcome am I implementing, what proves it, what constrains it, and where
> is the closest trustworthy precedent?

### Within a workstream

- First selected task → dispatch a fresh, named `executor`.
- Subsequent selected tasks in the same workstream → resume that same executor
  by name or agent ID.
- Execute dependent tasks in dependency order.
- Do not spawn a fresh executor merely because the task number changed.

Reusing the executor preserves codebase context, prior file reads,
implementation decisions, and task-local knowledge instead of repaying
discovery cost for every task.

### Across workstreams

A genuinely independent workstream gets a separate executor.

For now, implementation executors run **sequentially**, even across independent
workstreams.

Multiple writing executors must never operate concurrently against the same git
checkout. `Edit`, `Write`, `Bash`, staging, and commits share mutable repository
state; non-overlapping source files do not eliminate working-tree or git-index
races.

Finish the active executor step before dispatching or resuming another
workstream.

### Future parallel execution

Independent, dependency-ready workstreams may run concurrently only when each
executor is isolated in its own git worktree/branch.

When parallel implementation is enabled:

- one active executor per worktree;
- one workstream per executor;
- only dependency-ready, genuinely independent workstreams may overlap;
- tasks inside one workstream remain sequential and reuse the same executor;
- never run multiple writing executors against the same checkout;
- integration remains sequential even when implementation is parallel.

Parallel execution does not imply parallel integration.

After parallel workstreams complete:

1. verify each workstream independently;
2. integrate completed workstreams one at a time in dependency order;
3. resolve integration conflicts before integrating the next workstream;
4. run affected tests after each integration;
5. run combined task/workstream verification after all selected workstreams are
   integrated.

If integration invalidates a completed workstream's assumptions, resume that
workstream's existing executor instead of spawning a fresh one when practical.

### Model tier

Use the executor's configured default model for routine implementation.

Override the model only when a workstream is architecturally ambiguous,
unusually high-risk, or an incorrect implementation decision would be expensive
to undo.

Keep model defaults in the executor definition; `/build` owns only the override
policy.

### Capability and permission discipline

Do not broaden an executor's tools or permissions merely for convenience.

If implementation genuinely requires a capability the executor does not have
—for example, secret access, an external writing, a destructive operation, or a
network integration requiring additional authority—surface that requirement at
the orchestration boundary instead of teaching the executor to work around the
restriction.

### Retry discipline

Do not use blind retries as progress.

A retry should follow new evidence: a code/configuration change, a changed
environmental condition, or a new hypothesis derived from the failure. If the
same failure persists and there is no new evidence or materially different
hypothesis, stop the loop and report the blocker rather than burning another
agent turn.

### Cost gate

Concurrency is a spend decision, not just a wall-clock decision.

Current implementation cap:

- writing executors: **1 active at a time**

If isolated parallel implementation is enabled later, start with a maximum of
**2 active implementation executors** unless the user explicitly requests a
higher cap.

## 3. Build completion gate

Before `/build` completes, ensure every selected task/workstream has completed
its executor-level verification.

For sequential execution, verify the resulting integrated checkout.

For future parallel execution, first integrate all selected workstreams and run
combined task/workstream verification.

`/build` is complete when:

- all selected tasks are implemented;
- all selected workstreams are integrated;
- executor-required verification is green;
- commits are complete;
- the working tree is in the expected clean state.

Then stop and report:

**BUILD COMPLETE**

Include:

- tasks completed
- workstreams completed
- commits created
- exact verification commands run and their outcomes
- anything noticed but not touched
- any remaining blocker

Also include a compact **Run metrics** block using actual values only:

- fresh executor dispatches
- executor resumes
- model-tier overrides
- verification failures that caused implementation rework
- human redirects/decisions during BUILD
- directly required scope expansions
- token/cost/duration only when the runtime exposes real measurements

Never estimate missing usage or timing data.

See `references/agent-run-metrics.md` for the measurement vocabulary. Do not
create a per-project metrics file unless that project already designates one or
the user asks for persistence.

Do not perform the independent VERIFY phase here.
Do not dispatch code reviewers here.
Do not issue GO/NO-GO here.

The next workflow stage is `/test`.
