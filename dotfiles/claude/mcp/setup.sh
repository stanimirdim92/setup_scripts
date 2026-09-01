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
#   ./dotfiles/claude/mcp/setup.sh
#
# No secrets are passed to this script. Auth headers are written as literal
# `${VAR}` placeholders that Claude Code expands from the environment when it
# loads the server, so the stored config holds a variable name, not a token
# (see https://code.claude.com/docs/en/mcp). Export the variables the servers
# below name in the shell that starts Claude Code — e.g. from ~/.bashrc or a
# secret manager — not here.
#
# Re-running is safe: each server is skipped if it already exists. `claude mcp
# add` fails with a non-zero exit on a duplicate name, and with `set -e` that
# would abort the script before the later servers were ever added, so the
# check has to happen before the add rather than being left to the failure.
set -euo pipefail

# Adds one server unless a server of that name already resolves. `claude mcp
# get` also resolves project- and local-scope servers, so an existing
# same-named server at another scope is reported and skipped rather than
# silently shadowed by a new user-scope entry.
add_server() {
  local name="$1"
  shift

  if claude mcp get "$name" >/dev/null 2>&1; then
    echo "    skipped: '$name' already exists (re-add with: claude mcp remove $name)"
    return 0
  fi

  claude mcp add "$name" "$@"
}

# Warns (does not fail) about a variable the stored config references but the
# current shell doesn't set — the config is still written correctly; the server
# just won't authenticate until the variable is exported where Claude Code runs.
warn_unset() {
  if [ -z "${!1:-}" ]; then
    echo "    note: \$$1 is not set in this shell — export it where Claude Code starts, or the server won't authenticate."
  fi
}

echo "==> GitHub MCP server (user scope, all projects)"
warn_unset GITHUB_TOKEN
add_server github --transport http https://api.githubcopilot.com/mcp/ \
  --header 'Authorization: Bearer ${GITHUB_TOKEN}' \
  --scope user

echo "==> Filesystem MCP server (user scope, all projects)"
# Version pinned rather than floating: `npx -y <pkg>` resolves the newest
# release at every launch, which hands an unreviewed package version
# filesystem access on the roots below — see references/supply-chain.md.
# Bump this deliberately.
add_server filesystem --transport stdio --scope user \
  -- npx -y @modelcontextprotocol/server-filesystem@2026.8.31 "$HOME"

echo "==> Atlassian (Jira/Confluence) MCP server (user scope, all projects)"
# Official Atlassian remote MCP server (Cloud-only) — also covers
# Confluence, Jira Service Management, Bitbucket, and Compass under the
# same endpoint. OAuth 2.1, so no token env var here: after this runs,
# start a Claude Code session and run `/mcp` to authenticate interactively.
add_server jira --transport http https://mcp.atlassian.com/v1/mcp/authv2 \
  --scope user

echo "==> Context7 docs MCP server (user scope, all projects)"
# Works without a key at low rate limits; set CONTEXT7_API_KEY for a higher
# limit (free key at https://context7.com/dashboard). The branch decides only
# whether an auth header exists at all — a header carrying an unexpanded
# `${CONTEXT7_API_KEY}` is a malformed credential, not the same thing as
# sending none. The header value itself stays a placeholder either way.
if [ -n "${CONTEXT7_API_KEY:-}" ]; then
  add_server context7 --transport http https://mcp.context7.com/mcp \
    --header 'Authorization: Bearer ${CONTEXT7_API_KEY}' \
    --scope user
else
  echo "    note: \$CONTEXT7_API_KEY unset — adding unauthenticated (low rate limit)."
  add_server context7 --transport http https://mcp.context7.com/mcp --scope user
fi

echo "==> Structurizr MCP server (user scope, all projects)"
# Official hosted instance — DSL validate/parse/inspect plus Mermaid and
# PlantUML export tools. No auth needed for these; server workspace CRUD
# tools require self-hosting instead, not used here.
add_server structurizr --transport http https://mcp.structurizr.com/mcp --scope user

echo
echo "Done. Run 'claude mcp list' and confirm each server shows Connected."
echo "A server showing a missing-variable warning needs its token exported in the shell that starts Claude Code."
