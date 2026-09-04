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

## Repository evidence

Use the smallest adequate evidence path from
`../references/repository-precedent.md` §1: reuse a current recon report;
dispatch `repo-recon` when its triggers match; otherwise inspect only applicable
instructions and the named source, test, README, manifest, or CI files needed
for this bounded change. Never guess or abbreviate repository rules, commands,
or precedent. If the bounded check cannot find an exact verification command,
dispatch recon or leave it unresolved; do not invent one.

Choose the smallest valid spec shape. For bounded, low-risk changes that
qualify, use the skill's compact form. Use the full form only when the change
does not qualify for compact or bugfix form. In every form, give each fact one home;
don't repeat acceptance criteria outside their requirement scenarios.

Before asking for approval, run the skill's Approval Check and the applicable
checks in `../references/spec-quality-gates.md`. Do not present a contradictory,
incomplete, or unresolved spec.

If the request bundles several independently testable capabilities, first propose a capability map (module ids, dependency direction, build order) per the skill's Phase 0 and get it approved, then spec each module in dependency order.

Save the spec as docs/specs/[TICKET]-SPEC.md in the project root and confirm with the user before proceeding.

## Approval state

Start with `# Spec: [name]`, then write the complete header from
`../references/templates/spec.md`: `Status: Draft`, Ticket,
`Change kind: New | Modify | Remove | Rename | Bugfix`, Supersedes,
`Approved by: —`, and `Approved at: —`. After presenting it, set
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
