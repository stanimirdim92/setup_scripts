#!/usr/bin/env bash
# Does the candidate still pass on the current base? (ADR 0095)
#
# Two changes can each pass on their own and break the base together. A merge
# queue catches that by re-running the checks on the latest base with the
# change applied. This is the same check, for /ship, before GO:
#   1. fetch the base;
#   2. when the base has not moved past the candidate's merge base, report
#      "base current" and stop;
#   3. otherwise merge the base into a scratch worktree of the candidate (the
#      candidate itself is never touched), run the setup command, then each
#      check command, and report;
#   4. remove the scratch worktree.
#
# Usage:
#   base-check.sh --base origin/main [--setup "bin/worktree-setup.sh"] -- "composer test" "yarn build"
#
# Exit: 0 base current or every check passed · 1 merge conflict or a check
# failed · 2 usage error or the base cannot be fetched. Project-agnostic: the
# commands come from the plan's integrated verification.
set -uo pipefail

BASE="" SETUP="" KEEP=0
while [ $# -gt 0 ]; do
  case "$1" in
    --base) BASE="${2:?--base needs a ref}"; shift 2 ;;
    --setup) SETUP="${2:?--setup needs a command}"; shift 2 ;;
    --keep) KEEP=1; shift ;;
    -h|--help) sed -n '2,21p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    --) shift; break ;;
    *) echo "base-check: unknown argument $1" >&2; exit 2 ;;
  esac
done
[ -n "$BASE" ] || { echo "base-check: --base is required" >&2; exit 2; }
[ $# -gt 0 ] || { echo "base-check: give the check commands after --" >&2; exit 2; }

top="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "base-check: not in a git repository" >&2; exit 2; }
remote="${BASE%%/*}"
if [ "$remote" != "$BASE" ] && git remote | grep -qx "$remote"; then
  git fetch -q "$remote" "${BASE#*/}" 2>/dev/null || { echo "base-check: cannot fetch $BASE" >&2; exit 2; }
fi
base_sha="$(git rev-parse --verify -q "$BASE^{commit}")" || { echo "base-check: unknown base $BASE" >&2; exit 2; }
head_sha="$(git rev-parse HEAD)"

if git merge-base --is-ancestor "$base_sha" "$head_sha"; then
  echo "Base: current ($BASE ${base_sha:0:10} is already in the candidate ${head_sha:0:10}); no re-run needed."
  exit 0
fi
behind="$(git rev-list --count "$head_sha..$base_sha")"
echo "Base: moved ($BASE ${base_sha:0:10} has $behind commit(s) the candidate ${head_sha:0:10} lacks)."

# One scratch path per invocation: concurrent checks of the same candidate must
# never share, or remove, each other's checkout.
parent="$(git rev-parse --git-common-dir)/base-check"
mkdir -p "$parent" && parent="$(cd "$parent" && pwd)"
scratch="$(mktemp -d "$parent/${head_sha:0:10}-${base_sha:0:10}.XXXXXX")" || { echo "base-check: cannot create the scratch directory" >&2; exit 2; }
cleanup() { [ "$KEEP" = 1 ] || { git -C "$top" worktree remove --force "$scratch" >/dev/null 2>&1; rmdir "$scratch" 2>/dev/null; }; }
trap cleanup EXIT
git worktree add -q --detach "$scratch" "$head_sha" || { echo "base-check: cannot create the scratch worktree" >&2; exit 2; }

if ! git -C "$scratch" -c user.email=base-check@local -c user.name=base-check \
     merge -q --no-edit --no-ff "$base_sha" >/dev/null 2>&1; then
  echo "Merge: CONFLICT with the current base. Files:"
  git -C "$scratch" diff --name-only --diff-filter=U | sed 's/^/  /'
  exit 1
fi
echo "Merge: clean."

status=0
if [ -n "$SETUP" ]; then
  if (cd "$scratch" && bash -c "$SETUP") >"$scratch.setup.log" 2>&1; then
    echo "Setup: ok ($SETUP)"
  else
    echo "Setup: FAILED ($SETUP); log: $scratch.setup.log"
    exit 1
  fi
fi
for cmd in "$@"; do
  log="$scratch.$(printf '%s' "$cmd" | tr -c 'A-Za-z0-9' '_' | cut -c1-40).log"
  if (cd "$scratch" && bash -c "$cmd") >"$log" 2>&1; then
    echo "Check: pass  $cmd"
  else
    echo "Check: FAIL  $cmd  (log: $log)"
    tail -15 "$log" | sed 's/^/    /'
    status=1
  fi
done
exit "$status"
