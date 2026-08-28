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
- The change touches multiple files or modules
- You're about to make an architectural decision
- The change would decompose into more than one task in `/plan`

**When NOT to use:** Single-line fixes, typo corrections, or changes where requirements are unambiguous AND the change is self-contained in one file. When the two lists conflict (e.g., a large but unambiguous change), write the spec — scope wins over clarity.

## The Gated Workflow

The harness has these user-invoked stages:

```text
DEFINE      PLAN       BUILD       REVIEW       SHIP
/spec  ->   /plan  ->  /build  ->  /review  ->  /ship
                              \
                               -> /test -> /review
                                  VERIFY, when required
```

This skill owns the capability scope check (Phase 0) and DEFINE/specification
only. `/plan` owns the implementation plan and task breakdown, `/build` owns TDD
implementation, `/review` owns code quality findings and decides whether
independent verification is required (`../../references/verification-triggers.md`),
`/test` owns that verification when triggered, and `/ship` owns the
release-readiness verdict. Do not advance or execute a downstream stage from
this skill.

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
gets its own spec, scoped to that module's objective, boundaries, and success
criteria. Save the approved map at `docs/specs/[TICKET]-CAPABILITY-MAP.md` and
each module's spec alongside it, named by module id (`SPEC-identity.md`,
`SPEC-billing.md`) — the map, not filename guessing, is the index of what exists.
After specification approval, hand the module to `/plan`; do not plan or
implement it inside this skill.

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
Ask, record the decision in the spec, remove the block, and rerun the closure
pass. Treat a choice as needing an `OPEN QUESTION` block when picking the wrong
option would change an acceptance criterion, a schema, a public contract, or
data lifecycle behavior; choices below that bar (internal naming, private
helper structure) may be decided directly.

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

Do not assume the above paths exist; discover the project's actual instruction sources.

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
- if the evidence is mixed or the choice would change an acceptance criterion,
  schema, public contract, or lifecycle behavior, raise an `OPEN QUESTION`
  block instead of silently deciding.

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

Areas 2–4 describe repository-wide facts. In a feature or module spec, cover
them **by reference plus delta**: link the authoritative repo doc (or state
"per `CLAUDE.md`") and list only what this feature adds or changes. Write them
out in full only for a new project where no such doc exists yet. This is how
"covers all six areas" and "do not repeat repository-wide conventions" are both
satisfied.

1. **Objective** — What are we building and why? Who is the user? What does success look like?

2. **Commands** — Full executable commands with flags, not just tool names.
   ```
   Install: yarn install or composer install|update -o
   Build: yarn run build
   Lint: yarn run lint:fix
   Dev: yarn run dev
   ```

3. **Project Structure** — Where source code lives, where tests go, where docs belong.
```
vendor/              → framework source code
resources/components → React components
Modules/<MODULE>/    → App modules
app/                 → Default app code
tests/               → Unit and integration tests
e2e/                 → End-to-end tests
docs/                → Documentation
```

4. **Code Style** — One real code snippet showing your style beats three paragraphs describing it. Include naming conventions, formatting rules, and examples of good output.

5. **Testing Strategy** — Define how the feature will be proven correct.

Include:

- the repository's existing test framework and test locations;
- automated verification for every behavior whose failure would produce wrong
  data, a broken user journey, an authorization gap, or a violated invariant —
  when in doubt whether a case clears this bar, include it; a redundant test
  costs seconds, a missing one costs an incident;
- validation, error, edge, and regression cases meeting the same bar;
- the appropriate test level for each concern (unit, integration/feature, E2E, persistence/DB, manual);
- invariants that must be tested below the application layer when the database, queue, cache, or another infrastructure boundary enforces correctness;
- the state transitions required to establish, preserve, transfer, or release important invariants;
- any behavior that cannot reasonably be automated and therefore needs explicit manual verification.

When a requirement defines an invariant, derive the transitions needed to keep it
true instead of testing only the obvious CRUD operations. Check every transition that applies:

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

Before presenting a spec for human approval, perform an internal-consistency pass across
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

Do not present a spec for approval while any contradiction between two sections
or any `OPEN QUESTION` block remains. Surface the conflict, update the spec
after the decision, and rerun the closure pass.

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

**Reframe instructions as success criteria.** When receiving vague requirements, translate them into concrete, measurable conditions:

```
REQUIREMENT: "Make the dashboard faster"

REFRAMED SUCCESS CRITERIA:
- Dashboard LCP < 2.5s on 4G connection
- Initial data load completes in < 500ms
- No layout shift during load (CLS < 0.1)
→ Are these the right targets?
```

