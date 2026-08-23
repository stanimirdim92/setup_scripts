---
name: planning-and-task-breakdown
description: Breaks work into ordered tasks. Use when you have a spec or clear requirements and need to break work into implementable tasks. Use when a task feels too large to start, when you need to estimate scope, or when parallel work is possible.
---

# Planning and Task Breakdown

## Overview

Decompose work into small, verifiable tasks with explicit acceptance criteria. Good task breakdown is the difference between an agent that completes work reliably and one that produces a tangled mess. Every task should be small enough to implement, test, and verify in a single focused session.

## When to Use

- You have a spec and need to break it into implementable units
- A task feels too large or vague to start
- Work needs to be parallelized across multiple agents or sessions
- You need to communicate scope to a human
- The implementation order isn't obvious

**When NOT to use:** Single-file changes with obvious scope, or when the spec already contains well-defined tasks.

## The Planning Process

### Step 1: Enter Plan Mode

Before making implementation decisions, operate in read-only mode.

- Read the approved spec.
- Discover and read project-local instruction sources relevant to the affected area.
- Inspect the closest repository precedents and affected code.
- Resolve implementation constraints, dependencies, risks, and unknowns.

Common project instruction sources include:

- `CLAUDE.md`
- `AGENTS.md`
- `.ai/rules/*.md`
- module-local instruction files
- architecture/design documentation
- repository contribution/development guides

Do not assume these exact paths exist; discover the project's actual instruction
sources.

Use evidence in this order:

1. Approved spec decisions and explicit user instructions.
2. Applicable project-local rules.
3. Closest owning-module / sibling implementation precedent.
4. Repository-wide conventions.
5. Framework conventions only when the repository has no applicable precedent.

**Do NOT write code during planning.** The output is a plan document saved to `docs/tasks/[TICKET]-plan.md` and a task list saved to `docs/tasks/[TICKET]-todo.md`, not implementation.

### Decision provenance

Do not make implementation-shaping decisions appear arbitrary.

When a decision is materially constrained by the spec, a project rule, or a
repository precedent, record that source briefly in the plan when it helps
explain the decision.

Examples:

- Request/DTO boundary — required by an applicable project rule.
- Parent resolution by UUID or id — mirrors `AdvertiserTagAssignmentController`.
- Generated-column uniqueness guard — approved spec decision; new repository pattern.

Do not annotate obvious or trivial decisions merely for traceability.

### Step 2: Identify the Dependency Graph

Map implementation prerequisites, not architectural containment.

A dependency exists when one piece of work cannot be implemented or verified
correctly until another decision, contract, capability, or foundation exists.

Example:

```text
Database invariant
        ↓
Contact persistence behavior
        ↓
Contact CRUD API contract
        ↓
Frontend CRUD flow
```

Implementation order follows the dependency graph: satisfy real prerequisites before dependent behavior.

A dependency graph answers:

> What must exist before this can work?

It does not answer:

> Which architectural layer deserves its own task?

Do not create dependency edges merely because one class calls, injects,
implements, or sits architecturally beside another.

Examples:

- A repository implementing a contract does not mean the contract depends on
  the repository.
- A factory is not a dependency unless planned verification genuinely requires it.
- Controller, service, repository, builder, and model may all belong to one
  behavioral slice.

### Step 3: Slice by Behavior

Prefer vertical tasks that leave behind independently verifiable behavior.

Instead of building all the database, then all the API, then all the UI — build one complete feature path at a time:

**Bad (horizontal slicing):**
```
Task 1: Build entire database schema
Task 2: Build all API endpoints
Task 3: Build all UI components
Task 4: Connect everything
```

**Good (vertical slicing):**
```
Task 1: User can create an account (schema + API + UI for registration)
Task 2: User can log in (auth schema + API + UI for login)
Task 3: User can create a task (task schema + API + UI for creation)
Task 4: User can view task list (query + API + UI for list view)
```

Before accepting a task boundary, ask:

> Does this task produce behavior that can be meaningfully verified on its own?

If the answer is only "these architectural files now exist," merge it into the
behavioral task that consumes them unless it is a justified foundation.

A foundation task is justified only when later behavioral tasks genuinely depend
on it and it has meaningful independent verification.

Each vertical slice delivers working, testable functionality.

### Step 4: Assign Workstreams

Every task belongs to a workstream.

Default to **one workstream** for ordinary feature work.

Keep tasks in the same workstream when they:

- Share files or mutable state
- Belong to the same subsystem
- Form a dependency chain
- Share important implementation context
- Benefit from retaining decisions and codebase knowledge across tasks

Create another workstream only when the work is genuinely independent:

- No shared files or mutable state
- No unfinished dependency between the tasks
- Materially separate subsystem or implementation context

"Could be done in parallel" is not enough reason to create another workstream.

Workstreams primarily exist so `/build` can reuse one executor's context across
related tasks rather than spawning a fresh executor for every task.

