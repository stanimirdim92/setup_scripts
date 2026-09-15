#!/usr/bin/env bash
# SessionStart hook (matcher: startup|resume). Warns when the checkout you are
# about to start a ticket from is behind its remote default branch.
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
# Deliberately narrow, because a warning that fires when nothing is wrong gets
# ignored: only when the checkout sits ON the default branch and is behind it.
# Being behind origin/main on a ticket branch is normal mid-ticket and says
# nothing.
#
# SessionStart cannot block; plain stdout becomes context. Exit 0 always --
# a session must never fail to start because this hook had a bad day.
set -uo pipefail

input="$(cat 2>/dev/null)" || exit 0
cwd="$(jq -r '.cwd // empty' <<<"$input" 2>/dev/null)"
[ -n "$cwd" ] && [ -d "$cwd" ] || exit 0
cd "$cwd" 2>/dev/null || exit 0

git rev-parse --git-dir >/dev/null 2>&1 || exit 0
git remote get-url origin >/dev/null 2>&1 || exit 0

# The default branch as origin reports it; fall back to the usual names.
default="$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null)"
default="${default#origin/}"
if [ -z "$default" ]; then
  for candidate in main master; do
    git show-ref --verify --quiet "refs/remotes/origin/$candidate" && { default="$candidate"; break; }
  done
fi
[ -n "$default" ] || exit 0

branch="$(git symbolic-ref --quiet --short HEAD 2>/dev/null)" || exit 0
[ "$branch" = "$default" ] || exit 0   # on a ticket branch: nothing to say

# A cached origin ref is only as fresh as the last fetch, so a stale cache
# would report "up to date" while being days behind. Refresh when the last
# fetch is over an hour old, capped at 5s the way Claude Code caps its own
# `fresh` base resolution, falling back to the cache when the network is gone.
# An hour rather than a day because this only runs while sitting on the default
# branch -- which is when a ticket is about to start, and the one moment the
# five seconds is worth spending.
fetch_head="$(git rev-parse --git-common-dir 2>/dev/null)/FETCH_HEAD"
if [ ! -f "$fetch_head" ] || [ -n "$(find "$fetch_head" -mmin +60 2>/dev/null)" ]; then
  timeout 5 git fetch --quiet origin "$default" >/dev/null 2>&1 || true
fi

behind="$(git rev-list --count "HEAD..origin/$default" 2>/dev/null)" || exit 0
[ "${behind:-0}" -gt 0 ] 2>/dev/null || exit 0

printf 'Worktree base: this checkout is on %s and is %s commit(s) behind origin/%s.\n' \
  "$branch" "$behind" "$default"
printf 'A ticket worktree branches from local HEAD (worktree.baseRef: head), so starting one now\n'
printf 'produces a ticket branch behind by the same %s commit(s). Run `git pull` first.\n' "$behind"
exit 0