This lets you loop, retry, and problem-solve toward a clear goal rather than guessing what "faster" means.

## Output Files

- Single-capability spec: `docs/specs/[TICKET]-spec.md` (create `docs/specs/` if needed)
- Multi-capability initiative: `docs/specs/[TICKET]-CAPABILITY-MAP.md` with `SPEC-<module-id>.md` files alongside it

Projects may designate different locations in their instruction sources; the
project rule wins over these defaults.

### Handoff after specification

After the human approves the closed specification, stop. Planning and task
decomposition belong to `/plan`, which invokes `planning-and-task-breakdown` and
writes the canonical plan/todo artifacts. Do not execute that methodology inside
this skill.

After the human approves the plan, implementation belongs to `/build`.
`/build` selects executor skills and dispatches workstreams; the user then invokes
`/test`, `/review`, and `/ship` sequentially. Do not write production code,
dispatch executors, or run implementation phases from `/spec`.

**Handling a returned `SPEC CONFLICT`.** When `/plan` (or a later stage) returns
a `SPEC CONFLICT`, treat it as a spec change request: raise the decision with
the human, record the resolution in the spec, remove or update the conflicting
requirement, rerun the closure pass, and obtain re-approval before the work
returns to `/plan`.

## Keeping the Spec Alive

The spec is a living document, not a one-time artifact:

- **Update when decisions change** — If you discover the data model needs to change, update the spec first, then implement.
- **Update when scope changes** — Features added or cut should be reflected in the spec.
- **Commit the spec** — The spec belongs in version control alongside the code.
- **Reference the spec in PRs** — Link back to the spec section that each PR implements.

## Guardrails

The four most common specification failures, shown as bad/good pairs:

**Silently resolving ambiguity**

```
Bad:  Requirement says "users can share reports" → spec quietly
      decides link-sharing with public URLs
Good: OPEN QUESTION: Sharing model — link-based (public URL) vs
      invite-based (account required)? → decision before approval
```

**Inventing conventions from framework practice**

```
Bad:  Spec's Project Structure adds app/DTOs/ and a service
      interface layer "because that's standard Laravel/Spring/etc."
Good: Every proposed layer/file/pattern cites repository evidence,
      a project rule, an explicit user requirement — or is labeled
      "new feature-specific decision" with its tradeoff stated
```

**One spec for independently shippable capabilities**

```
Bad:  One 40-page spec covering identity + billing + reporting
Good: Phase 0 capability map, approved first; one spec per module
      in dependency order
```

**Implementation smuggled into the spec**

```
Bad:  Spec contains a complete controller and CRUD service class
Good: Spec contains a minimal snippet only where it captures a
      non-obvious technical decision or an existing pattern the
      planner would otherwise miss
```

Also:

- Do not implement the feature during specification.
- Do not repeat repository-wide conventions in a feature spec — reference them (see the reference-plus-delta rule for areas 2–4).
- Ticket/domain wording does not automatically determine code identifiers; derive naming from the owning module and closest repository precedents.
- Absence of repository precedent does not forbid a deliberate new pattern — state the reason/tradeoff and never present it as an existing convention.
- Do not present a spec for approval while any cross-section contradiction or `OPEN QUESTION` block remains.
- Do not claim an invariant is concurrency-safe without a mechanism proof that covers every writer and the empty-state transition.

## Verification

Confirm every item. The first block is a self-check; the second block requires
the human.

Agent self-check:

- [ ] The spec covers all six core areas (areas 2–4 by reference plus delta in feature/module specs)
- [ ] Success criteria are specific and testable
- [ ] Boundaries (Always/Ask First/Never) are defined
- [ ] The spec is saved per Output Files (or the project-designated location)
- [ ] If the request bundles several independently testable capabilities, a capability map (module ids, dependency direction, build order) was approved before any module spec was written
- [ ] Every module spec traces to a module id in the approved map
- [ ] An internal-consistency pass found no contradictory behavior across sections
- [ ] No `OPEN QUESTION` block remains in the spec
- [ ] Every invariant stated in the requirements or enforced by the schema has precise empty-state semantics, complete state transitions, layer ownership, and a mechanism proof
- [ ] Any deletion marker or soft-delete field has explicit deletion, read, restoration, uniqueness, retention, and invariant semantics

Human gate (do not self-certify these):

- [ ] The human has reviewed and approved the capability map (when one exists)
- [ ] The human has reviewed and approved the spec
