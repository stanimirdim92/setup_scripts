#!/usr/bin/env bash
# Reports actual run metrics from a Claude Code transcript: tool-call batching,
# token usage, the main-session/subagent split, and the main-session tool
# results large enough to be whole files read inline. Read-only.
#
# Every number here is measured, never estimated — see
# dotfiles/claude/references/agent-run-metrics.md.
#
# Usage:
#   tools/run-metrics.sh                      # most recent session, this project
#   tools/run-metrics.sh <session.jsonl>
#   tools/run-metrics.sh --list               # sessions for this project
#   tools/run-metrics.sh --since 2026-08-29T14:00 --until 2026-08-29T15:30
#   tools/run-metrics.sh --large-lines 500    # large-result threshold (default 350)
#   tools/run-metrics.sh --row LD-412 /build --since ... --until ...
#                                             # one docs/observation-log.md row
#
# Scope one BUILD by passing --since (the /build invocation) and --until
# (BUILD COMPLETE); without them the whole session is reported.
# Transcript timestamps are UTC - convert from local time before comparing.
set -euo pipefail

command -v jq >/dev/null || { echo "run-metrics: jq is required" >&2; exit 1; }

PROJECTS="${CLAUDE_PROJECTS_DIR:-$HOME/.claude/projects}"
SINCE="" ; UNTIL="" ; FILE="" ; LIST=0 ; LARGE=350 ; ROW_TICKET="" ; ROW_STAGE=""

# Claude Code's project-dir slug replaces both "/" and "_" with "-".
slug() { printf '%s' "$PWD" | sed 's|[/_]|-|g'; }

while [ $# -gt 0 ]; do
  case "$1" in
    --since) SINCE="${2:?--since needs a timestamp}"; shift 2 ;;
    --until) UNTIL="${2:?--until needs a timestamp}"; shift 2 ;;
    --large-lines) LARGE="${2:?--large-lines needs a number}"; shift 2 ;;
    --list)  LIST=1; shift ;;
    --row)   ROW_TICKET="${2:?--row needs TICKET STAGE}"; ROW_STAGE="${3:?--row needs TICKET STAGE}"; shift 3 ;;
    -h|--help) sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*) echo "run-metrics: unknown option $1" >&2; exit 1 ;;
    *)  FILE="$1"; shift ;;
  esac
done

case "$LARGE" in
  ''|*[!0-9]*) echo "run-metrics: --large-lines needs a whole number, got '$LARGE'" >&2; exit 1 ;;
esac

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

