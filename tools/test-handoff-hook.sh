#!/usr/bin/env bash
# Fixture tests for dotfiles/claude/hooks/require-handoff-report.sh, the
# SubagentStop hook on executor and test-engineer. Each case builds a JSONL
# transcript whose last assistant message is a handoff report, runs the hook
# with a SubagentStop payload, and checks the decision:
#   block — report is missing a required section
#   allow — report is complete, or the hook must stay out of the way
#           (unknown agent, second attempt, unreadable transcript)
#
# Run: tools/test-handoff-hook.sh
set -uo pipefail

HOOK="$(cd "$(dirname "${BASH_SOURCE[0]}")/../dotfiles/claude/hooks" && pwd)/require-handoff-report.sh"
command -v jq >/dev/null || { echo "test-handoff-hook: jq is required" >&2; exit 1; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
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

decision() { # agent_type, transcript, stop_hook_active
  jq -n --arg a "$1" --arg t "$2" --argjson s "$3" \
    '{hook_event_name:"SubagentStop",agent_type:$a,agent_transcript_path:$t,stop_hook_active:$s,cwd:"/tmp"}' \
    | bash "$HOOK" 2>/dev/null | jq -r '.decision // "allow"' 2>/dev/null || echo ERROR
}

check() { # label, expected, agent, transcript, active
  local got; got="$(decision "$3" "$4" "$5")"; [ -z "$got" ] && got=allow
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
check second_attempt      allow executor      "$(transcript c9 "$CLAIM_ONLY")"          true   # stop_hook_active: no loop
check unknown_agent       allow repo-recon    "$(transcript c10 "$CLAIM_ONLY")"         false
check missing_transcript  allow executor      "$TMP/does-not-exist.jsonl"               false
printf 'not json\n' > "$TMP/garbage.jsonl"
check garbage_transcript  allow executor      "$TMP/garbage.jsonl"                      false

echo "handoff hook: $PASS passed, $FAIL failed"
if [ "$FAIL" -gt 0 ]; then
  printf '\n'; for f in "${FAILED[@]}"; do echo "  FAIL $f"; done; exit 1
fi
