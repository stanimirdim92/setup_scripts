# Executor concurrency: sequential only, no parallel writers

**Decision.** `/build` originally capped concurrent `executor`
workstreams at 2 (see `0002-model-split-sonnet-orchestrator-tiered-subagents.md`'s
cost-gate history). A second review caught that the cap didn't address a
real correctness risk: `executor` has `Edit`/`Write`/`Bash` and commits,
so two of them running at once write into the *same* checkout — a git-index
race (`.git/index.lock` contention, or one agent's `git add` scooping up
the other's uncommitted edit) that exists regardless of whether their file
scopes overlap. Non-overlapping scope prevents a content conflict, not a
git-state race. Fixed by capping executor dispatch at strictly 1-at-a-time:
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
