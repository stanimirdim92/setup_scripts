#!/usr/bin/env bash
# Creates a fresh sandbox project for the ADD-1 eval.
#
#   evals/add-business/setup.sh DEST
#
# Copies seed/ to DEST, writes the ticket as docs/specs/ADD-1-intake.md (the
# intake /spec accepts), and makes one initial commit. DEST must be outside this
# repository and must not exist, or be empty. hidden/ and reference/ are never copied.
set -euo pipefail

HERE=$(cd "$(dirname "$0")" && pwd)
TICKET="$HERE/ticket.md"

die() { echo "setup.sh: $*" >&2; exit 2; }

[ $# -eq 1 ] || die "usage: setup.sh DEST"
command -v git >/dev/null || die "missing tool: git"

parent=$(dirname -- "$1")
[ -d "$parent" ] || die "parent directory does not exist: $parent"
DEST="$(cd -- "$parent" && pwd)/$(basename -- "$1")"
[ -d "$DEST" ] && DEST=$(cd -- "$DEST" && pwd)

# Refuse this checkout and, from a linked worktree, the main checkout too.
REPO=$(git -C "$HERE" rev-parse --show-toplevel 2>/dev/null || echo "$HERE")
MAIN=$(dirname "$(git -C "$HERE" rev-parse --path-format=absolute --git-common-dir 2>/dev/null || echo "$REPO/.git")")
for root in "$REPO" "$MAIN"; do
  case "$DEST/" in
    "$root"/*) die "DEST is inside $root. Pick a directory outside it, for example /tmp/add-business-run" ;;
  esac
done
if [ -e "$DEST" ]; then
  [ -d "$DEST" ] || die "DEST exists and is not a directory: $DEST"
  [ -z "$(ls -A -- "$DEST")" ] || die "DEST exists and is not empty: $DEST"
fi

mkdir -p "$DEST"
cp -R "$HERE/seed/." "$DEST/"
mkdir -p "$DEST/docs/specs"

# Prints the body of "## NAME" in ticket.md, without the heading.
section() { awk -v h="## $1" '$0 == h { f = 1; next } /^## / { f = 0 } f' "$TICKET"; }
field() { sed -n "s/^\*\*$1:\*\* *//p" "$TICKET" | head -1; }

{
  echo "### ADD-1 — $(sed -n '1s/^# ADD-1 — //p' "$TICKET")"
  echo
  echo "Fetched: $(date +%F). Source: the eval ticket (no live Jira)."
  echo
  echo "**Status:** $(field Status)  "
  echo "**Type:** $(field Type)  "
  echo "**Priority:** $(field Priority)  "
  echo "**Assignee:** $(field Assignee)"
  echo
  echo "**Subtasks / Child Issues**"
  section 'Sub-tasks' | sed -n 's/^- \(ADD-[0-9]*\) — \(.*\)$/- \1 — Sub-task — \2 — To Do/p'
  echo
  echo "**Related Issues**"
  echo "- None."
  echo
  echo "**Source Coverage**"
  echo "- Tickets: 7 unique discovered; enumeration complete — 7 fully read, 0 partially read, 0 unread."
  echo "- ADD-1 — read — description, scope, flow, states, rules, copy, accessibility and API contract, acceptance criteria."
  echo "- ADD-2 to ADD-7 — read — titles only. The sub-tasks have no description of their own."
  echo "- Design file — none attached. The States, Copy and Accessibility contract sections are the design reference."
  echo
  echo "**Requirements**"
  echo
  for name in 'Summary' 'Scope' 'Out of scope' 'User flow' 'States' 'Duplicate rules' \
              'Interaction rules' 'Copy' 'Accessibility contract' 'API contract' 'Test hooks'; do
    echo "#### $name"
    section "$name" | sed 's/^### /##### /'
  done
  echo "**Acceptance Criteria**"
  section 'Acceptance criteria'
  echo "**Constraints**"
  section 'Constraints'
  echo "**Relevant Context**"
  echo "- The project's commands and conventions are in CLAUDE.md (same text in AGENTS.md)."
  echo
  echo "**Questions for \`/spec\`**"
  echo "- Where the request ID and the enrichment request live in the existing schema."
  echo "- How the modal fits the existing front end in \`public/assets/app.js\` and \`app.css\`."
  echo "- Which existing test patterns the new endpoints and rules follow."
  echo
  echo "**Blockers**"
  echo "- None."
  echo
  echo "**Next action:** \`/clear\`, then \`/spec ADD-1\`"
} >"$DEST/docs/specs/ADD-1-intake.md"

cd "$DEST"
git init -q
git add -A
git -c user.name="ADD-1 eval" -c user.email="eval@example.invalid" -c commit.gpgsign=false \
  commit -q -m "Acme Leads: starting point for ADD-1"

cat <<EOF
Sandbox ready: $DEST
Intake:        $DEST/docs/specs/ADD-1-intake.md

Next:
  cd $DEST
  claude
  /spec ADD-1

When the pipeline is done, score it:
  $HERE/grade.sh $DEST
EOF
