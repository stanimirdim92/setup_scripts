# The cost of `worktree.baseRef: head` is paid at the session level, and guarded there

**Decision.** Two hooks enforce the conditions that
[0056](0056-role-tiered-models-blind-review-recon-width-writer-isolation.md)'s
fourth decision quietly depends on:

1. **`hooks/warn-stale-base.sh`** — `SessionStart`, matcher `startup|resume`.
   Warns when the checkout sits *on* the remote default branch and is behind
   it. Prints to stdout, which becomes context; exits 0 unconditionally.
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
it means nothing, and a five-minute-old fetch is not a problem. Only one
combination is worth a word — sitting on the default branch, behind it, which is
the moment before a ticket starts — and even then the human may have a reason.
A hook that cannot tell a real problem from an ordinary state must not block,
and `SessionStart` cannot block anyway. So: a warning, on the one combination.

Dispatching a writer onto the default branch of the main checkout has no
legitimate reading. There is no workflow in this harness where the right place
for an executor's commits is the branch the human is editing from, and the fix
is one command. `SubagentStart` can block, the condition is unambiguous, so it
blocks — and names both fixes in the refusal, because a gate that stops the work
without saying how to proceed gets deleted within a week.

## Why the allow cases carry the test weight

Thirteen of the eighteen fixture cases assert that nothing happens. That ratio is
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

## The fetch window

`warn-stale-base.sh` refreshes `origin/<default>` when the last fetch is over
an hour old, capped at five seconds, falling back to the cached ref when the
network is unavailable. A cached ref is only as fresh as the last fetch, so
without this the hook would report "up to date" while being days behind — it
would be a check that reliably says nothing.

An hour rather than a day because the hook only reaches the fetch while sitting
on the default branch, which is the moment a ticket is about to start. Five
seconds spent there is worth it; spent on every session start it would not be,
and the branch check upstream is what makes the narrow window affordable.

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

- Starting a ticket from a stale default branch now costs one line of context
  and up to five seconds; this is the only place in the harness where a hook
  touches the network.
- `/build` from the main checkout on the default branch now fails at dispatch
  rather than succeeding into the wrong branch. The refusal is the intended
  behavior, and the message carries both fixes.
- Both hooks read `origin/HEAD` for the default branch and fall back to
  `main`/`master` by name. A repository whose default branch is neither, and
  whose `origin/HEAD` is unset, is not covered by either hook — it exits 0,
  silently, which is the correct direction to fail.
- `tools/test-worktree-hooks.sh` joins CI as the tenth self-test suite.