`/build` owns execution order and concurrency. Planning only classifies the
work.

### Step 5: Write Tasks

Each task follows `../../references/templates/task.md`.

Every task must have:

- One coherent outcome
- Explicit acceptance criteria
- A verification step
- Dependencies
- A workstream
- Likely affected files or areas when useful

File count is context, not a sizing rule.

A task touching a migration, model, request, service, controller, route,
component, and feature test may still be one coherent behavioral slice.

### Step 6: Order and Checkpoint

Arrange tasks so that:

1. Dependencies are satisfied.
2. Each task leaves the system in a working state.
3. Add checkpoints where they materially reduce implementation or integration risk.
4. Put high-risk work early enough to fail fast.

Useful checkpoints include:

- after a risky schema or external-contract decision;
- before dependent work consumes a newly established contract;
- after integrating multiple workstreams.

Do not add a checkpoint or human approval merely because a fixed number of tasks
has elapsed.

Example:

```markdown
## Checkpoint: API contract established
- [ ] All tests pass
- [ ] Application builds without errors
- [ ] The contract required by dependent work is stable enough to consume
```

## Task Sizing Guidelines

Use size as a planning heuristic, not a hard file-count gate.

| Size | Typical Files | Scope |
|---|---:|---|
| XS | 1 | Localized change |
| S | 1-2 | One small behavior/component |
| M | 3-5 | One focused implementation session |
| L | 5-8 | Likely >1 focused session — consider splitting |
| XL | 8+ | Usually too broad — split unless highly cohesive |

Prefer S/M tasks. Split when the work cannot reasonably be implemented,
tested, and verified in one focused session.

**When to break a task down further:**
- It would take more than one focused session (roughly 2+ hours of agent work)
- You cannot describe the acceptance criteria in 3 or fewer bullet points
- It touches two or more independent subsystems (e.g., auth and billing)
- You find yourself writing "and" in the task title (a sign it is two tasks)

## Output Files

Default outputs:

- Plan: `docs/tasks/[TICKET]-plan.md`
- Task list: `docs/tasks/[TICKET]-todo.md`

Create `docs/tasks/` if needed.

Projects may designate an external task tracker instead of the default todo
file, but the plan should still preserve task dependencies and workstream
assignments.

## Guardrails

- Do not implement while planning
- Do not create tasks solely around architectural layers
- Do not split tasks based on an arbitrary file-count limit
- Do not manufacture multiple workstreams for possible parallelism
- Do not duplicate repository-wide conventions already documented elsewhere
- Do not copy the spec into the plan
- Do not hide unresolved technical risks inside implementation tasks
- Do not treat "parallelizable" as "should run in parallel"
- Do not introduce files, architectural layers, factories, DTOs, resources,
  test helpers, or abstractions solely because they are common framework
  conventions.
- Every planned new layer or support artifact must come from the approved spec,
  an applicable project rule, repository precedent, or a clearly stated new
  technical decision.


## Plan Document Template

Use `../../references/templates/plan.md`.

## Parallelization Opportunities

When multiple agents or sessions are available:

- **Safe to parallelize:** Independent feature slices, tests for already-implemented features, documentation
- **Must be sequential:** Database migrations, shared state changes, dependency chains
- **Needs coordination:** Features that share an API contract (define the contract first, then parallelize)

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "I'll figure it out as I go" | That's how you end up with a tangled mess and rework. 10 minutes of planning saves hours. |
| "The tasks are obvious" | Write them down anyway. Explicit tasks surface hidden dependencies and forgotten edge cases. |
| "Planning is overhead" | Planning is the task. Implementation without a plan is just typing. |
| "I can hold it all in my head" | Context windows are finite. Written plans survive session boundaries and compaction. |

## Red Flags

- Starting implementation without a written task list
- Tasks that say "implement the feature" without acceptance criteria
- No verification steps in the plan
- All tasks are XL-sized
- Risky boundaries or integration points with no checkpoint where one would materially reduce risk
- Dependency order isn't considered

## Verification

Before the plan is ready for `/build`, confirm:

- [ ] No task exists solely because an architectural layer exists, unless it is a justified foundation with independent verification value.
- [ ] Every task has explicit acceptance criteria
- [ ] Every task has a verification step
- [ ] Dependencies are explicit and correctly ordered
- [ ] Every task has a workstream
- [ ] Related or dependent tasks share a workstream
- [ ] Additional workstreams are genuinely independent
- [ ] Task boundaries follow coherent behavior rather than arbitrary file counts
- [ ] High-risk decisions are addressed early enough to fail fast
- [ ] Checkpoints exist where they materially reduce risk
- [ ] The plan does not unnecessarily duplicate the spec
- [ ] The plan contains no production implementation
- [ ] The human has reviewed and approved the plan

## See Also

Acceptance criteria are per-task and answer:

> Did this increment deliver the intended behavior?

Project-wide completion standards remain defined in
`../../references/definition-of-done.md`.
