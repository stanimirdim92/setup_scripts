---
name: spec-driven-development
description: Creates specs before coding. Use when starting a new project, feature, or significant change and no specification exists yet. Use when requirements are unclear, ambiguous, or only exist as a vague idea. Use when a single requirement spans several independently testable capabilities and needs decomposing into a capability map of modules before specifying.
---

# Spec-Driven Development

## Overview

Write a structured specification before writing any code. The spec is the shared source of truth between you and the human engineer — it defines what we're building, why, and how we'll know it's done. Code without a spec is guessing.

## When to Use

- Starting a new project or feature
- Requirements are ambiguous or incomplete
- The change touches multiple files or modules
- You're about to make an architectural decision
- The task would take more than 30 minutes to implement

**When NOT to use:** Single-line fixes, typo corrections, or changes where requirements are unambiguous and self-contained.

## The Gated Workflow

Spec-driven development has four phases, preceded by a scope check (Phase 0) that activates only when one request bundles several independently testable capabilities. Do not advance to the next phase until the current one is validated.

```
SPECIFY ──→ PLAN ──→ TASKS ──→ IMPLEMENT
   │          │        │          │
   ▼          ▼        ▼          ▼
 Human      Human    Human      Human
 reviews    reviews  reviews    reviews
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

**Then recurse per module.** Run Specify → Plan → Tasks → Implement for each module in dependency order. Each module gets its own spec, scoped to that module's objective, boundaries, and success criteria. Save the approved map at the project root and each module's spec alongside it, named by module id (`SPEC-identity.md`, `SPEC-billing.md`) — the map, not filename guessing, is the index of what exists.

### Phase 1: Specify

Start with a high-level vision. Ask the human clarifying questions until requirements are concrete.

**Surface assumptions immediately.** Before writing any spec content, list what you're assuming:

```
ASSUMPTIONS I'M MAKING:
1. This is a web application (not native mobile)
2. Authentication uses session-based cookies (not JWT)
3. The database is MySQL or PostgreSQL
4. We're targeting modern browsers only
→ Correct me now or I'll proceed with these.
```

Don't silently fill in ambiguous requirements. The spec's entire purpose is to surface misunderstandings *before* code gets written — assumptions are the most dangerous form of misunderstanding.

### Repository Recon Before Specifying

Before naming files, classes, tables, architectural layers, test helpers, or
implementation patterns, discover and read the project's instruction sources
that apply to the feature.

Common locations include:

- `CLAUDE.md`
- `AGENTS.md`
- `.ai/rules/*.md`
- module-local instruction files
- architecture/design documentation
- repository contribution or development guides

Do not assume these exact paths exist; discover the project's actual instruction
sources.

Then inspect the relevant repository area and closest sibling implementations.

Look for:

- sibling features solving a similar problem;
- naming conventions for models, tables, services, repositories, controllers,
  components, and tests;
- the actual architectural chain used by the owning module;
- existing test setup and fixture/factory conventions;
- how data crosses boundaries such as Controller → Service;
- existing registration/binding/routing patterns.

Use evidence in this order:

1. Explicit user requirements and approved feature-specific decisions.
2. Applicable project-local rules.
3. Existing patterns in the owning module or closest sibling feature.
4. Existing repository-wide conventions.
5. Framework conventions only when the repository provides no applicable precedent.

Repository precedent is a strong default, not a prohibition against deliberate
change.

When no precedent exists:

- if an explicit user requirement or approved feature-specific decision requires
  a new layer, file, pattern, or abstraction, include it and label it clearly as
  a **new feature-specific decision**;
- if no requirement or decision justifies it, do not invent it merely because it
  is common framework practice;
- if the evidence is mixed or the tradeoff is material and unresolved, surface
  the choice instead of silently deciding.

Examples:

- A Factory may be introduced when comparable tests use factories, the feature
  needs reusable test/seed data, or it is an explicit feature decision.
- A DTO/Data layer may be introduced when project rules require it, repository
  precedent supports it, or an explicit feature decision accepts the additional
  boundary/complexity for a concrete benefit.
- Do not derive class/table names solely from ticket wording when sibling
  resources establish a different ownership/naming convention.

Do not confuse **no precedent** with **forbidden**. New patterns are acceptable
when they are intentional, justified, and identified as new rather than
misrepresented as existing repository convention.

**Write a spec document covering these six core areas:**

1. **Objective** — What are we building and why? Who is the user? What does success look like?

2. **Commands** — Full executable commands with flags, not just tool names.
   ```
   Build: yarn run build
   Lint: yarn run lint:fix
   Dev: yarn run dev
   ```

3. **Project Structure** — Where source code lives, where tests go, where docs belong.

- Derive names and locations from repository evidence, especially sibling features in the owning module.

For each proposed new path, be able to answer:
- What existing pattern supports this path/name?
- Is this required by the feature, or merely a framework convention?

```
vendor/           → framework source code
resources/components → React components
Modules/<MODULE>/       → App modules 
app/           → Default app code 
tests/         → Unit and integration tests for frontend and backend
e2e/           → End-to-end tests
docs/          → Documentation
```

4. **Code Style** — One real code snippet showing your style beats three paragraphs describing it. Include naming conventions, formatting rules, and examples of good output.


5. **Testing Strategy** — Define how the feature will be proven correct.

Include:

- the repository's existing test framework and test locations;
- the important behaviors and acceptance criteria that require automated verification;
- validation, error, edge, and regression cases that materially affect correctness;
- the appropriate test level for each concern (unit, integration/feature, E2E, persistence/DB, manual);
- invariants that must be tested below the application layer when the database, queue, cache, or another infrastructure boundary enforces correctness;
- the state transitions required to establish, preserve, transfer, or release important invariants;
- any behavior that cannot reasonably be automated and therefore needs explicit manual verification.

When a requirement defines an invariant, derive the transitions needed to keep it
true instead of testing only the obvious CRUD operations. Check the transitions
that apply, such as:

- creation from an empty state;
- creation when related state already exists;
- updates that establish or transfer the invariant;
- deletion of the entity currently satisfying the invariant;
- deletion of the final remaining entity;
- concurrent writes when the invariant spans multiple rows, resources, or processes.

For each invariant, distinguish which layer guarantees which part of it. For
example, a persistence constraint may guarantee **at most one**, while
application behavior is still responsible for guaranteeing **at least one when
applicable**.

Prefer behavior-driven coverage over layer-driven coverage.

Do not require a unit test merely because a service/class exists, and do not
introduce factories, mocks, test helpers, or a new testing framework unless
repository precedent or the feature itself requires them.

The strategy should make it possible for `/plan`, `/build`, and `/test` to
answer: **what evidence proves this feature works?**
Example:

- invalid input → API/feature test
- business rule spanning persistence → integration/feature test
- DB uniqueness or constraint invariant → persistence-level test
- critical user journey → E2E test
- UI behavior with no existing automation precedent → explicit manual verification

6. **Boundaries** — Three-tier system:
    - **Always do:** Run tests before commits, follow naming conventions, validate inputs
    - **Ask first:** Database schema changes, adding dependencies, changing CI config
    - **Never do:** Commit secrets, edit vendor directories, remove failing tests without approval

### Specification Closure

Before presenting a spec for approval, perform an internal-consistency pass across
the entire document. Compare the objective, requirements, data model,
implementation guidance, testing strategy, boundaries, success criteria, and
open questions. The same behavior must not be described differently in two
sections.

At minimum, reconcile:

- cardinality and state invariants against empty, populated, and final-deletion
  states;
- pagination, ordering, filtering, validation, authorization, and error
  semantics wherever they appear;
- implementation guidance against every acceptance criterion and planned test;
- newly confirmed decisions against older assumptions or wording;
- schema fields against their observable lifecycle behavior.

Do not call a spec ready while a material contradiction or unresolved choice
remains. Surface the conflict, update the spec after the decision, and rerun the
closure pass.

### Prove Invariant Mechanisms

Naming a transaction, lock, constraint, retry, or "last write wins" policy is not
proof that an invariant holds. For every cross-row, cross-resource, or concurrent
invariant, explain why the chosen mechanism covers every transition and writer.

The proof must identify:

- the precise invariant, including zero/empty-state semantics;
- every operation that can establish, transfer, violate, or release it;
- the common serialization point or persistence constraint;
- how the mechanism works when no child/entity row exists yet;
- what the application guarantees and what infrastructure guarantees;
- the verification evidence, including a lower-level constraint test when
  infrastructure participates in correctness.

If the mechanism cannot be shown to serialize or reject all conflicting writes,
the invariant design is unresolved. A transaction alone does not imply a common
lock or uniqueness guarantee.

### Define Data Lifecycle Semantics

When the schema or existing model contains a deletion marker, soft-delete
timestamp, tombstone, archival flag, status, or equivalent lifecycle field, the
spec must define what "delete" means. State whether deletion is hard, soft,
archival, or another transition, and define how deleted records affect reads,
uniqueness, relationships, restoration, invariant calculations, retention, and
tests. Do not propose a deletion marker while leaving deletion behavior as an
implementation detail.

**Spec template:** see `../../references/templates/spec.md`.

**Reframe instructions as success criteria.** When receiving vague requirements, translate them into concrete conditions:

```
REQUIREMENT: "Make the dashboard faster"

REFRAMED SUCCESS CRITERIA:
- Dashboard LCP < 2.5s on 4G connection
- Initial data load completes in < 500ms
- No layout shift during load (CLS < 0.1)
→ Are these the right targets?
```

This lets you loop, retry, and problem-solve toward a clear goal rather than guessing what "faster" means.

### Phase 2: Plan

With the validated spec, generate a technical implementation plan:

1. Identify the major components and their dependencies
2. Determine the implementation order (what must be built first)
3. Note risks and mitigation strategies
4. Identify what can be built in parallel vs. what must be sequential
5. Define verification checkpoints between phases

> Follow `planning-and-task-breakdown` for the dependency-graph mapping and vertical-slicing mechanics behind these steps; it is the canonical source. The bullets above are a lightweight summary; if they ever diverge, `planning-and-task-breakdown` takes precedence.
>
> **Output convention:** Save the plan to `docs/tasks/[TICKET]-plan.md` and record the task list in the task list target defined by `planning-and-task-breakdown` (default `docs/tasks/[TICKET]-todo.md`; projects may designate an external tracker instead). Create `tasks/` if it does not exist. Downstream commands (`/build`, etc.) expect these defaults.

The plan should be reviewable: the human should be able to read it and say "yes, that's the right approach" or "no, change X."

### Phase 3: Tasks

Break the plan into discrete, implementable tasks:

- Each task should be completable in a single focused session
- Each task has explicit acceptance criteria
- Each task includes a verification step (test, build, manual check)
- Tasks are ordered by dependency, not by perceived importance

> Follow `planning-and-task-breakdown` for the full task-sizing and dependency-ordering mechanics; it is the canonical source. The template below is a lightweight inline form; if they ever diverge, `planning-and-task-breakdown` takes precedence.

**Task template:** see `../../references/templates/task.md`.

### Phase 4: Implement

Execute tasks one at a time following `skills/incremental-implementation/SKILL.md` (`incremental-implementation`) and `skills/test-driven-development/SKILL.md` (`test-driven-development`). Use `skills/context-engineering/SKILL.md` (`context-engineering`) to load the right spec sections and source files at each step rather than flooding the agent with the entire spec.

## Keeping the Spec Alive

The spec is a living document, not a one-time artifact:

- **Update when decisions change** — If you discover the data model needs to change, update the spec first, then implement.
- **Update when scope changes** — Features added or cut should be reflected in the spec.
- **Commit the spec** — The spec belongs in version control alongside the code.
- **Reference the spec in PRs** — Link back to the spec section that each PR implements.

## Guardrails

- Do not implement the feature during specification.
- Code snippets are allowed only when they capture a non-obvious technical
  decision or existing pattern that materially helps planning.
- Prefer minimal snippets over complete classes or CRUD implementations.
- Do not silently resolve material ambiguity.
- Do not produce one spec for independently shippable capabilities.
- Do not repeat repository-wide conventions in a feature spec.
- A 15-minute spec prevents hours of rework. Waterfall in 15 minutes beats debugging in 15 hours.
- Do not invent repository conventions from framework conventions. Every
  proposed layer/file/pattern in Project Structure or Existing Patterns must be
  backed by repository evidence, an explicit project rule, an explicit user
  requirement, or clearly labeled as a justified new feature-specific decision.
- Absence of repository precedent does not forbid a deliberate new pattern.
  When introducing one, state the reason/tradeoff and do not present it as an
  existing convention.
- Ticket/domain wording does not automatically determine code identifiers. Derive naming from the owning module and closest repository precedents.
- Do not approve a spec until its objective, requirements, implementation
  guidance, tests, success criteria, and lifecycle semantics agree.
- Do not claim an invariant is concurrency-safe without a mechanism proof that
  covers every writer and the empty-state transition.

## Verification

Before considering the specification ready for implementation, confirm:

- [ ] The spec covers all six core areas
- [ ] The human has reviewed and approved the spec
- [ ] Success criteria are specific and testable
- [ ] Boundaries (Always/Ask First/Never) are defined
- [ ] The spec is saved to a file in the repository
- [ ] If the request bundles several independently testable capabilities, a capability map (module ids, dependency direction, build order) was approved before any module spec was written
- [ ] Every module spec traces to a module id in the approved map
- [ ] An internal-consistency pass found no contradictory behavior across sections
- [ ] Every important invariant has precise empty-state semantics, complete state transitions, layer ownership, and a mechanism proof
- [ ] Any deletion marker or soft-delete field has explicit deletion, read, restoration, uniqueness, retention, and invariant semantics
