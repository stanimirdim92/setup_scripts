#!/usr/bin/env bash
# Symlinks AI-tool dotfiles from this repo into $HOME, backing up any existing
# real file the first time (as <name>.bak). Safe to re-run and failure-atomic for
# paths changed during the current invocation.
set -Eeuo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOTFILES="$REPO_DIR/dotfiles"

SOURCES=(
  "$DOTFILES/claude/CLAUDE.md"
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
  "$DOTFILES/claude/CLAUDE.md"
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
  preflight_link "${DESTINATIONS[$i]}"
done

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
