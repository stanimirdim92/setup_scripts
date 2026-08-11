#!/usr/bin/env bash
# PreToolUse hook (matcher: Bash). Hard-blocks a short list of commands that
# are almost never intentional and hard to undo. Exit 0 always; a "deny"
# decision is communicated via JSON on stdout, per Claude Code's hook schema
# (see https://code.claude.com/docs/en/hooks).
set -euo pipefail

input="$(cat)"
command="$(jq -r '.tool_input.command // empty' <<<"$input")"

deny() {
  jq -n --arg reason "$1" '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: $reason
    }
  }'
  exit 0
}

[ -z "$command" ] && exit 0

# rm -rf (or -fr, or -r -f) targeting root, home, a bare dot/dotdot, or a
# top-level wildcard. The target must be its own whitespace-delimited word
# (immediately followed by a space or end-of-string) so this does NOT match
# a real path like `rm -rf ./build` or `rm -rf /srv/app` — only bare `/`,
# `~`, `$HOME`, `.`, `..`, `/*`, or `~/*`.
if echo "$command" | grep -Eq 'rm[[:space:]]+(-[a-zA-Z]*[rf][a-zA-Z]*|--recursive|--force)([[:space:]]+-[a-zA-Z-]+)*[[:space:]]+(/\*?|~(/\*)?|\$HOME|\.{1,2})([[:space:]]|$)'; then
  deny "rm -rf against /, ~, \$HOME, or . is almost never intended — confirm the exact path with the user first."
fi

# Writing directly to a block device.
if echo "$command" | grep -Eq '(dd|mkfs\.\w+|shred)[[:space:]].*(of=)?/dev/(sd|nvme|xvd|vd|hd)[a-z0-9]+'; then
  deny "Direct write to a block device ($command) — confirm this isn't a typo'd path before running it."
fi

# chmod/chown -R on root or home. Allows the mode/owner argument to appear
# on either side of -R (`chmod -R 777 /` or `chmod 777 -R /`), same
# word-boundary logic as rm above so a real path doesn't match.
if echo "$command" | grep -Eq '(chmod|chown)[[:space:]]+(-R[[:space:]]+[^[:space:]]+|[^[:space:]]+[[:space:]]+-R)[[:space:]]+(/|~|\$HOME)([[:space:]]|$)'; then
  deny "Recursive chmod/chown on / or \$HOME — almost always a mistyped path."
fi

# git reset --hard: discards uncommitted work (and, with a ref, commits too)
# with no undo. Two independent greps, order-independent, same style as
# warn-force-push.sh — the ref (if any) can sit on either side of the flag.
if echo "$command" | grep -Eq 'git[[:space:]]+reset\b' \
  && echo "$command" | grep -Eq -- '--hard\b'; then
  deny "git reset --hard discards uncommitted changes with no undo — confirm nothing unsaved is about to be lost."
fi

# git clean -f (or -fd, -fdx, --force, any combination): permanently deletes
# untracked files. Matches -f alone, combined short flags containing f
# (-fd, -df, -xfd, ...), or the --force long form.
if echo "$command" | grep -Eq 'git[[:space:]]+clean\b' \
  && echo "$command" | grep -Eq -- '(^|[[:space:]])(-[a-zA-Z]*f[a-zA-Z]*|--force)([[:space:]]|$)'; then
  deny "git clean -f permanently deletes untracked files — confirm nothing untracked is worth keeping first."
fi

# git branch -D (or -D combined with other short flags, or --delete
# together with --force): force-deletes a branch, discarding any commits
# on it that aren't reachable from elsewhere.
if echo "$command" | grep -Eq 'git[[:space:]]+branch\b' \
  && { echo "$command" | grep -Eq -- '(^|[[:space:]])(-[a-zA-Z]*D[a-zA-Z]*)([[:space:]]|$)' \
    || { echo "$command" | grep -Eq -- '--delete\b' && echo "$command" | grep -Eq -- '--force\b'; }; }; then
  deny "git branch -D force-deletes the branch, discarding any commits on it that aren't reachable elsewhere."
fi

# git checkout . / git restore .: discards all uncommitted changes in the
# working tree. Same word-boundary logic as rm above — a real path like
# `git checkout ./src` does NOT match, only a bare `.` as its own argument.
if echo "$command" | grep -Eq 'git[[:space:]]+(checkout|restore)([[:space:]]+-[a-zA-Z-]+)*[[:space:]]+\.([[:space:]]|$)'; then
  deny "This discards every uncommitted change in the working tree with no undo — confirm that's really intended."
fi

exit 0
