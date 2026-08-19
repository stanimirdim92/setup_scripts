# Architecture Decision Records

One file per decision — why this repo's `.claude` config is built the way
it is, including choices reversed after contact with reality. Format and
the difference from `docs/IDEAS.md` (unjudged) is defined in
`dotfiles/claude/references/documentation-practices.md`; don't duplicate
that explanation here, just the index.

| # | Decision | Status |
|---|---|---|
| [0001](0001-superpowers-overlap.md) | Superpowers overlap | Accepted |
| [0002](0002-model-split-sonnet-orchestrator-tiered-subagents.md) | Model split: Sonnet orchestrator, tiered subagents | Accepted |
| [0003](0003-executor-concurrency-sequential-only.md) | Executor concurrency: sequential only, no parallel writers | Accepted |
| [0004](0004-reviewer-batch-cap-no-high-risk-exception.md) | Reviewer batch cap: no high-risk exception | Accepted |
| [0005](0005-reviewer-trigger-matrix-single-source.md) | Reviewer trigger matrix: one file, not two copies | Accepted |
| [0006](0006-review-thin-wrapper-over-code-reviewer.md) | `/review`: thin wrapper over `code-reviewer`, not a second rubric | Accepted |
| [0007](0007-agents-doc-trimmed-to-match-built.md) | docs/agents.md: trimmed to match what's actually built | Accepted |
| [0008](0008-matt-pocock-skills-removed.md) | Matt Pocock's skills: removed, committing to the addyosmani SDLC shape | Accepted |
| [0009](0009-infra-security-reviewers-merged-into-security-auditor.md) | Infra + security reviewers merged into `security-auditor` | Accepted |
| [0010](0010-new-vendored-skills-deprecation-migration-security-hardening.md) | New vendored skills: `deprecation-and-migration`, `security-and-hardening` | Accepted |
| [0011](0011-plugin-set-dropped-feature-dev-added-official-plugins.md) | Plugin set: dropped `feature-dev`, added four `@claude-plugins-official` | Accepted |
| [0012](0012-replaced-llm-integration-reviewer-with-builder-trio.md) | Replaced `llm-integration-reviewer` with the `llm-application-dev` plugin's builder trio | Accepted |
| [0013](0013-added-qdrant-skills-skipped-langsmith.md) | Added `qdrant-skills@knowledge-work-plugins`, skipped langsmith | Accepted |
| [0014](0014-extracted-spec-plan-task-templates.md) | Extracted spec/plan/task templates to `references/templates/` | Superseded by [0015](0015-adopted-docs-adr-split-technical-decisions.md) (its `docs/adr/*.md` rejection) |
| [0015](0015-adopted-docs-adr-split-technical-decisions.md) | Adopted `docs/adr/*.md`, split `TECHNICAL_DECISIONS.md` | Accepted |
| [0016](0016-c4-architecture-rewritten-around-structurizr-mcp.md) | `c4-architecture` rewritten around Structurizr MCP, DSL instead of Markdown | Accepted |

Adding a new decision: create the next-numbered `NNNN-kebab-title.md`
(4-digit, zero-padded — MADR-style, matches the files already here) and
add one row here. If it reverses an earlier entry, leave that entry's
text as-is, mark its Status column "Superseded by NNNN", and state the
reversal in the new entry instead of editing the old one.
