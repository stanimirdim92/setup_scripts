---
name: spec-driven-development
description: Creates specs before coding. Use when starting a new project, feature, or significant change and no specification exists yet. Use when requirements are unclear, ambiguous, or only exist as a vague idea. Use when a single requirement spans several independently testable capabilities and needs decomposing into a capability map of modules before specifying.
---

# Spec-Driven Development

## Overview

Write a structured specification before writing any code. The spec is the shared source of truth between you and the human engineer — it defines what we're building, why, and how we'll know it's done. Code without a spec is guessing. A 15-minute spec prevents hours of rework.

## When to Use

- Starting a new project or feature
- Requirements are ambiguous or incomplete
- The change coordinates behavior across files or modules; a source file plus
  its focused tests does not qualify by file count alone
- You're about to make an architectural decision
- The change would decompose into more than one task in `/plan`

**When NOT to use:** Single-line fixes, typo corrections, or bounded low-risk
changes whose expected behavior is unambiguous, even when implementation and
focused tests span a few files. When the lists conflict, ambiguity, risk, or
independently planned behavior wins over file count.

## The Gated Workflow

The harness has these user-invoked stages:

```text
DEFINE      PLAN       BUILD       REVIEW       SHIP
/spec  ->   /plan  ->  /build  ->  /review  ->  /ship
                              \
                               -> /test -> /review
                                  VERIFY, when required
```

### Phase 0: Scope Check

Most requests describe one capability. If this one does, skip this phase and go straight to Specify — Phase 0 exists for the exception, not the rule, and it puts no hierarchy on single-capability features.

**Detection.** Decompose before specifying when a single requirement bundles several independently testable capabilities:

- The requirement names distinct capabilities with their own consumers or data (e.g. identity, billing, notifications, reporting)
- Acceptance criteria cluster into groups that could ship and be verified separately
- One capability could be cut or replaced without rewriting the others' requirements

**Propose a capability map before writing any spec.** Small and reviewable — a module table plus a build order, not a project plan:

```markdown
# Capability Map: [Initiative Name]

| Module id | Responsibility | Depends on |
|---|---|---|
| identity | Accounts, sessions, SSO | — |
| billing | Plans, invoices, payments | identity |
| notifications | Email and webhook fan-out | identity |
| reporting | Usage dashboards | billing, notifications |

Build order: identity → billing, notifications → reporting
```

- **Stable module ids.** Kebab-case, chosen once, never renamed mid-initiative. Specs, plans, and downstream commands select work by these ids instead of guessing which spec is active.
- **Dependency direction, no cycles.** Arrows point one way. If two modules each need the other, they are one module.
- **Interfaces live at the boundary.** The map records that `billing` depends on `identity`; the contract between them belongs in the provider module's spec (see `api-and-interface-design` for designing it).

**The map is gated like every phase.** The human reviews module boundaries, dependency direction, and build order before any module spec is written. Getting the map wrong is expensive; reviewing ten lines is not.

**Then recurse per module.** Specify each module in dependency order. Each module
gets its own spec, scoped to that module's objective, boundaries, and requirements.
Save the approved map at `docs/specs/[TICKET]-CAPABILITY-MAP.md` and each module's spec alongside it, 
named by ticket and module id (`[TICKET]-SPEC-identity.md`, `[TICKET]-SPEC-billing.md`) — the map, 
not filename guessing, is the index of what exists.
After specification approval, hand the module to `/plan`; do not plan or implement it inside this skill.

### Phase 1: Specify

Start with a high-level vision. Ask the human clarifying questions until requirements are concrete.

**Surface assumptions immediately.** Before writing any spec content, list what you're assuming:

```
ASSUMPTIONS I'M MAKING:
1. This is a web application (not native mobile)
2. Authentication uses session-based cookies (not JWT)
3. The database is MySQL or PostgreSQL
4. We're targeting modern browsers only (no IE11)
→ Correct me now or I'll proceed with these.
```

Don't silently fill in ambiguous requirements. The spec's entire purpose is to surface misunderstandings *before* code gets written — assumptions are the most dangerous form of misunderstanding.

**Surface unresolved choices in a fixed format.** Whenever the evidence is
mixed, a tradeoff is unresolved, or two readings of a requirement lead to
different behavior, record it as an `OPEN QUESTION` block in the spec instead
of deciding silently:

```
OPEN QUESTION: Deletion semantics for contacts
- Option A: hard delete — simpler, loses audit trail
- Option B: soft delete — spec §4 mentions "restore", implies this
→ Decision needed before this spec can be approved.
```

A spec containing any `OPEN QUESTION` block cannot be presented for approval.
Ask, record the decision in the spec, remove the block, and rerun the approval
check. When the resolution materially changed specified behavior — a product,
domain, contract, or lifecycle choice — record it as a `DEC-###` entry under
Material Decisions naming the alternative that lost and the requirements it
affects. Otherwise the reasoning disappears into the final prose and gets
re-litigated by whoever reads the spec next. Technical decisions belong to the
plan as `TD-###`, a separate id space from the spec's `DEC-###`.

Treat a choice as needing an `OPEN QUESTION` block when picking the wrong
option would change an acceptance criterion, a schema, a public contract, or
data lifecycle behavior; choices below that bar (internal naming, private
helper structure) may be decided directly.

**Ask for domain knowledge the repository cannot reveal.** When the area
plausibly carries history — known production failures, compatibility
obligations, regulatory or unusual business rules — ask the human about it
directly; no amount of recon surfaces what was never written down. Ask only
what is relevant to this change and not already answered (by the intake
summary or earlier in the conversation), and record each answer beside the
requirement it constrains, with its source. This is a targeted question or
two, not another questionnaire.

