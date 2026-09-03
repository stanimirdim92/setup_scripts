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
- Work from the `repo-recon` report `/plan` provides for the affected area, per
  `../../references/repository-precedent.md`. Do not survey the repository
  yourself. The evidence order for choosing between a project rule, module
  precedent, repository-wide convention and framework default is the same one
  `/spec` applied — `../spec-driven-development/SKILL.md`, "Repository Recon";
  a plan does not get to re-rank it.
- Note implementation constraints, dependencies, risks, and unknowns, treating
  the report's **No precedent found for** and **Not surveyed** sections as
  explicit unknowns rather than settled ground.

Before decomposing work, confirm the spec's `Status` header reads `Approved`,
reading it from disk rather than relying on approval seen earlier in the
conversation. Any other status stops planning and returns the spec to `/spec`
(`../../references/spec-quality-gates.md` §2). Then pin the spec by the commit
that last touched it, requiring it committed first, and record it in the plan:
an approved status proves a human approved something, not that the spec still
says what this plan assumes (`../../references/plan-quality-gates.md` §2).

Then reconcile the proposed plan against the approved spec. Build the trace from
each planned behavior and acceptance criterion back to its spec source, keyed by
`REQ-###`: every requirement maps to at least one task, every task names at
least one requirement, and the plan reports `Unmapped requirements: None` and
`Orphan tasks: None`. An orphan task is scope the spec never asked for — remove
it, or report a `SPEC CONFLICT` if the behavior is genuinely needed (§3).

If the repository makes an approved spec decision infeasible or reveals a
contradiction, stop and report a `SPEC CONFLICT`; do not silently rewrite the
requirement in the plan.

A `SPEC CONFLICT` report contains: the spec section and quoted requirement, what
in the repository contradicts or blocks it, and 1-3 candidate resolutions. Write
it at the top of the plan document under a `## SPEC CONFLICT` heading, save the
partial plan as-is, and stop — do not continue planning past the conflict.

**Do NOT write code during planning.** The output is a plan document saved to `docs/tasks/[TICKET]-plan.md` and a task list saved to `docs/tasks/[TICKET]-todo.md`, not implementation.

### Decision provenance

Do not make implementation-shaping decisions appear arbitrary.

Record a source for every decision a reviewer could reasonably ask "why this
way and not another?" about — any decision with two or more plausible
implementations where the spec, a project rule, or a repository precedent
picked the winner. When in doubt, record it: an unnecessary annotation costs
one line; a missing one costs a review round-trip.

Skip annotation only when the decision has one obvious implementation (e.g.,
"the new route lives in the existing routes file").

Examples:

- Request/DTO boundary — required by an applicable project rule.
- Parent resolution by UUID or id — mirrors `AdvertiserTagAssignmentController`.
- Generated-column uniqueness guard — approved spec decision; new repository pattern.

### Preserve the approved behavioral contract

The plan may refine implementation detail, but it may not silently change the
approved feature contract.

- Do not contradict, omit, weaken, or reinterpret an approved requirement.
- Do not strengthen acceptance criteria or invent validation, uniqueness,
  authorization, lifecycle, pagination, performance, or error behavior merely
  because it seems desirable or conventional.
- Additional implementation checks are allowed when they verify an approved
  behavior without changing externally observable acceptance criteria.
- A genuinely needed behavior not present in the spec is a proposed spec change,
  not a planning assumption. Record the conflict and return to `/spec` for human
  approval before continuing.

Before approval, compare the plan and every task packet against the spec section by section.
Every acceptance criterion must be equal to or directly derived from the approved spec.

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

### Step 3: Slice Vertically

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

Before accepting any task boundary, ask:

> Does this task produce behavior that can be meaningfully verified on its own?

If the answer is only "these architectural files now exist," merge it into the
behavioral task that consumes them — unless it is a **justified foundation**: a
task that is independently verifiable AND consumed by two or more downstream
tasks (e.g., a migration establishing a schema three later tasks build on).

Each vertical slice delivers working, testable functionality. Its production
implementation and the automated tests that prove it are normally one task:
red, green, and refactor are execution steps inside that task, not separate
planning units. Split out test work only when it has independently verifiable
value without the production change (for example, a characterization suite
that passes against the current behavior and gates a risky later task).

### Carry invariants into the task boundary

When the approved spec defines an invariant, do not leave it as background
prose that the executor has to rediscover.

**Every** task that can establish, transfer, violate, or release that invariant
must carry the relevant transition in its acceptance criteria or verification —
not just the first task that touches it. Also preserve which layer is
responsible for enforcing it when the spec or a project rule assigns
enforcement to a specific layer.

This keeps the task behavioral: "first entity establishes the invariant" is a
better execution contract than "implement service methods."

### Step 4: Assign Workstreams

Every task belongs to a workstream.

Default to **one workstream** for ordinary feature work.

Keep tasks in the same workstream when they:

