# Compact specs and plans state each fact once

**Decision.** Tighten the existing compact forms without removing any lifecycle
gate. A full harness canary for a two-file behavior change produced a 115-line
spec, an 81-line plan, and a 5-line todo for a final code-and-test diff of 23
additions and one removal. The documents repeated the same cases in Objective,
Change Impact, Requirements, Testing Strategy, Boundaries, and Success Criteria;
the plan then split implementation and its proving tests into two tasks even
though neither task was independently verifiable.

For bounded, low-risk work:

1. Requirement scenarios own acceptance behavior. The compact spec keeps a
   short Objective, requirements, and concise test evidence; Change Impact,
   Boundaries, and Material Decisions appear only when their distinct content
   exists. A separate Success Criteria section is omitted.
2. The compact plan contains only its header, short technical approach, task
   index, requirement coverage, non-duplicated verification, and handoff. Full
   task packets live in the todo artifact rather than being copied into the
   plan.
3. One behavioral task includes its production implementation and the tests
   that prove it. Test work becomes a separate task only when it has verifiable
   value before the production change, such as characterization evidence that
   gates later risky work.
4. `/plan` reuses `/spec`'s recon report while the surveyed implementation and
   test area is unchanged. Committing the spec is not an implementation change
   and does not by itself justify paying for the same survey twice.

The durable controls from [0045](0045-spec-approval-state-change-impact-and-requirement-traceability.md)
and [0046](0046-plan-technical-approach-spec-pinning-and-plan-gates.md) remain:
approval state, requirement ids and sources, spec pinning, requirement coverage,
closure checks, and integrated verification. This changes representation and
task boundaries, not the acceptance bar.

**Validation.** A fresh canary produced an 81-line spec, 40-line plan, and
33-line executor-ready todo: 154 lines total versus 201 before (23% fewer). The
plan contained one `T001` rather than separate implementation and test tasks;
`/build T001` consumed it through one executor and all five tests passed.

**Rejected — skip `/spec` or `/plan` whenever the output would be compact.**
Compactness describes the document shape, not whether durable approval and
traceability matter. The existing opt-out for obvious self-contained work stays
the proportionality boundary.

**Rejected — impose a line or token limit.** A quota encourages deleting
load-bearing evidence when a bounded change has many legitimate scenarios.
Single ownership and conditional sections target duplication directly without
making document length a gate.

**Rejected — merge the plan and todo artifacts in this pass.** `/build` already
uses the todo as its task-packet source while the plan owns approach, coverage,
and integrated verification. Changing that interface is broader than the
observed problem; enforcing the existing separation removes the duplication.

**Revisit if** compact canaries still create duplicate acceptance prose or split
implementation from its tests. That would mean prose guidance is insufficient
and the compact forms need mechanically validated schemas rather than more
instructions.
