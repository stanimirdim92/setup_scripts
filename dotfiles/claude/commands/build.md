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

## 2. Dispatch — by workstream, not by task

Group resolved tasks into workstreams first: tasks that share files,
share a subsystem, or sit in the same dependency chain belong in one
workstream. Dispatch **one `executor` per workstream, not one per task**
— every fresh subagent spawn loads and cache-writes its own copy of
`CLAUDE.md`, project rules, and tool definitions from scratch (a named
subagent's prompt cache is separate from the parent's, unlike a fork), so
five tasks in one dependency chain should mean one executor carried
through all five, not five fresh spawns each re-paying that cost.

- **First task in a workstream:** dispatch a fresh, named `executor`.
- **Each subsequent task in the *same* workstream:** resume that same
  agent (by name or agent ID) instead of spawning a new one — it already
  has the codebase context, file reads, and prior decisions from the
  earlier task; a fresh spawn would throw that away and re-pay the
  discovery cost for no reason.
- **A task in a genuinely independent workstream:** dispatch a new,
  separate `executor`.

Workstreams that don't share files *can* run concurrently; workstreams
that touch overlapping files run one at a time, in dependency order —
never two executors (including a resume racing a fresh dispatch)
writing to the same file concurrently.

**Model tier per workstream, when the default isn't right.** `executor`'s
frontmatter now defaults to `claude-sonnet-5` — routine implementation
doesn't need Opus-tier reasoning by default. A per-dispatch `model`
override is still available and takes precedence over the frontmatter
default for just that invocation: reach for it to bump a specific
workstream *up* to Opus when it's architecturally ambiguous or a wrong
implementation call would be genuinely expensive to undo, rather than
running everything at the higher tier "just in case." See
`docs/TECHNICAL_DECISIONS.md`'s "Model split" entry for the full
reasoning.

**Cost gate — a batch cap, not just a prompt.** A 5-hour usage window is
metered by total token volume, not wall-clock time — running several
agents concurrently for a few minutes (worse when any of them are
Opus-tier, e.g. a security- or architecturally-ambiguous workstream
bumped up per the model-tier note above) can spend as much of that
budget as hours of solo conversation, and *asking* before firing them
doesn't cap the spend if the answer is yes. So cap actual concurrency
instead of just confirming it:

- Never run more than **2** `executor` workstreams active at once,
  regardless of how many are eligible to run in parallel. With 5
  independent workstreams, that's dispatch 2, wait for both to report
  back, dispatch the next 2, then the last 1 — not all 5 at once.
- This cap applies even after the user says go ahead on a larger batch —
  it isn't a one-time confirmation that then lifts the ceiling, it's the
  ceiling itself.
- If a workstream's dependency graph forces sequencing anyway (overlapping
  files), that ordering already keeps concurrency low — the cap only
  bites when 3+ workstreams are actually independent and would otherwise
  all fire together.

## 3. Fan out review, independently

Once every dispatched `executor` has reported back, fan out against the
resulting diff. Each reviewer's trigger condition must match `review.md`
exactly — don't let this command and `/review` disagree about when a
reviewer runs (rule 6: pick one condition, don't let two commands each
invent their own):

- `code-reviewer` — always
- `security-reviewer` — only if the diff touches `nginx/`, `mysql`/
  `database/`, `redis/`, or `php/fpm/` config
- `infra-reviewer` — only if the diff touches `nginx/`, `database/`,
  `redis/`, `php/fpm/`, `linux/etc/`, or a Dockerfile
- `distributed-systems-reviewer` — only if the diff touches a cross-
  process/network/queue boundary: an RPC or HTTP call between services, a
  queue producer/consumer, a scheduled job, or a background worker

**Same batch cap applies here.** Never run more than **2** reviewers at
once, same reasoning as the executor cap above — if 3 or more triggers
match, dispatch 2, wait for both to report back, then dispatch the rest.
Exception: a diff already flagged high-risk (e.g. touches a shared
production pipeline) can run the full fan-out concurrently since it's
earning the cost — say so explicitly when that's why, rather than
silently defaulting to the full fan-out either way.

Give each reviewer the diff plus a one-line goal and the task's
acceptance criteria — not the full spec, not `tasks/plan.md`, not each
other's output. Enough to review against a stated intent without
flooding a fresh subagent with the whole plan; each axis also reviews
blind to the others, same reasoning as the two-axis review this pattern
is adapted from: an axis that can see another axis's findings starts
anchoring on them instead of forming its own.

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
