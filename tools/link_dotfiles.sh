#!/usr/bin/env bash
# Symlinks AI-tool dotfiles from this repo into $HOME, backing up any existing
# real file the first time (as <name>.bak). Safe to re-run.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOTFILES="$REPO_DIR/dotfiles"

link() {
  local src="$1" dst="$2"

  if [ -L "$dst" ]; then
    if [ "$(readlink "$dst")" = "$src" ]; then
      echo "ok      $dst"
      return
    fi
    echo "relink  $dst (was -> $(readlink "$dst"))"
    rm "$dst"
  elif [ -e "$dst" ]; then
    echo "backup  $dst -> $dst.bak"
    mv "$dst" "$dst.bak"
  fi

  mkdir -p "$(dirname "$dst")"
  ln -s "$src" "$dst"
  echo "linked  $dst -> $src"
}

link "$DOTFILES/claude/CLAUDE.md"              "$HOME/.claude/CLAUDE.md"
link "$DOTFILES/claude/settings.json"          "$HOME/.claude/settings.json"
link "$DOTFILES/claude/remote-settings.json"   "$HOME/.claude/remote-settings.json"
link "$DOTFILES/codex/config.toml"             "$HOME/.codex/config.toml"
link "$DOTFILES/codex/rules/default.rules"     "$HOME/.codex/rules/default.rules"