### Repository Evidence

Before naming implementation details, choose the smallest adequate evidence path
from `../../references/repository-precedent.md`: reuse a current recon report,
perform a bounded check of named files, or dispatch `repo-recon` when its
triggers match.

Apply evidence in this order: user decisions → project rules → owning-module
precedent → repository convention → framework default. Distinguish verified
facts from inference. A missing precedent needs explicit justification; mixed
evidence or a choice that changes behavior, schema, contract, or lifecycle
becomes an `OPEN QUESTION`.

### Draft the Spec

Choose the smallest valid form:

- **Bugfix:** use `../../references/templates/bugfix-spec.md`; lead with
  reproduction evidence and make preserved behavior its own requirement. Root
  cause and fix mechanism stay in `/plan`.
- **Compact:** use for bounded low-risk work with no new architecture or
  pattern, public contract or schema change, cross-row/concurrent invariant, or
  data-lifecycle field. Include the complete header, Objective, Requirements,
  and Testing Strategy. Add Change Impact for non-`New` work, Boundaries only
  for a feature-specific constraint, and Material Decisions only when a
  `DEC-###` exists. Omit every other section.
- **Full:** otherwise use `../../references/templates/spec.md`.

In every form:

- scenarios own the acceptance criteria; do not restate them elsewhere;
- requirements use the exact `### Requirement: REQ-### — Title`, standalone
  `Source:`, and `#### Scenario: Name` forms consumed downstream; ids are never
  renumbered after approval (`../../references/spec-quality-gates.md` §3);
- `Change kind` is recorded, and non-`New` work names modified and explicitly
  preserved behavior in Change Impact;
- commands are exact and repository-defined, never abbreviated or inferred;
- testing maps each requirement to credible evidence at the layer that
  guarantees it; and
- applicable invariant and lifecycle checks follow
  `../../references/spec-quality-gates.md` §4–5.

For a long full spec, add a short index of links rather than a second summary.

### Approval Check

Before presenting a spec for human approval:

- every requested behavior is a requirement or explicit exclusion;
- every added behavior traces to a requirement or approved decision;
- no sections contradict each other;
- no `OPEN QUESTION` remains; and
- applicable checks in `../../references/spec-quality-gates.md` §1 and §4–5
  pass.

Fix failures and rerun the check. Passing it does not grant approval; only the
human can do that.

## Output Files

- Single-capability spec: `docs/specs/[TICKET]-SPEC.md` (create `docs/specs/` if needed)
- Multi-capability initiative: `docs/specs/[TICKET]-CAPABILITY-MAP.md` with `[TICKET]-SPEC-<module-id>.md` files alongside it — the ticket prefix keeps two initiatives that touch the same module from targeting the same file

Projects may designate different locations in their instruction sources; the
project rule wins over these defaults.

### Handoff after specification

After the human approves the specification, stop. Planning and task
decomposition belong to `/plan`, which invokes `planning-and-task-breakdown` and
writes the canonical plan/todo artifacts. Do not execute that methodology inside
this skill.

After the human approves the plan, implementation belongs to `/build`.
`/build` selects executor skills and dispatches workstreams; the user then
invokes `/review` and `/ship`. Independent verification is conditional, not a
fixed stage: `/review` evaluates `../../references/verification-triggers.md`
and requires `/test` only when a trigger matches (matching the Gated Workflow
diagram above). Do not write production code, dispatch executors, or run
implementation phases from `/spec`.

**Handling a returned `SPEC CONFLICT`.** When `/plan` (or a later stage) returns
a `SPEC CONFLICT`, treat it as a spec change request: raise the decision with
the human, record the resolution in the spec, remove or update the conflicting
requirement, rerun the approval check, and obtain re-approval before the work
returns to `/plan`.

## Keeping the Spec Alive

The spec is a living document, not a one-time artifact:

- **Update when decisions change** — If you discover the data model needs to change, update the spec first, then implement.
- **Update when scope changes** — Features added or cut should be reflected in the spec.
- **Commit the spec** — The spec belongs in version control alongside the code.
- **Reference the spec in PRs** — Link back to the spec section that each PR implements.

**Approval is document state, not conversation history.** The spec's `Status`
header (`Draft` / `Approved` / `Needs reapproval` / `Superseded`) is the record,
because a later session, a compaction boundary, or a downstream stage cannot see
what was said in this one. `/spec` moves `Draft` → `Approved` only on explicit
human approval — never on its own judgment, and a passing approval check is not
approval. Transitions and who may set them:
`../../references/spec-quality-gates.md` §2.

Any edit to an approved spec that changes behavior — a requirement, scenario,
schema, contract, invariant, boundary, or Change Impact entry — follows the same
path as a `SPEC CONFLICT`: set `Needs reapproval`, identify the affected
requirement ids, rerun the approval check, and obtain re-approval before
downstream work resumes on the changed sections.
Editorial corrections (typos, formatting, clarified wording that changes no
behavior) do not reopen approval. Never weaken a valid requirement because an
implementation fails to meet it — a failing implementation is a finding
against the code or a decision for the human, not grounds to move the goal.

## Verification

Verification is a human gate. The agent runs the Approval Check before presenting
the draft but cannot self-certify approval:

- [ ] The human has reviewed and approved the capability map (when one exists)
- [ ] The human has reviewed and explicitly approved this exact spec
- [ ] The header records `Status: Approved`, `Approved by`, and `Approved at`

The spec is not ready for `/plan` until all applicable items pass.
