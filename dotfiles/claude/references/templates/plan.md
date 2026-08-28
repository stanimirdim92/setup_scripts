# Plan Template

The canonical implementation-plan document shape. Used by
`planning-and-task-breakdown`'s Step 4-6 output — saved to
`docs/tasks/[TICKET]-plan.md` per that skill's Output Files convention.

Structure the task list by workstream and dependency order — not by
generic phases like Foundation/Core/Polish. Place checkpoints only at
the skill's Step 6 risk points, named for the risk they gate.

```markdown
# Implementation Plan: [Feature/Project Name]

Spec: [path to approved spec, and module-id if from a capability map]

## SPEC CONFLICT
[Only when one exists — spec section + quoted requirement, what in the
repository contradicts or blocks it, 1-3 candidate resolutions. Planning
stops here until resolved via /spec. Delete this section otherwise.]

## Decisions and Provenance
- [Decision] — [source: spec §X / project rule <file> / mirrors <precedent> /
  new technical decision: <reason>]

## Workstreams
- ws-main: [scope — default single workstream]
- [ws-other: only per Step 4 criteria; note the contract checkpoint that
  gates it]

## Task List
[Dependency order. Each task's full packet lives in the todo file /
tracker per task.md; this list is the ordered index.]

- [ ] T1 (S, ws-main, deps: —, spec 2.1): [behavioral outcome]
- [ ] T2 (M, ws-main, deps: T1, spec 2.2): [behavioral outcome]

### Checkpoint: [named risk — e.g. "API contract established"]
[Placed per Step 6: after a risky schema/external-contract decision,
before dependent work consumes a new contract, or after integrating
workstreams.]
- [ ] All tests pass
- [ ] Application builds without errors
- [ ] [The specific contract/decision this checkpoint gates is stable]

- [ ] T3 (M, ws-frontend, deps: checkpoint above, spec 3): [outcome]

## Sizing Exceptions
[Every task kept at L/XL, with why splitting would break a single
coherent behavioral slice. "None" if all tasks are XS-M.]

## Parallelization Metadata
[Dependency-ready workstreams with no shared mutable state, if any.
Informational for /build — not an instruction to run in parallel.]

## Risks and Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| [Risk] | [High/Med/Low] | [Strategy] |

## Open Questions
[Planning-level only (tooling, environment, sequencing). Any question
about feature behavior is a SPEC CONFLICT, not an open question. Must
read "None" before the handoff line below.]

---
Handoff: Ready for /build — [pending human approval / approved by <name>]
```
