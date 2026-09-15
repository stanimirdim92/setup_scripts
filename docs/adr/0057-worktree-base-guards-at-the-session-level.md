# The cost of `worktree.baseRef: head` is paid at the session level, and guarded there

**Decision.** Two hooks enforce the conditions that
[0056](0056-role-tiered-models-blind-review-recon-width-writer-isolation.md)'s
fourth decision quietly depends on:

1. **`hooks/warn-stale-base.sh`** — `SessionStart`, matcher `startup|resume`.
   Warns in the two arrangements that put a ticket on a stale base: the
   checkout sits *on* the remote default branch and is behind it
   (`git pull`), or a linked worktree's branch carries no commits of its own
   and is behind it — `claude --worktree` just branched off a stale local
   default (`git merge --ff-only origin/<default>`). Prints to stdout, which
   becomes context; exits 0 unconditionally.
2. **`hooks/require-worktree-for-writers.sh`** — `SubagentStart`, matcher
   `executor|test-engineer`. Refuses the dispatch (exit 2) when the session is
   on the default branch in the main checkout. Allows everywhere else: in a
   linked worktree, on any non-default branch, outside a git repository.

Both are wired in `settings.json` and tested by
`tools/test-worktree-hooks.sh` against real git fixtures.

## The risk 0056 moved rather than removed

0056 set `worktree.baseRef: "head"` because the level below it requires that: a
subagent with `isolation: worktree` branches from *its session's* worktree
HEAD, so an executor inherits the ticket branch, the approved spec commit and
earlier workstream commits. Under the default `fresh` it would have branched
from the remote default branch and lost all three, and 0056 records that as the
reason the field alone would have been a regression.

What it did not record is that one setting governs both levels. The ticket
worktree above now also branches from local HEAD. So the failure 0056 described
for executors — a checkout created successfully, missing work that exists — did
not disappear; it moved up one level and changed its trigger from *always* to
*whenever the human's checkout is stale*. That is a better failure. It is not
an absent one, and nothing in the harness would have surfaced it.

The second hook covers a case `head` makes reachable rather than one it causes.
With `isolation: worktree` on both writers, an executor dispatched from the main
checkout on the default branch gets a sub-worktree branched from that branch.
There is no ticket branch for its commits to belong to, `/build` integrates them
back into the default branch, and that is the checkout the human has open in
their editor. As with the first, every individual step succeeds.

Both are configuration-shaped failures: silent, and only visible by the time
work has been done in the wrong place.

## Why the strengths are split — a warning and a block

The two cases differ in what the harness can know, and the mechanism follows.

Being behind origin is often fine. Mid-ticket it is normal, on a feature branch
it means nothing, and a five-minute-old fetch is not a problem. Only the moment
a ticket's base is fixed is worth a word — and even then the human may have a
reason. A hook that cannot tell a real problem from an ordinary state must not
block, and `SessionStart` cannot block anyway. So: a warning, on the two
arrangements where that moment is observable.

Dispatching a writer onto the default branch of the main checkout has no
legitimate reading. There is no workflow in this harness where the right place
for an executor's commits is the branch the human is editing from, and the fix
is one command. `SubagentStart` can block, the condition is unambiguous, so it
blocks — and names both fixes in the refusal, because a gate that stops the work
without saying how to proceed gets deleted within a week.

## Why the allow cases carry the test weight

Fourteen of the twenty-two fixture cases assert that nothing happens. That ratio is
the point. Both hooks fail in the direction that destroys them: a session-start
warning that fires when nothing is wrong is ignored inside a week, and a gate
that refuses a legitimate dispatch is removed rather than debugged. The block
cases prove the hooks do something; the allow cases prove they can be lived
with, and they are the ones that will break when someone widens a condition.

The fixtures build real repositories — a bare origin, a main checkout cloned
from it, a linked worktree, a feature branch, a repository with no remote at
all — because both hooks decide entirely from git state, and a mocked `git`
would test the mock. This follows [0049](0049-durable-spec-pin-and-hook-bypasses.md):
the regexes are not the fix, the fixtures are.

The suite asserts its own setup before running a case. A broken fixture reads
exactly like a passing hook here — git answering "no such branch" and a hook
staying silent are the same observation — and the first version of this suite
did precisely that in two cases before the assertion was added.

