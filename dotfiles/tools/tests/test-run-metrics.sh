#!/usr/bin/env bash
# Fixture tests for the LARGE TOOL RESULTS section of dotfiles/tools/run/run-metrics.sh,
# for --row, the observation-log row it prints, and for FAILURE SIGNALS.
# Builds a JSONL transcript by hand — main-session Read/Bash/Grep results of
# known sizes plus a subagent (isSidechain) result that must not count — runs
# the script on it, and checks the printed figures:
#   threshold  — default 350, --large-lines override, non-number rejected
#   scope      — --until drops results outside the window
#   exclusion  — subagent results never count as main-session context
#   shape      — string and array-form tool_result content both measure
#
# Run: dotfiles/tools/tests/test-run-metrics.sh
set -uo pipefail

SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../run" && pwd)/run-metrics.sh"
command -v jq >/dev/null || { echo "test-run-metrics: jq is required" >&2; exit 1; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0; FAILED=()

lines() { seq 1 "$1" | awk '{print $1"\tline "$1}'; }   # numbered like a Read result

# Records carry only the fields run-metrics.sh reads: type, timestamp,
# isSidechain, requestId, message.content, message.usage.
call() { # ts, sidechain, requestId, id, tool, input-json
  jq -nc --arg ts "$1" --argjson sc "$2" --arg r "$3" --arg id "$4" --arg t "$5" --argjson in "$6" \
    '{type:"assistant",timestamp:$ts,isSidechain:$sc,requestId:$r,
      message:{role:"assistant",content:[{type:"tool_use",id:$id,name:$t,input:$in}],
               usage:{input_tokens:10,output_tokens:5}}}'
}
result() { # ts, sidechain, id, content (string form)
  jq -nc --arg ts "$1" --argjson sc "$2" --arg id "$3" --arg c "$4" \
    '{type:"user",timestamp:$ts,isSidechain:$sc,
      message:{role:"user",content:[{type:"tool_result",tool_use_id:$id,content:$c}]}}'
}
result_blocks() { # ts, sidechain, id, content (array-of-text-blocks form)
  jq -nc --arg ts "$1" --argjson sc "$2" --arg id "$3" --arg c "$4" \
    '{type:"user",timestamp:$ts,isSidechain:$sc,
      message:{role:"user",content:[{type:"tool_result",tool_use_id:$id,content:[{type:"text",text:$c}]}]}}'
}

T="$TMP/session.jsonl"
{
  # r1: two Reads batched in one request — one whole 1200-line file, one small.
  call   2026-09-13T10:00:00Z false r1 A Read '{"file_path":"/w/big.ts"}'
  call   2026-09-13T10:00:00Z false r1 C Read '{"file_path":"/w/small.ts"}'
  result 2026-09-13T10:00:01Z false A "$(lines 1200)"
  result 2026-09-13T10:00:01Z false C "$(lines 40)"
  # r2: the same file through Bash.
  call   2026-09-13T10:05:00Z false r2 B Bash '{"command":"cat /w/big.ts"}'
  result 2026-09-13T10:05:01Z false B "$(lines 800)"
  # r3: a subagent reading a huge file — its own context, not the main session's.
  call   2026-09-13T10:06:00Z true  r3 D Read '{"file_path":"/w/huge.ts"}'
  result 2026-09-13T10:06:01Z true  D "$(lines 5000)"
  # r4: array-form tool_result content, small.
  call          2026-09-13T10:07:00Z false r4 E Grep '{"pattern":"TODO"}'
  result_blocks 2026-09-13T10:07:01Z false E "$(lines 10)"
} > "$T"

EMPTY="$TMP/empty.jsonl"
{
  jq -nc '{type:"user",timestamp:"2026-09-13T10:00:00Z",message:{role:"user",content:"hello"}}'
  jq -nc '{type:"assistant",timestamp:"2026-09-13T10:00:01Z",requestId:"r1",
           message:{role:"assistant",content:[{type:"text",text:"hi"}],usage:{input_tokens:1,output_tokens:1}}}'
} > "$EMPTY"

run() { bash "$SCRIPT" "$@" 2>&1; }

check() { # label, expected substring, output
  if grep -qF -- "$2" <<<"$3"; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); FAILED+=("[$1] expected to find: $2"); fi
}
check_absent() { # label, forbidden substring, output
  if grep -qF -- "$2" <<<"$3"; then FAIL=$((FAIL+1)); FAILED+=("[$1] must not contain: $2"); else PASS=$((PASS+1)); fi
}

