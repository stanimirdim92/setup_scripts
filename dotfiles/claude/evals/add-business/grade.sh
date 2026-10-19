#!/usr/bin/env bash
# Scores a project against the hidden ADD-1 checks.
#
#   dotfiles/claude/evals/add-business/grade.sh DEST
#
# Prints one JSON object (per-check and per-criterion pass/fail, and totals).
# Exit 0: every check passed. Exit 1: some check failed. Exit 2: the grader could
# not run (missing tool, bad DEST). Set GRADE_KEEP=1 to keep the logs.
set -uo pipefail

HERE=$(cd "$(dirname "$0")" && pwd)
HIDDEN="$HERE/hidden"

die() { echo "grade.sh: $*" >&2; exit 2; }

[ $# -eq 1 ] || die "usage: grade.sh DEST"
[ -d "$1" ] || die "not a directory: $1"
DEST=$(cd "$1" && pwd)
[ -f "$DEST/bin/serve" ] && [ -f "$DEST/bin/migrate" ] || die "$DEST has no bin/serve or bin/migrate"

for tool in php node npm; do
  command -v "$tool" >/dev/null || die "missing tool: $tool"
done
php -r 'exit(in_array("sqlite", PDO::getAvailableDrivers(), true) ? 0 : 1);' \
  || die "php has no pdo_sqlite driver"

if [ ! -d "$HIDDEN/node_modules/@playwright/test" ]; then
  (cd "$HIDDEN" && npm ci --no-audit --no-fund --silent) >&2 || die "npm ci failed in $HIDDEN"
fi

WORK=$(mktemp -d "${TMPDIR:-/tmp}/add-business-grade.XXXXXX") || die "mktemp failed"
if [ "${GRADE_KEEP:-}" = 1 ]; then
  echo "grade.sh: logs in $WORK" >&2
else
  trap 'rm -rf "$WORK"' EXIT
fi

# Baseline: the project's own tests.
(cd "$DEST" && php tests/run.php) >"$WORK/base1.log" 2>&1
echo $? >"$WORK/base1.status"

# API checks (PHP, against bin/serve).
php "$HIDDEN/api/run.php" "$DEST" "$WORK/api.json" "$HIDDEN/fixtures/places.json" "$WORK" \
  >"$WORK/api.log" 2>&1

# UI checks (Playwright, one bin/serve per worker).
(cd "$HIDDEN" && DEST="$DEST" GRADE_WORK="$WORK" FIXTURE="$HIDDEN/fixtures/places.json" \
  UI_REPORT="$WORK/ui.json" npx --no-install playwright test) >"$WORK/ui.log" 2>&1
if [ ! -s "$WORK/ui.json" ]; then
  tail -20 "$WORK/ui.log" >&2
  die "Playwright wrote no report. Is Chromium installed? Run: (cd $HIDDEN && npx playwright install chromium)"
fi

node "$HIDDEN/report.mjs" "$WORK" "$DEST"
