#!/usr/bin/env bash
# PreToolUse hook (matcher: Bash), scoped to the writing personas via their
# frontmatter `hooks:` — executor and test-engineer. Hard-denies anything that
# moves work off the machine: `git push` in every spelling, and the `gh`
# commands that push or publish for you. Local commits and local tags stay
# allowed — they are what /review and /ship inspect; nothing reaches a remote
# until a human pushes. Exit 0 always; the decision is JSON on stdout, per
# https://code.claude.com/docs/en/hooks.
set -euo pipefail

input="$(cat)"
command="$(jq -r '.tool_input.command // empty' <<<"$input")"

[ -z "$command" ] && exit 0

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

# Same normalisation as warn-force-push.sh: strip git global options, then
# expand the dotfiles/.gitconfig aliases and push typos that reach `push`.
# Keep the alias list in sync with that [alias] section and with
# warn-force-push.sh; every form is covered by tools/test-hooks.sh.
command="$(sed -E \
  -e "s/\bgit((([[:space:]]+(-C|-c|--git-dir|--work-tree|--exec-path|--namespace)([[:space:]]+|=)(\"[^\"]*\"|'[^']*'|[^[:space:]]+)))|([[:space:]]+(--no-pager|--paginate|--bare|--literal-pathspecs|--no-optional-locks|--no-replace-objects)))+/git/g" \
  -e 's/\bgit[[:space:]]+fu\b/git push --force-with-lease -u/g' \
  -e 's/\bgit[[:space:]]+(pish|poush|ps|psuh|puhs|puosh|pus|pushy|toyou|tpush|upsh)\b/git push/g' \
  <<<"$command")"

if echo "$command" | grep -Eq '\bgit[[:space:]]+push\b'; then
  deny "This persona may commit and tag locally but never push — the orchestrator or a human pushes after /review. Report the commit id instead."
fi

# `gh` can push or publish without the word push: pr create pushes the branch
# when it isn't upstream yet, pr merge lands it, release create publishes.
if echo "$command" | grep -Eq '\bgh[[:space:]]+(pr[[:space:]]+(create|merge)|release[[:space:]]+create|repo[[:space:]]+sync)\b'; then
  deny "This persona may not open, merge, or publish anything on the remote — leave that to the orchestrator or a human after /review."
fi

exit 0