- Share files or mutable state
- Belong to the same subsystem
- Form a dependency chain
- Share important implementation context
- Benefit from retaining decisions and codebase knowledge across tasks

Create another workstream only when the implementation context is materially
different — different subsystem, language, framework, or repository area, such
that one executor's accumulated context does not help the other — and either
the work is genuinely independent or a stable contract forms a clean dependency
boundary.

Independent workstreams have:

- No shared files or mutable state
- No unfinished dependency between the tasks
- Materially separate subsystem or implementation context

Contract-separated workstreams may retain a dependency when all of the following
are true:

- upstream and downstream implementation contexts are materially different;
- the shared contract is explicit, reviewable, and stable enough to consume;
- the downstream workstream is ordered after a named contract checkpoint;
- dependency ordering remains explicit in the plan and task packets;
- `/build` must not treat the downstream work as dependency-ready before the
  checkpoint passes.

For example, backend API implementation and frontend consumption may use
separate workstreams after an API-contract checkpoint. Separation does not erase
the dependency or authorize premature parallel execution.

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

A delivery task includes both the implementation and the tests needed to prove
its acceptance criteria. Do not create a test-only follower merely because the
test files differ from the production files.

Every task should also carry, whenever they exist for its area:

- Likely affected files or areas
- Compact context pointers: the applicable project/module rules, the one or two
  closest repository precedents, and any shared contract or invariant the task
  must respect. Include a pointer whenever an executor implementing the task
  cold — without reading the full spec or plan — would otherwise miss a rule,
  precedent, or invariant that changes what correct output looks like. Omit
  pointers only when no such rule, precedent, or contract applies.

The task should be dispatchable without copying the full spec or full plan into
an executor prompt. Prefer references to authoritative files over duplicated
prose.

File count is context, not a sizing rule.

A task touching a migration, model, request, service, controller, route,
component, and feature test may still be one coherent behavioral slice.

### Step 6: Order and Checkpoint

Arrange tasks so that:

1. Dependencies are satisfied.
2. Each task leaves the system in a working state.
3. Checkpoints exist at the risk points listed below.
4. Put high-risk work early enough to fail fast.

Add a checkpoint at each of these points (and only these, unless the plan
states a specific new risk it mitigates):

- after a risky schema or external-contract decision;
- before dependent work consumes a newly established contract;
- after integrating multiple workstreams.

Do not add a checkpoint or human approval merely because a fixed number of tasks
has elapsed.

**Technical uncertainty that cannot be resolved read-only becomes a bounded
spike task, not an open question** — acceptance criteria naming the evidence and
the deciding threshold, gated by a checkpoint before dependent work. It runs
during `/build`, changes no production behavior, and is only for technical
questions: if the answer could change a `REQ-###` it is a `SPEC CONFLICT`.
Rules: `../../references/plan-quality-gates.md` §5.

Example:

```markdown
## Checkpoint: API contract established
- [ ] All tests pass
- [ ] Application builds without errors
- [ ] The contract required by dependent work is stable enough to consume
```

## Task Sizing Guidelines

| Size | Typical Files | Scope |
|---|---:|---|
| XS | 1 | Localized change |
| S | 1-2 | One small behavior/component |
| M | 3-5 | One focused implementation session |
| L | 5-8 | More than one focused session |
| XL | 8+ | Multiple sessions, multiple concerns |

Agents perform best on S and M tasks. **Split every L and XL task** unless
splitting would break a single coherent behavioral slice that cannot be
verified in parts — and when you keep one, record that justification in the
plan. File count is a proxy: size by verification effort, not by counting
files.

**When to break a task down further:**
- It would take more than one focused session (roughly one context window of agent work)
- You cannot describe the acceptance criteria in 3 or fewer bullet points
- It touches two or more independent subsystems (e.g., auth and billing)
- You find yourself writing "and" in the task title (a sign it is two tasks)

## Output Files

Default outputs:

- Plan: `docs/tasks/[TICKET]-plan.md`
- Task list: `docs/tasks/[TICKET]-todo.md`

Create `docs/tasks/` if needed.

In a compact plan, the plan indexes tasks and the todo contains their full
packets. Never copy the packet into both artifacts; follow the compact form in
`../../references/templates/plan.md`.

Projects may designate an external task tracker instead of the default todo
file, but the plan should still preserve task dependencies and workstream
assignments.

## Guardrails

The four most common planning failures, shown as bad/good pairs:

**Layer tasks instead of behavior tasks**

```
Bad:  Task: Create ContactRepository, ContactFactory, ContactDTO
Good: Task: Contacts persist with the uniqueness invariant
      (repository + factory + DTO live inside this slice)
```

**Invented behavior not in the spec**

```
Bad:  Task: Contact creation (adds soft-delete and audit log —
      "standard practice")
Good: Task: Contact creation, exactly per spec §3.2.
      Soft-delete looks needed → SPEC CONFLICT, return to /spec.
```

**Speculative framework artifacts**

