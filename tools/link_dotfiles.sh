#!/usr/bin/env bash
# link_dotfiles.sh [-y|--yes] [-n|--dry-run] [-h|--help]
#
# Symlinks AI-tool dotfiles from this repo into $HOME, backing up any existing
# real file the first time (as <name>.bak). Safe to re-run and failure-atomic for
# paths changed during the current invocation.
#
# Prints what it is about to do and asks before changing anything, because the
# destinations include whole directories (~/.claude/agents, skills, hooks,
# commands, references, docs): a real directory is moved aside whole, it does
# not merge with the repo's.
#
#   -y, --yes      skip the confirmation (required when stdin is not a terminal)
#   -n, --dry-run  print the plan and exit without changing anything
#
# Exits 1 when declined, having changed nothing.
set -Eeuo pipefail

ASSUME_YES=0
DRY_RUN=0
while [ $# -gt 0 ]; do
  case "$1" in
    -y|--yes)     ASSUME_YES=1; shift ;;
    -n|--dry-run) DRY_RUN=1; shift ;;
    -h|--help)    sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "link_dotfiles: unknown option $1" >&2; exit 1 ;;
  esac
done

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOTFILES="$REPO_DIR/dotfiles"

SOURCES=(
  "$DOTFILES/claude/AGENTS.md"
  "$DOTFILES/claude/AGENTS.md"
  "$DOTFILES/claude/settings.json"
  "$DOTFILES/claude/statusline.sh"
  "$DOTFILES/claude/subagent-statusline.sh"
  "$DOTFILES/claude/remote-settings.json"
  "$DOTFILES/claude/agents"
  "$DOTFILES/claude/skills"
  "$DOTFILES/claude/hooks"
  "$DOTFILES/claude/commands"
  "$DOTFILES/claude/references"
  "$DOTFILES/claude/docs"
  "$DOTFILES/codex/config.toml"
  "$DOTFILES/codex/rules/default.rules"
  "$DOTFILES/claude/AGENTS.md"
  "$DOTFILES/codex/agents"
  "$DOTFILES/codex/hooks"
  "$DOTFILES/codex/hooks.json"
  "$DOTFILES/codex/references"
  "$DOTFILES/codex/bin/codex-worktree"
)
DESTINATIONS=(
  "$HOME/.claude/CLAUDE.md"
  "$HOME/.claude/AGENTS.md"
  "$HOME/.claude/settings.json"
  "$HOME/.claude/statusline.sh"
  "$HOME/.claude/subagent-statusline.sh"
  "$HOME/.claude/remote-settings.json"
  "$HOME/.claude/agents"
  "$HOME/.claude/skills"
  "$HOME/.claude/hooks"
  "$HOME/.claude/commands"
  "$HOME/.claude/references"
  "$HOME/.claude/docs"
  "$HOME/.codex/config.toml"
  "$HOME/.codex/rules/default.rules"
  "$HOME/.codex/AGENTS.md"
  "$HOME/.codex/agents"
  "$HOME/.codex/hooks"
  "$HOME/.codex/hooks.json"
  "$HOME/.codex/references"
  "$HOME/.local/bin/codex-worktree"
)

CHANGED_DESTINATIONS=()
CHANGE_KINDS=()
OLD_TARGETS=()

