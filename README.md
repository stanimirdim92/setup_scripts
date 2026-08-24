# AI tool dotfiles (Claude Code / Codex)

`dotfiles/` holds the syncable config from `~/.claude` and `~/.codex`. On a
machine, `tools/link_dotfiles.sh` symlinks these into place (backing up any
existing real file as `<name>.bak` the first time). Re-run it any time,
including right after `git clone` on a new machine:

    ./tools/link_dotfiles.sh

This repo's own build decisions (why an agent is configured one way and
not another, including choices reversed after contact with reality) are
recorded in `docs/adr/*.md` — read that before re-proposing
something already tried and rejected here.

Synced:
- `dotfiles/claude/CLAUDE.md` -> `~/.claude/CLAUDE.md` — global working rules (Karpathy's rules + kept extensions + the document-set convention), loaded on every session unconditionally, unlike skills below
- `dotfiles/claude/AGENTS.md` -> `~/.claude/AGENTS.md` — pointer to `CLAUDE.md`
- `dotfiles/claude/settings.json` -> `~/.claude/settings.json` — model, plugins (including `episodic-memory@superpowers-marketplace` — cross-project conversation search, see `dotfiles/claude/CLAUDE.md`'s memory section), `hooks` (PreToolUse safety checks), and `autoMemoryEnabled` (Claude Code's own per-project memory; its output lives under the already-excluded `~/.claude/projects/` below)
- `dotfiles/claude/remote-settings.json` -> `~/.claude/remote-settings.json`
- `dotfiles/claude/statusline.sh` -> `~/.claude/statusline.sh` — status line script wired via `settings.json`'s `statusLine.command`: model name, cwd, git branch, context-usage bar, session cost, elapsed time
- `dotfiles/claude/subagent-statusline.sh` -> `~/.claude/subagent-statusline.sh` — per-subagent row override wired via `settings.json`'s `subagentStatusLine.command`: status icon, name, model, token count/percentage, elapsed time
- `dotfiles/claude/agents/` -> `~/.claude/agents/` (whole directory) — custom subagents: `distributed-systems-reviewer` (timeouts/idempotent retries/backoff/circuit breakers/backpressure/checkpointing, for anything crossing a process/network/queue boundary), `unblock-triage` (sorts a batch of blocked PRs/tickets into needs-you-now vs. delegate, ranked by blocking radius), `executor` (dispatched by `/build` to implement one task end-to-end; never invokes another agent) — first-party — plus vendored `code-reviewer` (five-axis review), `security-auditor` (vulnerability detection, threat modeling, and hardening across input handling, auth, data protection, infra, third-party integrations, and LLM/OWASP-LLM-Top-10 surfaces — see `docs/adr/0025-security-auditor-provenance-corrected.md` for its actual addyosmani origin, which superseded `infra-reviewer`/`security-reviewer`), and `test-engineer` (dispatched by `/test` as the bounded verifier for the VERIFY gate; also answers direct test-design/coverage-analysis requests) — all three MIT-licensed, see `dotfiles/claude/skills/ADDYOSMANI_AGENT_SKILLS_LICENSE`. The former `ai-engineer`/`prompt-engineer`/`vector-database-engineer` personas (production LLM app/RAG/agent architecture, prompt optimization, vector search/embedding) now come from the installed `llm-application-dev@claude-code-workflows` plugin instead of vendored files — see `docs/adr/0018-llm-application-dev-switched-to-installed-plugin.md`
- `dotfiles/claude/skills/` -> `~/.claude/skills/` (whole directory) — `dotfiles-sync` (meta, first-party), `adr-recording` (first-party, portable version of this repo's own `docs/adr/*.md` practice — records a technical decision as one Decision/Rejected file per project, with an index and a no-silent-overwrite rule for reversals), `jira-ticket` (first-party, intake ONLY for a Jira ticket — fetch, read, restate, flag ambiguity, then hand off to `/spec`; moved here from a project-local `.ai/skills/` copy once it became clear the intake step and the project-specific SDLC chain shouldn't live in the same skill), `c4-architecture` (first-party, general-purpose — not part of the SDLC chain — inspects a codebase directly and writes a Structurizr DSL workspace, validated/inspected via the `structurizr` MCP server and exported to Mermaid/PlantUML for Context/Container/Component views; rewritten from the community `c4-architecture` Claude Code plugin rather than vendored), nine vendored engineering skills (`spec-driven-development`, `planning-and-task-breakdown`, `code-review-and-quality`, `git-workflow-and-versioning`, `incremental-implementation`, `deprecation-and-migration`, `security-and-hardening`, `api-and-interface-design`, `context-engineering`) under `ADDYOSMANI_AGENT_SKILLS_LICENSE` (MIT), `caveman` (terse response mode) under `CAVEMAN_LICENSE` (MIT — only the plain `skills/` directory of that repo; its compression-engine binaries are BSL-1.1 and not used here). The eight LLM-application-dev skills (`langchain-architecture`, `rag-implementation`, `llm-evaluation`, `prompt-engineering-patterns`, `embedding-strategies`, `similarity-search-patterns`, `vector-index-tuning`, `hybrid-search-implementation`) that used to be vendored here now come from the installed `llm-application-dev@claude-code-workflows` plugin instead — see `docs/adr/0018-llm-application-dev-switched-to-installed-plugin.md`. Matt Pocock's `research`/`handoff` skills were removed — see `docs/adr/0008-matt-pocock-skills-removed.md`. Debugging routes to the `superpowers` marketplace plugin instead of a vendored copy — see `docs/adr/0001-superpowers-overlap.md`. TDD routing is now explicit: the local `test-driven-development` methodology owns implementation TDD (inlined by `executor`, which has no Skill tool), while `/test` is the independent VERIFY gate; `superpowers:systematic-debugging` remains the debugging route — see `docs/adr/0021-reconcile-superpowers-overlap-with-current-sdlc.md`
- `dotfiles/claude/commands/` -> `~/.claude/commands/` (whole directory) — `/spec`, `/plan`: short aliases into the SDLC skills above; the back half of the chain is a three-gate split (`docs/adr/0020-build-test-review-pipeline-split.md`) — `/build` groups tasks into workstreams and dispatches one `executor` per workstream (resumed across that workstream's later tasks instead of a fresh spawn per task; executors always run one at a time, never concurrently even across independent workstreams, since two of them writing into the same checkout races regardless of file-scope overlap), implements only, no review/verify/verdict; `/test` is the independent VERIFY gate after `/build`, reports VERIFY PASS/FAIL; `/review` is the independent REVIEW gate after `/test` — fans out `code-reviewer`/`security-auditor`/`distributed-systems-reviewer` (only `code-reviewer` is unconditional; the rest trigger per `references/reviewer-triggers.md`) capped at 2 concurrent reviewers with no exception, and issues the GO/NO-GO verdict. The former `/ai-assistant`, `/langchain-agent`, `/prompt-optimize` vendored commands now come from the installed `llm-application-dev@claude-code-workflows` plugin instead
- `dotfiles/claude/references/` -> `~/.claude/references/` (whole directory) — shared checklists (`definition-of-done.md`, `security-checklist.md`) that the SDLC skills point at with a `../../references/` path, `documentation-practices.md` (the Ideas/Decisions/Memory practice moved out of `CLAUDE.md` so it isn't force-loaded into every subagent), `reviewer-triggers.md` (the single trigger-condition matrix `/review` reads when dispatching specialist reviewers), `agent-run-metrics.md` (lightweight actual-only signals for tuning executor/workstream/model policy), and `templates/` (`spec.md`, `plan.md`, `task.md` — the canonical document shapes `spec-driven-development`/`planning-and-task-breakdown` point at instead of embedding their own copy, so the two skills can't drift apart on format either); must stay a sibling of `skills/`, not nested inside it
- `dotfiles/claude/hooks/` -> `~/.claude/hooks/` (whole directory) — scripts referenced by `settings.json`'s `hooks` key: destructive-bash blocking (`rm -rf`, block-device writes, recursive chmod/chown, and the git equivalents — `reset --hard`, `clean -f`, `branch -D`, `checkout .`/`restore .`), a force-push-to-main/master warning plus a plain-push confirm in local IDE sessions (`$CLAUDE_CODE_REMOTE` unset), and an always-ask on Pint/PHPStan/Deptrac (never auto-run)
- `dotfiles/claude/docs/` -> `~/.claude/docs/` (whole directory) — `agents.md`: the persona/orchestration reference (roster, `/build`→`/test`→`/review` shapes, context-discipline, adding-a-persona checklist), made available at runtime instead of living only in this repo's own `docs/` (which holds repo-specific meta-documentation — ADRs, IDEAS.md, MEMORY.md — that has no reason to sync to every machine's `~/.claude/`)
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
