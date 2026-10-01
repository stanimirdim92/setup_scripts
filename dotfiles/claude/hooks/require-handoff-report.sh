#!/usr/bin/env bash
# SubagentStop hook, scoped to the writing personas via their frontmatter
# `hooks: Stop:` (Claude Code converts an agent-scoped Stop to SubagentStop).
# The orchestrator otherwise takes "done" on faith; this refuses to let an
# executor or test-engineer finish until its final report carries what the
# persona already promises: verification commands *with outcomes*, a commit id
# (or an explicit no-commit with the reason), and the working-tree state.
#
# It also catches the early stop Opus 5.5 is prone to on long tasks: a turn
# that ends by announcing the next step ("Next, I'll …") without taking it and
# without naming a blocker.
#
# This is a shape check, not a truth check — it catches a report that skipped
# a section, not one that lies. It blocks at most twice per agent run (the
# 2–3 automatic continuations Anthropic's Opus 5.5 guide recommends): a
# counter in the state directory, keyed by agent id, tracks the blocks this
# hook issued, and a third stop is allowed through so a stuck run ends and
# can be reviewed. A stop_hook_active stop with no counter belongs to some
# other hook's loop and is allowed. Any failure to read the transcript
# allows, never blocks — a broken hook must not wedge a build.
set -uo pipefail
MAX_BLOCKS=2

input="$(cat)"
agent="$(jq -r '.agent_type // empty' <<<"$input" 2>/dev/null)"
active="$(jq -r '.stop_hook_active // false' <<<"$input" 2>/dev/null)"
transcript="$(jq -r '.agent_transcript_path // .transcript_path // empty' <<<"$input" 2>/dev/null)"
key="$(jq -r '.agent_id // .session_id // empty' <<<"$input" 2>/dev/null)"

case "$agent" in
  executor|test-engineer) ;;
  *) exit 0 ;;
esac
[ -n "$key" ] || key="$(printf '%s' "$transcript" | cksum | cut -d' ' -f1)"
key="$(printf '%s' "$key" | tr -c 'A-Za-z0-9._-' '_')"
state_dir="${HARNESS_HANDOFF_STATE_DIR:-${TMPDIR:-/tmp}/harness-handoff-hook}"
counter="$state_dir/$key"
blocks="$(cat "$counter" 2>/dev/null || echo 0)"
case "$blocks" in ''|*[!0-9]*) blocks=0 ;; esac
if [ "$blocks" -ge "$MAX_BLOCKS" ] || { [ "$active" = "true" ] && [ "$blocks" -eq 0 ]; }; then
  rm -f "$counter"
  exit 0
fi
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

# First-person intent to keep going, with no blocker named. A pointer to the
# next stage ("next: /review") is not first person and does not match.
if grep -Eqi "(next,? i('ll| will)|i('ll| will) now|now i('ll| will)|let me now|i'm going to|i am going to)" <<<"$report" \
  && ! grep -Eqi 'blocker|blocked|cannot proceed|can.t proceed|waiting (on|for)|needs? (your|the user|a human)' <<<"$report"; then
  missing+=("the step you announced — do it now, or state the blocker that stops it")
fi

if [ "${#missing[@]}" -gt 0 ]; then
  mkdir -p "$state_dir" 2>/dev/null && echo $((blocks + 1)) > "$counter" 2>/dev/null
  reason="Handoff report incomplete — add: $(IFS=';'; echo "${missing[*]}" | sed 's/;/; /g'). The orchestrator accepts evidence, not a completion claim."
  jq -n --arg reason "$reason" '{decision: "block", reason: $reason}'
else
  rm -f "$counter"
fi
exit 0
