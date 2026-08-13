# Technical Decisions

Why this repo's `.claude` config is built the way it is. Per the
convention this repo's own global `CLAUDE.md` prescribes for every
project: each entry states the decision, the reasoning, and everything
seriously considered and rejected along the way — including choices
reversed after contact with reality.

## Superpowers overlap

**Decision.** Two vendored skills collided by name/job with skills the
`superpowers` marketplace plugin already ships: `test-driven-development`
and `debugging-and-error-recovery`, against superpowers' own
`test-driven-development` and `systematic-debugging`. Running both meant
ambiguity over which one actually fires on a given trigger — rule 6
territory: pick one, don't blend them. Dropped the vendored copies.
`/test` and any debugging work now go through the `superpowers` plugin's
`test-driven-development` and `systematic-debugging` skills. `/spec` and
`/plan` also now open with a `superpowers` step instead of jumping
straight to the vendored one: `brainstorming`'s spike/bounded/
architectural classification (with its own approval gate) runs before
`spec-driven-development` writes anything, and
`dispatching-parallel-agents`'s independence test runs once
`planning-and-task-breakdown` has the dependency graph, to flag which
tasks `/build` can dispatch concurrently.

**Rejected — swapping in more of superpowers.** `writing-plans`,
`requesting-code-review`/`receiving-code-review`, and
`finishing-a-development-branch` cover the same ground as
`planning-and-task-breakdown` and `code-review-and-quality` without being
clearly better, so they weren't swapped in — only the two actual
name/job collisions and the two compositional additions above were made.

## Model split: Sonnet orchestrator, Opus subagents

**Decision.** The main session (the one drafting specs and plans with
you) runs on whatever `settings.json`'s `model` key says — currently the
floating `sonnet` alias. Every dispatched agent pins `model:
claude-opus-4-8` explicitly in its own frontmatter — a specific version,
not the floating `opus` alias — deliberately the opposite of the
cheap-workers/expensive-orchestrator split that's the default instinct:
the orchestrator is a conversation, the subagents are where judgment
calls that are expensive to get wrong actually happen (an `executor`
commits code; the reviewers decide GO/NO-GO). Pinned rather than floating
because `opus` now resolves to Opus 5, and delegation work should target
a version deliberately chosen and verified, not whatever "opus" floats to
on the next model release. A subagent with no `model` field would
`inherit` the main session's model instead — silently downgrading every
dispatch to whatever the orchestrator happens to be running on, so this
only stays true as long as each agent file's `model: claude-opus-4-8`
line does. If you add a new agent, give it one deliberately; don't leave
it on the default and assume it matches, and don't reach for the floating
`opus` alias instead of the pinned string.

**Reconsider — after the 2026-08-13 cost incident.** A `/build` run
burned a full 5-hour usage window in ~15 minutes by fanning out several
Opus-tier `executor`/reviewer agents concurrently. That incident produced
two confirmed fixes already applied (see `dotfiles/claude/commands/
build.md`): a hard concurrency cap (never more than 2 agents running at
once) and workstream-grouped dispatch (one agent per dependency chain,
resumed across its tasks, not one fresh agent per task). Whether the
*default model tier* for `executor`/`code-reviewer` should also drop from
Opus to Sonnet — reserving Opus for security/distributed-systems/
architecturally-ambiguous work specifically — is still open; flip it only
with an explicit decision recorded here, not silently. Claude Code
supports overriding the model per-dispatch (independent of the agent's
frontmatter default), which is the more precise lever to reach for before
changing the frontmatter default wholesale: route a routine, well-
specified task to a per-invocation Sonnet override and keep the Opus
default for ambiguous or high-stakes ones, rather than picking one tier
for every dispatch regardless of the task.

Update `dotfiles/claude/CLAUDE.md`'s skills list and this repo's
`README.md` together when agents change — `dotfiles-sync`'s checklist
covers both.
