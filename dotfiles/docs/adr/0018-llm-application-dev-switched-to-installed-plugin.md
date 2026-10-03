# `llm-application-dev` switched from vendored files to an installed plugin

**Decision.** The user pointed at the actual upstream repo
(`github.com/wshobson/agents`) and asked whether it could be installed
directly instead of kept as a vendored copy. Checked it first: it's a real,
live Claude Code plugin marketplace (`claude-code-workflows`, 92 plugins),
and `llm-application-dev` in it is exactly what was vendored here — same
three agents, same eight skills, same three commands, same author (Seth
Hobson) confirmed by the plugin's own `plugin.json`. Already at `v2.0.6`
upstream versus whatever was vendored under
[0012](0012-replaced-llm-integration-reviewer-with-builder-trio.md).

Surfaced the real tradeoff to the user rather than switching unprompted:
`0012` deliberately hand-edited the three agents' frontmatter to pin
`model`/`effort` per
[0002](0002-model-split-sonnet-orchestrator-tiered-subagents.md) (upstream
ships `model: inherit`, no `tools`/`effort` fields — exactly what `0002`
rejects). An installed plugin's files aren't locally editable, so switching
means giving that pinning up in exchange for automatic upstream tracking
and no vendoring/license bookkeeping (the same tradeoff already accepted
for `qdrant-skills` in
[0013](0013-added-qdrant-skills-skipped-langsmith.md)). User chose to
switch.

Removed: `agents/{ai-engineer,prompt-engineer,vector-database-engineer}.md`,
`commands/{ai-assistant,langchain-agent,prompt-optimize}.md`, the eight
`skills/{langchain-architecture,rag-implementation,llm-evaluation,
prompt-engineering-patterns,embedding-strategies,similarity-search-patterns,
vector-index-tuning,hybrid-search-implementation}/` directories, and
`skills/SETH_HOBSON_LLM_APPLICATION_DEV_LICENSE` (no longer vendoring, so
no license-bookkeeping file needed — the plugin catalog covers that, same
as every other real plugin here). Added `claude-code-workflows` →
`wshobson/agents` to `extraKnownMarketplaces` and
`llm-application-dev@claude-code-workflows` to `enabledPlugins`, mirroring
the `qdrant-skills@knowledge-work-plugins` pattern exactly. Updated
`README.md` and `docs/agents.md` to stop listing the three personas as
local agent files.

`0012`'s text is left as-is (it accurately describes what was decided and
done at the time) — this entry supersedes it rather than editing history,
per this file's own "reversal" convention.

**Correction, same investigation.** While verifying the repo, found that
`0012`'s own attribution — crediting `amoustakas/claude-code-plugins` —
was wrong; the plugin has always been `wshobson/agents`, the same author
already credited elsewhere in that entry. Also found the `c4-architecture`
skill ([0016](0016-c4-architecture-rewritten-around-structurizr-mcp.md))
carried the identical wrong attribution for its own inspiration — that
plugin turns out to be from the same `wshobson/agents` marketplace too
(matching agent names `c4-code`/`c4-component`/`c4-container`/
`c4-context`, same author). Fixed the note in `c4-architecture/SKILL.md`
directly (it's living documentation, not a decision record) rather than
opening a separate entry for a citation fix. `0012`'s text is left
uncorrected for the same reason as above — it's a historical record of an
error made at the time, not a decision being reversed.

**Rejected — installing the `c4-architecture` plugin too, now that its
real source is known.** This repo's `c4-architecture` skill isn't a
vendored copy any more (see `0016`) — it's a from-scratch rewrite around
Structurizr DSL, materially different in design (no per-directory Code
agent, DSL instead of five-plus Markdown files, opt-in Deployment/Dynamic
views). There's no vendored copy left to replace with an install; the two
have simply diverged past the point where "install the upstream instead"
is a meaningful choice.