```
Bad:  Plan adds a service interface, a factory, and a test helper
      "because that's the usual structure"
Good: Every new layer or support artifact cites its source: the
      approved spec, a project rule, a repository precedent, or a
      stated new technical decision recorded in the plan.
```

**Manufactured parallelism**

```
Bad:  6 workstreams because 6 tasks "could run in parallel"
Good: 1 workstream; genuinely independent contexts split off only
      per Step 4. "Parallelizable" is metadata for /build, not a
      command to spend concurrency.
```

Also:

- Do not implement while planning
- Do not copy the spec into the plan, or duplicate repository-wide conventions documented elsewhere
- Do not hide unresolved technical risks inside implementation tasks
- Do not contradict, weaken, strengthen, omit, or reinterpret approved spec behavior; return new behavioral decisions to `/spec`

## Plan Document Template

Use `../../references/templates/plan.md` — it adds a Technical Approach (the
HOW a task list alone does not express) and a plan-level Verification Strategy,
since task-focused checks do not prove integrated behavior.

Plan approval state, spec-revision pinning, id stability (`REQ`/`DEC` in the
spec; `TD`/`T`/`CP` in the plan, never renumbered after approval), closure
checks, and spike rules: `../../references/plan-quality-gates.md`.

## Parallelization Opportunities

Planning may identify independent workstreams; it does not authorize simultaneous
writing by itself. `/build` owns the execution/concurrency policy.

- **Potentially parallel:** genuinely independent, dependency-ready workstreams
  with no shared mutable state.
- **Parallel writing requires isolation:** each writing executor needs its own
  worktree/branch (or equivalent isolated checkout). Never infer safety merely
  from non-overlapping source files.
- **Must be sequential:** dependency chains within one implementation context,
  shared mutable state, migrations whose order matters, or work that must consume
  an unfinished contract.
- **Needs coordination:** workstreams sharing an API/interface contract — define
  and stabilize the contract first, preserve an explicit dependency/checkpoint,
  then parallelize only dependency-ready consumers/implementations.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "I'll figure it out as I go" | That's how you end up with a tangled mess and rework. 10 minutes of planning saves hours. |
| "The tasks are obvious" | Write them down anyway. Explicit tasks surface hidden dependencies and forgotten edge cases. |
| "Planning is overhead" | Planning is the task. Implementation without a plan is just typing. |
| "I can hold it all in my head" | Context windows are finite. Written plans survive session boundaries and compaction. |

## Red Flags

- Starting implementation without a written task list
- Writing `docs/tasks/[TICKET]-todo.md` when the project has designated an external tracker (or scattering tasks across both)
- Tasks that say "implement the feature" without acceptance criteria
- No verification steps in the plan
- All tasks are XL-sized
- A risky schema decision, new contract, or workstream integration point with no checkpoint
- Dependency order isn't considered

## Verification

Before the plan is ready for `/build`, confirm every item. The first block is a
self-check; the second block requires the human.

Agent self-check:

- [ ] No task exists solely because an architectural layer exists, unless it is a justified foundation (independently verifiable AND consumed by 2+ downstream tasks)
- [ ] Every task has explicit acceptance criteria
- [ ] Every task has a verification step
- [ ] Dependencies are explicit and correctly ordered
- [ ] Every task has a workstream
- [ ] Every task carries context pointers for each project rule, precedent, contract, or invariant that applies to its area
- [ ] Related tasks share a workstream unless a stable contract separates materially different implementation contexts
- [ ] Contract-separated workstreams retain explicit dependencies and a contract checkpoint
- [ ] Task boundaries follow coherent behavior rather than arbitrary file counts
- [ ] Production implementation and its proving tests share one delivery task unless the test work is independently verifiable before that change
- [ ] Every L/XL task is split, or its cohesion justification is recorded in the plan
- [ ] High-risk decisions are addressed early enough to fail fast
- [ ] A checkpoint exists at each risk point listed in Step 6 that occurs in this plan
- [ ] The plan does not unnecessarily duplicate the spec
- [ ] The plan contains no production implementation
- [ ] Every planned behavior and acceptance criterion traces to the approved spec
- [ ] The spec's `Status` header read `Approved` on disk before planning began, the spec is committed, and the commit that last touched it is recorded as the plan's `Spec revision`
- [ ] The plan states a Technical Approach, and a Verification Strategy whose commands come from repository evidence
- [ ] Every risk mitigation names the task or checkpoint that performs it
- [ ] Conditional sections are present when they apply, omitted rather than N/A when they don't
- [ ] Every spec requirement maps to at least one task and every task names at least one `REQ-###`; the plan reports `Unmapped requirements: None` and `Orphan tasks: None`
- [ ] The plan does not contradict, weaken, or strengthen the approved spec

Human gate (do not self-certify these):

- [ ] The human has reviewed and approved the plan
- [ ] The final handoff is `Ready for /build`

## See Also

Acceptance criteria are per-task and answer:

> Did this increment deliver the intended behavior?

Project-wide completion standards remain defined in
`../../references/definition-of-done.md`.
