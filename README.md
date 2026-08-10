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
- `dotfiles/claude/CLAUDE.md` -> `~/.claude/CLAUDE.md` — global working rules (Karpathy's rules + kept extensions + the document-set convention), loaded on every session unconditionally, unlike skills below
- `dotfiles/claude/settings.json` -> `~/.claude/settings.json` — model, plugins (including `episodic-memory@superpowers-marketplace` — cross-project conversation search, see `dotfiles/claude/CLAUDE.md`'s memory section), `hooks` (PreToolUse safety checks), and `autoMemoryEnabled` (Claude Code's own per-project memory; its output lives under the already-excluded `~/.claude/projects/` below)
- `dotfiles/claude/remote-settings.json` -> `~/.claude/remote-settings.json`
- `dotfiles/claude/agents/` -> `~/.claude/agents/` (whole directory) — custom subagents: `infra-reviewer`, `security-reviewer` (first-party), plus vendored `code-reviewer` (five-axis review, MIT-licensed — see `dotfiles/claude/skills/ADDYOSMANI_AGENT_SKILLS_LICENSE`)
- `dotfiles/claude/skills/` -> `~/.claude/skills/` (whole directory) — `fastapi` (first-party), `dotfiles-sync` (meta), and six vendored SDLC-workflow skills (`spec-driven-development`, `planning-and-task-breakdown`, `test-driven-development`, `code-review-and-quality`, `debugging-and-error-recovery`, `git-workflow-and-versioning`) under `ADDYOSMANI_AGENT_SKILLS_LICENSE` (MIT)
- `dotfiles/claude/commands/` -> `~/.claude/commands/` (whole directory) — `/spec`, `/plan`, `/test`, `/review`: short aliases into the SDLC skills above
- `dotfiles/claude/references/` -> `~/.claude/references/` (whole directory) — shared checklists (`definition-of-done.md`, `security-checklist.md`, `performance-checklist.md`) that the SDLC skills point at with a `../../references/` path; must stay a sibling of `skills/`, not nested inside it
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
- `~/.config/superpowers/` — the `episodic-memory` plugin's archived conversation
  transcripts and local SQLite/vector index. Rebuilds itself from `~/.claude/projects`
  and `~/.codex/sessions` on each machine; nothing here is worth carrying over, and
  transcripts can hold anything that was ever pasted into a session.