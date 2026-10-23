# Plan Template

The canonical implementation-plan document shape. Used by
`planning-and-task-breakdown`'s Draft the Plan section — saved to
`docs/tasks/[TICKET]-plan.md` per that skill's Output Files convention.

Structure the task list by workstream and dependency order — not by
generic phases like Foundation/Core/Polish. Place checkpoints only at the risk
points defined by the skill, named for the risk they gate.

Approval state, spec-revision pinning, id stability, the approval checks, and
the rules for spike tasks live in `../plan-quality-gates.md`. Requirement-id
rules are in `../spec-quality-gates.md` §3.

Sections marked **conditional** are omitted entirely when they don't apply —
not filled with N/A.

**Compact plan.** Prefer this form for a bounded single-workstream change with
no schema change, public contract, migration, or major risk. Keep exactly: the
metadata header; a short Technical Approach (current → proposed flow and
affected paths, without mandatory subheadings); Task Index; Requirement
Coverage; a Verification Strategy containing the focused command only when it
differs from the integrated command; and Handoff. Do not add empty Decisions,
Workstreams, Boundaries, Risks, or other sections. The metadata header and ids
are never optional — `/build`, `/review` and `/ship` read them.

The todo file holds each full task packet; the plan only indexes it. For one
coherent behavior, implementation and its proving tests are one task, not an
implementation task plus a test task. Omit empty optional fields from a compact
task packet rather than spelling out `None`.

```markdown
# Implementation Plan: [Feature/Project Name]

Status: Draft
Spec: docs/specs/[TICKET]-SPEC.md
Modules: [module ids this plan covers, or N/A without a capability map]
Not yet planned: [remaining module ids, or None]
Spec status: Approved
Spec revision: git-commit:[sha]:docs/specs/[TICKET]-SPEC.md
Approved by: —
Approved at: —

## SPEC CONFLICT
[Only when one exists — spec section + quoted requirement, what in the
repository contradicts or blocks it, 1-3 candidate resolutions. Planning
stops here until resolved via /spec. Delete this section otherwise.]

## Technical Approach
[How the solution fits together. This is the HOW the task list alone doesn't
carry. No production code, and no restating requirements — the spec owns what
and why.]

### Current Flow
[What happens today, with repository pointers. "None — new capability" is a
valid answer.]

### Proposed Flow
[The ordered data/control flow after the change.]

### Root-Cause Trace
[Bugfix plans only (spec `Change kind: Bugfix`); delete otherwise. A logical
trace from the reproduction to the faulty line, every hop a `file:line`
(ADR 0097). `check-plan.py` fails a bugfix plan without it, and
`code-reviewer` walks it against the code.]

- Trigger: [the reproduction's entry point — route, command, job — `file:line`]
- Path:
  1. `file:line` — [what happens here; the value or state at this hop]
  2. `file:line` — [...]
- Fault: `file:line` — [the line where behavior goes wrong, and the wrong
  assumption it makes]
- Other paths: [every other caller that reaches the fault, from a search such
  as `rg -n "<symbol>"`; each one fixed by the change or stated safe, with
  `file:line`]
- Proof: [the regression test that drives the Trigger and fails before the
  fix, `file:line` or test name]

### Components and Responsibilities
- `[existing or NEW component]`: [responsibility]

### Affected Areas
- `path/or/module`

## Decisions and Provenance
[One line per decision. Use the expanded `TD-###` form only where two or more
plausible implementations existed and the choice needs to survive review.]

- [Decision] — [source: spec §X / project rule <file> / mirrors <precedent> /
  new technical decision: <reason>]

### TD-001 — [Short title]
- Choice: [what was chosen]
- Alternatives: [what was rejected]
- Reason: [why]
- Source: [REQ-004 / approved invariant mechanism / project rule]
- Affects: [T001, T002]

