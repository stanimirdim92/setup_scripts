#!/usr/bin/env bash
# PreToolUse hook (matcher: Bash). Force-pushing to main/master always asks,
# everywhere — it's the harder-to-undo case regardless of surface. A plain
# push only asks in a local IDE session ($CLAUDE_CODE_REMOTE unset): that's
# where edits need review before they leave the machine. In Claude app /
# Claude Code on the web ($CLAUDE_CODE_REMOTE=true), plain pushes go through
# without asking — that surface is fine pushing on its own.
# This asks rather than hard-denies (unlike block-destructive-bash.sh) —
# see https://code.claude.com/docs/en/hooks.
set -euo pipefail

input="$(cat)"
command="$(jq -r '.tool_input.command // empty' <<<"$input")"
cwd="$(jq -r '.cwd // empty' <<<"$input")"

[ -z "$command" ] && exit 0

# dotfiles/.gitconfig defines shortcut/typo aliases that expand to commands
# checked below -- `fu` -> `push --force-with-lease -u`, plus a dozen push typos -- and git
# accepts global options between `git` and the subcommand (`git -C /srv push`,
# `git --no-pager push`), so a grep for the spelled-out command misses both.
# Normalise before matching: expand the aliases, then strip the global options.
# Keep the alias list in sync with the [alias] section of dotfiles/.gitconfig.
# Every form here is covered by tools/test-hooks.sh -- add a fixture before
# adding a matcher. Note `git help.autocorrect = 1` can still run a near-miss
# typo that no fixed list covers.
command="$(sed -E \
  -e 's/\bgit[[:space:]]+fu\b/git push --force-with-lease -u/g' \
  -e 's/\bgit[[:space:]]+(pish|poush|ps|psuh|puhs|puosh|pus|pushy|toyou|tpush|upsh)\b/git push/g' \
  -e 's/\bgit((([[:space:]]+(-C|-c|--git-dir|--work-tree|--exec-path|--namespace)([[:space:]]+|=)[^[:space:]]+))|([[:space:]]+(--no-pager|--paginate|--bare|--literal-pathspecs|--no-optional-locks|--no-replace-objects)))+/git/g' \
  <<<"$command")"

ask() {
  jq -n --arg reason "$1" '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "ask",
      permissionDecisionReason: $reason
    }
  }'
  exit 0
}

! echo "$command" | grep -Eq 'git[[:space:]]+push\b' && exit 0

# --mirror can delete every remote ref that isn't present locally, whatever
# branch you're on, so it asks unconditionally rather than via the main/master
# check below.
if echo "$command" | grep -Eq -- '(^|[[:space:]])--mirror([[:space:]]|$)'; then
  ask "git push --mirror can delete remote refs that don't exist locally — confirm this is intentional."
fi

# Deleting a remote branch: --delete, or a refspec with an empty source
# (`git push origin :main`). Outward-facing and awkward to undo on any branch,
# so this also asks unconditionally.
if echo "$command" | grep -Eq -- '(^|[[:space:]])--delete([[:space:]]|$)' \
  || echo "$command" | grep -Eq '(^|[[:space:]]):[^[:space:]]+'; then
  ask "This deletes a remote branch — confirm the branch and remote first."
fi

# Force, including the `+refspec` spelling (`git push origin +HEAD:main`),
# which is a force push that never writes the word --force.
if echo "$command" | grep -Eq -- '(--force([[:space:]]|$)|--force-with-lease|(^|[[:space:]])-f([[:space:]]|$)|(^|[[:space:]])\+[^[:space:]]+)'; then
  # An alias-expanded force push (`git fu`) carries no refspec, so the branch
  # it targets isn't in the command text — resolve the checked-out branch to
  # catch a force push to main/master that never spells the name out.
  branch=""
  if [ -n "$cwd" ]; then
    branch="$(git -C "$cwd" rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
  fi

  if echo "$command" | grep -Eq '(main|master)' \
    || [ "$branch" = "main" ] || [ "$branch" = "master" ]; then
    ask "Force-push to main/master — confirm this is intentional."
  fi
fi

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  ask "git push from a local IDE session — confirm before pushing so edits get reviewed first."
fi

exit 0
