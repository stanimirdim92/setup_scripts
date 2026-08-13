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

[ -z "$command" ] && exit 0

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

if echo "$command" | grep -Eq '(--force([[:space:]]|$)|--force-with-lease|[[:space:]]-f([[:space:]]|$))' \
  && echo "$command" | grep -Eq '(main|master)'; then
  ask "Force-push to main/master — confirm this is intentional."
fi

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  ask "git push from a local IDE session — confirm before pushing so edits get reviewed first."
fi

exit 0
