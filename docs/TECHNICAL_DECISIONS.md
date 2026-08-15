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

## Model split: Sonnet orchestrator, tiered subagents

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

`security-reviewer`, `distributed-systems-reviewer`, `infra-reviewer`,
`llm-integration-reviewer`, and `unblock-triage` were **not** part of this
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

## Executor concurrency: sequential only, no parallel writers

**Decision.** `/build` originally capped concurrent `executor`
workstreams at 2 (see the cost-gate history above). A second review
caught that the cap didn't address a real correctness risk: `executor`
has `Edit`/`Write`/`Bash` and commits, so two of them running at once
write into the *same* checkout — a git-index race (`.git/index.lock`
contention, or one agent's `git add` scooping up the other's
uncommitted edit) that exists regardless of whether their file scopes
overlap. Non-overlapping scope prevents a content conflict, not a git-
state race. Fixed by capping executor dispatch at strictly 1-at-a-time:
finish (or resume-to-completion on) one workstream's current task before
the next workstream's first dispatch, full stop, even when two
workstreams are independent enough to otherwise parallelize. This
folds the executor half of the earlier cost gate into a correctness
rule instead of a cost rule — sequential dispatch caps spend as a side
effect, but the reason for it is the shared checkout, not the token
meter.

**Rejected — keep 2 concurrent, add `isolation: worktree`.** The `Agent`
tool supports per-invocation git-worktree isolation, which would let two
executors write safely in parallel with an explicit merge/cherry-pick
step back into the main checkout. Rejected for now: it's real
parallelism at the cost of real complexity (a merge step that itself
needs to succeed cleanly), and this repo's own stated priority is
predictable spend over shaved wall-clock minutes — the same reasoning
that produced the original batch cap. Revisit if `/build` runs start
actually being bottlenecked on wall-clock time with genuinely
independent workstreams; the mechanism to reach for is documented in
`build.md`, not re-invented from scratch.

## Reviewer batch cap: no high-risk exception

**Decision.** The review fan-out's "never more than 2 reviewers at once"
cap originally had an exception: a diff already flagged high-risk could
run the full specialist fan-out concurrently, "since it's earning the
cost." That exception directly contradicted this repo's own README,
which stated the cap as "regardless of how many are eligible" with no
carve-out — a real drift between what two files claimed about the same
rule (rule 6 territory). Fixed by removing the exception: the cap holds
unconditionally, including for high-risk diffs that trigger every
specialist — those diffs get all the same reviewers, just in sequential
batches of 2 instead of all at once. A high-risk diff earns more
distinct review perspectives, not a faster concurrent token burn.

## Reviewer trigger matrix: one file, not two copies

**Decision.** `build.md` claimed its reviewer trigger conditions "must
match `review.md` exactly," but `review.md` never defined conditions for
`infra-reviewer` or `llm-integration-reviewer` at all — there was
nothing for `build.md`'s copy to match, and `llm-integration-reviewer`
wasn't wired into either command's routing despite existing specifically
for LLM-call-site review, which is the majority of this machine's actual
project work. Fixed by moving the trigger matrix into
`dotfiles/claude/references/reviewer-triggers.md` as the single source,
with both commands reading it instead of each keeping its own copy, and
adding `llm-integration-reviewer`'s trigger (diff touches an LLM API call
site: new/changed prompt, model call, tool definition, or model output
feeding a record write or downstream action).

## `/review`: thin wrapper over `code-reviewer`, not a second rubric

**Decision.** `/review` invoked the `code-review-and-quality` skill
directly — a 320-line five-axis framework loaded fresh into context on
every call — duplicating the same five-axis rubric the much smaller
`code-reviewer` agent already implements (the one `/build` dispatches).
Two rubrics for the same review is a rule-6 case, not two legitimately
different reviews. Fixed by making `/review` dispatch `code-reviewer`
directly, plus specialist fan-out per the trigger matrix above — the
same pattern `/build` already uses for its review step, so there's one
five-axis rubric in the repo, not two.

**Rejected — delete `code-review-and-quality` entirely.** The skill is
still referenced by `git-workflow-and-versioning` (splitting-strategy
detail for large diffs) and `references/definition-of-done.md`. Kept as
a reference; only `/review`'s direct invocation of it was removed.

