#!/usr/bin/env bash
# Fixture tests for skills/git-workflow-and-versioning/scripts/base-check.sh
# (ADR 0095): base current, base moved and clean, two changes that pass alone
# but fail together, a merge conflict, usage errors, the candidate untouched, and
# two concurrent checks of one candidate that must not share a scratch checkout.
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
scratch_dirs() { find "$(git -C "$R" rev-parse --git-common-dir)/base-check" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l | tr -d ' '; }
run() { OUT="$(cd "$R" && bash "$SCRIPT" "$@" 2>&1)"; RC=$?; }

# base current: main is already in the candidate
run --base main -- "true"
check current_rc 0 "$RC"; has current_msg "Base: current" "$OUT"

# base moved, merges cleanly, check passes
g checkout -q main; printf 'docs\n' > "$R/README"; g add -A; g commit -qm docs; g checkout -q ticket
run --base main -- "test -f README" "test -f feature"
check moved_rc 0 "$RC"; has moved_msg "Base: moved" "$OUT"; has moved_merge "Merge: clean." "$OUT"
check scratch_removed 0 "$(git -C "$R" worktree list | grep -c base-check)"
check scratch_dirs_after_pass 0 "$(scratch_dirs)"
check candidate_untouched "" "$(git -C "$R" status --porcelain)"
check candidate_lacks_base 1 "$([ ! -f "$R/README" ] && echo 1 || echo 0)"

# each passes alone, together they fail: main removes what the feature needs
g checkout -q main; rm "$R/config"; g add -A; g commit -qm "drop config"; g checkout -q ticket
run --base main -- "test -f config"
check combined_fail_rc 1 "$RC"; has combined_fail_msg "Check: FAIL  test -f config" "$OUT"
check scratch_removed_after_fail 0 "$(git -C "$R" worktree list | grep -c base-check)"
check scratch_dirs_after_fail 0 "$(scratch_dirs)"

# setup command runs first
run --base main --setup "touch config" -- "test -f config"
check setup_rc 0 "$RC"; has setup_msg "Setup: ok" "$OUT"

# two synchronized checks of one candidate: A starts and waits until B has
# finished and cleaned up, then reads the checkout it was given. B must not have
# deleted it.
SYNC="$TMP/sync"; mkdir -p "$SYNC"
wait_for() { for _ in $(seq 100); do [ -e "$1" ] && return 0; sleep 0.1; done; return 1; }
( cd "$R" && bash "$SCRIPT" --base main -- \
    "touch $SYNC/a.up; for _ in \$(seq 100); do [ -e $SYNC/b.exited ] && break; sleep 0.1; done; test -f feature" \
    >"$SYNC/a.out" 2>&1; echo $? >"$SYNC/a.rc" ) &
wait_for "$SYNC/a.up"
( cd "$R" && bash "$SCRIPT" --base main -- "true" >"$SYNC/b.out" 2>&1; echo $? >"$SYNC/b.rc"; touch "$SYNC/b.exited" ) &
wait
check concurrent_a_rc 0 "$(cat "$SYNC/a.rc")"
check concurrent_b_rc 0 "$(cat "$SYNC/b.rc")"
has concurrent_a_check "Check: pass" "$(cat "$SYNC/a.out")"
check concurrent_worktrees_removed 0 "$(git -C "$R" worktree list | grep -c base-check)"
check concurrent_scratch_dirs 0 "$(scratch_dirs)"

# conflict: both sides edit the same file
g checkout -q main; printf 'main side\n' > "$R/feature"; g add -A; g commit -qm "main feature"; g checkout -q ticket
run --base main -- "true"
check conflict_rc 1 "$RC"; has conflict_msg "CONFLICT" "$OUT"; has conflict_file "feature" "$OUT"
check conflict_removed 0 "$(git -C "$R" worktree list | grep -c base-check)"
check conflict_scratch_dirs 0 "$(scratch_dirs)"

# usage
run -- "true"; check no_base_rc 2 "$RC"
run --base main; check no_cmd_rc 2 "$RC"
run --base nope -- "true"; check bad_base_rc 2 "$RC"

echo "base-check: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
