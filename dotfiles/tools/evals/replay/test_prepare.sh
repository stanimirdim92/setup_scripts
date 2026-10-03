#!/usr/bin/env bash
# Fixture tests for prepare.sh against a throwaway git project. Runs in CI.
set -u
SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/prepare.sh"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
pass=0; fail=0
check() { if [ "$2" = "$3" ]; then pass=$((pass+1)); else fail=$((fail+1)); echo "  FAIL [$1] expected '$2', got '$3'"; fi; }
g() { git -C "$P" -c user.email=t@t -c user.name=t "$@"; }

P="$TMP/app"; mkdir -p "$P"; g init -q -b main
printf '.env\nnode_modules/\n' > "$P/.gitignore"; printf '.env\n' > "$P/.worktreeinclude"
echo base > "$P/a.txt"; g add -A; g commit -qm 'base work'
echo secret=1 > "$P/.env"
mkdir -p "$P/docs/specs"; echo answer > "$P/docs/specs/LD-441-SPEC.md"; g add -A; g commit -qm 'docs(spec): LD-441 draft'
echo impl > "$P/a.txt"; g commit -qam 'feat: LD-442 T001'

bash "$SCRIPT" "$P" 'LD-44[12]' "$TMP/replay" >/dev/null 2>&1; rc=$?
check prepare_rc 0 "$rc"
check base_content base "$(cat "$TMP/replay/a.txt" 2>/dev/null)"
check answer_absent 0 "$([ -e "$TMP/replay/docs/specs/LD-441-SPEC.md" ] && echo 1 || echo 0)"
check one_commit 1 "$(git -C "$TMP/replay" rev-list --count --all 2>/dev/null)"
check no_remote '' "$(git -C "$TMP/replay" remote 2>/dev/null)"
check env_copied secret=1 "$(cat "$TMP/replay/.env" 2>/dev/null)"
check temp_branch_removed 0 "$(git -C "$P" branch --list 'replay/*' | wc -l | tr -d ' ')"

bash "$SCRIPT" "$P" 'LD-44[12]' "$TMP/replay" >/dev/null 2>&1; check existing_dest_rc 1 "$?"
bash "$SCRIPT" "$P" 'LD-999' "$TMP/other" >/dev/null 2>&1; check no_match_rc 1 "$?"

mkdir -p "$TMP/locked"; chmod 555 "$TMP/locked"
if [ ! -w "$TMP/locked" ]; then   # root can write anywhere; the case only holds for a normal user
  bash "$SCRIPT" "$P" 'LD-44[12]' "$TMP/locked/replay" >/dev/null 2>"$TMP/err"; check unwritable_rc 1 "$?"
  check unwritable_says 1 "$(grep -c 'not writable' "$TMP/err")"
fi
chmod 755 "$TMP/locked"

echo "replay prepare: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
