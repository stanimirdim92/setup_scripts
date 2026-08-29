# Spec Template

The canonical spec document shape. Used by `spec-driven-development`'s
Phase 1 (Specify) — fill in every section before a human reviews it; don't
skip a section because it "doesn't apply," write "N/A" and why instead.

```markdown
# Spec: [Project/Feature Name]

## Objective
[What we're building and why. User stories; detailed acceptance criteria go
under Requirements below.]

## Requirements
[One `### Requirement:` per behavior the change must provide, each with
`#### Scenario:` blocks for its cases. These exact heading forms are
load-bearing: `/test` and `/review` enumerate them mechanically (grep
`### Requirement:` / `#### Scenario:`) to map coverage
requirement-by-requirement instead of interpreting prose.]

### Requirement: [Behavior the system must provide]
[One or two sentences stating the requirement precisely.]

#### Scenario: [Named case — happy path, boundary, failure]
- GIVEN [precondition]
- WHEN [action]
- THEN [observable outcome]

## Tech Stack
[Framework, language, key dependencies with versions]

## Commands
[Build, test, lint, dev — full commands]

## Project Structure
[Directory layout with descriptions]

## Code Style
[Example snippet + key conventions]

## Testing Strategy
[Framework, test locations, coverage requirements, test levels]

## Invariants and Mechanism Proof
[Precise invariant including empty state; transitions/writers; enforcement layer;
serialization/constraint mechanism; why it covers every transition; evidence.]

## Data Lifecycle
[Hard/soft/archive semantics; read visibility; uniqueness/relationships;
restoration/retention; effect on invariants and tests. Use N/A and why when no
lifecycle state exists.]

## Boundaries
- Always: [...]
- Ask first: [...]
- Never: [...]

## Success Criteria
[How we'll know this is done — specific, testable conditions]

## Open Questions
[Anything unresolved that needs human input]
```
