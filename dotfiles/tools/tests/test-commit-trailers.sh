#!/usr/bin/env bash
# Fixture tests for dotfiles/claude/hooks/require-commit-trailers.sh.
#
# Every case is (command, expected decision). The allow cases matter as much
# as the deny ones: the hook runs on every Bash call an executor makes, and a
# hook that blocks an ordinary command or a message-reusing commit stops a
# build for nothing.
#
# Run: dotfiles/tools/tests/test-commit-trailers.sh
set -uo pipefail

HOOK="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../claude/hooks" && pwd)/require-commit-trailers.sh"
command -v jq >/dev/null || { echo "test-commit-trailers: jq is required" >&2; exit 1; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
printf 'Rank the feed\n\nRefs: LD-442\nTask: T002\n' > "$TMP/good.txt"
printf 'Rank the feed\n' > "$TMP/bad.txt"

PASS=0; FAIL=0
run() {  # expected command
  local expected="$1" cmd="$2" out decision
  out="$(jq -n --arg c "$cmd" --arg d "$TMP" '{tool_input: {command: $c}, cwd: $d}' | bash "$HOOK")"
  decision="$(jq -r '.hookSpecificOutput.permissionDecision // "allow"' <<<"${out:-{\}}")"
  if [ "$decision" = "$expected" ]; then PASS=$((PASS + 1))
  else FAIL=$((FAIL + 1)); echo "FAIL expected $expected, got $decision: $cmd"; fi
}

# deny: a new message without Refs:
run deny  'git commit -m "Rank the feed"'
run deny  'git commit -qm "Rank the feed"'
run deny  'git -C /repo commit -m "Rank the feed" -m "Task: T002"'
run deny  'git commit -F bad.txt'
run deny  "git commit --file=$TMP/bad.txt"
run deny  'git commit -m "Refs: see the ticket"'
run deny  'git add -A && git commit -m "Rank the feed"'

# allow: trailers present, in every way a message is passed
run allow 'git commit -m "Rank the feed" -m "Refs: LD-442
Task: T002"'
run allow "git commit -m \"\$(cat <<'EOF'
Rank the feed

Refs: LD-442
Task: T002
EOF
)\""
run allow 'git commit -F good.txt'
run allow "git commit --file $TMP/good.txt"
run allow 'git commit -m "test: pin Latest order" -m "Refs: LD-441"'

# allow: no new message, or nothing this hook can read
run allow 'git commit --amend --no-edit'
run allow 'git commit --fixup HEAD~1'
run allow 'git commit -C HEAD'
run allow 'git commit'
run allow 'git commit -F -'
run allow 'git commit -F missing.txt'

# allow: not a commit
run allow 'git status'
run allow 'git log --grep "commit -m"'
run allow 'composer test'
run allow 'echo "git commit -m x" > notes.txt && git tag v1'

echo "test-commit-trailers: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
