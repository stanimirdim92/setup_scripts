---
name: spec-driven-development
description: Create or revise a specification for a feature, significant change, or bugfix before planning implementation. Use for unclear requirements, material behavior changes, or requests spanning independently testable capabilities. Owns specification and approval, not implementation.
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

Reuse the intake, user decisions, existing spec, and current repository evidence
before asking questions. Discover stack, authentication, data shape, and other
repository facts rather than presenting guesses for the user to correct.
Surface only unresolved assumptions that materially affect the specification;
silence does not validate them. Keep proposals distinct from accepted decisions.

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
  cause and implementation details stay in `/plan`. When an affected invariant
  requires proof under `../../references/spec-quality-gates.md` §4, include it
  before approval; it is a deliberate exception to leaving technical detail
  for planning. Keep it limited to the mechanism needed to establish the
  invariant, without task breakdown or production code.
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

Read the existing target spec or capability map before writing. Revise the same
work in place, preserving stable ids and applying the approval transitions
below. If the target belongs to different work or cannot be resolved, ask rather
than overwriting it. New specs use the selected template's Draft header.

### Handoff after specification

Save and present the spec, then stop for human approval. Approval completes
this stage; the user invokes `/plan` separately. Spec and plan may share a
session, while `/build` may start fresh after plan approval; each stage must
also work without the previous conversation.

The saved spec owns requirements and sources, accepted material decisions,
constraints, preserved behavior, and the relevant repository/verification
pointers. Reuse current recon in the same session, but put conclusions needed
by planning into the spec rather than relying on a chat-only report. Link
source evidence instead of copying transcripts or creating another handoff file.
The plan and task packets own the later implementation handoff.

Keep the spec in version control: `/plan` requires an approved, committed spec
with no uncommitted edits to pin its revision. Report when that prerequisite
is pending. Do not plan tasks, write production code, dispatch executors, or
invoke later stages from this skill.

## Keeping the Spec Alive

Approval lives in the saved header, under
`../../references/spec-quality-gates.md` §2. Only explicit human approval may
set Approved and its approval metadata. Editorial changes retain existing
approval. Behavioral changes set Needs reapproval immediately, preserve ids,
identify affected requirements, and require a new Approval Check and human
approval before downstream work resumes.

Handle a returned `SPEC CONFLICT` through that same revision process: raise the
decision with the human and record its resolution in the spec. Never weaken a
valid requirement merely because the implementation fails it. Link relevant
spec sections from later PRs so the behavior remains traceable.

## Verification

Verification is a human gate. The agent runs the Approval Check before presenting
the draft but cannot self-certify approval:

- [ ] The human has reviewed and approved the capability map (when one exists)
- [ ] The human has reviewed and explicitly approved this exact spec
- [ ] The header records `Status: Approved`, `Approved by`, and `Approved at`

The spec is not ready for `/plan` until all applicable items pass.