## Matt Pocock's skills: removed, committing to the addyosmani SDLC shape

**Decision.** `research` and `handoff` (`MATTPOCOCK_SKILLS_LICENSE`) are
removed entirely — files deleted, all README/CLAUDE.md references
dropped. This machine commits to `addyosmani/agent-skills`'s phase-mapped
SDLC shape (`spec-driven-development` → `planning-and-task-breakdown` →
`incremental-implementation`/`code-review-and-quality`, orchestrated by
this repo's own `/spec`/`/plan`/`/build`/`/review` commands) as the one
active planning/build/review router, with `superpowers` scoped
narrowly to classification (`brainstorming`), TDD, and debugging — not
as a competing SDLC router. Per `addyosmani/agent-skills`' own
`docs/comparison.md`: "cherry-picking individual skills works;
stacking both frameworks as active routers fight over command names and
produce unpredictable behavior." Matt Pocock's collection is built
around a different assumption — `to-spec`/`to-tickets`/`wayfinder` all
synthesize a conversation into an external issue tracker — which doesn't
match this team's actual shape of work: tickets (e.g. LD-329) arrive
already fully authored in Jira, DoD and all, before Claude ever sees
them. There's nothing here for those skills to do.

## Infra + security reviewers merged into `security-auditor`

**Decision.** `infra-reviewer` (nginx/redis/mysql/sysctl/PHP-FPM/Dockerfile
pattern review) and `security-reviewer` (security pass over the same infra
surface) are replaced by a single `security-auditor` agent — one persona
covering input handling, auth, data protection, infra security, third-party
integrations, and LLM/OWASP-LLM-Top-10 findings. `reviewer-triggers.md` and
`build.md`/`review.md`/`code-reviewer.md`'s Composition blocks now point at
`security-auditor` alone. Filled in `tools: Read, Grep, Glob, Bash` and
`model: claude-opus-4-8` / `effort: high` on the new agent file, matching
the tier the two agents it replaces already carried — the merge shipped
without frontmatter the first time, which this repo's own "every agent
pins a model" rule (see "Model split" above) doesn't allow.

**Open, not yet resolved:** `infra-reviewer`'s job also included
pattern-*consistency* review (does this Dockerfile/nginx config match what
this repo already established), not just security. `security-auditor`'s
Infrastructure section only covers the security half. Whether that
consistency check needs a home somewhere else, or was deliberately dropped,
hasn't been settled — flagged to the user rather than assumed either way.

## New vendored skills: `deprecation-and-migration`, `security-and-hardening`

**Decision.** Both added from `addyosmani/agent-skills`, filling references
that previously said "if available — not currently vendored in this repo":
`git-workflow-and-versioning`'s breaking-change/deprecation-window note now
points at a real `deprecation-and-migration` skill, and
`references/security-checklist.md` / `code-review-and-quality`'s
dependency-audit section now point at a real `security-and-hardening`
skill instead of a dangling one.

## Plugin set: dropped `feature-dev`, added four `@claude-plugins-official`

**Decision.** `feature-dev@claude-plugins-official` removed from
`settings.json` — it ships its own `code-explorer`/`code-architect`/
`code-reviewer` agents running a 7-phase pipeline that duplicated this
repo's own `/spec` → `/plan` → `/build` → `/review`, one of the two
"active router" collisions raised via `addyosmani/agent-skills`'
`docs/comparison.md`. Added `security-guidance`, `typescript-lsp`,
`code-simplifier` (referenced by `references/definition-of-done.md`'s
Quality section), and `playwright`.

**Rejected — keep `domain-modeling` and/or `improve-codebase-architecture`
as standalone cherry-picks.** Floated as low-risk additive skills (no
tracker dependency, nothing here plays either role today) while
evaluating LD-329 against all three repos. Rejected on later, more
direct instruction: no Matt Pocock content stays vendored, full stop —
simpler than maintaining a policy of "his router is out, but individual
skills are still in," and this team's preference is explicitly to lean
into the SDLC/phase-mapped shape addyosmani's collection already
provides rather than blend in a second author's individual skills.
