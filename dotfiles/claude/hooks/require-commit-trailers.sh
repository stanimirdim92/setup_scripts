#!/usr/bin/env bash
# PreToolUse hook (matcher: Bash), scoped to the writing personas via their
# frontmatter `hooks:` — executor and test-engineer. Denies a `git commit`
# whose message has no `Refs:` trailer (git-workflow-and-versioning §Ticket
# trailers, ADR 0073). Plan coverage (`recall.py --trailer-only`) finds a
# ticket's commits by that trailer; a commit without it is invisible to it.
#
# It reads the message where the command carries it: `-m` / `--message`
# (heredocs included, since they are part of the command text) and
# `-F` / `--file`. A commit that reuses a message (`--amend --no-edit`, `-C`,
# `-c`, `--fixup`, `--squash`) or opens an editor is allowed: there is no new
# message to check, or none this hook can see. A file it cannot read is allowed
# too — a broken hook must not wedge a build. `Task:` is not required: review
# fixes and other unplanned commits have no task id.
#
# Exit 0 always; the decision is JSON on stdout, per
# https://code.claude.com/docs/en/hooks.
set -uo pipefail

input="$(cat)"
command="$(jq -r '.tool_input.command // empty' <<<"$input" 2>/dev/null)"
cwd="$(jq -r '.cwd // empty' <<<"$input" 2>/dev/null)"
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

# Strip git global options (`git -C dir`, `git -c k=v`, `git --no-pager`), the
# same normalisation block-agent-push.sh uses, so `git -C x commit` is seen.
normalized="$(sed -E \
  -e "s/\bgit((([[:space:]]+(-C|-c|--git-dir|--work-tree|--exec-path|--namespace)([[:space:]]+|=)(\"[^\"]*\"|'[^']*'|[^[:space:]]+)))|([[:space:]]+(--no-pager|--paginate|--bare|--literal-pathspecs|--no-optional-locks|--no-replace-objects)))+/git/g" \
  <<<"$command")"
# Detect the commit with quoted text removed, so `echo "git commit"` is not one.
unquoted="$(sed -E "s/\"[^\"]*\"//g; s/'[^']*'//g" <<<"$normalized")"
grep -Eq '\bgit[[:space:]]+commit\b' <<<"$unquoted" || exit 0

# No new message: reuse, fixup, or an amend that keeps the old one.
if grep -Eq '(^|[[:space:]])(--no-edit|-C|-c|--reuse-message(=|[[:space:]])|--reedit-message(=|[[:space:]])|--fixup(=|[[:space:]])|--squash(=|[[:space:]]))' <<<"$normalized"; then
  exit 0
fi

message=""
if grep -Eq '(^|[[:space:]])(-m|--message)([[:space:]=]|$)|(^|[[:space:]])-[a-zA-Z]*m([[:space:]]|$)' <<<"$normalized"; then
  message="$command"
else
  file="$(grep -Eo '(^|[[:space:]])(-F|--file)(=|[[:space:]]+)("[^"]+"|'"'"'[^'"'"']+'"'"'|[^[:space:]]+)' <<<"$normalized" | head -1 \
          | sed -E 's/^[[:space:]]*(-F|--file)(=|[[:space:]]+)//; s/^["'"'"']//; s/["'"'"']$//')"
  [ -z "$file" ] && exit 0            # editor: nothing to check here
  [ "$file" = "-" ] && exit 0          # message on stdin
  case "$file" in /*) path="$file" ;; *) path="${cwd:-.}/$file" ;; esac
  message="$(cat "$path" 2>/dev/null)" || exit 0
fi

if ! grep -Eq "(^|[[:space:]\"'])Refs:[[:space:]]*[A-Z][A-Z0-9]+-[0-9]+" <<<"$message"; then
  deny "End the commit message with git trailers: a blank line, then \`Refs: <TICKET>\` (for example \`Refs: LD-442\`) and, for a planned task, \`Task: T###\` on the next line (git-workflow-and-versioning §Ticket trailers). Plan coverage finds a ticket's commits by \`Refs:\`."
fi
exit 0