OUT="$(run "$T")"
check default_header        'LARGE TOOL RESULTS - main session (threshold: 350 lines)' "$OUT"
check default_count         'tool results   : 4  (Bash 1 · Grep 1 · Read 2)'          "$OUT"
check default_over          'over threshold : 2'                                          "$OUT"
check default_lines         'lines in those : 2000'                                       "$OUT"
check largest_read          '  1200 lines  Read    /w/big.ts'                             "$OUT"
check largest_bash          '   800 lines  Bash    cat /w/big.ts'                         "$OUT"
check_absent subagent_excluded 'huge.ts'                                                  "$OUT"
check array_content_counted '    10 lines  Grep    TODO'                                  "$OUT"

OUT="$(run --large-lines 2000 "$T")"
check override_header       '(threshold: 2000 lines)' "$OUT"
check override_none_over    'over threshold : 0'      "$OUT"
check override_lines        'lines in those : 0'      "$OUT"

OUT="$(run --large-lines 30 "$T")"
check low_threshold_over    'over threshold : 3'      "$OUT"   # 1200, 800, 40

OUT="$(run --until 2026-09-13T10:04:00Z "$T")"                # r1 only
check window_over           'over threshold : 1'          "$OUT"
check window_count          'tool results   : 2  (Read 2)' "$OUT"

OUT="$(run "$EMPTY")"
check no_results            '(no tool results)'       "$OUT"

if run --large-lines abc "$T" >/dev/null; then
  FAIL=$((FAIL+1)); FAILED+=("[bad_threshold] --large-lines abc must exit non-zero")
else PASS=$((PASS+1)); fi
check bad_threshold_msg     '--large-lines needs a whole number' "$(run --large-lines abc "$T")"

# --row: one observation-log row; measured columns filled, the rest FILL.
OUT="$(run --row LD-412 /spec "$T")"
check row_shape     '| 2026-09-13 | LD-412 | `/spec` | No | FILL: subagent reports (capped?) | n/a | 20 out · 0 cache read | FILL: /cost | 2 |' "$OUT"
check_absent row_only 'TOOL BATCHING' "$OUT"
OUT="$(run --row LD-412 /spec --until 2026-09-13T10:04:00Z "$T")"
check row_window    '| 1 |' "$OUT"

R="$TMP/recon.jsonl"
{
  call 2026-09-14T09:00:00Z false q1 G Agent '{"subagent_type":"repo-recon","prompt":"survey"}'
  call 2026-09-14T09:00:00Z false q1 H Agent '{"subagent_type":"repo-recon","prompt":"survey 2"}'
  jq -nc '{type:"assistant",timestamp:"2026-09-14T09:10:00Z",requestId:"q2",
           message:{role:"assistant",content:[{type:"text",text:"done"}],
                    usage:{input_tokens:1,output_tokens:109000,cache_read_input_tokens:3070000}}}'
} > "$R"
OUT="$(run --row LD-380 /build "$R")"
check row_recon     '| Yes (2) |' "$OUT"
check row_build     '| FILL: BUILD report |' "$OUT"
check row_tokens    '109k out · 3.07M cache read' "$OUT"
check row_date      '| 2026-09-14 |' "$OUT"

# FAILURE SIGNALS: errored and denied tool results, handoff blocks, turn caps,
# and repeated commands, from main session and subagents alike.
S="$TMP/signals.jsonl"
err() { # ts, sidechain, id, content
  jq -nc --arg ts "$1" --argjson sc "$2" --arg id "$3" --arg c "$4" \
    '{type:"user",timestamp:$ts,isSidechain:$sc,
      message:{role:"user",content:[{type:"tool_result",tool_use_id:$id,is_error:true,content:$c}]}}'
}
{
  call 2026-09-15T08:00:00Z true  s1 R1 Read '{"file_path":"/home/u/.claude/references/plan-quality-gates.md"}'
  err  2026-09-15T08:00:01Z true  R1 "Permission to read this file was denied."
  call 2026-09-15T08:01:00Z false s2 B1 Bash '{"command":"php artisan test"}'
  err  2026-09-15T08:01:01Z false B1 "Tests failed: 2 errors"
  for i in 1 2 3; do
    call 2026-09-15T08:0${i}:30Z false "s3$i" "C$i" Bash '{"command":"yarn test"}'
    result 2026-09-15T08:0${i}:31Z false "C$i" "1 failing"
  done
  jq -nc '{type:"user",timestamp:"2026-09-15T08:05:00Z",message:{role:"user",content:"Stop hook feedback: Handoff report incomplete — add: the working-tree state."}}'
  call 2026-09-15T08:06:00Z false s4 A1 Agent '{"subagent_type":"repo-recon","prompt":"survey"}'
  result 2026-09-15T08:07:00Z false A1 "Survey partial: reached maxTurns (100). Not surveyed: billing."
} > "$S"
OUT="$(run "$S")"
check signals_errors   'errored tool results : 2  (Bash 1 · Read 1)' "$OUT"
check signals_denials  'denials / blocks     : 1' "$OUT"
check signals_target   'plan-quality-gates.md' "$OUT"
check signals_handoff  'handoff-gate blocks  : 1' "$OUT"
check signals_capped   'turn-cap mentions    : 1' "$OUT"
check signals_repeat   '3x  yarn test' "$OUT"
OUT="$(run "$T")"
check signals_clean    'errored tool results : 0' "$OUT"