### TD-002 — Pre-authorized: [stop condition, e.g. "new index on leads"]
[One per owner answer in the approval's Pre-authorizations block.]
- Stop condition: [what would otherwise stop the executor]
- Answer: [the owner's answer — the recommended default or another choice]
- Source: owner approval, [date]
- Affects: [T003]

## Contracts and Data Changes
**Conditional** — include only for APIs, schemas, events, shared DTOs, or more
than one workstream.

### Contract: [name]
- Owner: [ws-…]
- Consumers: [ws-…, external caller]
- Authoritative definition: `[path]`
- Compatibility: additive | breaking | migration required
- Stabilization checkpoint: CP-001

## External Tool Access
**Conditional** — include when a task depends on an MCP server, a design
tool, or another external service. `/plan` probes each one; an executor does
not re-check a blocker recorded here.

| Tool | Access needed | Probe and result | Date |
|---|---|---|---|
| [Figma MCP] | [read / write (`use_figma` needs an edit seat)] | [`get_metadata <node>` — ok / error text] | [YYYY-MM-DD] |

## Workstreams
- ws-main: [scope — default single workstream]
- [ws-other: only per the skill's workstream criteria; note the contract checkpoint that
  gates it]

## Task Index
[Dependency order. Within it, tasks with no checkpoint dependency come before
checkpoint-gated tasks so they can start early. Each task's full packet lives
in the todo file / tracker per task.md; this is the ordered index. Every task names at least one REQ or TD id.
Ids are stable after approval — a dropped task keeps its id and is struck
through as superseded.]

- [ ] T001 (S, ws-main, deps: —) [REQ-001]: [behavioral outcome]
- [ ] T002 (M, ws-main, deps: T001) [REQ-002, TD-001]: [behavioral outcome]

### CP-001 — Checkpoint: [named risk, e.g. "API contract established"]
[Placed at the skill's risk points: after a risky schema/external-contract decision,
before dependent work consumes a new contract, or after integrating
workstreams.]
- [ ] All tests pass
- [ ] Application builds without errors
- [ ] [The specific contract/decision this checkpoint gates is stable]

- [ ] T003 (M, ws-frontend, deps: CP-001) [REQ-001]: [outcome]

## Requirement Coverage
[Requirement → tasks → the evidence that will prove it. The mechanical check
that planning dropped nothing and invented nothing.]

- REQ-001 → T001 → feature test
- REQ-002 → T002 → API contract test
- REQ-003 → T001, T003 → persistence and concurrency tests
- REQ-004 → withdrawn in spec, no task required

Unmapped requirements: None
Orphan tasks: None

## Verification Strategy
[Every command from repository evidence — recon report, package manifests, CI
config — never guessed. `/build` uses the integrated line for final
verification; task-focused checks alone do not prove integrated behavior.]

- Task-focused: [the command each task runs]
- Workstream: [the command run when a workstream completes]
- Integrated: [combined test/build/static-analysis commands]
- Data/migration: [constraint, backfill, EXPLAIN, or rollback evidence]
- Manual/operational: [only what automation cannot prove]

[For a bugfix plan, the three proofs: the pre-fix implementation reproduces the
defect; the fixed implementation produces the expected behavior; the explicitly
preserved behavior is unchanged — its tests pass both before and after.]

## Migration and Rollout
**Conditional** — include only when the change alters schema, stored data, or
deployment shape.

- Deployment order:
- Mixed-version behavior:
- Backfill strategy:
- Locking/downtime constraints:
- Rollback mechanism:
- Post-deployment evidence:

## Sizing Exceptions
**Conditional** — include only for a task kept at L/XL, with why splitting it
would break a single coherent behavioral slice.

## Parallelization Metadata
**Conditional** — dependency-ready workstreams with no shared mutable state.
Informational for `/build`, not an instruction to run in parallel.

## Risks and Mitigations
[Every mitigation names the task or checkpoint that performs it. A mitigation
with no owner is a hope, and fails the approval check.]

| Risk | Trigger/evidence | Mitigation | Task/checkpoint |
|---|---|---|---|
| [Risk] | [what would show it happening] | [strategy] | T001 / CP-001 |

## Open Questions
[Planning-level only (tooling, environment, sequencing). Any question
about feature behavior is a SPEC CONFLICT, not an open question. Technical
uncertainty that needs evidence becomes a spike task, not an entry here — see
`../plan-quality-gates.md` §5. Must read "None" before the handoff line.]

---
Handoff: Awaiting plan approval
[After explicit approval, replace with: Ready for /build]
```
