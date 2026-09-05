# Bugfix Spec Template

The spec shape for a defect, used instead of `spec.md` when `Change kind` is
`Bugfix`. Same status header and `REQ-###` id rules as `spec.md`; what differs
is the front and the middle.

Two things a feature spec does not force, and a bug fix needs:

1. **Reproduction evidence before expected behavior.** A fix specified from a
   description of the bug rather than a reproduction of it is a guess. If the
   current result cannot be stated concretely, the spec is not ready.
2. **Preserved behavior as its own requirement.** The characteristic failure of
   a bug fix is correcting one path while silently changing an adjacent one.
   Naming what must stay the same makes that a testable requirement instead of
   a hope.

**Proportionality.** This does not lower the bar for when a bug needs a spec at
all — `spec-driven-development`'s "When NOT to use" still governs. A typo fix or
a one-line correction with unambiguous expected behavior needs no spec. Use this
template when the defect clears that bar: unclear correct behavior, more than
one plausible fix, adjacent behavior at risk, or a data-correctness or
authorization consequence.

**Root cause and implementation detail belong in `/plan`.** For an affected
invariant, the mechanism proof required by `../spec-quality-gates.md` §4 is an
exception: add an Invariants and Mechanism Proof section before approval.
Limit it to establishing the invariant across its transitions and writers;
leave task breakdown and production code to later stages.

```markdown
# Bugfix Spec: [Title]

Status: Draft
Ticket: [TICKET-123 or N/A]
Change kind: Bugfix
Supersedes: [REQ ids this corrects, in this or an earlier spec, or N/A]
Approved by: —
Approved at: —

## Reproduction Evidence
- Preconditions: [state the system must be in]
- Exact steps/input: [reproducible, not paraphrased]
- Current result: [what actually happens, quoted or measured]
- Expected result: [one line — the full statement is under Expected Behavior]
- Frequency: [always / intermittent + observed rate]
- Affected versions/environments: [...]
- Evidence: [failing test, log excerpt, query result, screenshot]
- Scope of impact: [who or what data is affected, and whether any of it is
  already wrong and needs correcting separately from the fix]

## Change Impact
- Modified behavior: [the incorrect behavior, and the REQ id it violated if one
  exists]
- Explicitly preserved behavior: [adjacent behavior that must not change]
- Compatibility/migration constraints: [data already written incorrectly,
  consumers depending on the buggy behavior]

## Expected Behavior

### Requirement: REQ-001 — [Corrected behavior]
Source: [ticket / reproduction above]

#### Scenario: Previously failing case
- GIVEN [the reproduction preconditions]
- WHEN [the reproduction action]
- THEN [the correct observable outcome]

## Preserved Behavior

### Requirement: REQ-002 — [Existing behavior that must not change]
Source: [existing REQ id, or current production behavior as observed]

#### Scenario: Adjacent valid case remains unchanged
- GIVEN [...]
- WHEN [...]
- THEN [unchanged observable outcome]

## Material Decisions
[Only when correcting the bug required a product, domain, contract, or
lifecycle decision — e.g. choosing which of two defensible behaviors is
correct, or whether already-corrupted data gets repaired. "None" otherwise.]

## Testing Strategy
- Regression test reproducing the defect, written to fail against the current
  implementation and pass after the fix. A test that passes before the fix has
  not reproduced the bug.
- Corrected-behavior test per REQ-001.
- Preserved-behavior tests per REQ-002, which must pass both before and after
  the fix — that two-sided requirement is what makes them meaningful.
- [Data-repair verification, when existing records are already wrong.]

## Boundaries
- Always: [...]
- Ask first: [...]
- Never: [...]

## Open Questions
[Must be empty before approval.]
```
