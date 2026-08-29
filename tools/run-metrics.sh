#!/usr/bin/env bash
# Reports actual run metrics from a Claude Code transcript: tool-call batching,
# token usage, and the main-session/subagent split. Read-only.
#
# Every number here is measured, never estimated — see
# dotfiles/claude/references/agent-run-metrics.md.
#
# Usage:
#   tools/run-metrics.sh                      # most recent session, this project
#   tools/run-metrics.sh <session.jsonl>
#   tools/run-metrics.sh --list               # sessions for this project
#   tools/run-metrics.sh --since 2026-08-29T14:00 --until 2026-08-29T15:30
#
# Scope one BUILD by passing --since (the /build invocation) and --until
# (BUILD COMPLETE); without them the whole session is reported.
# Transcript timestamps are UTC - convert from local time before comparing.
set -euo pipefail

command -v jq >/dev/null || { echo "run-metrics: jq is required" >&2; exit 1; }

PROJECTS="${CLAUDE_PROJECTS_DIR:-$HOME/.claude/projects}"
SINCE="" ; UNTIL="" ; FILE="" ; LIST=0

# Claude Code's project-dir slug replaces both "/" and "_" with "-".
slug() { printf '%s' "$PWD" | sed 's|[/_]|-|g'; }

while [ $# -gt 0 ]; do
  case "$1" in
    --since) SINCE="${2:?--since needs a timestamp}"; shift 2 ;;
    --until) UNTIL="${2:?--until needs a timestamp}"; shift 2 ;;
    --list)  LIST=1; shift ;;
    -h|--help) sed -n '2,15p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*) echo "run-metrics: unknown option $1" >&2; exit 1 ;;
    *)  FILE="$1"; shift ;;
  esac
done

DIR="$PROJECTS/$(slug)"

