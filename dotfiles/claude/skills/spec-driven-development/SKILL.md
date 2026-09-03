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
gets its own spec, scoped to that module's objective, boundaries, and success criteria. 
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
Ask, record the decision in the spec, remove the block, and rerun the closure
pass. When the resolution materially changed specified behavior — a product,
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

### Repository Recon Before Specifying

Before naming files, classes, tables, layers, test helpers, or implementation
patterns, work from the `repo-recon` report `/spec` dispatched — do not survey
the repository in this context.

Use evidence in this order:

1. Explicit user requirements and approved feature-specific decisions.
2. Applicable project-local rules.
3. Existing patterns in the owning module or closest sibling feature.
4. Existing repository-wide conventions.
5. Framework conventions only when the repository provides no applicable
   precedent.

Repository precedent is a strong default, not a prohibition against deliberate
change.

Two consequences that bind this skill: the report's **No precedent found for**
entries must be justified explicitly in the spec rather than presented as the
obvious choice, and a choice with mixed evidence — or one that would change an
acceptance criterion, schema, public contract or lifecycle behavior — becomes an
`OPEN QUESTION` block instead of a silent decision.

How to use the report, and the rules for deciding when there is no precedent at
all: `../../references/repository-precedent.md`.

**State what this change does to behavior that already exists.** Every spec
carries a `Change kind` (New/Modify/Remove/Rename/Bugfix); every spec whose kind
is not `New` carries a `## Change Impact` section naming behavior added,
modified, removed, renamed, and — the load-bearing one — **explicitly
preserved**, each against a `REQ-###` or contract rather than an area. Naming
the adjacent behavior that must not change turns the characteristic brownfield
failure, fixing one path while silently altering its neighbour, into a testable
requirement instead of a hope. This is delta vocabulary inside one spec, not the
delta *storage* model that
`docs/adr/0040-openspec-conventions-adopted.md` rejected and `docs/IDEAS.md`
still parks.

**Write a spec document covering these six core areas:**

1. **Objective** — What are we building and why? Who is the user? What does
   success look like? When the request could plausibly be read wider than
   intended, record the relevant exclusions here ("out of scope: …") so scope
   is bounded by decision, not by omission.

2. **Commands** — Full executable commands with flags, not just tool names.
   Every command comes from repository evidence (the recon report, package
   manifests, CI config) — never guessed. Distinguish read-only checks (test,
   lint, typecheck) from commands that modify files or dependencies (install,
   update, codegen).
   ```
   Install FE: yarn install            (modifies node_modules)
   Install BE: composer install            (modifies node_modules)
   Build:   yarn run build          (writes build output)
   Test:    yarn run test           (check)
   Lint:    yarn run lint:fix       (modifies files; lint alone is the check)
   Dev:     yarn run dev
   Format:  yarn run format or format:write
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

The pass also checks completeness and scope, not only consistency — a spec can
be internally consistent while omitting part of the request:

- every behavior the request asked for appears in a `### Requirement:` with its
  scenarios, or in a recorded exclusion under Objective;
- every behavior the spec adds beyond the request traces to an explicit
  requirement or an approved decision, not to silent scope growth.

**Then test the requirements themselves, as prose that can be wrong.** Run
`../../references/spec-quality-gates.md` §1 — measurability, scenario coverage,
applicable operational concerns, validated assumptions, no duplicate or
conflicting requirements. It is a pass over this document, not a second
artifact.

Do not present a spec for approval while any contradiction between two sections
or any `OPEN QUESTION` block remains. Surface the conflict, update the spec
after the decision, and rerun the closure pass.

### Invariants and Data Lifecycle

Two gates the closure pass enforces, both in
`../../references/spec-quality-gates.md`:

- **§4 Invariant mechanism proof.** Naming a transaction, lock, constraint or
  retry is not proof. Every cross-row, cross-resource or concurrent invariant
  needs a proof covering each transition and writer, its empty-state semantics,
  the common serialization point, and which layer guarantees which part.
- **§5 Data lifecycle semantics.** A deletion marker, soft-delete timestamp,
  tombstone, archival flag or status field obliges the spec to define what
  "delete" means — for reads, uniqueness, relationships, restoration, invariant
  calculations, retention and tests. Never propose the field and leave the
  behavior as an implementation detail.

Neither is satisfied by asserting the mechanism exists.

**Spec template:** see `../../references/templates/spec.md`. For a defect use
`../../references/templates/bugfix-spec.md` instead — it leads with reproduction
evidence and makes preserved behavior its own requirement. It does not lower the
bar for when a bug needs a spec ("When NOT to use" still governs), and root
cause and fix mechanism stay in `/plan`.

