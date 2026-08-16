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

This repo's own build decisions (why an agent is configured one way and
not another, including choices reversed after contact with reality) are
recorded in `docs/TECHNICAL_DECISIONS.md` — read that before re-proposing
something already tried and rejected here.

Synced:
- `dotfiles/claude/CLAUDE.md` -> `~/.claude/CLAUDE.md` — global working rules (Karpathy's rules + kept extensions + the document-set convention), loaded on every session unconditionally, unlike skills below
- `dotfiles/claude/AGENTS.md` -> `~/.claude/AGENTS.md` — one-line pointer to `CLAUDE.md`, for any tool that checks the generic `AGENTS.md` convention instead of Claude Code's own file
- `dotfiles/claude/settings.json` -> `~/.claude/settings.json` — model, plugins (including `episodic-memory@superpowers-marketplace` — cross-project conversation search, see `dotfiles/claude/CLAUDE.md`'s memory section), `hooks` (PreToolUse safety checks), and `autoMemoryEnabled` (Claude Code's own per-project memory; its output lives under the already-excluded `~/.claude/projects/` below)
- `dotfiles/claude/remote-settings.json` -> `~/.claude/remote-settings.json`
- `dotfiles/claude/agents/` -> `~/.claude/agents/` (whole directory) — custom subagents: `security-auditor` (merged from the former `infra-reviewer`/`security-reviewer`: vulnerability detection, threat modeling, and hardening across input handling, auth, data protection, infra, third-party integrations, and LLM/OWASP-LLM-Top-10 surfaces), `distributed-systems-reviewer` (timeouts/idempotent retries/backoff/circuit breakers/backpressure/checkpointing, for anything crossing a process/network/queue boundary), `unblock-triage` (sorts a batch of blocked PRs/tickets into needs-you-now vs. delegate, ranked by blocking radius), `executor` (dispatched by `/build` to implement one task end-to-end; never invokes another agent), `c4-code`/`c4-component`/`c4-container`/`c4-context` (bottom-up C4 architecture documentation, dispatched only by the `c4-architecture` skill — never each other) — all first-party — plus vendored `code-reviewer` (five-axis review, MIT-licensed — see `dotfiles/claude/skills/ADDYOSMANI_AGENT_SKILLS_LICENSE`) and `ai-engineer`/`prompt-engineer`/`vector-database-engineer` (production LLM app/RAG/agent architecture, prompt optimization, and vector search/embedding personas — direct-invocation builders, not part of the `/build`/`/review` reviewer fan-out; replaced the former `llm-integration-reviewer`, MIT-licensed — see `dotfiles/claude/skills/SETH_HOBSON_LLM_APPLICATION_DEV_LICENSE`)
- `dotfiles/claude/skills/` -> `~/.claude/skills/` (whole directory) — `dotfiles-sync` (meta, first-party), `ticket-breakdown-and-delegation` (first-party, extends `planning-and-task-breakdown` with per-assignee sizing), `c4-architecture` (first-party, general-purpose — not part of the SDLC chain — orchestrates the four `c4-*` agents above to generate Context/Container/Component/Code documentation for a codebase; rewritten from the community `c4-architecture` Claude Code plugin rather than vendored), seven vendored SDLC-workflow skills (`spec-driven-development`, `planning-and-task-breakdown`, `code-review-and-quality`, `git-workflow-and-versioning`, `incremental-implementation`, `deprecation-and-migration`, `security-and-hardening`) under `ADDYOSMANI_AGENT_SKILLS_LICENSE` (MIT), `caveman` (terse response mode) under `CAVEMAN_LICENSE` (MIT — only the plain `skills/` directory of that repo; its compression-engine binaries are BSL-1.1 and not used here), and eight vendored LLM-application-dev skills (`langchain-architecture`, `rag-implementation`, `llm-evaluation`, `prompt-engineering-patterns`, `embedding-strategies`, `similarity-search-patterns`, `vector-index-tuning`, `hybrid-search-implementation`) under `SETH_HOBSON_LLM_APPLICATION_DEV_LICENSE` (MIT), paired with the `ai-engineer`/`prompt-engineer`/`vector-database-engineer` agents above. Matt Pocock's `research`/`handoff` skills were removed — see `docs/TECHNICAL_DECISIONS.md`. TDD and debugging route to the `superpowers` marketplace plugin instead of a vendored copy — see `docs/TECHNICAL_DECISIONS.md`'s "Superpowers overlap" section
- `dotfiles/claude/commands/` -> `~/.claude/commands/` (whole directory) — `/spec`, `/plan`, `/test`: short aliases into the SDLC skills above; `/build` groups tasks into workstreams and dispatches one `executor` per workstream (resumed across that workstream's later tasks instead of a fresh spawn per task), executors always run one at a time — never concurrently, even across independent workstreams, since two of them writing into the same checkout races regardless of file-scope overlap — then fans out `code-reviewer`/`security-auditor`/`distributed-systems-reviewer` (only `code-reviewer` is unconditional; the rest trigger per `references/reviewer-triggers.md`) capped at 2 concurrent reviewers with no exception, and merges a go/no-go verdict; `/review` is a thin wrapper over the same `code-reviewer` + specialist-fan-out pattern for a one-off review outside `/build`; `/ai-assistant`, `/langchain-agent`, `/prompt-optimize` are vendored alongside the LLM-application-dev agents/skills above — standalone builder commands, not part of the `/spec`→`/plan`→`/build`→`/test`→`/review` SDLC chain
- `dotfiles/claude/references/` -> `~/.claude/references/` (whole directory) — shared checklists (`definition-of-done.md`, `security-checklist.md`) that the SDLC skills point at with a `../../references/` path, `documentation-practices.md` (the Ideas/Decisions/Memory practice moved out of `CLAUDE.md` so it isn't force-loaded into every subagent), and `reviewer-triggers.md` (the single trigger-condition matrix `/build` and `/review` both read, so they can't drift apart on when a specialist reviewer runs); must stay a sibling of `skills/`, not nested inside it
- `dotfiles/claude/hooks/` -> `~/.claude/hooks/` (whole directory) — scripts referenced by `settings.json`'s `hooks` key: destructive-bash blocking (`rm -rf`, block-device writes, recursive chmod/chown, and the git equivalents — `reset --hard`, `clean -f`, `branch -D`, `checkout .`/`restore .`), a force-push-to-main/master warning plus a plain-push confirm in local IDE sessions (`$CLAUDE_CODE_REMOTE` unset), and an always-ask on Pint/PHPStan/Deptrac (never auto-run)
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
- `dotfiles/claude/skills/synced/`, `dotfiles/claude/skills/session-start-hook/`
  (gitignored) — Claude Code's own bundled/example skills (docx, pdf, pptx, xlsx,
  skill-creator, morning, session-start-hook), auto-materialized inside the
  symlinked `skills/` directory whenever one gets listed as available in a
  session. Same "regenerated automatically" category as the plugin files above,
  just written into a path this repo otherwise curates deliberately.
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