# Sandbox failures are not guard denials: a bwrap error is the command sandbox
# failing, and the same command works when rerun outside it.
B="$TMP/sandbox.jsonl"
{
  call 2026-09-16T08:00:00Z false b1 X1 Bash '{"command":"sleep 1"}'
  err  2026-09-16T08:00:01Z false X1 "bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted"
} > "$B"
OUT="$(run "$B")"
check sandbox_counted  'sandbox failures     : 1' "$OUT"
check sandbox_not_deny 'denials / blocks     : 0' "$OUT"

# Subagent transcripts live in <session>/subagents/, beside the main one.
M="$TMP/main.jsonl"
mkdir -p "$TMP/main/subagents"
{
  call   2026-09-17T09:00:00Z false m1 M1 Agent '{"subagent_type":"repo-recon","prompt":"survey"}'
  result 2026-09-17T09:05:00Z false M1 "survey done"
} > "$M"
{
  call   2026-09-17T09:01:00Z true sa1 S1 Read '{"file_path":"/w/a.ts"}'
  call   2026-09-17T09:01:00Z true sa1 S2 Read '{"file_path":"/w/b.ts"}'
  result 2026-09-17T09:01:01Z true S1 "a"
  result 2026-09-17T09:01:01Z true S2 "b"
} > "$TMP/main/subagents/agent-x.jsonl"
OUT="$(run "$M")"
check subagent_files   'subagents  : 1 transcript(s)' "$OUT"
check subagent_batch   'largest batch  : 2' "$OUT"
check subagent_tokens  'output         : 10' "$OUT"   # one usage per reply, not per record
check subagent_main    'tool results   : 1  (Agent 1)' "$OUT"

# Each content block of one reply is its own record and repeats the reply's
# usage; the totals count it once.
D="$TMP/dup.jsonl"
for b in text tool tool; do
  jq -nc --arg b "$b" '{type:"assistant",timestamp:"2026-09-18T09:00:00Z",requestId:"d1",
    message:{id:"msg_1",role:"assistant",content:[{type:"text",text:$b}],
             usage:{input_tokens:3,output_tokens:400,cache_read_input_tokens:90000}}}'
done > "$D"
OUT="$(run "$D")"
check usage_once_out   'output         : 400' "$OUT"
check usage_once_cache 'cache read     : 90000' "$OUT"

# The project folder: every non-alphanumeric character of the cwd becomes "-",
# the "." of .claude/worktrees included.
W="$TMP/repo/.claude/worktrees/LD-1_x"
mkdir -p "$W" "$TMP/projects/$(printf '%s' "$W" | sed 's|[^A-Za-z0-9]|-|g')"
cp "$M" "$TMP/projects/$(printf '%s' "$W" | sed 's|[^A-Za-z0-9]|-|g')/s.jsonl"
OUT="$(cd "$W" && CLAUDE_PROJECTS_DIR="$TMP/projects" bash "$SCRIPT" 2>&1)"
check slug_dot         'subagents  : 0 transcript(s)' "$OUT"
check_absent slug_dot_found 'no transcripts at' "$OUT"

echo "run-metrics: $PASS passed, $FAIL failed"
if [ "$FAIL" -gt 0 ]; then
  printf '\n'; for f in "${FAILED[@]}"; do echo "  FAIL $f"; done; exit 1
fi