**Compact specs for bounded, low-risk work.** When the change introduces no new
architecture or pattern, no public contract or schema change, no cross-row or
concurrent invariant, and no data-lifecycle field, the spec may use only: the
status header, Objective, Change Impact, Requirements (the `### Requirement:` /
`#### Scenario:` headings and `REQ-###` ids are still load-bearing), Testing
Strategy, Boundaries, and Success Criteria — the remaining template sections may
be omitted rather than filled with N/A. The status header and the ids are never
optional — they are what the downstream gates read — and bounded work is where
brownfield changes most often land, so Change Impact stays too. The
closure rules still apply in full: no `OPEN QUESTION` block and no
cross-section contradiction at approval. If drafting surfaces any of the
excluded concerns, upgrade to the full template — the compact form is
proportionality for genuinely bounded work, never a way past the invariant,
concurrency, or lifecycle gates.

**Requirement ids are mandatory** for any spec that will enter `/plan`: a
stable id inside the existing heading form (`### Requirement: REQ-001 — Title`)
plus a `Source:` line. They are what `/plan`, `/test`, `/review` and `/ship`
trace coverage and evidence against, so they are assigned once and never
renumbered. Rules and the per-stage chain:
`../../references/spec-quality-gates.md` §3.

**Navigation for long specs.** When a spec grows past what one screen of
reading can hold (many requirements, several invariants), add a short index at
the top — section links with a one-line description each. Link related
contracts and invariants from the requirements they protect. The index points;
it never restates — a summary that paraphrases the requirements is a second
copy that will drift.

**Reframe instructions as success criteria.** When receiving vague requirements, translate them into concrete, measurable conditions:

```
REQUIREMENT: "Make the dashboard faster"

REFRAMED SUCCESS CRITERIA:
- Dashboard LCP < 2.5s on 4G connection
- Initial data load completes in < 500ms
- No layout shift during load (CLS < 0.1)
→ Are these the right targets?
```

This lets you loop, retry, and problem-solve toward a clear goal rather than guessing what "faster" means. (The numbers above are illustrative, not defaults — each target comes from the actual requirement.)

Where prose alone leaves a scenario ambiguous, add representative inputs and
their expected outcomes to the scenario — one concrete example settles what a
sentence cannot. A performance criterion is complete only when it names the
metric, the threshold, the workload, the environment, and how it will be
measured; "fast" or a bare number with no measurement conditions is not
testable.

## Output Files

- Single-capability spec: `docs/specs/[TICKET]-SPEC.md` (create `docs/specs/` if needed)
- Multi-capability initiative: `docs/specs/[TICKET]-CAPABILITY-MAP.md` with `[TICKET]-SPEC-<module-id>.md` files alongside it — the ticket prefix keeps two initiatives that touch the same module from targeting the same file

Projects may designate different locations in their instruction sources; the
project rule wins over these defaults.

### Handoff after specification

After the human approves the closed specification, stop. Planning and task
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
requirement, rerun the closure pass, and obtain re-approval before the work
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
human approval — never on its own judgment, and a passing closure pass is not
approval. Transitions and who may set them:
`../../references/spec-quality-gates.md` §2.

Any edit to an approved spec that changes behavior — a requirement, scenario,
schema, contract, invariant, boundary, or Change Impact entry — follows the same
path as a `SPEC CONFLICT`: set `Needs reapproval`, identify the affected
requirement ids, rerun the closure pass, and obtain re-approval before
downstream work resumes on the changed sections.
Editorial corrections (typos, formatting, clarified wording that changes no
behavior) do not reopen approval. Never weaken a valid requirement because an
implementation fails to meet it — a failing implementation is a finding
against the code or a decision for the human, not grounds to move the goal.

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

- [ ] The spec covers all six core areas (areas 2–4 by reference plus delta in feature/module specs), or qualifies for the compact form and covers its required sections with none of the excluded concerns present
- [ ] The status header is present and complete, and `Status` is `Draft` — `Approved` is the human's to grant, not this checklist's
- [ ] Every requirement has a `REQ-###` id and a `Source:` line; no id was renumbered or reused
- [ ] `Change kind` is set, and a `Change Impact` section exists whenever it is not `New`, including its explicitly-preserved-behavior entry
- [ ] Every material product/domain/contract/lifecycle decision made while drafting is recorded as a `DEC-###`, or the section reads "None"
- [ ] A defect spec uses the bugfix template, with reproduction evidence concrete enough to write a failing test from
- [ ] No requirement rests on an unmeasurable adjective, and applicable operational concerns are requirements or recorded exclusions rather than silence
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