# --row prints one Run metrics row for docs/observation-log.md and nothing
# else. Only measured columns are filled; the rest say FILL and name their
# source, so a guess can never pass for a measurement.
if [ -n "$ROW_TICKET" ]; then
  jq -rs --arg since "$SINCE" --arg until "$UNTIL" --argjson large "$LARGE" \
         --arg ticket "$ROW_TICKET" --arg stage "$ROW_STAGE" --arg fallback "${SINCE:-$SPAN_LAST}" '
    def inwin: (($since == "") or (.timestamp >= $since))
           and (($until == "") or (.timestamp <= $until));
    def main: ((.isSidechain // false) | not);
    def human: if . >= 1000000 then "\((. / 10000 | round) / 100)M"
               elif . >= 1000 then "\(. / 1000 | round)k" else tostring end;
    [ .[] | select(inwin) ] as $w
    | ([ $w[] | select(.message.usage) | .message.usage ]) as $u
    | ([ $w[] | select(.type=="assistant" and main and (.message.content|type=="array"))
         | .message.content[] | select(.type=="tool_use" and (.name=="Agent" or .name=="Task"))
         | (.input.subagent_type // .input.agent_type // "") ] ) as $agents
    | ([ $agents[] | select(. == "repo-recon") ] | length) as $recon
    | ([ $w[] | select(.type=="assistant" and main and (.message.content|type=="array"))
         | .message.content[] | select(.type=="tool_use") | .id ]) as $ids
    | ([ $w[] | select(.type=="user" and main and (.message.content|type=="array"))
         | .message.content[] | select(.type=="tool_result") | select(.tool_use_id as $i | $ids | index($i))
         | (.content | if type=="string" then . elif type=="array" then (map(.text // "") | join("\n")) else "" end)
         | ([scan("\n")] | length) + (if endswith("\n") or . == "" then 0 else 1 end)
         | select(. > $large) ] | length) as $over
    | "| \($fallback[0:10]) | \($ticket) | `\($stage)` | "
      + (if $recon > 0 then "Yes (\($recon))" else "No" end)
      + " | FILL: subagent reports (capped?) | "
      + (if $stage == "/build" then "FILL: BUILD report" else "n/a" end)
      + " | \($u | map(.output_tokens // 0) | add // 0 | human) out · \($u | map(.cache_read_input_tokens // 0) | add // 0 | human) cache read"
      + " | FILL: /cost | \($over) |"
  ' "$FILE"
  exit 0
fi

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

# A tool result is the text that actually entered the context, so its size is
# measured from the transcript, not from the file on disk (which may have
# changed since, or be a command's output with no file at all). Subagent
# results (isSidechain) are their own context and are excluded.
echo
echo "LARGE TOOL RESULTS - main session (threshold: $LARGE lines)"
jq -rs --arg since "$SINCE" --arg until "$UNTIL" --argjson large "$LARGE" '
  def inwin: (($since == "") or (.timestamp >= $since))
         and (($until == "") or (.timestamp <= $until));
  def main: ((.isSidechain // false) | not);
  def rpad($w): tostring | (" " * ($w - length)) + .;
  def lpad($w): tostring | . + (" " * ($w - length));

  ([ .[] | select(.type=="assistant" and main and (.message.content|type=="array")) | select(inwin)
     | .message.content[] | select(.type=="tool_use")
     | {key: .id, value: {t: .name,
        target: ((.input.file_path // .input.command // .input.pattern // "") | tostring | .[0:72])}} ]
   | from_entries) as $uses
  | [ .[] | select(.type=="user" and main and (.message.content|type=="array")) | select(inwin)
      | .message.content[] | select(.type=="tool_result") | select($uses[.tool_use_id] != null)
      | (.content | if type=="string" then . elif type=="array" then (map(.text // "") | join("\n")) else "" end) as $c
      | ([$c | scan("\n")] | length) as $nl
      | {t: $uses[.tool_use_id].t, target: $uses[.tool_use_id].target,
         lines: (if $c == "" then 0 elif ($c | endswith("\n")) then $nl else $nl + 1 end)} ] as $res
  | if ($res|length) == 0 then "  (no tool results)"
    else ([$res[] | select(.lines > $large)]) as $over
      | "  tool results   : \($res|length)  (\($res | group_by(.t) | map("\(.[0].t) \(length)") | join(" · ")))",
        "  over threshold : \($over|length)",
        "  lines in those : \($over | map(.lines) | add // 0)",
        "  largest:",
        ($res | sort_by(-.lines) | .[:5][]
          | "  \(.lines | rpad(6)) lines  \(.t | .[0:6] | lpad(6))  \(.target)")
    end
' "$FILE"

# Failure signals: the things a failure row in docs/observation-log.md is made
# of, pulled from the transcript instead of noticed by eye. Main session and
# subagents both count -- a subagent's denied read is still a failure. The
# observation that motivated this: a /plan run had 15 of 23 tool results denied
# and reported it as a footnote; nothing counted them.
echo
echo "FAILURE SIGNALS (main session + subagents)"
jq -rs --arg since "$SINCE" --arg until "$UNTIL" '
  def inwin: (($since == "") or (.timestamp >= $since))
         and (($until == "") or (.timestamp <= $until));
  def text: if type=="string" then . elif type=="array" then (map(.text // "") | join("\n")) else "" end;
  [ .[] | select(inwin) ] as $w
  | ([ $w[] | select(.type=="assistant" and (.message.content|type=="array"))
       | .message.content[] | select(.type=="tool_use")
       | {key: .id, value: {t: .name, target: ((.input.file_path // .input.command // .input.pattern // .input.subagent_type // "") | tostring | .[0:72])}} ]
     | from_entries) as $uses
  | [ $w[] | select(.type=="user" and (.message.content|type=="array"))
      | .message.content[] | select(.type=="tool_result" and .is_error == true)
      | {t: ($uses[.tool_use_id].t // "?"), target: ($uses[.tool_use_id].target // ""), c: (.content | text)} ] as $err
  | [ $err[] | select(.c | test("denied|refus|not permitted|blocked|outside (the )?(allowed|working)"; "i")) ] as $deny
  | ([ $w[] | (.message.content? // .content? // "") | text | select(test("Handoff report incomplete")) ] | length) as $handoff
  | ([ $w[] | select(.type=="user" and (.message.content|type=="array")) | .message.content[]
       | select(.type=="tool_result") | (.content | text)
       | select(test("max(imum)?[ _-]?turns|turn (limit|cap)"; "i")) ] | length) as $capped
  | ([ $w[] | select(.type=="assistant" and (.message.content|type=="array")) | .message.content[]
       | select(.type=="tool_use" and .name=="Bash") | .input.command // "" ]
     | group_by(.) | map(select(length >= 3)) | map({cmd: .[0][0:72], n: length})) as $repeats
  | "  errored tool results : \($err|length)" + (if ($err|length) > 0 then "  (\($err | group_by(.t) | map("\(.[0].t) \(length)") | join(" · ")))" else "" end),
    "  denials / blocks     : \($deny|length)",
    ( $deny[:5][] | "    \(.t | .[0:6])  \(.target)" ),
    "  handoff-gate blocks  : \($handoff)",
    "  turn-cap mentions    : \($capped)",
    "  repeated commands    : \($repeats|length)  (same Bash command 3+ times: a blind-retry signal)",
    ( $repeats[:5][] | "    \(.n)x  \(.cmd)" )
' "$FILE"

cat <<'NOTE'

Reading this: a mean near 1.00 with few batched requests means independent
read-only operations went out one per turn, each paying a full context re-read.
Cost only - the same calls still execute. See
dotfiles/claude/skills/executor-development-discipline/SKILL.md and
dotfiles/claude/agents/repo-recon.md for the guidance this measures.

Failure signals are counts, not verdicts: a denial can be a guard working as
intended. Each one is a candidate failure row for docs/observation-log.md --
read the run, then record it or dismiss it.

Large tool results are whole files or command output the main session took
into context. Over the threshold they are the reads a bounded check or a
repo-recon dispatch is meant to keep out of it
(dotfiles/claude/references/repository-precedent.md §1). Count only - a large
result is not wrong by itself; an edit needs the exact lines.
NOTE
