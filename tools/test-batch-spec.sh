#!/usr/bin/env bash
# Fixture tests for tools/batch-spec.sh.
#
# The script spends money and creates branches, so the cases that matter are
# the ones where it must not: a decline, a non-terminal stdin, a dry run, a
# ticket already specced. `claude` is stubbed -- these test the runner's
# decisions, not the model.
#
# Run: tools/test-batch-spec.sh
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BATCH="$REPO/tools/batch-spec.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0; FAILED=()
G=(-c user.email=t@t -c user.name=t -c init.defaultBranch=main -c push.negotiate=false)

check()    { if [ "$2" = "$3" ]; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); FAILED+=("[$1] expected '$2', got '$3'"); fi; }
contains() { case "$3" in *"$2"*) check "$1" y y ;; *) check "$1" y n ;; esac; }
absent()   { case "$3" in *"$2"*) check "$1" n y ;; *) check "$1" n n ;; esac; }

# A stub `claude` that writes the spec its prompt asks for, so a job can
# "succeed" without a model. Records every invocation for the parallel cases.
mkdir -p "$TMP/bin"
cat > "$TMP/bin/claude" <<'STUB'
#!/usr/bin/env bash
prompt=""; next=0
for a in "$@"; do [ "$next" = 1 ] && { prompt="$a"; next=0; }; [ "$a" = "-p" ] && next=1; done
echo "$prompt" >> "$STUB_CALLS"
[ -n "${STUB_FAIL:-}" ] && { echo '{"total_cost_usd":0}'; exit 3; }
mkdir -p docs/specs
for t in ${prompt#/spec }; do printf 'Status: Draft\n# %s\n' "$t" > "docs/specs/$t-SPEC.md"; done
echo '{"total_cost_usd":1.25,"duration_ms":1000}'
STUB
chmod +x "$TMP/bin/claude"
export PATH="$TMP/bin:$PATH" STUB_CALLS="$TMP/calls.txt"

new_repo() {  # -> a throwaway repo with a manifest
  local d="$TMP/$1"; rm -rf "$d"; mkdir -p "$d"
  git "${G[@]}" init -q "$d"
  ( cd "$d" && echo x > README.md && git "${G[@]}" add -A && git "${G[@]}" commit -qm base )
  printf '# comment\n\nLD-1,LD-2   pair\nLD-3\n' > "$d/jobs.txt"
  : > "$STUB_CALLS"
  echo "$d"
}
run()     { OUT="$(cd "$1" && shift && bash "$BATCH" "$@" </dev/null 2>&1)"; RC=$?; }
run_tty() { local d="$1" ans="$2"; shift 2
            OUT="$(printf '%s\n' "$ans" | (cd "$d" && script -qec "bash '$BATCH' $*" /dev/null) 2>&1)"; RC=$?; }
specs()   { find "$1/.claude/worktrees" -name '*-SPEC.md' 2>/dev/null | wc -l | tr -d ' '; }

# ------------------------------------------------------------------ the plan
D="$(new_repo plan)"
run "$D" -m jobs.txt --dry-run
check    dry_rc                 0 "$RC"
check    dry_no_specs           0 "$(specs "$D")"
check    dry_no_branches        0 "$(git -C "$D" branch --list 'feature/*' | wc -l | tr -d ' ')"
contains dry_groups_the_pair    "pair" "$OUT"
contains dry_expands_tickets    "LD-1 LD-2" "$OUT"
contains dry_default_slug       "LD-3" "$OUT"
contains dry_counts_jobs        "2 job(s)" "$OUT"
contains dry_says_dry           "dry run; nothing started" "$OUT"
absent   dry_skips_comment      "comment" "$OUT"

# ------------------------------------------------------------ refusing to act
D="$(new_repo pipe)"
run "$D" -m jobs.txt
check    no_tty_rc              1 "$RC"
check    no_tty_no_specs        0 "$(specs "$D")"
contains no_tty_names_the_fix   "--yes" "$OUT"

D="$(new_repo decline)"
run_tty "$D" n -m jobs.txt
check    decline_rc             1 "$RC"
check    decline_no_specs       0 "$(specs "$D")"
check    decline_no_calls       0 "$(wc -l < "$STUB_CALLS" | tr -d ' ')"
contains decline_says_so        "aborted; nothing started" "$OUT"

D="$(new_repo junk)"
run_tty "$D" maybe -m jobs.txt
check    junk_answer_is_no      0 "$(specs "$D")"

# ---------------------------------------------------------------- proceeding
D="$(new_repo go)"
run "$D" -m jobs.txt --yes
check    yes_rc                 0 "$RC"
check    yes_wrote_three_specs  3 "$(specs "$D")"
check    yes_made_two_branches  2 "$(git -C "$D" branch --list 'feature/*' | wc -l | tr -d ' ')"
check    yes_called_twice       2 "$(wc -l < "$STUB_CALLS" | tr -d ' ')"
contains yes_reports_ok         "ok" "$OUT"
contains yes_sums_cost          "measured total: \$2.50" "$OUT"
contains yes_says_draft         "Draft and uncommitted" "$OUT"
# -uall: porcelain collapses an untracked directory to "?? docs/" otherwise.
n="$(cd "$D/.claude/worktrees/pair" && git status --porcelain -uall | grep -c SPEC)"
check    yes_left_uncommitted   y "$([ "$n" -gt 0 ] && echo y || echo n)"

# A ticket already specced in the main checkout is work already done.
D="$(new_repo skip)"
mkdir -p "$D/docs/specs" && echo x > "$D/docs/specs/LD-3-SPEC.md"
run "$D" -m jobs.txt --dry-run
contains skip_marks_it          "skipped" "$OUT"
contains skip_drops_to_one      "1 job(s)" "$OUT"

D="$(new_repo skipall)"
mkdir -p "$D/docs/specs" && echo x > "$D/docs/specs/LD-1-SPEC.md" && echo x > "$D/docs/specs/LD-3-SPEC.md"
run "$D" -m jobs.txt --yes
check    skip_all_rc            0 "$RC"
check    skip_all_no_calls      0 "$(wc -l < "$STUB_CALLS" | tr -d ' ')"
contains skip_all_says_nothing  "nothing to do" "$OUT"

# ------------------------------------------------------------------- failures
D="$(new_repo failing)"
STUB_FAIL=1 run "$D" -m jobs.txt --yes
check    failure_rc             1 "$RC"
contains failure_named          "NO SPEC" "$OUT"
contains failure_points_at_log  ".log" "$OUT"

# ---------------------------------------------------------------------- flags
D="$(new_repo flags)"
run "$D" -m jobs.txt --parallel 2 --dry-run
check    parallel_ok            0 "$RC"
run "$D" -m jobs.txt --parallel 0
check    parallel_zero_rc       1 "$RC"
run "$D" -m jobs.txt --parallel two
check    parallel_junk_rc       1 "$RC"
run "$D" -m nope.txt --dry-run
check    missing_manifest_rc    1 "$RC"
contains missing_manifest_says  "no manifest" "$OUT"
run "$D" --bogus
check    unknown_flag_rc        1 "$RC"
run "$D" --help
check    help_rc                0 "$RC"
contains help_shows_usage       "--dry-run" "$OUT"
OUT="$(cd "$TMP" && bash "$BATCH" --dry-run </dev/null 2>&1)"; RC=$?
check    outside_repo_rc        1 "$RC"

# the committed manifest must parse
D="$(new_repo real)"
cp "$REPO/tools/spec-batch.txt" "$D/jobs.txt"
run "$D" -m jobs.txt --dry-run
check    real_manifest_rc       0 "$RC"
contains real_manifest_jobs     "17 job(s)" "$OUT"

echo "batch-spec: $PASS passed, $FAIL failed"
if [ "$FAIL" -gt 0 ]; then printf '\n'; for f in "${FAILED[@]}"; do echo "  FAIL $f"; done; exit 1; fi
