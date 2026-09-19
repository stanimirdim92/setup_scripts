#!/usr/bin/env bash
# Fixture tests for the two worktree-base hooks in dotfiles/claude/hooks/.
#
# Both exist because settings.json sets `worktree.baseRef: "head"` (adr/0056),
# which the subagent level requires and which moves a risk up to the session
# level. Each case builds real git repositories -- a bare origin, a main
# checkout, a linked worktree, a feature branch -- because both hooks decide
# from git state and a mocked `git` would test the mock.
#
# The allow cases carry the weight. A session-start warning that fires when
# nothing is wrong gets ignored within a week, and a hook that refuses a
# legitimate dispatch gets deleted.
#
# Run: tools/test-worktree-hooks.sh
set -uo pipefail

HOOKS="$(cd "$(dirname "${BASH_SOURCE[0]}")/../dotfiles/claude/hooks" && pwd)"
WARN="$HOOKS/warn-stale-base.sh"
BLOCK="$HOOKS/require-worktree-for-writers.sh"
command -v jq >/dev/null || { echo "test-worktree-hooks: jq is required" >&2; exit 1; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0; FAILED=()
G=(-c user.email=t@t -c user.name=t -c init.defaultBranch=main -c push.negotiate=false)

# origin (bare) <- seed; main checkout clones it; a pusher moves origin ahead.
git init -q --bare -b main "$TMP/origin.git"
git "${G[@]}" init -q "$TMP/seed" && cd "$TMP/seed"
echo one > f.txt && git "${G[@]}" add -A && git "${G[@]}" commit -qm one
git "${G[@]}" remote add origin "$TMP/origin.git" && git "${G[@]}" push -q origin main
cd "$TMP"
git "${G[@]}" clone -q "$TMP/origin.git" main-checkout
git -C main-checkout "${G[@]}" remote set-head origin main >/dev/null 2>&1
# a checkout with no remote at all
git "${G[@]}" init -q "$TMP/no-remote" && cd "$TMP/no-remote" && echo x > a.txt \
  && git "${G[@]}" add -A && git "${G[@]}" commit -qm x && cd "$TMP"
# a linked worktree off the main checkout
git -C main-checkout "${G[@]}" worktree add -q -b ticket-LD-1 "$TMP/wt-LD-1" >/dev/null 2>&1
# a feature branch inside the main checkout (used by switching to it)
git -C main-checkout "${G[@]}" branch feature/x

# A broken fixture reads as a passing hook -- every case below asks git a
# question, and git answering "no such branch" looks like "nothing to warn
# about". Assert the fixture first so a setup bug fails here, loudly.
setup_ok=1
[ "$(git -C main-checkout rev-parse --abbrev-ref HEAD 2>/dev/null)" = main ] || setup_ok=0
git -C main-checkout rev-parse --verify -q feature/x >/dev/null || setup_ok=0
git -C wt-LD-1 rev-parse --verify -q HEAD >/dev/null || setup_ok=0
[ "$setup_ok" = 1 ] || { echo "test-worktree-hooks: fixture setup failed, aborting" >&2; exit 1; }

move_origin_ahead() {
  cd "$TMP/seed" && echo two >> f.txt && git "${G[@]}" commit -qam two \
    && git "${G[@]}" push -q origin main && cd "$TMP"
}
force_fetch_next_time() {  # age FETCH_HEAD past the 60-minute window
  # In a worktree `.git` is a file, and FETCH_HEAD lives in the common dir.
  local c; c="$(git -C "$1" rev-parse --git-common-dir 2>/dev/null)" || return 0
  case "$c" in /*) ;; *) c="$1/$c" ;; esac
  [ -f "$c/FETCH_HEAD" ] && touch -d '3 hours ago' "$c/FETCH_HEAD"
  return 0
}

warn_out() {  # cwd -> stdout of the SessionStart hook
  jq -nc --arg c "$1" '{hook_event_name:"SessionStart",source:"startup",cwd:$c}' \
    | bash "$WARN" 2>/dev/null
}
# The guard is a PreToolUse hook on the dispatch tool, so what it returns is a
# permissionDecision -- exit status is always 0. Asserting the exit code, as
# the first version of this suite did, would pass against a hook that decided
# nothing.
block_rc() {  # cwd, agent_type -> "deny" or "allow"
  local out; out="$(jq -nc --arg c "$1" --arg a "$2" \
    '{hook_event_name:"PreToolUse",tool_name:"Agent",tool_input:{subagent_type:$a},cwd:$c}' \
    | bash "$BLOCK" 2>/dev/null | jq -r '.hookSpecificOutput.permissionDecision // "allow"' 2>/dev/null)"
  echo "${out:-allow}"
}
block_rc_task() {  # same, dispatched as Task
  local out; out="$(jq -nc --arg c "$1" --arg a "$2" \
    '{hook_event_name:"PreToolUse",tool_name:"Task",tool_input:{subagent_type:$a},cwd:$c}' \
    | bash "$BLOCK" 2>/dev/null | jq -r '.hookSpecificOutput.permissionDecision // "allow"' 2>/dev/null)"
  echo "${out:-allow}"
}
check() { # label, expected, actual
  if [ "$2" = "$3" ]; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); FAILED+=("[$1] expected $2, got $3"); fi
}
check_quiet()  { local o; o="$(warn_out "$2")"; check "$1" "" "${o:+SOMETHING}"; }
check_warns()  { local o; o="$(warn_out "$2")"; case "$o" in *"behind origin/main"*) check "$1" warn warn ;; *) check "$1" warn "${o:-nothing}" ;; esac; }

# ---------------------------------------------------- warn-stale-base: quiet
check_quiet  not_a_git_repo              "$TMP"
check_quiet  no_remote_configured        "$TMP/no-remote"
check_quiet  on_main_and_current         "$TMP/main-checkout"
check_quiet  missing_cwd                 "$TMP/does-not-exist"
check_quiet  fresh_worktree_off_current  "$TMP/wt-LD-1"

move_origin_ahead
force_fetch_next_time "$TMP/main-checkout"

# ---------------------------------------------------- warn-stale-base: warns
check_warns  on_main_and_behind          "$TMP/main-checkout"

# The primary flow: `claude --worktree` branched this off a local main that was
# already behind. The session never touches the default branch, so the
# on-default test above never sees it -- this is the case the first version of
# the hook asserted silence for.
force_fetch_next_time "$TMP/wt-LD-1"
check_warns  fresh_worktree_off_stale    "$TMP/wt-LD-1"

# ...and the advice must differ: `git pull` on a ticket branch merges the
# default branch into it, which is not what a fresh branch needs.
ff="$(warn_out "$TMP/wt-LD-1")"
case "$ff" in *"--ff-only"*) check fresh_ticket_advice_is_ff y y ;; *) check fresh_ticket_advice_is_ff y n ;; esac
case "$(warn_out "$TMP/main-checkout")" in *"git pull"*) check on_default_advice_is_pull y y ;; *) check on_default_advice_is_pull y n ;; esac

# ...and stays quiet where being behind means nothing
git -C main-checkout "${G[@]}" checkout -q feature/x
force_fetch_next_time "$TMP/main-checkout"
check_quiet  on_feature_branch_behind    "$TMP/main-checkout"
git -C main-checkout "${G[@]}" checkout -q main

# Mid-ticket: the branch carries its own work, so being behind origin is the
# normal state of every ticket branch and warning about it trains you to skip
# the line.
( cd "$TMP/wt-LD-1" && echo work > t.txt && git "${G[@]}" add -A && git "${G[@]}" commit -qm work )
force_fetch_next_time "$TMP/wt-LD-1"
check_quiet  worktree_with_own_commits   "$TMP/wt-LD-1"

# ------------------------------------------- require-worktree-for-writers
check writer_on_main_blocked          deny  "$(block_rc "$TMP/main-checkout" executor)"
check tester_on_main_blocked          deny  "$(block_rc "$TMP/main-checkout" test-engineer)"
check writer_via_task_blocked         deny  "$(block_rc_task "$TMP/main-checkout" executor)"
check writer_in_worktree_allowed      allow "$(block_rc "$TMP/wt-LD-1" executor)"
check tester_in_worktree_allowed      allow "$(block_rc "$TMP/wt-LD-1" test-engineer)"
git -C main-checkout "${G[@]}" checkout -q feature/x
check writer_on_feature_allowed       allow "$(block_rc "$TMP/main-checkout" executor)"
git -C main-checkout "${G[@]}" checkout -q main
# States a real checkout reaches that a pristine fixture never does. Detached
# HEAD has no branch to compare against the default one, and a worktree deleted
# with `rm -rf` instead of `git worktree remove` lingers in `git worktree list`
# as prunable. Detached writer dispatch must refuse unverifiable ownership;
# a base warning still has nothing to say, and a prunable entry grants no pass.
git -C main-checkout "${G[@]}" checkout -q --detach HEAD
check writer_detached_head_blocked   deny "$(block_rc "$TMP/main-checkout" executor)"
check_quiet  detached_head_quiet     "$TMP/main-checkout"
git -C main-checkout "${G[@]}" checkout -q main
git -C main-checkout "${G[@]}" worktree add -q -b stale-wt "$TMP/wt-stale" >/dev/null 2>&1
rm -rf "$TMP/wt-stale"                 # prunable from here on
check writer_on_main_still_blocked   deny  "$(block_rc "$TMP/main-checkout" executor)"

check reviewer_never_blocked          allow "$(block_rc "$TMP/main-checkout" code-reviewer)"
check blind_reviewer_never_blocked    allow "$(block_rc "$TMP/main-checkout" blind-reviewer)"
check recon_never_blocked             allow "$(block_rc "$TMP/main-checkout" repo-recon)"
check writer_outside_git_blocked      deny "$(block_rc "$TMP" executor)"
check writer_missing_cwd_blocked      deny "$(block_rc "$TMP/does-not-exist" executor)"
check no_remote_repo_on_main_blocked  deny  "$(block_rc "$TMP/no-remote" executor)"
check no_agent_type_allowed           allow "$(block_rc "$TMP/main-checkout" "")"

# The decision must be a real permissionDecision, not an exit code: a hook that
# exits 2 from an event that cannot block refuses nothing.
raw="$(jq -nc --arg c "$TMP/main-checkout" '{hook_event_name:"PreToolUse",tool_name:"Agent",tool_input:{subagent_type:"executor"},cwd:$c}' | bash "$BLOCK" 2>/dev/null)"
check decision_is_json                deny "$(jq -r '.hookSpecificOutput.permissionDecision // "none"' <<<"$raw" 2>/dev/null)"
check decision_names_the_event        PreToolUse "$(jq -r '.hookSpecificOutput.hookEventName // "none"' <<<"$raw" 2>/dev/null)"

# the refusal must name the fix, or it teaches nobody anything
reason="$(jq -r '.hookSpecificOutput.permissionDecisionReason // ""' <<<"$raw" 2>/dev/null)"
case "$reason" in *"--worktree"*) check refusal_names_the_fix y y ;; *) check refusal_names_the_fix y n ;; esac

# Malformed dispatch and dependency outages cannot silently grant writing.
block_raw_rc() { # JSON, optional PATH -> deny/allow
  local out
  out="$(printf '%s' "$1" | PATH="${2:-$PATH}" /bin/bash "$BLOCK" 2>/dev/null)"
  if [ -z "$out" ]; then echo allow; else jq -r '.hookSpecificOutput.permissionDecision // "invalid"' <<<"$out"; fi
}
writer_input="$(jq -nc --arg c "$TMP/wt-LD-1" '{tool_input:{subagent_type:"executor"},cwd:$c}')"
reader_input="$(jq -nc --arg c "$TMP/absent" '{tool_input:{subagent_type:"repo-recon"},cwd:$c}')"
check bad_json_blocked deny "$(block_raw_rc '{"tool_input":{"subagent_type":"executor"}')"
check nonobject_input_blocked deny "$(block_raw_rc '[]')"
check multiple_json_objects_blocked deny "$(block_raw_rc '{"tool_input":{"subagent_type":"repo-recon"}} {}')"
check invalid_persona_type_blocked deny "$(block_raw_rc '{"tool_input":{"subagent_type":[]}}')"
check invalid_tool_type_blocked deny "$(block_raw_rc '{"tool_input":false}')"
check invalid_cwd_type_blocked deny "$(block_raw_rc '{"tool_input":{"subagent_type":"executor"},"cwd":[]}')"
check no_cwd_writer_blocked deny "$(block_raw_rc '{"tool_input":{"subagent_type":"executor"}}')"
check reader_without_checkout_allowed allow "$(block_raw_rc "$reader_input")"
mkdir "$TMP/no-jq" "$TMP/no-parser" "$TMP/no-git"
for tool in cat python3 git dirname timeout; do ln -s "$(command -v "$tool")" "$TMP/no-jq/$tool"; done
for tool in cat jq dirname timeout; do ln -s "$(command -v "$tool")" "$TMP/no-git/$tool"; done
ln -s "$(command -v cat)" "$TMP/no-parser/cat"
check no_jq_writer_fallback_allowed allow "$(block_raw_rc "$writer_input" "$TMP/no-jq")"
check no_jq_reader_fallback_allowed allow "$(block_raw_rc "$reader_input" "$TMP/no-jq")"
check no_jq_main_writer_blocked deny "$(block_raw_rc "$(jq --arg c "$TMP/main-checkout" '.cwd=$c' <<<"$writer_input")" "$TMP/no-jq")"
check no_jq_malformed_blocked deny "$(block_raw_rc '{' "$TMP/no-jq")"
check no_jq_invalid_persona_blocked deny "$(block_raw_rc '{"tool_input":{"subagent_type":[]}}' "$TMP/no-jq")"
check no_jq_invalid_tool_blocked deny "$(block_raw_rc '{"tool_input":false}' "$TMP/no-jq")"
check no_parsers_blocked deny "$(block_raw_rc "$writer_input" "$TMP/no-parser")"
check no_git_writer_blocked deny "$(block_raw_rc "$writer_input" "$TMP/no-git")"
check no_git_reader_allowed allow "$(block_raw_rc "$reader_input" "$TMP/no-git")"
check parallel_dispatch_in_ticket_allowed allow "$(block_raw_rc "$(jq '.tool_input.isolation="worktree"' <<<"$writer_input")")"

# Default-branch discovery must be verifiable outside a linked ticket checkout.
git -C "$TMP/no-remote" branch -m unusual-default
check unknown_default_blocked deny "$(block_rc "$TMP/no-remote" executor)"
git -C "$TMP/no-remote" branch -m main
check writer_in_bare_repo_blocked deny "$(block_rc "$TMP/origin.git" executor)"
git -C "$TMP/wt-LD-1" checkout -q --detach HEAD
check detached_linked_writer_blocked deny "$(block_rc "$TMP/wt-LD-1" executor)"
git -C "$TMP/wt-LD-1" checkout -q ticket-LD-1

# A main-checkout doctor introduces a readiness contract to older checkouts,
# including external paths. Missing doctor is distinct from ordinary Git lag.
mkdir -p "$TMP/main-checkout/bin"
cat > "$TMP/main-checkout/bin/worktree-doctor.sh" <<'DOCTOR'
#!/bin/bash
[ "$#" = 1 ] && [ "$1" = --infrastructure ] || exit 9
printf 'ready\n'
DOCTOR
chmod +x "$TMP/main-checkout/bin/worktree-doctor.sh"
check old_runner_blocked deny "$(block_rc "$TMP/wt-LD-1" executor)"
case "$(warn_out "$TMP/wt-LD-1")" in *"lacks bin/worktree-doctor.sh"*) check mid_ticket_missing_doctor_warns y y ;; *) check mid_ticket_missing_doctor_warns y n ;; esac
check reader_with_old_runner_allowed allow "$(block_rc "$TMP/wt-LD-1" code-reviewer)"
mkdir -p "$TMP/wt-LD-1/bin"
cp "$TMP/main-checkout/bin/worktree-doctor.sh" "$TMP/wt-LD-1/bin/worktree-doctor.sh"
check ready_runner_allowed allow "$(block_rc "$TMP/wt-LD-1" executor)"
check_quiet mid_ticket_ready_runner_quiet "$TMP/wt-LD-1"
report="$(jq -nc --arg c "$TMP/wt-LD-1" '{cwd:$c}' | bash "$WARN" --report)"
check report_is_session_start SessionStart "$(jq -r '.hookSpecificOutput.hookEventName' <<<"$report")"
check report_visible_and_context_match true "$(jq '.systemMessage == .hookSpecificOutput.additionalContext' <<<"$report")"
case "$(jq -r '.systemMessage' <<<"$report")" in *'PASS: worktree infrastructure is current.'*'SKIP: this is ongoing branch work'*) check report_ready_and_skipped_checks y y ;; *) check report_ready_and_skipped_checks y n ;; esac
cat > "$TMP/wt-LD-1/bin/worktree-doctor.sh" <<'DOCTOR'
#!/bin/bash
printf 'runner version is stale; reconcile "bin/worktree-test.sh"\n'
exit 1
DOCTOR
check stale_runner_blocked deny "$(block_rc "$TMP/wt-LD-1" executor)"
case "$(warn_out "$TMP/wt-LD-1")" in *'runner version is stale'*) check mid_ticket_stale_runner_warns y y ;; *) check mid_ticket_stale_runner_warns y n ;; esac
reason="$(printf '%s' "$writer_input" | bash "$BLOCK" | jq -r '.hookSpecificOutput.permissionDecisionReason')"
case "$reason" in *'reconcile "bin/worktree-test.sh"'*) check readiness_reason_keeps_quotes y y ;; *) check readiness_reason_keeps_quotes y n ;; esac
report="$(jq -nc --arg c "$TMP/wt-LD-1" '{cwd:$c}' | bash "$WARN" --report)"
case "$(jq -r '.systemMessage' <<<"$report")" in *'reconcile "bin/worktree-test.sh"'*'FAIL: worktree infrastructure needs attention.'*) check report_failure_keeps_details y y ;; *) check report_failure_keeps_details y n ;; esac
report="$(printf '{"cwd":"/nonexistent-checkout"}' | bash "$WARN" --report)"
case "$(jq -r '.systemMessage' <<<"$report")" in *'SKIP: checkout path is missing or unavailable.'*) check report_missing_checkout y y ;; *) check report_missing_checkout y n ;; esac
chmod -x "$TMP/wt-LD-1/bin/worktree-doctor.sh"
check nonexecutable_doctor_blocked deny "$(block_rc "$TMP/wt-LD-1" executor)"
cp "$TMP/main-checkout/bin/worktree-doctor.sh" "$TMP/wt-LD-1/bin/worktree-doctor.sh"
chmod +x "$TMP/wt-LD-1/bin/worktree-doctor.sh"
git -C "$TMP/main-checkout" worktree add -q -b ticket-space "$TMP/wt with spaces"
check missing_doctor_spaced_path_blocked deny "$(block_rc "$TMP/wt with spaces" executor)"
mkdir -p "$TMP/wt with spaces/bin"
cp "$TMP/main-checkout/bin/worktree-doctor.sh" "$TMP/wt with spaces/bin/worktree-doctor.sh"
check ready_doctor_spaced_path_allowed allow "$(block_rc "$TMP/wt with spaces" executor)"
# Simulate timeout's failure without sleeping in the suite.
mkdir "$TMP/timed-out"
for tool in cat jq git dirname; do ln -s "$(command -v "$tool")" "$TMP/timed-out/$tool"; done
printf '#!/bin/bash\nexit 124\n' > "$TMP/timed-out/timeout"
chmod +x "$TMP/timed-out/timeout"
check timed_out_doctor_blocked deny "$(block_raw_rc "$writer_input" "$TMP/timed-out")"

echo "worktree hooks: $PASS passed, $FAIL failed"
if [ "$FAIL" -gt 0 ]; then printf '\n'; for f in "${FAILED[@]}"; do echo "  FAIL $f"; done; exit 1; fi
