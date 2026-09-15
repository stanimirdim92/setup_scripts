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
cp "$TMP/bin/claude" "$TMP/claude.good"
restore_stub() { cp "$TMP/claude.good" "$TMP/bin/claude"; chmod +x "$TMP/bin/claude"; }
export PATH="$TMP/bin:$PATH" STUB_CALLS="$TMP/calls.txt"

# A repository in the state real ones are in, not a pristine one. Two of the
# bugs an external review found hid behind a clean fixture: an inherited
# *-SPEC.md was reported as this job's output, and a job whose worktree could
# not be created vanished from the results. Neither could happen in a repo with
# no prior specs and no branches. So every case gets:
#   - a spec from some earlier ticket, committed;
#   - an unrelated branch, so branch-name collisions are reachable;
#   - an untracked file, because a working checkout is never clean;
#   - a stale prunable worktree entry, the state `rm -rf` leaves behind.
new_repo() {  # -> a throwaway repo with a manifest
  local d="$TMP/$1"; rm -rf "$d"; mkdir -p "$d"
  git "${G[@]}" init -q "$d"
  ( cd "$d" && echo x > README.md && mkdir -p docs/specs \
      && printf 'Status: Approved\n' > docs/specs/ARCHIVE-1-SPEC.md \
      && git "${G[@]}" add -A && git "${G[@]}" commit -qm base \
      && git "${G[@]}" branch unrelated/work \
      && echo scratch > notes.local )
  git -C "$d" "${G[@]}" worktree add -q -b stale-wt "$TMP/$1-stale" >/dev/null 2>&1
  rm -rf "$TMP/$1-stale"          # prunable: the state `rm -rf` leaves
  printf '# comment\n\nLD-1,LD-2   pair\nLD-3\n' > "$d/jobs.txt"
  : > "$STUB_CALLS"
  echo "$d"
}
run()     { OUT="$(cd "$1" && shift && bash "$BATCH" "$@" </dev/null 2>&1)"; RC=$?; }
run_tty() { local d="$1" ans="$2"; shift 2
            OUT="$(printf '%s\n' "$ans" | (cd "$d" && script -qec "bash '$BATCH' $*" /dev/null) 2>&1)"; RC=$?; }
# Only specs for the tickets in jobs.txt. Counting every *-SPEC.md would count
# the inherited ARCHIVE-1-SPEC.md the fixture plants, which is the exact
# conflation that let an inherited spec be reported as a job's own output.
specs()   { find "$1/.claude/worktrees" -name 'LD-*-SPEC.md' 2>/dev/null | wc -l | tr -d ' '; }
inherited(){ find "$1/.claude/worktrees" -name 'ARCHIVE-*-SPEC.md' 2>/dev/null | wc -l | tr -d ' '; }

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
# ...and the inherited spec is present in both worktrees the whole time, so
# "a spec file exists here" was never evidence of anything.
check    yes_inherited_present  2 "$(inherited "$D")"
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

# A project declaring .worktreeinclude needs those ignored files in every
# worktree. `git worktree add` does not do the managed-worktree copy, so the
# script must; leadbuster's .env.testing is the case that matters.
D="$(new_repo includes)"
printf '.env\n.env.testing\n' > "$D/.worktreeinclude"
printf '.env\n.env.testing\nnode_modules/\n' > "$D/.gitignore"
printf 'APP_ENV=local\n' > "$D/.env"
printf 'DB_DATABASE=leadbuster_test\n' > "$D/.env.testing"
mkdir -p "$D/node_modules" && echo junk > "$D/node_modules/x.js"
( cd "$D" && git "${G[@]}" add -A && git "${G[@]}" commit -qm ignore )
run "$D" -m jobs.txt --yes
check    include_copies_env       1 "$([ -f "$D/.claude/worktrees/pair/.env" ] && echo 1 || echo 0)"
check    include_copies_testing   1 "$([ -f "$D/.claude/worktrees/pair/.env.testing" ] && echo 1 || echo 0)"
check    include_content_matches  "DB_DATABASE=leadbuster_test" "$(cat "$D/.claude/worktrees/pair/.env.testing" 2>/dev/null)"
check    include_skips_unlisted   0 "$([ -e "$D/.claude/worktrees/pair/node_modules" ] && echo 1 || echo 0)"
check    include_both_worktrees   1 "$([ -f "$D/.claude/worktrees/LD-3/.env" ] && echo 1 || echo 0)"

