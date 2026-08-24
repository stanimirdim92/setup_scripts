# Architecture Decision Records

One file per decision — why this repo's `.claude` config is built the way
it is, including choices reversed after contact with reality. Format and
the difference from `docs/IDEAS.md` (unjudged) is defined in
`dotfiles/claude/references/documentation-practices.md`; don't duplicate
that explanation here, just the index.

| # | Decision | Status |
|---|---|---|
| [0001](0001-superpowers-overlap.md) | Superpowers overlap | Partially superseded by [0021](0021-reconcile-superpowers-overlap-with-current-sdlc.md) |
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
| [0012](0012-replaced-llm-integration-reviewer-with-builder-trio.md) | Replaced `llm-integration-reviewer` with the `llm-application-dev` plugin's builder trio | Superseded by [0018](0018-llm-application-dev-switched-to-installed-plugin.md) (vendored → installed plugin) |
| [0013](0013-added-qdrant-skills-skipped-langsmith.md) | Added `qdrant-skills@knowledge-work-plugins`, skipped langsmith | Accepted |
| [0014](0014-extracted-spec-plan-task-templates.md) | Extracted spec/plan/task templates to `references/templates/` | Superseded by [0015](0015-adopted-docs-adr-split-technical-decisions.md) (its `docs/adr/*.md` rejection) |
| [0015](0015-adopted-docs-adr-split-technical-decisions.md) | Adopted `docs/adr/*.md`, split `TECHNICAL_DECISIONS.md` | Accepted |
| [0016](0016-c4-architecture-rewritten-around-structurizr-mcp.md) | `c4-architecture` rewritten around Structurizr MCP, DSL instead of Markdown | Accepted |
| [0017](0017-c4-architecture-people-vs-external-systems-plus-opt-in-deployment-dynamic.md) | `c4-architecture`: fixed people/external-system terminology, added opt-in Deployment/Dynamic views | Accepted |
| [0018](0018-llm-application-dev-switched-to-installed-plugin.md) | `llm-application-dev` switched from vendored files to an installed plugin | Accepted |
| [0019](0019-adr-recording-compared-against-adr-github-vercel-ecc.md) | `adr-recording` compared against adr.github.io, vercel/ai, and ECC's ADR skills | Accepted |
| [0020](0020-build-test-review-pipeline-split.md) | `/build` → `/test` → `/review`: split implementation from verification and review | Accepted |
| [0021](0021-reconcile-superpowers-overlap-with-current-sdlc.md) | Reconcile Superpowers overlap with the current SDLC | Accepted |
| [0022](0022-agent-execution-context-evidence-and-measurement.md) | Agent execution: bounded context, evidence, and measurement | Accepted |
| [0023](0023-agents-doc-moved-to-synced-dotfiles-claude-docs.md) | `docs/agents.md` moved to `dotfiles/claude/docs/`, now synced | Accepted |
| [0024](0024-vendored-test-engineer-persona-for-test-verify-gate.md) | Vendored `test-engineer` persona, `/test` now dispatches it instead of investigating inline | Accepted |

Adding a new decision: create the next-numbered `NNNN-kebab-title.md`
(4-digit, zero-padded — MADR-style, matches the files already here) and
add one row here. If it reverses an earlier entry, leave that entry's
text as-is, mark its Status column "Superseded by NNNN", and state the
reversal in the new entry instead of editing the old one.
