# Spec Template

The canonical spec document shape. Used by `spec-driven-development`'s
Phase 1 (Specify) — fill in every section before a human reviews it; don't
skip a section because it "doesn't apply," write "N/A" and why instead.

```markdown
# Spec: [Project/Feature Name]

## Objective
[What we're building and why. User stories or acceptance criteria.]

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
