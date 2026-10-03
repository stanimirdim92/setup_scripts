# Parallel executors enabled via worktree isolation, superseding 0003

**Decision.** `/build` may now run up to **2 concurrent writing executors**,
each dispatched with `isolation: worktree`. This supersedes
[0003](0003-executor-concurrency-sequential-only.md)'s strict 1-at-a-time cap by
taking the alternative 0003 rejected "for now" — its own **Revisit if** condition
(wall-clock bottleneck on genuinely independent workstreams) is what triggered
this.

0003's reason still holds and is preserved, not overridden: two executors with
`Edit`/`Write`/`Bash` in the **same** checkout race on git state
(`.git/index.lock` contention, one executor's `git add` capturing another's
uncommitted edit) regardless of whether their file scopes overlap. Worktree
isolation removes the shared mutable state that made the race possible; it does
not make concurrent writers safe in one checkout. So the rule is conditional
rather than lifted: **2 concurrent with `isolation: worktree`, 1 without.**
Integration stays strictly sequential — worktree branches merge back one at a
time in dependency order, with verification after each merge.

Verified against the Claude Code subagent reference before adopting: `isolation`
is a real capability, available both as agent frontmatter and per-dispatch on the
`Agent` tool, and an unchanged worktree is cleaned up automatically. It is set
per dispatch rather than in `agents/executor.md`'s frontmatter, so a sequential
single-workstream run — still the common case — pays no worktree setup or merge
cost.

The cap is 2 to match [0004](0004-reviewer-batch-cap-no-high-risk-exception.md)'s
reviewer cap and this repo's stated preference for predictable spend. It also
resolves a live three-way contradiction in `commands/build.md`, which
simultaneously said executors run "sequentially, even across independent
workstreams", described a "Future parallel execution" mode, and set the cost gate
at "writing executors: 2 active at a time".

**This buys wall-clock, not tokens.** Each isolated executor rediscovers context
the other already holds, so two concurrent workstreams cost *more* total tokens
than the same two run sequentially. Recorded explicitly because the motivation
offered for revisiting 0003 was token usage, and parallelism does not serve that
goal — 0002's original 2-executor cap was a cost gate, but 0003 replaced it with
a correctness rule, and cost was never what sequential execution was protecting.
For token reduction the lever is bounded context per dispatch, not concurrency.

**Rejected — put `isolation: worktree` in `agents/executor.md`'s frontmatter.**
Every executor would then get a worktree, including the single sequential
executor that is the common case, paying setup and a merge step for no benefit.
Per-dispatch keeps the cost where the concurrency is.

**Rejected — raise the cap above 2.** Nothing measured says 2 is the bottleneck,
and each additional concurrent executor adds a merge that must itself succeed
cleanly. Revisit with an actual measurement, per
`references/agent-run-metrics.md`.

**Rejected — allow parallel integration too.** Merging two worktree branches
concurrently reintroduces exactly the shared-git-state race worktrees were
adopted to remove, at the point where conflicts are most likely.
