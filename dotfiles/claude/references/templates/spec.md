# Spec Template

The canonical spec document shape. Used by `spec-driven-development`'s
Phase 1 (Specify) — fill in every section before a human reviews it; don't
skip a section because it "doesn't apply," write "N/A" and why instead.

Exception: the skill's compact form for bounded, low-risk work (no new
architecture/pattern, no contract or schema change, no concurrent invariant,
no lifecycle field) keeps only the status header, Objective, Change Impact,
Requirements, Testing Strategy, Boundaries, and Success Criteria, and omits the
rest outright. The `### Requirement:` / `#### Scenario:` heading forms and the
`REQ-###` ids stay mandatory in both forms — `/plan`, `/test`, `/review` and
`/ship` enumerate them mechanically.

For a bug fix, use `bugfix-spec.md` instead: same header and id rules, but it
leads with reproduction evidence and carries an explicit preserved-behavior
section.

```markdown
# Spec: [Project/Feature Name]

Status: Draft
Ticket: [TICKET-123 or N/A]
Change kind: New | Modify | Remove | Rename | Bugfix
Supersedes: [spec path + requirement ids it replaces, or N/A]
Approved by: —
Approved at: —

## Objective
[What we're building and why. User stories; detailed acceptance criteria go
under Requirements below. Record out-of-scope exclusions here when the request
could be read wider than intended.]

## Change Impact
[What this change does to behavior that already exists. Required whenever
Change kind is not New; for a greenfield capability, "Added behavior" alone is
enough. Name the affected `REQ-###` or contract, not just the area.]

- Added behavior: [...]
- Modified behavior: [existing REQ id or contract, and what changes about it]
- Removed behavior: [reason and migration path]
- Renamed behavior: [old → new, and who has to change with it]
- Explicitly preserved behavior: [adjacent behavior that must NOT change, with
  the REQ id that pins it — this is the line that stops one path getting fixed
  while a neighbouring one silently changes]
- Compatibility/migration constraints: [mixed-version windows, stored data
  already written under the old behavior, external consumers]

## Requirements
[One `### Requirement:` per behavior the change must provide, each with
`#### Scenario:` blocks for its cases. These exact heading forms are
load-bearing: `/plan`, `/test`, `/review` and `/ship` enumerate them
mechanically (grep `### Requirement:`) to map coverage and evidence
requirement-by-requirement instead of interpreting prose.]

### Requirement: REQ-001 — [Behavior the system must provide]
Source: [ticket AC-2 / user decision in conversation / existing REQ this refines]

[One or two sentences stating the requirement precisely. Ids are mandatory for
any spec that will enter `/plan`, sequential and never renumbered once
approved — downstream artifacts reference them. A withdrawn requirement keeps
its id and is marked withdrawn rather than reused.]

#### Scenario: [Named case — happy path, boundary, failure]
- GIVEN [precondition]
- WHEN [action]
- THEN [observable outcome]

[Where prose leaves the outcome ambiguous, add representative inputs and their
expected outputs. Performance criteria name metric, threshold, workload,
environment, and measurement method.]

## Material Decisions
[Only decisions that materially changed specified behavior — product, domain,
contract, or lifecycle. Technical decisions belong in the plan, as `TD-###`
under its Decisions and Provenance — `DEC` and `TD` are separate id spaces so
"see DEC-002" is never ambiguous between the two documents. This exists so a resolved OPEN QUESTION leaves a trace instead of
disappearing into the final prose. "None" is a valid entry.]

### DEC-001 — [Short title]
- Decision: [what was decided]
- Alternatives: [what was rejected]
- Reason: [why, referencing the REQ id that forced it]
- Source: [user decision + date / project rule / repository precedent]
- Affects: [REQ ids]

## Tech Stack
[Framework, language, key dependencies with versions]

## Commands
[Build, test, lint, dev — full commands]

## Project Structure
[Directory layout with descriptions]

## Code Style
[Example snippet + key conventions]

## Testing Strategy
[Framework, test locations, coverage requirements, test levels. Every
requirement's evidence is traceable to a REQ id.]

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
[Anything unresolved that needs human input. Must be empty before approval.]
```

## Status header rules

`Status` is the durable record of approval — it survives the session boundary
that conversation history does not. Transitions, who may set them, and how
`Approved by` / `Approved at` are recorded: `../spec-quality-gates.md` §2.
Requirement-id rules and the per-stage trace: §3 of the same file.

The one rule worth repeating here, because it is the one a drafting agent is
most tempted to break: `Approved` is the human's to grant. Leave the header at
`Draft` and ask.
