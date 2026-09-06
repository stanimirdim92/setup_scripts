---
name: project-docs
description: Create or refresh repository documentation from the actual project. Use when asked to document a project, generate architecture and companion docs, or reconcile existing project docs with source. Does not implement features or redesign the system.
---

# Project documentation

Generate useful documentation for the repository as it exists. Apply
[document responsibilities and maintenance](../../references/documentation-practices.md#project-documentation).
This workflow is independent of ticket spec/plan/build stages.

## Select scope

Use the requested repository or the current project. Read applicable project
instructions, existing documentation, and the working-tree state first. Respect
existing locations and names; do not create a parallel documentation hierarchy.

- Default: choose the smallest useful set after inspection. Explain the selected
  files briefly and proceed; no separate planning artifact or approval ceremony.
- Explicit file list or full-set request: cover the requested documents, keeping
  each factual and proportional to the project. The full set is `ARCHITECTURE.md`,
  `DESIGN.md`, `CONVENTIONS.md`, `COMMANDS.md`, `TESTING.md`, `SECURITY.md`, and
  `.ai/repo-map.md`, or their existing equivalents. Do not fabricate content to
  fill a template; explain any requested document that cannot be grounded.
- Refresh: reconcile existing docs with current source, retaining relevant
  human decisions, known constraints, and intentional exceptions.

Ask only when scope, contradictory requirements, or an unresolved architectural
decision materially changes the result. Document uncertainty when it can remain
an explicit gap without preventing useful documentation.

## Gather evidence

Inspect entry points, manifests and lockfiles, module boundaries, key execution
paths, data stores, integrations, test setup, and deployment/configuration
sources relevant to the selected documents. Read the applicable rules and ADRs.
Use source pointers and bounded reads; do not dump entire directories or logs.

Distinguish current implementation, prescribed rules, and proposed future work.
If source violates an intentional rule, record the discrepancy without silently
changing the rule. If two authoritative sources disagree, name both and the
unresolved choice. Report declared, locked, and installed versions separately
when the difference matters; prefer manifest/lockfile pointers over volatile
version inventories.

Find exact commands in project scripts/configuration. Label commands discovered
in source separately from commands executed successfully. Documentation generation
does not require running every command: do not run installs, migrations,
deployment, or external writes to fill the docs. Never copy secret values;
document variable names, responsibilities, and configuration locations instead.

## Write and verify

Write current facts with nearby repository pointers. Keep a fact in one place
and link to it elsewhere. Summarize rules rather than copying whole rule files;
use existing ADRs for accepted decisions and never invent decision history.
Keep proposed changes clearly separate from the current architecture.

Revise only affected content in existing documents. Add concise navigation to
the existing README or instruction entrypoint when useful, preserving its rules.
Do not introduce new mandatory startup reads or rewrite project instructions.
Do not modify application code, configuration, or ticket specs/plans.

Before reporting completion:

- resolve referenced files/directories; label proposed paths as proposed;
- trace architectural and behavioral claims to inspected source;
- reconcile summaries, diagrams, commands, and companion docs with each other;
- inspect the complete documentation diff and preserve unrelated work;
- report files created/updated, checks actually performed, and remaining gaps.

Examples:

- `project-docs` — document this project with the smallest useful set.
- `project-docs full set` — generate the seven documents above from this repo.
- `project-docs refresh ARCHITECTURE.md TESTING.md` — reconcile just those docs.
