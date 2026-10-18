#!/usr/bin/env bash
# Fixture tests for skills/git-workflow-and-versioning/scripts/base-check.sh
# (ADR 0095): base current, base moved and clean, two changes that pass alone
# but fail together, a merge conflict, usage errors, and the candidate untouched.
set -uo pipefail
SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../claude/skills/git-workflow-and-versioning/scripts" && pwd)/base-check.sh"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0
g() { git -C "$R" -c user.email=t@t -c user.name=t "$@" >/dev/null 2>&1; }
check() { if [ "$2" = "$3" ]; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); echo "FAIL [$1] expected '$2', got '$3'"; fi; }
has() { if grep -qF -- "$2" <<<"$3"; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); echo "FAIL [$1] missing: $2"; fi; }

R="$TMP/repo"; mkdir -p "$R"; g init -q -b main
printf 'limit=10\n' > "$R/config"; g add -A; g commit -qm base
g checkout -q -b ticket
printf 'use limit\n' > "$R/feature"; g add -A; g commit -qm feature
run() { OUT="$(cd "$R" && bash "$SCRIPT" "$@" 2>&1)"; RC=$?; }

# base current: main is already in the candidate
run --base main -- "true"
check current_rc 0 "$RC"; has current_msg "Base: current" "$OUT"

# base moved, merges cleanly, check passes
g checkout -q main; printf 'docs\n' > "$R/README"; g add -A; g commit -qm docs; g checkout -q ticket
run --base main -- "test -f README" "test -f feature"
check moved_rc 0 "$RC"; has moved_msg "Base: moved" "$OUT"; has moved_merge "Merge: clean." "$OUT"
check scratch_removed 0 "$(git -C "$R" worktree list | grep -c base-check)"
check candidate_untouched "" "$(git -C "$R" status --porcelain)"
check candidate_lacks_base 1 "$([ ! -f "$R/README" ] && echo 1 || echo 0)"

# each passes alone, together they fail: main removes what the feature needs
g checkout -q main; rm "$R/config"; g add -A; g commit -qm "drop config"; g checkout -q ticket
run --base main -- "test -f config"
check combined_fail_rc 1 "$RC"; has combined_fail_msg "Check: FAIL  test -f config" "$OUT"

# setup command runs first
run --base main --setup "touch config" -- "test -f config"
check setup_rc 0 "$RC"; has setup_msg "Setup: ok" "$OUT"

# conflict: both sides edit the same file
g checkout -q main; printf 'main side\n' > "$R/feature"; g add -A; g commit -qm "main feature"; g checkout -q ticket
run --base main -- "true"
check conflict_rc 1 "$RC"; has conflict_msg "CONFLICT" "$OUT"; has conflict_file "feature" "$OUT"
check conflict_removed 0 "$(git -C "$R" worktree list | grep -c base-check)"

# usage
run -- "true"; check no_base_rc 2 "$RC"
run --base main; check no_cmd_rc 2 "$RC"
run --base nope -- "true"; check bad_base_rc 2 "$RC"

echo "base-check: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
