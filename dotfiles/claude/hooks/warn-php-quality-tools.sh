#!/usr/bin/env bash
# PreToolUse hook (matcher: Bash). Laravel Pint, PHPStan, and Deptrac must
# never auto-run — always ask first, however the command is invoked
# (vendor/bin/, ./vendor/bin/, php vendor/bin/, composer run ...). The
# user denies these most of the time, so a silent auto-run is usually the
# wrong call, not a convenience worth defaulting to.
# This asks rather than hard-denies (unlike block-destructive-bash.sh) —
# see https://code.claude.com/docs/en/hooks.
set -euo pipefail

input="$(cat)"
command="$(jq -r '.tool_input.command // empty' <<<"$input")"

[ -z "$command" ] && exit 0

if echo "$command" | grep -Eq '\b(pint|phpstan|deptrac)\b'; then
  jq -n '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "ask",
      permissionDecisionReason: "Pint/PHPStan/Deptrac — confirm before running, do not auto-run these."
    }
  }'
  exit 0
fi

exit 0
