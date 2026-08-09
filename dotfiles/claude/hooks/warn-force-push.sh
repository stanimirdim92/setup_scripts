#!/usr/bin/env bash
# PreToolUse hook (matcher: Bash). Force-pushing to main/master isn't always
# wrong, so this asks for confirmation instead of hard-denying (unlike
# block-destructive-bash.sh). See https://code.claude.com/docs/en/hooks.
set -euo pipefail

input="$(cat)"
command="$(jq -r '.tool_input.command // empty' <<<"$input")"

[ -z "$command" ] && exit 0

if echo "$command" | grep -Eq 'git[[:space:]]+push' \
  && echo "$command" | grep -Eq '(--force([[:space:]]|$)|--force-with-lease|[[:space:]]-f([[:space:]]|$))' \
  && echo "$command" | grep -Eq '(main|master)'; then
  jq -n '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "ask",
      permissionDecisionReason: "Force-push to main/master — confirm this is intentional."
    }
  }'
  exit 0
fi

exit 0
