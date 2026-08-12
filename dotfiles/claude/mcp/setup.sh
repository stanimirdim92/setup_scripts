#!/usr/bin/env bash
# One-time-per-machine MCP server setup for Claude Code.
#
# This is deliberately a SCRIPT, not a synced JSON file: `claude mcp add`
# writes into ~/.claude.json (user scope), which also holds per-project
# trust state and can carry OAuth tokens/API keys. Syncing that whole file
# across machines would leak/overwrite machine-specific state, so it's
# excluded in README.md's "Deliberately not synced" list. Run this script
# by hand on each machine instead:
#
#   GITHUB_TOKEN=... CONTEXT7_API_KEY=... ./dotfiles/claude/mcp/setup.sh
#
# Re-running is safe: `claude mcp add` fails loudly (non-zero exit) if a
# server with the same name already exists at that scope, it does not
# silently duplicate or overwrite.
set -euo pipefail

echo "==> GitHub MCP server (user scope, all projects)"
: "${GITHUB_TOKEN:?Set GITHUB_TOKEN to a GitHub PAT with repo scope first}"
claude mcp add --transport http github https://api.githubcopilot.com/mcp/ \
  --header "Authorization: Bearer ${GITHUB_TOKEN}" \
  --scope user

echo "==> Filesystem MCP server (user scope, all projects)"
claude mcp add --transport stdio filesystem --scope user \
  -- npx -y @modelcontextprotocol/server-filesystem "$HOME"

echo "==> Atlassian (Jira/Confluence) MCP server (user scope, all projects)"
# Official Atlassian remote MCP server (Cloud-only) — also covers
# Confluence, Jira Service Management, Bitbucket, and Compass under the
# same endpoint. OAuth 2.1, so no token env var here: after this runs,
# start a Claude Code session and run `/mcp` to authenticate interactively.
claude mcp add --transport http jira https://mcp.atlassian.com/v1/mcp/authv2 \
  --scope user

echo "==> Context7 docs MCP server (user scope, all projects)"
# Works without a key at low rate limits; set CONTEXT7_API_KEY for a higher
# limit (free key at https://context7.com/dashboard).
if [ -n "${CONTEXT7_API_KEY:-}" ]; then
  claude mcp add --transport http context7 https://mcp.context7.com/mcp \
    --header "Authorization: Bearer ${CONTEXT7_API_KEY}" \
    --scope user
else
  claude mcp add --transport http context7 https://mcp.context7.com/mcp --scope user
fi

echo
echo "Done. Run 'claude mcp list' and confirm each server shows Connected."