## Correction: the first condition missed the primary flow

As first written, the warning fired only on "sitting on the default branch and
behind it". That covers a moment the intended workflow does not have.
`claude --worktree <ticket>` creates the worktree and drops the session
straight into it, already on the ticket branch — the session never sits on the
default branch, so the condition never matched. The warning was silent on
exactly the case that motivated it, and `inside_a_worktree` asserted that
silence as correct behavior.

The gap came from writing the condition against where staleness is *visible*
(a checkout on the default branch, behind origin) rather than against where it
is *fixed* (the instant a ticket branch's base is chosen). The second framing
produces both arrangements from one idea and is why the conditions now read as
they do.

The fix is narrow on purpose: in a linked worktree, warn only while the branch
carries **no commits of its own**. That is true from creation until the first
commit, which is the whole window in which the base is still free to move, and
false for the rest of the ticket — when being behind origin is the ordinary
state of every branch and a warning would be noise. It fires once, at the only
moment the advice is both cheap and correct.

## The fetch window

`warn-stale-base.sh` refreshes `origin/<default>` when the last fetch is over
an hour old, capped at five seconds, falling back to the cached ref when the
network is unavailable. A cached ref is only as fresh as the last fetch, so
without this the hook would report "up to date" while being days behind — it
would be a check that reliably says nothing.

An hour rather than a day because the conditions upstream have already
established that a ticket's base is being fixed. Five seconds spent there is
worth it; spent on every session start it would not be, and those conditions are
what make the narrow window affordable. The commit-count pre-filter matters for
the same reason: a mid-ticket session in a worktree must not pay for a fetch,
and a cached zero own-commit count can only stay zero once origin moves forward,
so the cheap test is safe to gate the expensive one. `FETCH_HEAD` lives in the
common git dir, so a worktree and its main checkout share one window.

## Rejected alternatives

**Rejected — `worktree.baseRef: "fresh"` with a per-subagent override.** The
cleanest fix on paper: leave the session level branching from origin and let
only writers branch from HEAD. `baseRef` is a settings-level key with no
frontmatter equivalent, so this does not exist. Recorded because it is the
first thing anyone reading 0056 will reach for.

**Rejected — auto-pulling instead of warning.** A `SessionStart` hook that runs
`git pull` mutates a checkout the human has open in an editor, before they have
typed anything, with merge conflicts and rebase state as available outcomes.
The warning costs one line of context and leaves the decision where it belongs.

**Rejected — warning on any branch that is behind origin.** Simpler condition,
and it fires constantly: every ticket branch is behind origin the moment anyone
else merges. It would train the reader to skip the line, which is worse than
not printing it.

**Rejected — blocking on a stale base as well.** The stale-base case has
legitimate readings (a deliberate build against yesterday's main, an offline
session) and blocking session start over it trades a rare silent failure for a
frequent loud obstruction.

**Rejected — refusing writers outside a linked worktree entirely.** Stricter,
and it breaks the ordinary `git checkout -b` flow for a one-file change. A
feature branch in the main checkout lands work somewhere recoverable, which is
all the guard is protecting.

## Consequences

- Starting a ticket from a stale default branch now costs a few lines of
  context and up to five seconds; this is the only place in the harness where a
  hook touches the network.
- The two warnings give different advice on purpose. `git pull` is right on the
  default branch and wrong on a ticket branch, where it merges the default
  branch in rather than moving the branch point. A fresh ticket branch has
  nothing to rebase, so `--ff-only` can only fast-forward and refuses if
  anything would be lost. Two fixture cases assert the advice does not get
  swapped.
- `/build` from the main checkout on the default branch now fails at dispatch
  rather than succeeding into the wrong branch. The refusal is the intended
  behavior, and the message carries both fixes.
- Both hooks read `origin/HEAD` for the default branch and fall back to
  `main`/`master` by name. A repository whose default branch is neither, and
  whose `origin/HEAD` is unset, is not covered by either hook — it exits 0,
  silently, which is the correct direction to fail.
- `tools/test-worktree-hooks.sh` joins CI as the tenth self-test suite.
