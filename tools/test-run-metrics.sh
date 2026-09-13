#!/usr/bin/env bash
# Fixture tests for the LARGE TOOL RESULTS section of tools/run-metrics.sh.
# Builds a JSONL transcript by hand — main-session Read/Bash/Grep results of
# known sizes plus a subagent (isSidechain) result that must not count — runs
# the script on it, and checks the printed figures:
#   threshold  — default 350, --large-lines override, non-number rejected
#   scope      — --until drops results outside the window
#   exclusion  — subagent results never count as main-session context
#   shape      — string and array-form tool_result content both measure
#
# Run: tools/test-run-metrics.sh
set -uo pipefail

SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/run-metrics.sh"
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

echo "run-metrics: $PASS passed, $FAIL failed"
if [ "$FAIL" -gt 0 ]; then
  printf '\n'; for f in "${FAILED[@]}"; do echo "  FAIL $f"; done; exit 1
fi
