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
link "$DOTFILES/claude/AGENTS.md"              "$HOME/.claude/AGENTS.md"
link "$DOTFILES/claude/settings.json"          "$HOME/.claude/settings.json"
link "$DOTFILES/claude/statusline.sh"          "$HOME/.claude/statusline.sh"
link "$DOTFILES/claude/subagent-statusline.sh" "$HOME/.claude/subagent-statusline.sh"
link "$DOTFILES/claude/remote-settings.json"   "$HOME/.claude/remote-settings.json"

# Linked as whole directories (not per-file) so new agents/skills/hooks don't
# need a script change — see dotfiles/claude/skills/dotfiles-sync/SKILL.md.
link "$DOTFILES/claude/agents"                 "$HOME/.claude/agents"
link "$DOTFILES/claude/skills"                 "$HOME/.claude/skills"
link "$DOTFILES/claude/hooks"                  "$HOME/.claude/hooks"
link "$DOTFILES/claude/commands"               "$HOME/.claude/commands"

# Sibling of skills/, not nested inside it: some vendored skills reference
# shared checklists via a relative ../../references/ path (matching their
# upstream repo's layout), which only resolves if this sits next to skills/
# at the same ~/.claude/ level.
link "$DOTFILES/claude/references"             "$HOME/.claude/references"
link "$DOTFILES/claude/docs"                   "$HOME/.claude/docs"

link "$DOTFILES/codex/config.toml"             "$HOME/.codex/config.toml"
link "$DOTFILES/codex/rules/default.rules"     "$HOME/.codex/rules/default.rules"

# Codex reads its global instructions from $HOME/.codex/AGENTS.md (and
# AGENTS.override.md ahead of it, if one exists), NOT from ~/.claude — so
# without this line Codex ran with no global rules at all while Claude Code
# had the full set. Same file, one source of truth: CLAUDE.md is the rules
# document, and its "Agent orchestration" section is marked Claude
# Code-specific for the Codex reader.
#
# Codex skills are deliberately NOT linked. $HOME/.codex/skills already holds
# Codex's own vendor-shipped .system skills, which a whole-directory symlink
# would shadow, and the pipeline skills are written around /build, /test,
# /review and /ship, which Codex has no equivalent of.
link "$DOTFILES/claude/CLAUDE.md"              "$HOME/.codex/AGENTS.md"

# MCP servers are NOT symlinked: `claude mcp add` writes into ~/.claude.json,
# which also holds per-project trust state and can carry OAuth tokens/API
# keys. Run the setup script by hand on each machine instead:
#   ./dotfiles/claude/mcp/setup.sh
echo
echo "Note: MCP servers aren't auto-linked. Run ./dotfiles/claude/mcp/setup.sh separately (once per machine; no secrets needed — it writes \${VAR} placeholders)."
