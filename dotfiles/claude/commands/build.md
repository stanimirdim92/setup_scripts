---
description: Dispatch execution for one or more planned tasks, then fan out review and merge a go/no-go verdict
argument-hint: "[task number(s) from tasks/todo.md, or a task description]"
---

Invoke the `incremental-implementation` skill's discipline via dispatched
`executor` agents — this command is the orchestration layer around it,
not a replacement for it.

## 1. Resolve before dispatching anything

Read `tasks/todo.md` (or `tasks/plan.md`, or take the task description
given as an argument) and pin down exactly which task(s) are in scope,
their acceptance criteria, and file scope. If that's ambiguous, ask now —
**don't dispatch and find out inside a running executor.** A bad task
reference should fail here, free, not three commits into an `executor`
run.

## 2. Dispatch

For each resolved task, dispatch one `executor` agent with the task's
full context (acceptance criteria, file scope, relevant spec/plan
excerpts). Tasks that don't share files can run in parallel, one
`executor` per task; tasks that touch overlapping files run one at a
time, in dependency order — never two executors writing to the same file
concurrently.

## 3. Fan out review, independently

Once every dispatched `executor` has reported back, fan out in parallel
against the resulting diff:

- `code-reviewer` — always
- `security-reviewer` — always
- `infra-reviewer` — only if the diff touches `nginx/`, `database/`,
  `redis/`, `php/fpm/`, `linux/etc/`, or a Dockerfile
- `distributed-systems-reviewer` — only if the diff touches a cross-
  process/network/queue boundary: an RPC or HTTP call between services, a
  queue producer/consumer, a scheduled job, or a background worker

Give each reviewer only the diff. Not the plan, not each other's output —
each axis reviews blind to the others, same reasoning as the two-axis
review this pattern is adapted from: an axis that can see another axis's
findings starts anchoring on them instead of forming its own.

## 4. Merge without reranking

Report each reviewer's findings under its own heading — Correctness/
Readability/Architecture/Security/Performance from `code-reviewer`,
security findings from `security-reviewer`, infra findings from
`infra-reviewer` if it ran, cross-boundary reliability findings from
`distributed-systems-reviewer` if it ran. **Don't blend them into one
ranked list.**
Reporting them separately is deliberate: it stops one axis's silence from
reading as another axis's clearance, and stops a loud axis from burying a
quiet but real finding from a different one.

## 5. Verdict

**GO** or **NO-GO**, stated explicitly:

- Any Critical finding from any reviewer → default **NO-GO**. The user
  can override explicitly; don't talk yourself into overriding it.
- No Critical findings, some Required/Important findings → your call,
  but say what's outstanding either way.
- Clean across every reviewer that ran → **GO**. The work is already
  committed per-increment by the executor(s); there's nothing left to
  land.

On **NO-GO**, list exactly what has to change and hand it back — either a
fresh `executor` dispatch scoped to just the fix, or handle it directly if
it's small enough that spinning up another agent would cost more than it
saves.
