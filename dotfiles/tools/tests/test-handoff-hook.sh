#!/usr/bin/env bash
# Fixture tests for dotfiles/claude/hooks/require-handoff-report.sh, the
# SubagentStop hook on executor and test-engineer. Each case builds a JSONL
# transcript whose last assistant message or SubagentHandback call is a
# handoff report, runs the hook
# with a SubagentStop payload, and checks the decision:
#   block — report is missing a required section
#   allow — report is complete, or the hook must stay out of the way
#           (unknown agent, another hook's loop, third stop, unreadable
#           transcript)
#
# Run: dotfiles/tools/tests/test-handoff-hook.sh
set -uo pipefail

HOOK="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../claude/hooks" && pwd)/require-handoff-report.sh"
command -v jq >/dev/null || { echo "test-handoff-hook: jq is required" >&2; exit 1; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export HARNESS_HANDOFF_STATE_DIR="$TMP/state"
PASS=0; FAIL=0; FAILED=()

transcript() { # name, final assistant text  -> path
  local path="$TMP/$1.jsonl"
  {
    jq -nc '{type:"user",message:{role:"user",content:"Implement T001."}}'
    jq -nc '{type:"assistant",message:{role:"assistant",content:[{type:"text",text:"Starting."},{type:"tool_use",id:"t1",name:"Bash",input:{command:"yarn test"}}]}}'
    jq -nc --arg t "$2" '{type:"assistant",message:{role:"assistant",content:[{type:"text",text:$t}]}}'
  } > "$path"
  echo "$path"
}

handback_transcript() { # name, handback message, [text after]  -> path
  # The shape LD-507 produced: a short text before the commit, then the report
  # as a SubagentHandback tool call with no text of its own.
  local path="$TMP/$1.jsonl"
  {
    jq -nc '{type:"user",message:{role:"user",content:"Implement T001."}}'
    jq -nc '{type:"assistant",message:{role:"assistant",content:[{type:"text",text:"Committing."},{type:"tool_use",id:"t1",name:"Bash",input:{command:"git commit"}}]}}'
    jq -nc '{type:"user",message:{role:"user",content:[{type:"tool_result",tool_use_id:"t1",content:"ok"}]}}'
    jq -nc --arg m "$2" '{type:"assistant",message:{role:"assistant",content:[{type:"tool_use",id:"t2",name:"SubagentHandback",input:{message:$m}}]}}'
    jq -nc '{type:"user",message:{role:"user",content:[{type:"tool_result",tool_use_id:"t2",content:"{\"success\":true}"}]}}'
    [ -n "${3:-}" ] && jq -nc --arg t "$3" '{type:"assistant",message:{role:"assistant",content:[{type:"text",text:$t}]}}'
  } > "$path"
  echo "$path"
}

stale_handback_transcript() { # name, old handback, final text  -> path
  # A resumed run: a complete handback for T001, then more work and a bare
  # final text. The old handback must not satisfy the new stop.
  local path="$TMP/$1.jsonl"
  {
    jq -nc --arg m "$2" '{type:"assistant",message:{role:"assistant",content:[{type:"tool_use",id:"t1",name:"SubagentHandback",input:{message:$m}}]}}'
    jq -nc '{type:"user",message:{role:"user",content:"Implement T002."}}'
    jq -nc '{type:"assistant",message:{role:"assistant",content:[{type:"tool_use",id:"t2",name:"Edit",input:{file_path:"a.ts"}}]}}'
    jq -nc --arg t "$3" '{type:"assistant",message:{role:"assistant",content:[{type:"text",text:$t}]}}'
  } > "$path"
  echo "$path"
}

decision() { # agent_type, transcript, stop_hook_active, [agent_id]
  jq -n --arg a "$1" --arg t "$2" --argjson s "$3" --arg id "${4:-id-$RANDOM$RANDOM}" \
    '{hook_event_name:"SubagentStop",agent_type:$a,agent_id:$id,agent_transcript_path:$t,stop_hook_active:$s,cwd:"/tmp"}' \
    | bash "$HOOK" 2>/dev/null | jq -r '.decision // "allow"' 2>/dev/null || echo ERROR
}

check() { # label, expected, agent, transcript, active, [agent_id]
  local got; got="$(decision "$3" "$4" "$5" "${6:-}")"; [ -z "$got" ] && got=allow
  if [ "$got" = "$2" ]; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); FAILED+=("[$1] expected $2, got $got"); fi
}

