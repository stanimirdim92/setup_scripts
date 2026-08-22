---
description: Dispatch execution for one or more planned tasks, then fan out review and merge a go/no-go verdict
argument-hint: "[task number(s) from docs/tasks/[TICKET]-todo.md, or a task description]"
---


Dispatch `executor` agents for implementation.
The executor owns incremental/TDD execution discipline;
`/build` owns orchestration only.

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

### Within a workstream

- First selected task → dispatch a fresh, named `executor`.
- Subsequent selected tasks in the same workstream → resume that same executor
  by name or agent ID.
- Execute dependent tasks in dependency order.
- Do not spawn a fresh executor merely because the task number changed.

Reusing the executor preserves codebase context, prior file reads, implementation
decisions, and task-local knowledge instead of repaying discovery cost for every
task.

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
5. run combined verification after all selected workstreams are integrated.

If integration invalidates a completed workstream's assumptions, resume that
workstream's existing executor instead of spawning a fresh one when practical.

### Model tier

Use the executor's configured default model for routine implementation.

Override the model only when a workstream is architecturally ambiguous, unusually
high-risk, or an incorrect implementation decision would be expensive to undo.

Keep model defaults in the executor definition; `/build` owns only the override
policy.

### Cost gate

Concurrency is a spend decision, not just a wall-clock decision.

Current implementation cap:

- writing executors: **1 active at a time**
- reviewers: **maximum 2 active at a time**

If isolated parallel implementation is enabled later, start with a maximum of
**2 active implementation executors** unless the user explicitly requests a
higher cap.

## 3. Verify executor results before review

Before reviewer fan-out, ensure every selected task/workstream has completed its
task-level verification.

For sequential execution, review the resulting integrated checkout.

For future parallel execution, do not issue a final verdict from isolated
worktree results alone. First integrate all selected workstreams and run combined
verification.

No final GO is possible until:

- all selected workstreams are integrated;
- combined verification passes;
- reviewers evaluate the integrated result.

## 4. Fan out review independently

Once implementation is integrated and verified, review the resulting diff.

Trigger conditions live in:

`references/reviewer-triggers.md`

Read that file before deciding which reviewers run.

`/review` uses the same trigger source. Do not duplicate reviewer-trigger logic
inside `/build`.

### Reviewer concurrency

Never run more than **2 reviewers concurrently**.

If 3 or more reviewer triggers match:

1. dispatch up to 2;
2. wait for both;
3. dispatch the next batch.

A high-risk diff earns more review perspectives, not unlimited concurrency.

### Reviewer context

Give each reviewer:

- the integrated diff;
- a one-line goal;
- the relevant task acceptance criteria.

Do **not** give reviewers:

- the full spec unless specifically necessary;
- the full implementation plan;
- other reviewers' findings.

Reviewers should form independent judgments without unnecessary context or
anchoring.

## 5. Report findings without reranking

Report each reviewer's findings under its own heading.

Examples:

- Correctness / Readability / Architecture / Security / Performance from
  `code-reviewer`
- security findings from `security-auditor`
- cross-boundary reliability findings from
  `distributed-systems-reviewer`

Do not blend all findings into one newly ranked list.

Keeping review axes separate prevents one reviewer's silence from being mistaken
for another reviewer's clearance and prevents a loud category from burying a
quieter but important finding.

## 6. Verdict

State one explicit verdict:

**GO** or **NO-GO**

Rules:

- Any Critical finding from any reviewer → default **NO-GO**.
- No Critical findings, but Required/Important findings remain → decide whether
  they block the selected scope and state what remains outstanding.
- Clean across all reviewers that ran → **GO**.

A **GO** requires:

- selected implementation complete;
- selected workstreams integrated;
- combined verification green;
- review completed against the integrated diff.

On **NO-GO**, list exactly what must change.

For fixes:

- resume the relevant existing executor/workstream when the fix belongs to its
  context;
- dispatch a fresh executor only when the fix is genuinely separate;
- handle a very small localized fix directly only when spawning an executor
  would cost more context than it saves.

After fixes, rerun the affected verification and any review needed to support a
new verdict.

## 7. Retro after GO

After GO, ask whether the run revealed a reusable lesson.

If yes:

- **Harness/process lesson** → update the relevant rule in the dotfiles/setup
  repository, such as `/build`, executor behavior, or reviewer orchestration.
- **Project-specific lesson** → update the project's `docs/MEMORY.md`.

Record nothing when there is no reusable lesson.

Do not duplicate the same lesson into both places unless it genuinely applies to
both.

For every executor dispatch/resume provide:
- task
- acceptance criteria
- dependencies
- workstream
- expected scope
- verification
- is_last_selected_task_in_workstream: yes/no
- workstream verification command, when applicable
