# `c4-architecture` rewritten around Structurizr MCP, DSL instead of Markdown

**Decision.** A ChatGPT-drafted proposal suggested replacing the skill's
hand-rolled four-agent Markdown pipeline with the official Structurizr MCP
server (`mcp.structurizr.com` — confirmed real via its own docs, not taken
on faith). Verified what the MCP actually does before acting on the
proposal: it validates, parses, and inspects Structurizr DSL and exports
views to Mermaid/PlantUML — it does not read or discover architecture from
a codebase. That half of the job (finding containers, components,
relationships in the actual code) still had to stay Claude's, so this
wasn't a drop-in tool swap; it changed the skill's whole output contract.

Rewrote the skill: `Discover` (direct `Read`/`Grep`/`Glob` over the repo,
no subagent fan-out) → draft `C4-Documentation/workspace.dsl` → Structurizr
MCP validate/inspect loop (capped at 3 fix passes, surfaces remaining
violations rather than guessing past them) → export Mermaid/PlantUML views.
One DSL workspace is now the source of truth instead of five-plus
hand-written Markdown files per level (`c4-code-*.md`, `c4-component-*.md`,
`c4-container.md`, `c4-context.md`) — Structurizr enforces C4's structural
rules (component nests in container, container nests in system) on the DSL
directly, instead of Claude policing them by convention across separate
documents. Code-level detail was dropped from scope entirely — Structurizr's
model doesn't cover it either, and a standing Code-level diagram drifts
every commit; read the source directly for those questions instead.

Deleted the four `c4-code`/`c4-component`/`c4-container`/`c4-context`
subagents — nothing calls them once the skill inspects directly, and this
repo's convention (`code-reviewer.md`'s Composition section) is that an
agent invoked only by one skill has no reason to exist once that skill stops
calling it. Registered `structurizr` (HTTP, hosted, user scope) in
`dotfiles/claude/mcp/setup.sh` alongside the other MCP servers — no auth
needed for validate/inspect/export; the server's workspace CRUD tools
require self-hosting instead, not used here.