if [ "$LIST" = 1 ]; then
  [ -d "$DIR" ] || { echo "run-metrics: no transcripts at $DIR" >&2; exit 1; }
  printf '%-34s  %-34s  %s\n' "FIRST RECORD (UTC)" "LAST RECORD (UTC)" "TRANSCRIPT"
  ls -1t "$DIR"/*.jsonl 2>/dev/null | while read -r f; do
    first=$(head -400 "$f" | jq -rs '[.[]|select(.timestamp)|.timestamp]|first // empty' 2>/dev/null || true)
    last=$(tail -400 "$f"  | jq -rs '[.[]|select(.timestamp)|.timestamp]|last  // empty' 2>/dev/null || true)
    printf '%-34s  %-34s  %s\n' "${first:-?}" "${last:-?}" "$f"
  done
  echo
  echo "Timestamps are UTC. Pick the transcript whose span covers your window,"
  echo "then pass it explicitly: run-metrics.sh --since ... --until ... <file>"
  exit 0
fi

if [ -z "$FILE" ]; then
  [ -d "$DIR" ] || { echo "run-metrics: no transcripts at $DIR (pass a file, or set CLAUDE_PROJECTS_DIR)" >&2; exit 1; }
  FILE="$(ls -1t "$DIR"/*.jsonl 2>/dev/null | head -1 || true)"
  [ -n "$FILE" ] || { echo "run-metrics: no .jsonl transcripts in $DIR" >&2; exit 1; }
fi
[ -r "$FILE" ] || { echo "run-metrics: cannot read $FILE" >&2; exit 1; }

SPAN_FIRST=$(head -400 "$FILE" | jq -rs '[.[]|select(.timestamp)|.timestamp]|first // empty' 2>/dev/null || true)
SPAN_LAST=$(tail -400  "$FILE" | jq -rs '[.[]|select(.timestamp)|.timestamp]|last  // empty' 2>/dev/null || true)

echo "transcript : $FILE"
echo "spans (UTC): ${SPAN_FIRST:-?} .. ${SPAN_LAST:-?}"
[ -n "$SINCE$UNTIL" ] && echo "window     : ${SINCE:-start} .. ${UNTIL:-end}"

# A window that misses this transcript entirely is the most common mistake:
# --since/--until filter ONE file, and with no file given that is the newest
# transcript, which may predate or postdate the window completely.
if [ -n "$SPAN_FIRST" ] && [ -n "$SPAN_LAST" ]; then
  if { [ -n "$UNTIL" ] && [ "$UNTIL" \< "$SPAN_FIRST" ]; } ||
     { [ -n "$SINCE" ] && [ "$SINCE" \> "$SPAN_LAST" ]; }; then
    echo
    echo "WARNING: the window does not overlap this transcript at all." >&2
    echo "         All figures below will be zero. Run --list to find the" >&2
    echo "         transcript whose span covers your window, and pass it" >&2
    echo "         explicitly. Timestamps are UTC." >&2
  fi
fi
echo

# Parallel tool calls are written as SEPARATE assistant records sharing one
# requestId. Counting per record reports mean 1.0 and zero batching regardless
# of what actually happened, so every batching figure below groups by requestId.
jq -rs --arg since "$SINCE" --arg until "$UNTIL" '
  def inwin: (($since == "") or (.timestamp >= $since))
         and (($until == "") or (.timestamp <= $until));

  def batching($rows):
    ($rows | group_by(.r) | map({n:(map(.n)|add)}) | map(select(.n>0))) as $g
    | if ($g|length) == 0 then "  (no tool calls)"
      else ($g|map(.n)|add) as $c | ($g|length) as $r
        | "  tool calls     : \($c)",
          "  requests       : \($r)",
          "  mean calls/req : \($c/$r*100|round|./100)",
          "  batched (>1)   : \($g|map(select(.n>1))|length)  (\(($g|map(select(.n>1))|length)*100/$r|floor)%)",
          "  largest batch  : \($g|map(.n)|max)"
      end;

  [ .[] | select(.type=="assistant" and .requestId and .message.content) | select(inwin)
    | {r:.requestId, side:(.isSidechain//false),
       n:(.message.content|if type=="array" then map(select(.type=="tool_use"))|length else 0 end)} ] as $all
  | [ .[] | select(.message.usage) | select(inwin) | .message.usage ] as $u

  | "TOOL BATCHING - main session", batching([$all[]|select(.side|not)]),
    "", "TOOL BATCHING - subagents", batching([$all[]|select(.side)]),
    "",
    "TOKENS (measured, all turns in window)",
    "  input          : \($u|map(.input_tokens//0)|add // 0)",
    "  output         : \($u|map(.output_tokens//0)|add // 0)",
    "  cache read     : \($u|map(.cache_read_input_tokens//0)|add // 0)",
    "  cache creation : \($u|map(.cache_creation_input_tokens//0)|add // 0)"
' "$FILE"

echo
echo "TOP SOLO-CALL TOOLS (issued alone in their request - batching candidates)"
jq -rs --arg since "$SINCE" --arg until "$UNTIL" '
  def inwin: (($since == "") or (.timestamp >= $since))
         and (($until == "") or (.timestamp <= $until));
  [ .[] | select(.type=="assistant" and .requestId and .message.content) | select(inwin)
    | .requestId as $r | .message.content | select(type=="array") | .[] | select(.type=="tool_use") | {r:$r, t:.name} ]
  | group_by(.r) | map({n:length, tool:(map(.t)|first)})
  | map(select(.n==1)) | group_by(.tool)
  | map({tool:.[0].tool, solo:length}) | sort_by(-.solo) | .[:6][]
  | "  \(.tool): \(.solo)"
' "$FILE"

cat <<'NOTE'

Reading this: a mean near 1.00 with few batched requests means independent
read-only operations went out one per turn, each paying a full context re-read.
Cost only - the same calls still execute. See
dotfiles/claude/skills/executor-development-discipline/SKILL.md and
dotfiles/claude/agents/repo-recon.md for the guidance this measures.
NOTE
