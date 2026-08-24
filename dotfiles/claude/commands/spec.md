---
description: Start spec-driven development — write a structured specification before writing code
argument-hint: "[ticket or feature description]"
---

Invoke `../skills/spec-driven-development`.

Begin by understanding what the user wants to build. If a `jira-ticket` intake summary already answered some of this, don't re-ask it — confirm what's already known and ask only what's still open. Otherwise ask clarifying questions about:
1. The objective and target users
2. Core features and acceptance criteria
3. Tech stack preferences and constraints
4. Known boundaries (what to always do, ask first about, and never do)

Then generate a structured spec covering all six core areas: objective, commands, project structure, code style, testing strategy, and boundaries.

Before asking for approval, run the skill's specification-closure gate. Reconcile
all sections, prove any cross-row/resource concurrency mechanism, and define
deletion semantics whenever a deletion marker or soft-delete field exists. Do
not present a materially contradictory or lifecycle-ambiguous spec as complete.

If the request bundles several independently testable capabilities, first propose a capability map (module ids, dependency direction, build order) per the skill's Phase 0 and get it approved, then spec each module in dependency order.

Save the spec as docs/specs/[TICKET]-SPEC.md in the project root and confirm with the user before proceeding.
