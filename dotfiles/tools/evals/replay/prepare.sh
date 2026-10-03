#!/usr/bin/env bash
# Prepare a replay of a shipped ticket: a standalone checkout of the project as
# it was before the ticket's first commit, with none of the later history.
#
#   prepare.sh PROJECT TICKET_REGEX DEST
#   prepare.sh /var/www/html/leadbuster 'LD-44[012]' /var/www/html/replay-LD-440
#
# Why a shallow clone and not a worktree: a worktree shares the project's
# object store, so a session could `git show main:docs/specs/...` and read the
# answer. A depth-1 clone of the base commit holds no later commit at all.
# The clone gets no remote, so nothing in it can be pushed and the stale-base
# hook has nothing to compare against. Gitignored files the project lists in
# .worktreeinclude (.env and the like) are copied from PROJECT.
set -euo pipefail

usage() { sed -n '2,8p' "$0" | sed 's/^# \{0,1\}//'; }
[ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ] && { usage; exit 0; }
[ $# -eq 3 ] || { usage >&2; exit 1; }
PROJECT="$(cd "$1" && pwd)"; REGEX="$2"; DEST="$3"

[ -e "$DEST" ] && { echo "replay: $DEST already exists; remove it or pick another path" >&2; exit 1; }
first="$(git -C "$PROJECT" log --all --reverse -E -i --grep="$REGEX" --format=%H | head -1)"
[ -n "$first" ] || { echo "replay: no commit message matches $REGEX" >&2; exit 1; }
base="$(git -C "$PROJECT" rev-parse "$first^")"
branch="replay/$(echo "$REGEX" | tr -c 'A-Za-z0-9-' '-' | sed 's/-*$//')"

git -C "$PROJECT" branch -f "$branch" "$base" >/dev/null
git clone -q --depth 1 --single-branch --branch "$branch" "file://$PROJECT" "$DEST"
git -C "$PROJECT" branch -D "$branch" >/dev/null
git -C "$DEST" remote remove origin

copied=0
if [ -f "$PROJECT/.worktreeinclude" ]; then
  while IFS= read -r -d '' f; do
    mkdir -p "$DEST/$(dirname "$f")"
    cp -p "$PROJECT/$f" "$DEST/$f"
    copied=$((copied + 1))
  done < <(git -C "$PROJECT" ls-files -z --others --ignored --exclude-from=.worktreeinclude)
fi

cat <<MSG
replay: $DEST
  base      $(git -C "$PROJECT" log -1 --format='%h %ad %s' --date=short "$base")
  first     $(git -C "$PROJECT" log -1 --format='%h %ad %s' --date=short "$first")
  branch    $branch (no remote, depth 1)
  copied    $copied gitignored file(s) from .worktreeinclude
Next: cd $DEST, install dependencies (bin/worktree-setup.sh if the project has it), then start claude.
MSG
