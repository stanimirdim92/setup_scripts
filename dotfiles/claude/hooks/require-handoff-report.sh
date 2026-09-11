#!/usr/bin/env bash
# SubagentStop hook, scoped to the writing personas via their frontmatter
# `hooks: Stop:` (Claude Code converts an agent-scoped Stop to SubagentStop).
# The orchestrator otherwise takes "done" on faith; this refuses to let an
# executor or test-engineer finish until its final report carries what the
# persona already promises: verification commands *with outcomes*, a commit id
# (or an explicit no-commit with the reason), and the working-tree state.
#
# This is a shape check, not a truth check — it catches a report that skipped
# a section, not one that lies. It blocks at most once: when
# `stop_hook_active` is true the agent is already answering a block, so the
# second attempt is allowed through to avoid a loop. Any failure to read the
# transcript allows, never blocks — a broken hook must not wedge a build.
set -uo pipefail

input="$(cat)"
agent="$(jq -r '.agent_type // empty' <<<"$input" 2>/dev/null)"
active="$(jq -r '.stop_hook_active // false' <<<"$input" 2>/dev/null)"
transcript="$(jq -r '.agent_transcript_path // .transcript_path // empty' <<<"$input" 2>/dev/null)"

[ "$active" = "true" ] && exit 0
case "$agent" in
  executor|test-engineer) ;;
  *) exit 0 ;;
esac
[ -n "$transcript" ] && [ -f "$transcript" ] || exit 0

# Last assistant message, text blocks joined. Transcripts are JSONL; a line
# that is not JSON makes the slurp fail, which allows.
report="$(jq -rs '
  [ .[]
    | select((.type == "assistant") or (.message.role? == "assistant"))
    | .message.content
    | if type == "string" then .
      else ([ .[]? | select(.type == "text") | .text ] | join("\n")) end
    | select(length > 0)
  ] | last // ""' "$transcript" 2>/dev/null)" || exit 0
[ -z "$report" ] && exit 0

missing=()
if ! { grep -Eqi 'verif|check|test' <<<"$report" \
    && grep -Eqi 'pass|fail|exit|outcome|succeed|error|\bok\b|green|red|blocked|not run' <<<"$report"; }; then
  missing+=("the exact verification commands with their outcomes")
fi
grep -Eqi 'commit' <<<"$report" \
  || missing+=("the commit id, or an explicit 'no commit' with the reason")
grep -Eqi 'working[- ]tree|tree state|uncommitted|untracked|clean' <<<"$report" \
  || missing+=("the working-tree state")

if [ "${#missing[@]}" -gt 0 ]; then
  reason="Handoff report incomplete — add: $(IFS=';'; echo "${missing[*]}" | sed 's/;/; /g'). The orchestrator accepts evidence, not a completion claim."
  jq -n --arg reason "$reason" '{decision: "block", reason: $reason}'
fi
exit 0
