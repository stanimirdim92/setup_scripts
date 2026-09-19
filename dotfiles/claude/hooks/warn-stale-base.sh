#!/usr/bin/env bash
# SessionStart hook (matcher: startup|resume). Warns when the base a ticket is
# about to be built on is behind the remote default branch.
#
# Why this exists: settings.json sets `worktree.baseRef: "head"`, which the
# level below requires -- a subagent with `isolation: worktree` branches from
# its session's worktree HEAD, so an executor inherits the ticket branch, the
# spec commit and earlier workstream commits. The cost is at the level above:
# a ticket worktree now branches from your LOCAL HEAD, not from origin. Start a
# ticket from a main that is three days behind and the ticket branch is three
# days behind, silently, because the worktree is created successfully either
# way (docs/adr/0056, 0057).
#
# Two arrangements put you on a stale base, and they need different advice:
#
#   on-default    the checkout sits ON the default branch and is behind it.
#                 The moment before a ticket starts: `git pull` fixes it.
#   fresh-ticket  a linked worktree whose branch carries no commits of its own
#                 and is behind the default branch -- `claude --worktree` just
#                 branched it off a stale local main. This is the primary flow
#                 and the session never touches the default branch, so the
#                 on-default test alone never sees it.
#
# Base warnings stay quiet elsewhere, because a warning that fires when nothing is
# wrong gets ignored: a ticket branch that carries its own commits is behind
# origin as a matter of course, and that says nothing.
#
# SessionStart cannot block; plain stdout becomes context. Exit 0 always --
# a session must never fail to start because this hook had a bad day.
set -uo pipefail

if [ "${1:-}" = --report ]; then
  output="$(bash "${BASH_SOURCE[0]}" --verbose)"
  jq -n --arg message "$output" '{systemMessage:$message,hookSpecificOutput:{hookEventName:"SessionStart",additionalContext:$message}}'
  exit 0
fi
progress() { if [ "${verbose:-0}" = 1 ]; then printf '%s\n' "$*"; fi; }
verbose=0
[ "${1:-}" != --verbose ] || verbose=1
progress 'Startup: checking the current checkout.'

input="$(cat 2>/dev/null)" || exit 0
cwd="$(jq -r '.cwd // empty' <<<"$input" 2>/dev/null)"
[ -n "$cwd" ] && [ -d "$cwd" ] || { progress 'SKIP: checkout path is missing or unavailable.'; exit 0; }
cd "$cwd" 2>/dev/null || exit 0

top="$(git rev-parse --show-toplevel 2>/dev/null)" || { progress 'SKIP: this directory is not a Git checkout.'; exit 0; }
progress "Checkout: $top"
# Infrastructure can drift after a ticket has commits, independently of its
# Git base. Run before the branch/remote early exits (docs/adr/0058).
hook_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)" || exit 0
if source "$hook_dir/worktree-readiness.sh"; then
  progress 'Infrastructure: checking the worktree runner against the main checkout.'
  if worktree_infrastructure_ready "$top"; then
    if [ -e "$top/bin/worktree-doctor.sh" ]; then
      progress 'PASS: worktree infrastructure is current.'
    else
      progress 'SKIP: this project has no infrastructure checker.'
    fi
  else
    progress 'FAIL: worktree infrastructure needs attention.'
  fi
else
  printf 'Worktree infrastructure: readiness helper unavailable; restore the harness hooks.\n'
fi

git remote get-url origin >/dev/null 2>&1 || { progress 'SKIP: Git base check has no origin remote.'; exit 0; }

# The default branch as origin reports it; fall back to the usual names.
default="$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null)"
default="${default#origin/}"
if [ -z "$default" ]; then
  for candidate in main master; do
    git show-ref --verify --quiet "refs/remotes/origin/$candidate" && { default="$candidate"; break; }
  done
fi
[ -n "$default" ] || { progress 'SKIP: origin default branch could not be identified.'; exit 0; }

branch="$(git symbolic-ref --quiet --short HEAD 2>/dev/null)" || { progress 'SKIP: Git base check is on detached HEAD.'; exit 0; }
progress "Git base: checking $branch against origin/$default."

# In a linked worktree, --git-dir points inside <common>/worktrees/<name>; in
# the main checkout the two resolve to the same directory.
git_dir="$(cd "$(git rev-parse --git-dir 2>/dev/null)" && pwd -P)" || exit 0
common_dir="$(cd "$(git rev-parse --git-common-dir 2>/dev/null)" && pwd -P)" || exit 0

# `own` counts commits on this branch that origin's default branch lacks. The
# cached origin ref can only be behind the real one, and fetching moves it
# forward, so a cached zero stays zero -- which makes this a safe pre-filter
# for the fetch below and keeps the network out of every mid-ticket session.
own() { git rev-list --count "origin/$default..HEAD" 2>/dev/null || echo 1; }

if [ "$branch" = "$default" ]; then
  mode=on-default
elif [ "$git_dir" != "$common_dir" ] && [ "$(own)" = 0 ]; then
  mode=fresh-ticket
else
  progress 'SKIP: this is ongoing branch work; the fresh-ticket base warning does not apply.'
  exit 0                               # mid-ticket, or a branch of your own
fi

# A cached origin ref is only as fresh as the last fetch, so a stale cache
# would report "up to date" while being days behind. Refresh when the last
# fetch is over an hour old, capped at 5s the way Claude Code caps its own
# `fresh` base resolution, falling back to the cache when the network is gone.
# An hour rather than a day because the checks above have already established
# that a ticket is about to start, which is the one moment the five seconds is
# worth spending. FETCH_HEAD lives in the common dir, so a worktree and its
# main checkout share one window.
fetch_head="$common_dir/FETCH_HEAD"
if [ ! -f "$fetch_head" ] || [ -n "$(find "$fetch_head" -mmin +60 2>/dev/null)" ]; then
  progress 'Git base: refreshing the remote reference (up to 5 seconds).'
  timeout 5 git fetch --quiet origin "$default" >/dev/null 2>&1 || progress 'NOTICE: refresh failed; using the cached remote reference.'
else
  progress 'Git base: using the remote reference fetched within the last hour.'
fi

behind="$(git rev-list --count "HEAD..origin/$default" 2>/dev/null)" || exit 0
[ "${behind:-0}" -gt 0 ] 2>/dev/null || { progress "PASS: checkout is not behind the checked origin/$default reference."; exit 0; }
# Re-test against the refreshed ref: the fetch may have revealed that this
# branch's commits are already on the default branch.
[ "$mode" = fresh-ticket ] && { [ "$(own)" = 0 ] || { progress 'SKIP: refreshed reference confirms independent ticket work.'; exit 0; }; }

if [ "$mode" = on-default ]; then
  printf 'Worktree base: this checkout is on %s and is %s commit(s) behind origin/%s.\n' \
    "$branch" "$behind" "$default"
  printf 'A ticket worktree branches from local HEAD (worktree.baseRef: head), so starting one now\n'
  printf 'produces a ticket branch behind by the same %s commit(s). Run `git pull` first.\n' "$behind"
else
  printf 'Worktree base: %s has no commits of its own yet and is %s commit(s) behind origin/%s.\n' \
    "$branch" "$behind" "$default"
  printf 'It was branched from a local %s that was already behind (worktree.baseRef: head), so the\n' "$default"
  printf 'ticket starts %s commit(s) stale. Nothing to rebase yet -- move it forward now:\n' "$behind"
  printf '\n    git merge --ff-only origin/%s\n\n' "$default"
  printf 'and `git pull` on %s before the next `claude --worktree`.\n' "$default"
fi
exit 0