COMPLETE='## Report
- Behavior implemented: Download label, callback preserved.
- Tests: verify.py label assertion updated.
- Verification: `python3 verify.py` — pass (exit 0).
- Commit: a1b2c3d "feat: rename export label".
- Working-tree state: clean.'
NO_COMMIT_EXPLAINED='Verification: yarn test — 12 passed. No commit: user requested an uncommitted result. Working tree: 2 files modified, nothing untracked.'
MISSING_COMMIT='Implemented the label change. Verification: python3 verify.py passed. Working tree clean.'
MISSING_TREE='Implemented the label change. Verification: python3 verify.py passed. Commit 9f8e7d6.'
MISSING_OUTCOMES='Implemented the change. Ran the verification. Commit 9f8e7d6. Working tree clean.'
CLAIM_ONLY='Done. Everything works as expected.'

check complete            allow executor      "$(transcript c1 "$COMPLETE")"            false
check no_commit_explained allow executor      "$(transcript c2 "$NO_COMMIT_EXPLAINED")"  false
check test_engineer_ok    allow test-engineer "$(transcript c3 "$COMPLETE")"            false
check missing_commit      block executor      "$(transcript c4 "$MISSING_COMMIT")"      false
check missing_tree        block executor      "$(transcript c5 "$MISSING_TREE")"        false
check missing_outcomes    block executor      "$(transcript c6 "$MISSING_OUTCOMES")"    false
check claim_only          block executor      "$(transcript c7 "$CLAIM_ONLY")"          false
check claim_only_tester   block test-engineer "$(transcript c8 "$CLAIM_ONLY")"          false
check other_hooks_loop    allow executor      "$(transcript c9 "$CLAIM_ONLY")"          true   # active, but no block of ours
check announced_next_step block executor "$(transcript c13 "$COMPLETE
Next, I'll update the README section.")" false
check next_step_blocked   allow executor "$(transcript c14 "$COMPLETE
I'll now wire the endpoint, but it is blocked on the missing API contract.")" false
check stage_pointer       allow executor "$(transcript c15 "$COMPLETE
Next step: /review.")" false

# Two continuations, then the third stop goes through and the counter resets.
STUCK="$(transcript c16 "$CLAIM_ONLY")"
check retry_first_block   block executor "$STUCK" false run-1
check retry_second_block  block executor "$STUCK" true  run-1
check retry_third_allows  allow executor "$STUCK" true  run-1
check retry_counter_reset block executor "$STUCK" false run-1
check complete_clears     allow executor "$(transcript c17 "$COMPLETE")" true run-1
check after_clear_fresh   block executor "$STUCK" false run-1
# Reports delivered through the SubagentHandback tool (LD-507).
check handback_complete       allow executor      "$(handback_transcript c20 "$COMPLETE")"       false
check handback_complete_tester allow test-engineer "$(handback_transcript c21 "$COMPLETE")"      false
check handback_missing_tree   block executor      "$(handback_transcript c22 "$MISSING_TREE")"   false
check handback_claim_only     block executor      "$(handback_transcript c23 "$CLAIM_ONLY")"     false
check handback_then_announce  block executor      "$(handback_transcript c24 "$COMPLETE" "Next, I'll update the README.")" false
check handback_stale          block executor      "$(stale_handback_transcript c25 "$COMPLETE" "Committing.")" false
check unknown_agent      allow repo-recon    "$(transcript c10 "$CLAIM_ONLY")"         false
check missing_transcript  allow executor      "$TMP/does-not-exist.jsonl"               false
printf 'not json\n' > "$TMP/garbage.jsonl"
check garbage_transcript  allow executor      "$TMP/garbage.jsonl"                      false

echo "handoff hook: $PASS passed, $FAIL failed"
if [ "$FAIL" -gt 0 ]; then
  printf '\n'; for f in "${FAILED[@]}"; do echo "  FAIL $f"; done; exit 1
fi
