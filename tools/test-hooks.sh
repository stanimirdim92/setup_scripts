#!/usr/bin/env bash
# Fixture tests for the PreToolUse hooks in dotfiles/claude/hooks/.
#
# Every case is (command, expected decision). Expected decisions are:
#   deny  — block-destructive-bash.sh must refuse
#   ask   — warn-force-push.sh must ask for confirmation
#   allow — the hook must stay out of the way (regression guard: a hook that
#           denies real work is as broken as one that misses a bypass)
#
# Run: tools/test-hooks.sh
#
# These exist because both hooks shipped with bypasses that a regex read like
# it covered: git aliases, git global options (`git -C x`, `git --no-pager`),
# quoted targets, and push's force-refspec forms. A guardrail nothing tests is
# a guardrail nobody has checked — see docs/adr/0049.
set -uo pipefail

HOOKS="$(cd "$(dirname "${BASH_SOURCE[0]}")/../dotfiles/claude/hooks" && pwd)"
BLOCK="$HOOKS/block-destructive-bash.sh"
WARN="$HOOKS/warn-force-push.sh"

command -v jq >/dev/null || { echo "test-hooks: jq is required" >&2; exit 1; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
# A repo on main, so branch-resolution paths are exercised for real.
git init -q -b main "$TMP/on-main"
git -C "$TMP/on-main" -c user.email=t@t -c user.name=t commit -q --allow-empty -m init
git init -q -b feature/x "$TMP/on-feature"
git -C "$TMP/on-feature" -c user.email=t@t -c user.name=t commit -q --allow-empty -m init

PASS=0; FAIL=0; FAILED=()

decision() { # hook, command, cwd
  jq -n --arg c "$2" --arg d "$3" '{tool_input:{command:$c},cwd:$d}' \
    | bash "$1" 2>/dev/null \
    | jq -r '.hookSpecificOutput.permissionDecision // "allow"' 2>/dev/null \
    || echo "ERROR"
}

check() { # hook, command, expected, cwd, label
  local got; got="$(decision "$1" "$2" "$4")"
  [ -z "$got" ] && got="allow"
  if [ "$got" = "$3" ]; then
    PASS=$((PASS+1))
  else
    FAIL=$((FAIL+1)); FAILED+=("[$5] $2 — expected $3, got $got")
  fi
}

blk()  { check "$BLOCK" "$1" "$2" "$TMP/on-feature" "block"; }
warn() { check "$WARN"  "$1" "$2" "${3:-$TMP/on-feature}" "warn"; }

# ---------------------------------------------------------------- block: rm
blk 'rm -rf /'                                  deny
blk 'rm -rf ~'                                  deny
blk 'rm -rf $HOME'                              deny
blk 'rm -rf "$HOME"'                            deny
blk "rm -rf '\$HOME'"                           deny
blk 'rm -rf ${HOME}'                            deny
blk 'rm -rf "${HOME}"'                          deny
blk 'rm -rf ~/'                                 deny
blk 'rm -rf /*'                                 deny
blk 'rm -rf .'                                  deny
blk 'rm -fr ..'                                 deny
blk 'rm -rf ./build'                            allow
blk 'rm -rf /srv/app/cache'                     allow
blk 'rm -rf node_modules'                        allow
blk 'rm -f /tmp/one-file'                       allow

# ------------------------------------------------------- block: git resets
blk 'git reset --hard'                          deny
blk 'git reset --hard HEAD~1'                   deny
blk 'git rlc'                                   deny
blk 'git -C /tmp reset --hard HEAD~1'           deny
blk 'git --no-pager reset --hard'               deny
blk 'git -c core.pager=cat reset --hard'        deny
blk 'git reset --soft HEAD~1'                   allow
blk 'git ulc'                                   allow
blk 'git reset HEAD -- file.txt'                allow

# --------------------------------------------- block: discarding worktree
blk 'git checkout .'                            deny
blk 'git co .'                                  deny
blk 'git restore .'                             deny
blk 'git checkout -f'                           deny
blk 'git switch -f main'                        deny
blk 'git switch --discard-changes main'         deny
blk 'git -C /srv checkout .'                    deny
blk 'git checkout ./src/file.ts'                allow
blk 'git checkout -b feature/new'               allow
blk 'git switch main'                           allow
blk 'git co main'                               allow

# ------------------------------------------------------- block: clean, -D
blk 'git clean -fd'                             deny
blk 'git clean --force'                         deny
blk 'git -C /tmp clean -fdx'                    deny
blk 'git branch -D old'                         deny
blk 'git clean -n'                              allow
blk 'git branch -d merged'                      allow

# --------------------------------------------------- block: block devices
blk 'dd if=/dev/zero of=/dev/sda'               deny
blk 'mkfs.ext4 /dev/nvme0n1'                    deny
blk 'dd if=x.img of=./out.img'                  allow

# ---------------------------------- warn: force push, remote never in text
# CLAUDE_CODE_REMOTE=true so a plain push does not ask; only force/destructive.
export CLAUDE_CODE_REMOTE=true
warn 'git push --force origin main'             ask
warn 'git push --force-with-lease origin main'  ask
warn 'git push -f origin master'                ask
warn 'git --no-pager push --force origin main'  ask
warn 'git -C /srv push --force origin main'     ask
warn 'git push origin +HEAD:main'               ask
warn 'git push origin +refs/heads/main'         ask
warn 'git push --mirror origin'                 ask
warn 'git push --delete origin main'            ask
warn 'git push origin :main'                    ask
warn 'git fu'                        ask "$TMP/on-main"     # alias, on main
warn 'git push --force-with-lease -u' ask "$TMP/on-main"    # no refspec, on main
warn 'git fu'                        allow "$TMP/on-feature" # force onto a feature branch
warn 'git push -u origin feature/x'             allow
warn 'git push'                                 allow
warn 'git ps'                                   allow
warn 'git status'                               allow
warn 'yarn install'                             allow

# ----------------------------------- warn: local session asks on any push
unset CLAUDE_CODE_REMOTE
warn 'git push -u origin feature/x'             ask
warn 'git ps'                                   ask
warn 'git status'                               allow
export CLAUDE_CODE_REMOTE=true

# ------------------------------------------------------------------ report
echo "hooks: $PASS passed, $FAIL failed"
if [ "$FAIL" -gt 0 ]; then
  printf '\n'
  for f in "${FAILED[@]}"; do echo "  FAIL $f"; done
  exit 1
fi
