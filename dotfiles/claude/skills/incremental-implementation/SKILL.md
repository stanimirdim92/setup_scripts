---
name: incremental-implementation
description: Delivers changes in small, verifiable increments. Use when implementing multi-file features, refactors, or tasks that need safe slicing and commit boundaries.
---

# Incremental Implementation

## Overview

Build in small, coherent slices.

Each increment should leave the repository in a valid state and be small enough
to understand, verify, and commit independently.

This skill owns:

- slice boundaries
- scope discipline
- keeping the repository green
- verification cadence
- commit cadence

`test-driven-development` owns the implementation loop **inside behavioral
slices**.

## When to Use

Use when:

- implementing a multi-file change
- building a feature from a task breakdown
- refactoring existing code
- a task is too large to implement safely in one pass
- risk or dependency order makes incremental landing valuable

**When NOT to use:** Obvious, localized changes whose implementation and
verification are already minimal.

## Increment Cycle

### Behavioral slice

Use TDD inside each behavioral slice:

```text
RED
 ↓
Implement minimum behavior
 ↓
GREEN
 ↓
Refactor
 ↓
Verify increment
 ↓
Commit
 ↓
Next slice
```

1. **RED** — write or identify the test for the intended behavior and verify it
   fails for the expected reason.
2. **Implement** — write the minimum production code needed to satisfy the test.
3. **GREEN** — run the focused test and verify it passes.
4. **Refactor** — improve structure while keeping the test green.
5. **Verify** — run the broader checks earned by the slice.
6. **Commit** — save the coherent, verified increment.
7. Move to the next slice.

Do not reinterpret this as "implement first, test later."

For detailed test selection and Red-Green-Refactor rules, follow
`test-driven-development`.

### Non-behavioral slice

For documentation, static configuration, generated artifacts, or another change
where TDD does not apply:

```text
Implement
 ↓
Verify
 ↓
Commit
 ↓
Next slice
```

Use the repository's appropriate validation for that artifact.

## Slicing Strategies

### Vertical slices

Prefer a complete behavior over arbitrary architectural layers.

Example:

```text
Slice 1: User can create a task
Slice 2: User can list tasks
Slice 3: User can edit a task
Slice 4: User can delete a task
```

A slice may cross schema, backend, API, UI, and tests when that is the smallest
coherent behavior.

### Foundation first when genuinely shared

A shared foundation may be its own increment when several later slices depend on
it.

Examples:

- schema invariant
- shared API contract
- reusable migration primitive
- common type/interface required by independent consumers

Do not manufacture a foundation task merely to keep layers separate.

### Contract-first

When independent consumers need a shared contract:

```text
Contract
  ↓
Backend implementation
Frontend implementation
  ↓
Integration
```

Define the contract before treating dependent implementations as independent.

### Risk-first

Validate expensive uncertainty early.

Examples:

- external API feasibility
- migration safety
- concurrency invariant
- framework limitation
- performance-sensitive query shape

Fail before building low-risk dependent work.

## Implementation Rules

### Simplicity first

Implement the simplest design that satisfies the current task.

Avoid:

- speculative abstractions
- generic frameworks for one use
- configuration systems for a fixed behavior
- future-proofing with no current requirement

Prefer clear duplication over premature abstraction when the shared concept is
not yet stable.

### Scope discipline

Implement only what the current task requires.

Do not opportunistically:

- clean unrelated code
- modernize nearby syntax
- refactor unrelated modules
- add unrequested features
- remove code you do not understand

If nearby work is worth doing, report it separately.

### One logical increment at a time

Each increment should represent one coherent responsibility.

Separate unrelated:

- behavior changes
- refactors
- dependency changes
- formatting-only changes
- tooling/configuration changes

Small cleanup directly required by the behavior may stay with it.

### Keep the repository valid

Do not knowingly leave the repository broken between committed increments.

Run focused verification during the slice.

Run broader verification when the increment affects shared or risky surfaces
such as:

- schema/migrations
- shared libraries
- configuration
- public contracts
- cross-service boundaries

Do not repeatedly run an unchanged successful command for reassurance.

### Feature flags only when deployment exposure requires them

Use a feature flag when an incomplete increment may be merged/deployed and could
otherwise become visible or active before the complete feature is ready.

Do not introduce feature-flag infrastructure merely because local implementation
is incomplete.

### Safe defaults

Where behavior is optional or potentially risky, prefer conservative defaults
that preserve existing behavior unless the approved requirements say otherwise.

### Rollback-friendly increments

Prefer additive and independently revertible changes.

For risky migrations or compatibility changes, use the repository's established
migration/deprecation strategy.

Do not assume every database migration can or should be reversed mechanically;
follow the project's real migration policy and production constraints.

## Working with agents

When delegating an increment, provide:

- the behavior/outcome
- acceptance criteria
- dependencies
- expected scope
- verification
- whether broader workstream verification is required at completion

Do not ask an implementation agent to rediscover a plan that already exists.

## Verification

Before considering an implementation task complete:

- [ ] Every behavioral slice followed the required TDD loop
- [ ] Every increment had appropriate focused verification
- [ ] Risky/shared changes received broader verification when warranted
- [ ] Commits represent coherent logical increments
- [ ] No unrelated scope expansion was silently included
- [ ] The final task/workstream verification passed
- [ ] The working tree is in the expected state

## See Also

- `test-driven-development` — RED/GREEN/REFACTOR and test-quality methodology
- `../../references/definition-of-done.md` — project-wide completion standards
