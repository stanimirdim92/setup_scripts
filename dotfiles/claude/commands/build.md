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

## 6. Retro (only after GO)

Once the work has actually landed, ask one question: **is there anything
about how this run went that should change next time?** Don't force an
answer — "nothing" is a complete answer, same as `code-review-and-quality`
never manufacturing a finding to justify the review.

If the answer names something, sort it before recording it:

- **About `/build` itself, `executor`, or the review fan-out** — a real
  process gap (wrong dispatch order, a reviewer that should've run and
  didn't, a step that should exist and doesn't). This belongs in the
  dotfiles repo (`stanimirdim92/setup_scripts`), not in whatever project
  you were just working in — state the exact change and which file it
  belongs in (usually `dotfiles/claude/commands/build.md` or
  `dotfiles/claude/agents/executor.md`), and apply it directly if this
  session already has that repo open; otherwise hand the user the
  specific edit to carry over.
- **About this project specifically** — a convention, a gotcha, a "why we
  do it this way" that the next session here needs and wouldn't otherwise
  know. This belongs in *this* project's `docs/MEMORY.md`, per
  `CLAUDE.md`'s memory section — read it first, update it last, and don't
  let it silently rot into auto-memory instead where the next machine
  won't see it.

One or the other, not both by default — a retro finding is usually about
the process or about this codebase, rarely genuinely both at once.