rollback() {
  local status=$? i dst kind old
  trap - ERR
  echo "link_dotfiles: failure; reverting ${#CHANGED_DESTINATIONS[@]} changed path(s)" >&2
  for ((i=${#CHANGED_DESTINATIONS[@]}-1; i>=0; i--)); do
    dst="${CHANGED_DESTINATIONS[$i]}"
    kind="${CHANGE_KINDS[$i]}"
    old="${OLD_TARGETS[$i]}"
    rm -f "$dst"
    case "$kind" in
      backup) mv "$dst.bak" "$dst" ;;
      relink) ln -s "$old" "$dst" ;;
    esac
  done
  exit "$status"
}

preflight_link() {
  local dst="$1"
  if [ ! -L "$dst" ] && [ -e "$dst" ] && { [ -e "$dst.bak" ] || [ -L "$dst.bak" ]; }; then
    echo "Refusing to overwrite existing backup: $dst.bak" >&2
    return 1
  fi
}

link() {
  local src="$1" dst="$2"

  if [ -L "$dst" ]; then
    if [ "$(readlink "$dst")" = "$src" ]; then
      echo "ok      $dst"
      return
    fi
    echo "relink  $dst (was -> $(readlink "$dst"))"
    CHANGED_DESTINATIONS+=("$dst")
    CHANGE_KINDS+=("relink")
    OLD_TARGETS+=("$(readlink "$dst")")
    rm "$dst"
  elif [ -e "$dst" ]; then
    echo "backup  $dst -> $dst.bak"
    CHANGED_DESTINATIONS+=("$dst")
    CHANGE_KINDS+=("backup")
    OLD_TARGETS+=("")
    mv "$dst" "$dst.bak"
  else
    CHANGED_DESTINATIONS+=("$dst")
    CHANGE_KINDS+=("new")
    OLD_TARGETS+=("")
  fi

  mkdir -p "$(dirname "$dst")"
  ln -s "$src" "$dst"
  echo "linked  $dst -> $src"
}

# Preflight both the main links and Codex adapters before changing anything.
python3 "$DOTFILES/codex/install-skills.py" --preflight
for i in "${!DESTINATIONS[@]}"; do
  if [ ! -e "${SOURCES[$i]}" ]; then
    echo "Missing link source: ${SOURCES[$i]}" >&2
    exit 1
  fi
  preflight_link "${DESTINATIONS[$i]}"
done

# ---------------------------------------------------------------- the plan
# Same tests as link(), run without mutating, so the confirmation describes
# what will actually happen to each path rather than warning in general.
tilde() { case "$1" in "$HOME"/*) printf '~%s' "${1#"$HOME"}" ;; *) printf '%s' "$1" ;; esac; }

plan_kind() {  # dst src -> ok | relink | backup-dir | backup | new
  local dst="$1" src="$2"
  if [ -L "$dst" ]; then
    [ "$(readlink "$dst")" = "$src" ] && { echo ok; return; }
    echo relink; return
  fi
  [ -d "$dst" ] && { echo backup-dir; return; }
  [ -e "$dst" ] && { echo backup; return; }
  echo new
}

CHANGES=0
PLAN=()
for i in "${!DESTINATIONS[@]}"; do
  dst="${DESTINATIONS[$i]}"; src="${SOURCES[$i]}"
  case "$(plan_kind "$dst" "$src")" in
    ok)     PLAN+=("$(printf '  ok        %s' "$(tilde "$dst")")") ;;
    new)    PLAN+=("$(printf '  new       %s' "$(tilde "$dst")")"); CHANGES=$((CHANGES+1)) ;;
    relink) PLAN+=("$(printf '  relink    %s  (was -> %s)' "$(tilde "$dst")" "$(readlink "$dst")")"); CHANGES=$((CHANGES+1)) ;;
    backup) PLAN+=("$(printf '  backup    %s  -> %s.bak' "$(tilde "$dst")" "$(basename "$dst")")"); CHANGES=$((CHANGES+1)) ;;
    backup-dir)
      entries="$(find "$dst" -mindepth 1 -maxdepth 1 2>/dev/null | wc -l | tr -d ' ')"
      PLAN+=("$(printf '  BACKUP    %s  real directory, %s entr%s, moved whole -> %s.bak' \
        "$(tilde "$dst")" "$entries" "$([ "$entries" = 1 ] && echo y || echo ies)" "$(basename "$dst")")")
      CHANGES=$((CHANGES+1)) ;;
  esac
done

# The Codex adapters install separately and can have work pending on their own.
CODEX_PENDING=0
python3 "$DOTFILES/codex/install-skills.py" --check >/dev/null 2>&1 || CODEX_PENDING=1

if [ "$CHANGES" -eq 0 ] && [ "$CODEX_PENDING" -eq 0 ]; then
  echo "link_dotfiles: all ${#DESTINATIONS[@]} path(s) already linked here, Codex adapters in place; nothing to do."
  exit 0
fi

echo "link_dotfiles: linking ${#DESTINATIONS[@]} path(s) from $REPO_DIR/dotfiles into \$HOME"
echo
printf '%s\n' "${PLAN[@]}"
[ "$CODEX_PENDING" -eq 1 ] && echo "  install   Codex skill adapters in ~/.agents/skills"
echo
echo "Each path above becomes a symlink into this repo. An existing symlink is replaced"
echo "outright; a real file or directory is moved aside to <name>.bak first, and a real"
echo "directory moves WHOLE -- its contents are not merged with the repo's."
echo "$CHANGES of ${#DESTINATIONS[@]} path(s) change."

if [ "$DRY_RUN" -eq 1 ]; then
  echo
  echo "link_dotfiles: dry run; nothing changed."
  exit 0
fi

if [ "$ASSUME_YES" -eq 0 ]; then
  if [ ! -t 0 ]; then
    echo >&2
    echo "link_dotfiles: stdin is not a terminal, so there is nobody to confirm this." >&2
    echo "Re-run with --yes to proceed unattended, or --dry-run to see the plan only." >&2
    exit 1
  fi
  echo
  printf 'Proceed? [y/N] '
  read -r reply || reply=""
  case "$reply" in
    [yY]|[yY][eE][sS]) echo ;;
    *) echo "link_dotfiles: aborted; nothing changed."; exit 1 ;;
  esac
fi

trap rollback ERR
for i in "${!DESTINATIONS[@]}"; do
  link "${SOURCES[$i]}" "${DESTINATIONS[$i]}"
done
python3 "$DOTFILES/codex/install-skills.py"
trap - ERR

# MCP servers are NOT symlinked: `claude mcp add` writes into ~/.claude.json,
# which also holds per-project trust state and can carry OAuth tokens/API
# keys. Run the setup script by hand on each machine instead:
#   ./dotfiles/claude/mcp/setup.sh
echo
echo "Note: MCP servers aren't auto-linked. Run ./dotfiles/claude/mcp/setup.sh separately (once per machine; no secrets needed — it writes \${VAR} placeholders)."