# No .worktreeinclude is the ordinary case and must not break a job.
D="$(new_repo no_includes)"
run "$D" -m jobs.txt --yes
check    no_include_still_works   0 "$RC"

# A worktree inherits whatever specs the base commit carried, so an existing
# *-SPEC.md is not evidence this job produced anything. Reported by an external
# review: a job whose CLI exited 3 was reported ok, citing an inherited spec.
D="$(new_repo inherited)"
STUB_FAIL=1 run "$D" -m jobs.txt --yes
check    inherited_not_counted_ok  1 "$RC"
contains inherited_reported_failed "FAILED" "$OUT"
absent   inherited_not_cited_ok    "ARCHIVE-1-SPEC.md" "$OUT"

# ...and a spec for some *other* ticket does not count either, even when the
# CLI succeeds.
D="$(new_repo wrongspec)"
cat > "$TMP/bin/claude" <<'STUB2'
#!/usr/bin/env bash
mkdir -p docs/specs; printf 'Status: Draft
' > docs/specs/UNRELATED-SPEC.md
echo '{"total_cost_usd":0.5}'
STUB2
chmod +x "$TMP/bin/claude"
run "$D" -m jobs.txt --yes
check    wrong_spec_rc             1 "$RC"
contains wrong_spec_reported       "NO SPEC" "$OUT"
restore_stub

# A worker that dies before reporting used to vanish from the results and the
# run still exited 0. Every scheduled job must produce exactly one row.
D="$(new_repo deadworker)"
git -C "$D" "${G[@]}" branch feature/pair          # blocks `git worktree add -b`
# the other job must still complete; a dead worker is not a dead batch
run "$D" -m jobs.txt --yes
check    dead_worker_rc            1 "$RC"
contains dead_worker_reported      "pair" "$OUT"
check    dead_worker_has_a_row     1 "$(grep -c '^pair|' "$D/.spec-batch/results.txt" 2>/dev/null || echo 0)"
contains dead_worker_other_job_ok  "ok" "$OUT"

# A worker killed outright -- OOM, or the machine reclaiming it -- emits no row
# at all. Capturing the job's exit status cannot help: the shell that would
# report it is gone. Only counting rows against scheduled jobs notices. Without
# this case the accounting looks like dead code, because every other failure
# still reports; removing it passed the whole suite.
D="$(new_repo killed)"
printf 'LD-7\n' > "$D/jobs.txt"
cat > "$TMP/bin/claude" <<'KILLER'
#!/usr/bin/env bash
GRAND=$(ps -o ppid= -p $PPID 2>/dev/null | tr -d ' ')
[ -n "$GRAND" ] && kill -9 "$GRAND" 2>/dev/null
sleep 5
KILLER
chmod +x "$TMP/bin/claude"
OUT="$(cd "$D" && timeout 30 bash "$BATCH" -m jobs.txt --yes </dev/null 2>&1)"; RC=$?
check    killed_worker_rc          1 "$RC"
contains killed_worker_reported    "NO RESULT" "$OUT"
check    killed_worker_no_row      0 "$(wc -l < "$D/.spec-batch/results.txt" | tr -d ' ')"
restore_stub

# ------------------------------------------------------------------- failures
D="$(new_repo failing)"
STUB_FAIL=1 run "$D" -m jobs.txt --yes
check    failure_rc             1 "$RC"
# FAILED (the CLI exited non-zero) is distinct from NO SPEC (it exited 0 but
# wrote nothing for this ticket); wrong_spec_reported above covers the latter.
contains failure_named          "FAILED" "$OUT"
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
