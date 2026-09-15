#!/usr/bin/env bash
# Fixture tests for link_dotfiles.sh's confirmation gate.
#
# The gate exists because six of the destinations are whole directories and a
# real one is moved aside intact -- so the cases that matter are the ones where
# it must NOT act: a decline, a non-terminal stdin, a dry run. Each runs the
# real script against a throwaway $HOME and then checks the filesystem, because
# "it printed a warning" is not the same claim as "it changed nothing".
#
# Run: tools/test-link-dotfiles.sh
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LINK="$REPO/tools/link_dotfiles.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0; FAILED=()

check() { # label, expected, actual
  if [ "$2" = "$3" ]; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); FAILED+=("[$1] expected '$2', got '$3'"); fi
}
contains() { # label, needle, haystack
  case "$3" in *"$2"*) check "$1" y y ;; *) check "$1" y n ;; esac
}

# Not an empty HOME: a real one already holds files this script does not
# manage, and "it linked the right things" is only half the claim -- the other
# half is that it left everything else alone. Every case now carries two
# bystanders, asserted untouched at the end.
fresh_home() {  # -> a throwaway HOME with unmanaged content
  local h="$TMP/home-$1"; rm -rf "$h"; mkdir -p "$h/.claude" "$h/.codex"
  printf 'mine\n' > "$h/.claude/settings.local.json"
  printf 'notes\n' > "$h/.codex/notes.md"
  echo "$h"
}
bystanders_intact() {  # HOME -> y when the unmanaged files are untouched
  [ "$(cat "$1/.claude/settings.local.json" 2>/dev/null)" = mine ] \
    && [ "$(cat "$1/.codex/notes.md" 2>/dev/null)" = notes ] && echo y || echo n
}
run() {         # HOME, args... -> combined output; sets RC. stdin is a pipe.
  local h="$1"; shift
  OUT="$(HOME="$h" bash "$LINK" "$@" </dev/null 2>&1)"; RC=$?
}
run_tty() {     # HOME, answer, args... -> as run(), but stdin is a real pty
  local h="$1" answer="$2"; shift 2
  OUT="$(printf '%s\n' "$answer" | HOME="$h" script -qec "bash '$LINK' $*" /dev/null 2>&1)"; RC=$?
}
linked() {      # HOME -> 1 when the marquee link exists and points into the repo
  [ -L "$1/.claude/CLAUDE.md" ] && [ "$(readlink "$1/.claude/CLAUDE.md")" = "$REPO/dotfiles/claude/CLAUDE.md" ] \
    && echo 1 || echo 0
}

# -------------------------------------------------------------- the plan
H="$(fresh_home plan)"
run "$H" --dry-run
check  dry_run_rc                0 "$RC"
check  dry_run_changed_nothing   0 "$(linked "$H")"
contains dry_run_lists_new       "new       ~/.claude/CLAUDE.md" "$OUT"
contains dry_run_says_dry        "dry run; nothing changed"      "$OUT"
contains dry_run_warns_whole     "not merged with the repo"      "$OUT"

# A real directory is the case the warning is for: it must be named as one,
# with its size, not folded in with the files.
H="$(fresh_home realdir)"
mkdir -p "$H/.claude/agents" && touch "$H/.claude/agents/mine.md" "$H/.claude/agents/other.md"
run "$H" --dry-run
contains realdir_marked_loudly   "BACKUP    ~/.claude/agents"    "$OUT"
contains realdir_counts_entries  "2 entries"                     "$OUT"
contains realdir_says_whole      "moved whole"                   "$OUT"

H="$(fresh_home onedir)"
mkdir -p "$H/.claude/hooks" && touch "$H/.claude/hooks/one.sh"
run "$H" --dry-run
contains one_entry_singular      "1 entry,"                      "$OUT"

# ------------------------------------------------------- refusing to act
H="$(fresh_home pipe)"
run "$H"
check  no_tty_rc                 1 "$RC"
check  no_tty_changed_nothing    0 "$(linked "$H")"
contains no_tty_names_the_fix    "--yes"                         "$OUT"

H="$(fresh_home decline)"
run_tty "$H" n
check  decline_rc                1 "$RC"
check  decline_changed_nothing   0 "$(linked "$H")"
contains decline_says_so         "aborted; nothing changed"      "$OUT"

