#!/usr/bin/env bash
# PreToolUse hook (matcher: Bash). Force-pushing to main/master always asks,
# everywhere — it's the harder-to-undo case regardless of surface. A plain
# push only asks in a local IDE session ($CLAUDE_CODE_REMOTE unset): that's
# where edits need review before they leave the machine. In Claude app /
# Claude Code on the web ($CLAUDE_CODE_REMOTE=true), plain pushes go through
# without asking — that surface is fine pushing on its own.
# This asks rather than hard-denies (unlike block-destructive-bash.sh) —
# see https://code.claude.com/docs/en/hooks.
set -euo pipefail

input="$(cat)"
command="$(jq -r '.tool_input.command // empty' <<<"$input")"
cwd="$(jq -r '.cwd // empty' <<<"$input")"

[ -z "$command" ] && exit 0

# dotfiles/.gitconfig defines a large family of shortcut/typo aliases that
# expand to `push` (and `fu` -> `push --force-with-lease -u`), so a grep for
# the spelled-out command lets `git fu` and `git ps` straight through.
# Expand them before matching. Keep this list in sync with the [alias]
# section of dotfiles/.gitconfig; the destructive aliases live in
# block-destructive-bash.sh. Note `git help.autocorrect = 1` can still run a
# near-miss typo that no fixed list covers.
command="$(sed -E \
  -e 's/\bgit[[:space:]]+fu\b/git push --force-with-lease -u/g' \
  -e 's/\bgit[[:space:]]+(pish|poush|ps|psuh|puhs|puosh|pus|pushy|toyou|tpush|upsh)\b/git push/g' \
  <<<"$command")"

ask() {
  jq -n --arg reason "$1" '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "ask",
      permissionDecisionReason: $reason
    }
  }'
  exit 0
}

! echo "$command" | grep -Eq 'git[[:space:]]+push\b' && exit 0

if echo "$command" | grep -Eq '(--force([[:space:]]|$)|--force-with-lease|[[:space:]]-f([[:space:]]|$))'; then
  # An alias-expanded force push (`git fu`) carries no refspec, so the branch
  # it targets isn't in the command text — resolve the checked-out branch to
  # catch a force push to main/master that never spells the name out.
  branch=""
  if [ -n "$cwd" ]; then
    branch="$(git -C "$cwd" rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
  fi

  if echo "$command" | grep -Eq '(main|master)' \
    || [ "$branch" = "main" ] || [ "$branch" = "master" ]; then
    ask "Force-push to main/master — confirm this is intentional."
  fi
fi

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  ask "git push from a local IDE session — confirm before pushing so edits get reviewed first."
fi

exit 0
