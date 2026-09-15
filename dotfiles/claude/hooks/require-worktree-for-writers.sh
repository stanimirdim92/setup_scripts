#!/usr/bin/env bash
# PreToolUse hook (matcher: Agent|Task). Denies dispatching a writing persona
# while the session sits on the default branch of the main checkout.
#
# The failure it prevents: with `isolation: worktree` on both writers, an
# executor dispatched from the main checkout gets a sub-worktree branched from
# that checkout's HEAD -- the default branch. There is no ticket branch for its
# commits to belong to, /build integrates them back into the default branch,
# and that is the checkout the human has open in their IDE. Nothing else in the
# harness notices: every individual step succeeds.
#
# This was a SubagentStart hook returning exit 2 until an external review
# pointed out that the event's ability to block is not established -- the
# published table is "Can block? Yes" for PreToolUse and does not say so for
# SubagentStart, and a hook whose refusal might be advisory is not a guard.
# PreToolUse on the dispatch tool blocks by documented contract, uses the same
# JSON decision as the harness's three other enforcing hooks, and is testable
# end to end. See docs/adr/0057.
#
# Narrow on purpose. A writer is allowed when the session is in a linked
# worktree (the intended ticket flow), or on any branch that is not the default
# one (a deliberate branch-without-worktree flow, which lands work somewhere
# recoverable). Only "writing straight onto main" is refused, and the fix is a
# single command, named in the message.
#
# Exit 0 always; the decision is JSON on stdout, per
# https://code.claude.com/docs/en/hooks. Any failure allows, because a broken
# hook must not wedge a build.
set -uo pipefail

input="$(cat 2>/dev/null)" || exit 0
cwd="$(jq -r '.cwd // empty' <<<"$input" 2>/dev/null)"
# Agent and Task both carry the persona in subagent_type; agent_type is
# accepted too so the hook keeps working if it is ever dispatched differently.
agent="$(jq -r '.tool_input.subagent_type // .tool_input.agent_type // .agent_type // empty' <<<"$input" 2>/dev/null)"

case "$agent" in
  executor|test-engineer) ;;
  *) exit 0 ;;
esac

[ -n "$cwd" ] && [ -d "$cwd" ] || exit 0
cd "$cwd" 2>/dev/null || exit 0
git rev-parse --git-dir >/dev/null 2>&1 || exit 0

# In a linked worktree, --git-dir points inside <common>/worktrees/<name>; in
# the main checkout the two resolve to the same directory.
git_dir="$(cd "$(git rev-parse --git-dir 2>/dev/null)" && pwd -P)" || exit 0
common_dir="$(cd "$(git rev-parse --git-common-dir 2>/dev/null)" && pwd -P)" || exit 0
[ "$git_dir" != "$common_dir" ] && exit 0   # in a worktree: the intended flow

default="$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null)"
default="${default#origin/}"
if [ -z "$default" ]; then
  for candidate in main master; do
    git show-ref --verify --quiet "refs/heads/$candidate" && { default="$candidate"; break; }
  done
fi
[ -n "$default" ] || exit 0

branch="$(git symbolic-ref --quiet --short HEAD 2>/dev/null)" || exit 0
[ "$branch" = "$default" ] || exit 0        # on a feature branch: allowed

jq -n --arg reason "$(cat <<MSG
Refusing to dispatch $agent: this session is on '$branch', the default branch, in the
main checkout -- not a ticket worktree and not a feature branch.

The writer would get its own worktree branched from '$branch', with no ticket branch for
its commits to belong to, and /build would integrate them back into '$branch' -- the
checkout open in your editor. Every step of that succeeds, which is why nothing else
catches it.

Start the ticket in its own worktree:

    claude --worktree <ticket>

or, if you meant to work without one, create the branch first:

    git checkout -b <branch>
MSG
)" '{
  hookSpecificOutput: {
    hookEventName: "PreToolUse",
    permissionDecision: "deny",
    permissionDecisionReason: $reason
  }
}'
exit 0
