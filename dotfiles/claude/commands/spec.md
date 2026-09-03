---
description: Start spec-driven development — write a structured specification before writing code
argument-hint: "[ticket or feature description]"
---

Invoke the `spec-driven-development` skill before drafting; its methodology is
required, not optional background.

Begin by understanding what the user wants to build. If a `jira-ticket` intake summary already answered some of this, don't re-ask it — confirm what's already known and ask only what's still open. Otherwise ask clarifying questions about:
1. The objective and target users
2. Core features and acceptance criteria
3. Tech stack preferences and constraints
4. Known boundaries (what to always do, ask first about, and never do)

## Repository recon

Dispatch one `repo-recon` agent for the affected area before drafting the spec —
the area, `/spec` as the calling stage, and any specific questions you already
have. Do not survey the repository in this context. Reuse, pointer-following, and
**No precedent found for** / **Not surveyed** handling:
`../references/repository-precedent.md` §1.

Choose the smallest valid spec shape. For bounded, low-risk changes that
qualify, use the skill's compact form. Use the full form only when the change
needs all six core areas: objective, commands, project structure, code style,
testing strategy, and boundaries. In either form, give each fact one home;
don't repeat acceptance criteria outside their requirement scenarios.

Before asking for approval, run the skill's specification-closure gate. Reconcile
all sections, prove any cross-row/resource concurrency mechanism, and define
deletion semantics whenever a deletion marker or soft-delete field exists. Do
not present a materially contradictory or lifecycle-ambiguous spec as complete.

If the request bundles several independently testable capabilities, first propose a capability map (module ids, dependency direction, build order) per the skill's Phase 0 and get it approved, then spec each module in dependency order.

Save the spec as docs/specs/[TICKET]-SPEC.md in the project root and confirm with the user before proceeding.

## Approval state

Write the spec with `Status: Draft` and the rest of the header from
`../references/templates/spec.md` filled in. After presenting it, set
`Status: Approved` — with `Approved by` and `Approved at` — only when the human
has explicitly approved it. Approval is not implied by silence, by "looks good"
on a different question, or by an instruction to continue to `/plan`; when in
doubt, ask rather than promoting the status. Per-transition rules:
`../references/spec-quality-gates.md` §2.

Every requirement gets a `REQ-###` id and a `Source:` line — `/plan` refuses a
spec without them, and every later gate traces evidence against them (§3).

A defect uses `../references/templates/bugfix-spec.md` instead, which leads with
reproduction evidence and makes preserved behavior its own requirement.

The request that invoked `/spec` authorizes specification only, even when it
says to build or fix something — that instruction does not carry forward past
this command. After presenting the spec, stop and wait for a new user request;
do not start `/plan` or implementation in the same response.
