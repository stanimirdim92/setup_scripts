#!/usr/bin/env bash
# batch-spec.sh [-m FILE] [-p N] [-b USD] [-o DIR] [-n|--dry-run] [-y|--yes]
#
# Run `/spec` for many tickets, one worktree per job, and stop at the spec gate.
#
# Specs are the one pipeline stage that fans out for free: `/spec` reads Jira and
# the repository and writes one markdown file. It runs no migrations, binds no
# port and touches no shared mutable state, so the conditions commands/build.md
# puts on concurrent writers do not apply to it. Building is a different
# question and this script deliberately does not go there -- every job stops
# with a Draft spec awaiting a human.
#
# A job is one line of the manifest: comma-separated tickets, optional slug.
#
#     LD-223,LD-224,LD-225,LD-226   website-normalization
#     LD-234,LD-235                 google-ads-regions
#     LD-9
#
# Tickets that share files belong on one line. Four separate specs over one
# normalization path each propose their own helper, which is how a codebase
# ends up with three competing ones (CLAUDE.md rule 6).
#
#   -m, --manifest FILE  job list (default: tools/spec-batch.txt)
#   -p, --parallel N     concurrent jobs (default 1; they share one rate limit)
#   -b, --budget USD     --max-budget-usd per job (default 5)
#   -o, --out DIR        logs and run metadata (default: .spec-batch/)
#   -n, --dry-run        print the plan and exit
#   -y, --yes            skip the confirmation
#
# Exits 1 when declined or when any job fails.
set -Eeuo pipefail

MANIFEST=""; PARALLEL=1; BUDGET=5; OUT=""; DRY=0; YES=0
CLAUDE_BIN="${CLAUDE_BIN:-claude}"
while [ $# -gt 0 ]; do
  case "$1" in
    -m|--manifest) MANIFEST="${2:?--manifest needs a path}"; shift 2 ;;
    -p|--parallel) PARALLEL="${2:?--parallel needs a number}"; shift 2 ;;
    -b|--budget)   BUDGET="${2:?--budget needs a number}"; shift 2 ;;
    -o|--out)      OUT="${2:?--out needs a path}"; shift 2 ;;
    -n|--dry-run)  DRY=1; shift ;;
    -y|--yes)      YES=1; shift ;;
    -h|--help)     sed -n '2,28p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "batch-spec: unknown option $1" >&2; exit 1 ;;
  esac
done
case "$PARALLEL" in ''|*[!0-9]*) echo "batch-spec: --parallel needs a whole number" >&2; exit 1 ;; esac
[ "$PARALLEL" -ge 1 ] || { echo "batch-spec: --parallel must be at least 1" >&2; exit 1; }

ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "batch-spec: not a git repository" >&2; exit 1; }
cd "$ROOT"
MANIFEST="${MANIFEST:-tools/spec-batch.txt}"
OUT="${OUT:-$ROOT/.spec-batch}"
[ -f "$MANIFEST" ] || { echo "batch-spec: no manifest at $MANIFEST" >&2; exit 1; }
command -v "$CLAUDE_BIN" >/dev/null || { echo "batch-spec: '$CLAUDE_BIN' not on PATH" >&2; exit 1; }

# ------------------------------------------------------------- the manifest
TICKETS=(); SLUGS=(); SKIPPED=()
while IFS= read -r line || [ -n "$line" ]; do
  line="${line%%#*}"
  line="$(printf '%s' "$line" | tr -s '[:space:]' ' ' | sed 's/^ //;s/ $//')"
  [ -n "$line" ] || continue
  keys="${line%% *}"
  slug="${line#"$keys"}"; slug="${slug# }"
  [ -n "$slug" ] || slug="${keys%%,*}"
  # A ticket already specced in the main checkout is work already done.
  first="${keys%%,*}"
  if [ -f "docs/specs/$first-SPEC.md" ]; then SKIPPED+=("$slug ($first-SPEC.md exists)"); continue; fi
  TICKETS+=("${keys//,/ }"); SLUGS+=("$slug")
done < "$MANIFEST"

[ "${#SLUGS[@]}" -gt 0 ] || { echo "batch-spec: nothing to do (every job already has a spec)."; exit 0; }

