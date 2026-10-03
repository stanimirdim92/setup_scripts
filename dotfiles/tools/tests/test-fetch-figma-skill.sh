#!/usr/bin/env bash
# Fixture tests for dotfiles/tools/setup/fetch-figma-skill.sh, with no network:
# FIGMA_SKILL_URL points at local files.
set -u
SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../setup" && pwd)/fetch-figma-skill.sh"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
pass=0; fail=0
check() { if [ "$2" = "$3" ]; then pass=$((pass+1)); else fail=$((fail+1)); echo "  FAIL [$1] expected '$2', got '$3'"; fi; }

printf 'tampered\n' > "$TMP/bad.md"
FIGMA_SKILL_URL="file://$TMP/bad.md" FIGMA_SKILL_DEST="$TMP/dest" bash "$SCRIPT" >/dev/null 2>"$TMP/err"; rc=$?
check mismatch_rc 1 "$rc"
check mismatch_not_installed 0 "$([ -e "$TMP/dest/SKILL.md" ] && echo 1 || echo 0)"
check mismatch_says 1 "$(grep -c 'checksum mismatch' "$TMP/err")"

FIGMA_SKILL_URL="file://$TMP/missing.md" FIGMA_SKILL_DEST="$TMP/dest" bash "$SCRIPT" >/dev/null 2>&1; rc=$?
check download_failure_rc 1 "$rc"

pinned="$(grep '^SHA256=' "$SCRIPT" | cut -d= -f2)"
check pin_is_a_sha256 64 "${#pinned}"

echo "fetch-figma-skill: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
