# Added `qdrant-skills@knowledge-work-plugins`, skipped langsmith

**Decision.** Enabled `qdrant-skills@knowledge-work-plugins` in
`settings.json` (marketplace backed by `anthropics/knowledge-work-plugins`
on GitHub) — a real, catalog-listed plugin bundling Qdrant-specific skills
(scaling, indexing/search-quality tuning, monitoring, deployment, SDK
usage, version/model migration). Added as a plugin, not vendored files:
matches how every other real plugin here is added (`phpstorm-plugin`,
`superpowers`, `context7`, etc.) and sidesteps any vendoring/license
bookkeeping since the plugin catalog handles that.

**Rejected — a `langsmith` plugin/skill.** No `langsmith` plugin exists in
the catalog, and nothing to vendor from either (unlike `llm-application-dev`,
which was a real GitHub repo). Asked the user rather than fabricating one;
skipped outright instead of writing a first-party skill from scratch, since
nothing prompted that scope. `langchain` was left alone too — already
covered by the vendored `langchain-architecture` skill from the
`llm-application-dev` import, so no separate action needed.
