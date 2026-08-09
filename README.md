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
- `dotfiles/claude/CLAUDE.md` -> `~/.claude/CLAUDE.md` — global working rules (Karpathy's rules + kept extensions), loaded on every session unconditionally, unlike skills below
- `dotfiles/claude/settings.json` -> `~/.claude/settings.json` — model, plugins, and `hooks` (PreToolUse safety checks)
- `dotfiles/claude/remote-settings.json` -> `~/.claude/remote-settings.json`
- `dotfiles/claude/agents/` -> `~/.claude/agents/` (whole directory) — custom subagents (`infra-reviewer`, `security-reviewer`)
- `dotfiles/claude/skills/` -> `~/.claude/skills/` (whole directory) — on-demand, per-technology skills: `php`, `mysql`, `nginx`, `redis`, `postgresql`, `python`, `fastapi`, plus `dotfiles-sync` (meta, for this repo's own tooling)
- `dotfiles/claude/hooks/` -> `~/.claude/hooks/` (whole directory) — scripts referenced by `settings.json`'s `hooks` key
- `dotfiles/codex/config.toml` -> `~/.codex/config.toml`
- `dotfiles/codex/rules/default.rules` -> `~/.codex/rules/default.rules`

Since these are symlinks, editing the file in the repo or letting the app
edit it live (e.g. `/model`, `codex mcp add`) are the same thing — just
`git status` in this repo afterwards to see what changed, and commit when
you want to snapshot it. Adding a new agent/skill/hook file needs no script
change (whole directories are linked) — see
`dotfiles/claude/skills/dotfiles-sync/SKILL.md` for the full checklist.

MCP servers: **not symlinked** — see `dotfiles/claude/mcp/setup.sh`. Run it
by hand once per machine (`GITHUB_TOKEN=... ./dotfiles/claude/mcp/setup.sh`);
`claude mcp add` writes into `~/.claude.json`, which mixes server config with
per-project trust state and can carry OAuth tokens/API keys, so it belongs
in the "not synced" list below, not linked like the rest.

Deliberately **not** synced:
- `~/.claude.json` — MCP server config (user/local scope) plus per-project trust
  state and possible OAuth tokens/API keys. Use `dotfiles/claude/mcp/setup.sh`
  to reproduce the MCP servers on a new machine instead.
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