# ------------------------------------------------------------------ the plan
echo "batch-spec: ${#SLUGS[@]} job(s), $PARALLEL at a time, \$$BUDGET cap each"
echo
for i in "${!SLUGS[@]}"; do
  printf '  %-26s %s\n' "${SLUGS[$i]}" "${TICKETS[$i]}"
done
for s in "${SKIPPED[@]:-}"; do [ -n "$s" ] && printf '  %-26s skipped\n' "$s"; done
echo
echo "Each job: a worktree at .claude/worktrees/<slug> on feature/<slug>, then"
echo "\`/spec <tickets>\` headless. Specs are left as Draft and uncommitted -- only"
echo "you approve one, and /plan pins the commit you make afterwards."
echo "Worst case \$$(( ${#SLUGS[@]} * BUDGET )); measured runs come in far under the cap."

if [ "$DRY" -eq 1 ]; then echo; echo "batch-spec: dry run; nothing started."; exit 0; fi
if [ "$YES" -eq 0 ]; then
  if [ ! -t 0 ]; then
    echo >&2; echo "batch-spec: stdin is not a terminal. Re-run with --yes, or --dry-run for the plan." >&2
    exit 1
  fi
  echo; printf 'Start? [y/N] '
  read -r reply || reply=""
  case "$reply" in [yY]|[yY][eE][sS]) echo ;; *) echo "batch-spec: aborted; nothing started."; exit 1 ;; esac
fi

mkdir -p "$OUT"

# --------------------------------------------------------------- one job
run_job() {
  local slug="$1" tickets="$2"
  local dir="$ROOT/.claude/worktrees/$slug" log="$OUT/$slug.log"
  (
    echo "=== $slug: $tickets"
    if [ -d "$dir" ]; then
      echo "worktree exists, reusing: $dir"
    else
      git worktree add -q -b "feature/$slug" "$dir" || { echo "worktree add failed"; exit 1; }
    fi
    # Run INSIDE the worktree. Without this the spec lands in the main
    # checkout -- the branch is created, nothing writes to it, and the file
    # turns up on whatever the editor has open.
    cd "$dir" || { echo "cannot enter $dir"; exit 1; }
    # Budget is a cap, not a target: a job that hits it stops mid-spec, which
    # shows up as a missing or truncated file rather than a silent overrun.
    "$CLAUDE_BIN" -p "/spec $tickets" \
      --permission-mode acceptEdits \
      --max-budget-usd "$BUDGET" \
      --output-format json > "$OUT/$slug.json" 2>&1 || echo "claude exited $?"
  ) > "$log" 2>&1
  local spec; spec="$(ls "$dir"/docs/specs/*-SPEC.md 2>/dev/null | head -1 || true)"
  if [ -n "$spec" ]; then echo "$slug|ok|$spec"; else echo "$slug|NO SPEC|$log"; fi
}

# ------------------------------------------------------------ run them
RESULTS="$OUT/results.txt"; : > "$RESULTS"
running=0
for i in "${!SLUGS[@]}"; do
  run_job "${SLUGS[$i]}" "${TICKETS[$i]}" >> "$RESULTS" &
  running=$((running+1))
  echo "  started  ${SLUGS[$i]}"
  if [ "$running" -ge "$PARALLEL" ]; then wait -n 2>/dev/null || wait; running=$((running-1)); fi
done
wait

# --------------------------------------------------------------- report
echo
failed=0
while IFS='|' read -r slug state where; do
  [ -n "$slug" ] || continue
  printf '  %-8s %-26s %s\n' "$state" "$slug" "$where"
  [ "$state" = ok ] || failed=$((failed+1))
done < "$RESULTS"

python3 - "$OUT" <<'PY' 2>/dev/null || true
import json, pathlib, sys
total = 0.0
for f in pathlib.Path(sys.argv[1]).glob('*.json'):
    try: total += json.loads(f.read_text()).get('total_cost_usd', 0) or 0
    except Exception: pass
if total: print(f'\n  measured total: ${total:.2f}')
PY

echo
echo "Specs are Draft and uncommitted. Read each one, then approve, commit, and /plan."
[ "$failed" -eq 0 ] || { echo "batch-spec: $failed job(s) produced no spec; see $OUT/*.log" >&2; exit 1; }