H="$(fresh_home empty_answer)"
run_tty "$H" ""
check  empty_answer_is_no        0 "$(linked "$H")"

H="$(fresh_home junk_answer)"
run_tty "$H" "sure"
check  junk_answer_is_no         0 "$(linked "$H")"

# ------------------------------------------------------------- proceeding
H="$(fresh_home yes_flag)"
run "$H" --yes
check  yes_flag_rc               0 "$RC"
check  yes_flag_linked           1 "$(linked "$H")"
check  yes_flag_dir_linked       1 "$([ -L "$H/.claude/agents" ] && echo 1 || echo 0)"

H="$(fresh_home tty_yes)"
run_tty "$H" y
check  tty_yes_linked            1 "$(linked "$H")"

# A real directory survives as .bak rather than being merged or deleted.
H="$(fresh_home backup)"
mkdir -p "$H/.claude/agents" && touch "$H/.claude/agents/mine.md"
run "$H" --yes
check  backup_dir_preserved      1 "$([ -f "$H/.claude/agents.bak/mine.md" ] && echo 1 || echo 0)"
check  backup_dir_relinked       1 "$([ -L "$H/.claude/agents" ] && echo 1 || echo 0)"

# Re-running an already-linked HOME must not prompt -- a gate that fires on a
# no-op re-run is one people learn to answer without reading.
run "$H" --dry-run
check  rerun_rc                  0 "$RC"
contains rerun_is_a_noop         "nothing to do"                 "$OUT"
case "$OUT" in *"Proceed?"*) check rerun_does_not_prompt n y ;; *) check rerun_does_not_prompt n n ;; esac

# A second run must not destroy the first run's backup. preflight refuses, and
# refuses before touching anything.
H="$(fresh_home twice)"
mkdir -p "$H/.claude" && echo real > "$H/.claude/CLAUDE.md" && echo older > "$H/.claude/CLAUDE.md.bak"
run "$H" --yes
check  existing_bak_rc           1 "$RC"
contains existing_bak_named      "Refusing to overwrite existing backup" "$OUT"
check  existing_bak_kept         "older" "$(cat "$H/.claude/CLAUDE.md.bak")"
check  existing_bak_orig_kept    "real"  "$(cat "$H/.claude/CLAUDE.md")"
check  existing_bak_nothing_done 0 "$(linked "$H")"

# A symlink whose target no longer exists is still a symlink: relink, not
# backup. `[ -e ]` is false for it, so a naive check would call it new.
H="$(fresh_home dangling)"
mkdir -p "$H/.claude" && ln -s /nowhere/missing "$H/.claude/settings.json"
run "$H" --dry-run
contains dangling_is_relink      "relink    ~/.claude/settings.json" "$OUT"
run "$H" --yes
check  dangling_relinked         1 "$([ "$(readlink "$H/.claude/settings.json")" = "$REPO/dotfiles/claude/settings.json" ] && echo 1 || echo 0)"
check  dangling_no_bak           0 "$([ -e "$H/.claude/settings.json.bak" ] && echo 1 || echo 0)"

# ------------------------------------------------------------------ flags
H="$(fresh_home flags)"
run "$H" --help
check  help_rc                   0 "$RC"
contains help_shows_usage        "--dry-run"                     "$OUT"
check  help_changed_nothing      0 "$(linked "$H")"

run "$H" --bogus
check  unknown_flag_rc           1 "$RC"
contains unknown_flag_names_it   "unknown option --bogus"        "$OUT"
check  unknown_flag_no_change    0 "$(linked "$H")"

# Nothing above may have disturbed a file the script does not manage.
for name in plan realdir onedir pipe decline empty_answer junk_answer yes_flag tty_yes backup twice dangling flags; do
  h="$TMP/home-$name"; [ -d "$h" ] || continue
  check "bystanders_$name" y "$(bystanders_intact "$h")"
done

echo "link_dotfiles: $PASS passed, $FAIL failed"
if [ "$FAIL" -gt 0 ]; then printf '\n'; for f in "${FAILED[@]}"; do echo "  FAIL $f"; done; exit 1; fi
