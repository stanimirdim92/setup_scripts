# Install for terminal

https://github.com/ajeetdsouza/zoxide
https://starship.rs/
https://ghostty.org/docs
    sudo apt install fzf ripgrep

# AI tool dotfiles (Claude Code / Codex)

`dotfiles/` holds the syncable config from `~/.claude` and `~/.codex`. On a
machine, `tools/link_dotfiles.sh` symlinks these into place (backing up any
existing real file as `<name>.bak` the first time). Re-run it any time,
including right after `git clone` on a new machine:

    ./tools/link_dotfiles.sh

Synced:
- `dotfiles/claude/CLAUDE.md` -> `~/.claude/CLAUDE.md` — global working rules, applies to every project
- `dotfiles/claude/settings.json` -> `~/.claude/settings.json`
- `dotfiles/claude/remote-settings.json` -> `~/.claude/remote-settings.json`
- `dotfiles/codex/config.toml` -> `~/.codex/config.toml`
- `dotfiles/codex/rules/default.rules` -> `~/.codex/rules/default.rules`

Since these are symlinks, editing the file in the repo or letting the app
edit it live (e.g. `/model`, `codex mcp add`) are the same thing — just
`git status` in this repo afterwards to see what changed, and commit when
you want to snapshot it.

Deliberately **not** synced:
- `~/.claude/.credentials.json` — OAuth tokens, machine-specific secrets.
- `~/.claude/plugins/installed_plugins.json`, `known_marketplaces.json` — regenerated
  automatically from `settings.json`'s `enabledPlugins` / `extraKnownMarketplaces`.
- `~/.claude/{projects,sessions,cache,downloads,shell-snapshots,file-history,
  session-env,backups,ide,daemon,jobs,paste-cache}`, `~/.claude/history.jsonl`,
  `~/.claude/policy-limits.json`, `~/.claude/.last-*` — runtime state/logs, not config.
- `~/.codex/{sessions,shell_snapshots,tmp,.tmp,mcp-oauth-locks}`, the `*.sqlite*`
  state/memory/log/goals databases, `installation_id` — runtime state, machine-specific.
- `~/.codex/skills/.system/*` — vendor-shipped system skills bundled with Codex itself,
  not user config.
- `~/.ai/mcp/mcp.json` — currently empty (0 bytes), nothing to sync yet.