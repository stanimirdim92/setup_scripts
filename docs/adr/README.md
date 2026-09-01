# Architecture Decision Records

One file per decision — why this repo's `.claude` config is built the way
it is, including choices reversed after contact with reality. Format and
the difference from `docs/IDEAS.md` (unjudged) is defined in
`dotfiles/claude/references/documentation-practices.md`; don't duplicate
that explanation here, just the index.

| # | Decision | Status |
|---|---|---|
| [0001](0001-superpowers-overlap.md) | Superpowers overlap | Superseded by [0021](0021-reconcile-superpowers-overlap-with-current-sdlc.md) and [0039](0039-runtime-catalog-narrowed-by-observed-use.md) |
| [0002](0002-model-split-sonnet-orchestrator-tiered-subagents.md) | Model split: Sonnet orchestrator, tiered subagents | Accepted |
| [0003](0003-executor-concurrency-sequential-only.md) | Executor concurrency: sequential only, no parallel writers | Superseded by [0031](0031-parallel-executors-via-worktree-isolation.md) (2 concurrent with worktree isolation) |
| [0004](0004-reviewer-batch-cap-no-high-risk-exception.md) | Reviewer batch cap: no high-risk exception | Accepted |
| [0005](0005-reviewer-trigger-matrix-single-source.md) | Reviewer trigger matrix: one file, not two copies | Accepted |
| [0006](0006-review-thin-wrapper-over-code-reviewer.md) | `/review`: thin wrapper over `code-reviewer`, not a second rubric | Accepted |
| [0007](0007-agents-doc-trimmed-to-match-built.md) | docs/agents.md: trimmed to match what's actually built | Accepted |
| [0008](0008-matt-pocock-skills-removed.md) | Matt Pocock's skills: removed, committing to the addyosmani SDLC shape | Accepted |
| [0009](0009-infra-security-reviewers-merged-into-security-auditor.md) | Infra + security reviewers merged into `security-auditor` | Accepted |
| [0010](0010-new-vendored-skills-deprecation-migration-security-hardening.md) | New vendored skills: `deprecation-and-migration`, `security-and-hardening` | Accepted |
| [0011](0011-plugin-set-dropped-feature-dev-added-official-plugins.md) | Plugin set: dropped `feature-dev`, added four `@claude-plugins-official` | Partially superseded by [0039](0039-runtime-catalog-narrowed-by-observed-use.md) (`code-simplifier` no longer globally enabled) |
| [0012](0012-replaced-llm-integration-reviewer-with-builder-trio.md) | Replaced `llm-integration-reviewer` with the `llm-application-dev` plugin's builder trio | Superseded by [0018](0018-llm-application-dev-switched-to-installed-plugin.md) (vendored → installed plugin) |
| [0013](0013-added-qdrant-skills-skipped-langsmith.md) | Added `qdrant-skills@knowledge-work-plugins`, skipped langsmith | Accepted |
| [0014](0014-extracted-spec-plan-task-templates.md) | Extracted spec/plan/task templates to `references/templates/` | Superseded by [0015](0015-adopted-docs-adr-split-technical-decisions.md) (its `docs/adr/*.md` rejection) |
| [0015](0015-adopted-docs-adr-split-technical-decisions.md) | Adopted `docs/adr/*.md`, split `TECHNICAL_DECISIONS.md` | Accepted |
| [0016](0016-c4-architecture-rewritten-around-structurizr-mcp.md) | `c4-architecture` rewritten around Structurizr MCP, DSL instead of Markdown | Accepted |
| [0017](0017-c4-architecture-people-vs-external-systems-plus-opt-in-deployment-dynamic.md) | `c4-architecture`: fixed people/external-system terminology, added opt-in Deployment/Dynamic views | Accepted |
| [0018](0018-llm-application-dev-switched-to-installed-plugin.md) | `llm-application-dev` switched from vendored files to an installed plugin | Accepted |
| [0019](0019-adr-recording-compared-against-adr-github-vercel-ecc.md) | `adr-recording` compared against adr.github.io, vercel/ai, and ECC's ADR skills | Accepted |
| [0020](0020-build-test-review-pipeline-split.md) | `/build` → `/test` → `/review`: split implementation from verification and review | Partially superseded by [0035](0035-independent-verify-made-risk-triggered.md) (VERIFY made risk-triggered) |
| [0021](0021-reconcile-superpowers-overlap-with-current-sdlc.md) | Reconcile Superpowers overlap with the current SDLC | Superseded by [0029](0029-build-selects-executor-skills.md) and [0039](0039-runtime-catalog-narrowed-by-observed-use.md) |
| [0022](0022-agent-execution-context-evidence-and-measurement.md) | Agent execution: bounded context, evidence, and measurement | Accepted |
| [0023](0023-agents-doc-moved-to-synced-dotfiles-claude-docs.md) | `docs/agents.md` moved to `dotfiles/claude/docs/`, now synced | Accepted |
| [0024](0024-vendored-test-engineer-persona-for-test-verify-gate.md) | Vendored `test-engineer` persona, `/test` now dispatches it instead of investigating inline | Accepted |
| [0025](0025-security-auditor-provenance-corrected.md) | `security-auditor.md`'s provenance corrected: vendored from addyosmani/agent-skills, not written fresh | Accepted |
| [0026](0026-security-auditor-reconciled-with-reference-docs.md) | `security-auditor.md` reconciled with `security-checklist.md`/`ai-security.md`/`supply-chain.md` | Accepted |
| [0027](0027-vendored-shipping-and-launch-skill-no-ship-command.md) | Vendored `shipping-and-launch` skill, deliberately no `/ship` command | Partially superseded by [0028](0028-ship-command-as-synthesis-gate.md) (`/ship` added as a no-dispatch synthesis gate; skill stays deleted) |
| [0028](0028-ship-command-as-synthesis-gate.md) | `/ship` added as a synthesis gate, reversing 0027 | Partially superseded by [0030](0030-ship-accessibility-axis-dropped.md) (accessibility axis dropped) |
| [0029](0029-build-selects-executor-skills.md) | `/build` selects a compact execution skill for each executor | Accepted |
| [0030](0030-ship-accessibility-axis-dropped.md) | `/ship`'s accessibility axis dropped rather than improvised | Accepted |
| [0031](0031-parallel-executors-via-worktree-isolation.md) | Parallel executors enabled via worktree isolation, superseding 0003 | Partially superseded by [0042](0042-third-executor-as-conditional-exception.md) (conditional third executor) |
| [0032](0032-unblock-triage-persona-removed.md) | `unblock-triage` persona removed; blocked-item triage belongs to each gate | Accepted |
| [0033](0033-canonical-disposition-and-scoped-commit-authority.md) | Canonical release disposition, scoped commit authority, gate-state integrity | Clarified by [0038](0038-verify-pass-test-only-candidate-identity.md) |
| [0034](0034-spec-driven-development-narrowed-to-define.md) | `spec-driven-development` narrowed to the DEFINE stage | Accepted |
| [0035](0035-independent-verify-made-risk-triggered.md) | Independent VERIFY made risk-triggered; `/review` owns the decision | Clarified by [0038](0038-verify-pass-test-only-candidate-identity.md) |
| [0036](0036-specialist-reviewers-to-sonnet-and-narrowed-triggers.md) | Specialist reviewers to Sonnet/medium with narrowed triggers | Accepted |
| [0037](0037-fixed-session-context-reduced.md) | Fixed session context reduced: compact prompts and settings | Partially superseded by [0043](0043-automatic-memory-and-compaction-window-restored.md) (both settings changes reversed; the prompt compression stands) |
| [0038](0038-verify-pass-test-only-candidate-identity.md) | VERIFY PASS test-only commits may advance the BUILD candidate | Accepted |
| [0039](0039-runtime-catalog-narrowed-by-observed-use.md) | Runtime plugins narrowed; standalone engineering skills retained | Partially superseded by [0043](0043-automatic-memory-and-compaction-window-restored.md) (automatic memory no longer disabled) |
| [0040](0040-openspec-conventions-adopted.md) | Four conventions adopted from Fission-AI/openspec; nothing vendored | Accepted |
| [0041](0041-recon-delegated-to-repo-recon-subagent.md) | Repository recon delegated to a `repo-recon` subagent | Accepted |
| [0042](0042-third-executor-as-conditional-exception.md) | A third concurrent executor as a conditional exception, not a raised cap | Accepted |
| [0043](0043-automatic-memory-and-compaction-window-restored.md) | Automatic memory and the 500k compaction window restored, reversing 0037 | Accepted |
| [0044](0044-config-security-hardening-pass.md) | Config security hardening: enforcement made to match the stated guarantees | Accepted |
| [0045](0045-spec-approval-state-change-impact-and-requirement-traceability.md) | Spec approval state, change-impact semantics, and requirement traceability | Accepted |
| [0046](0046-plan-technical-approach-spec-pinning-and-plan-gates.md) | Plan gains a technical approach, a spec pin, and its own approval state | Accepted |
| [0047](0047-skill-trim-by-deduplication.md) | Skills trimmed by de-duplication, not by cutting policy | Accepted |

Adding a new decision: create the next-numbered `NNNN-kebab-title.md`
(4-digit, zero-padded — MADR-style, matches the files already here) and
add one row here. If it reverses an earlier entry, leave that entry's
text as-is, mark its Status column "Superseded by NNNN", and state the
reversal in the new entry instead of editing the old one.
