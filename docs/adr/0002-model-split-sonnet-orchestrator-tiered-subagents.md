# Model split: Sonnet orchestrator, tiered subagents

**Decision (original).** The main session (the one drafting specs and
plans with you) runs on whatever `settings.json`'s `model` key says —
currently the floating `sonnet` alias. Every dispatched agent originally
pinned `model: claude-opus-4-8` explicitly in its own frontmatter — a
specific version, not the floating `opus` alias — deliberately the
opposite of the cheap-workers/expensive-orchestrator split that's the
default instinct: the orchestrator is a conversation, the subagents are
where judgment calls that are expensive to get wrong actually happen (an
`executor` commits code; the reviewers decide GO/NO-GO). Pinned rather
than floating because `opus` now resolves to Opus 5, and delegation work
should target a version deliberately chosen and verified, not whatever
"opus" floats to on the next model release. A subagent with no `model`
field `inherit`s the main session's model instead — silently downgrading
that dispatch to whatever the orchestrator happens to be running on, so
this only stays true as long as each agent file's `model:` line is set
deliberately. If you add a new agent, give it a pinned model deliberately;
don't leave it on the default and assume it matches, and don't reach for
the floating `opus` alias instead of a pinned string.

**Decision (2026-08-13 update) — flip `executor`/`code-reviewer` to
Sonnet, keep Opus for the rest.** A `/build` run burned a full 5-hour
usage window in ~15 minutes by fanning out several Opus-tier
`executor`/reviewer agents concurrently. That incident produced two
confirmed process fixes (see `dotfiles/claude/commands/build.md`): a hard
concurrency cap (never more than 2 agents running at once) and
workstream-grouped dispatch (one agent per dependency chain, resumed
across its tasks, not one fresh agent per task). On top of those process
fixes, the *default model tier* itself was reconsidered: `executor` and
`code-reviewer` now pin `model: claude-sonnet-5` in their frontmatter —
routine implementation and routine review don't need Opus-tier reasoning
by default, and these two agents are dispatched the most often and in the
largest batches, so they're where the tier choice compounds. A
per-invocation `model` override (documented in `build.md`'s "Model tier
per workstream" note) is still available to bump a *specific* workstream
or review back up to Opus when it's architecturally ambiguous or a wrong
call would be genuinely expensive to undo — reach for it rather than
running everything at the higher tier "just in case."

`security-reviewer`, `distributed-systems-reviewer`, `infra-reviewer`, and `unblock-triage` were **not** part of this
decision and still pin `model: claude-opus-4-8` — the question asked and
answered was scoped to `executor`/`code-reviewer` specifically, since
those are the two dispatched unconditionally on every `/build` run. Their
tier is a separate call, revisit it separately if it comes up.

**Rejected — keeping Opus as the frontmatter default and routing routine
work through a per-dispatch Sonnet override instead.** Considered first,
since it's the more surgical lever and doesn't touch the agents' own
files. Rejected because `executor`/`code-reviewer` are dispatched on
*every* `/build` run, and "routine" is the common case for both — a
default that has to be overridden nearly every time is the wrong default;
flipping the frontmatter itself puts the common case on the cheaper tier
and makes the override the exception, not the rule.

Update `dotfiles/claude/CLAUDE.md`'s skills list and this repo's
`README.md` together when agents change — `dotfiles-sync`'s checklist
covers both.
