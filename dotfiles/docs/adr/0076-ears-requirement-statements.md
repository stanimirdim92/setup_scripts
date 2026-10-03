# EARS requirement statements

**Context.** ADR 0075 made requirement statements carry an uppercase RFC 2119
keyword and rejected EARS, on the grounds that it overlaps the GIVEN/WHEN/THEN
scenarios. The approver asked for EARS. On a second look the overlap is small.
GIVEN/WHEN/THEN (Gherkin, from BDD) describes one example. EARS (Easy Approach
to Requirements Syntax; Mavin et al., Rolls-Royce, 2009) describes the rule
that the examples test. A free-form statement still let a requirement hide its
trigger, or bundle two behaviors in one sentence.

**Decision — EARS patterns, RFC 2119 keywords.** Each requirement statement
uses one EARS pattern, with the RFC 2119 keyword where EARS puts "shall":

| Pattern | Form |
| --- | --- |
| Ubiquitous | The <system> MUST <response>. |
| State-driven | While <state>, the <system> MUST <response>. |
| Event-driven | When <trigger>, the <system> MUST <response>. |
| Optional feature | Where <feature is present>, the <system> MUST <response>. |
| Unwanted behavior | If <unwanted condition>, then the <system> MUST <response>. |
| Complex | While <state>, when <trigger>, the <system> MUST <response>. |

The spec template lists the patterns; `spec-driven-development` requires one. A
statement that fits no pattern usually holds two requirements, or none.
Scenarios keep GIVEN/WHEN/THEN. The evidence rule in ADR 0075 is unchanged.

**Reverses.** ADR 0075's rejection of EARS. The rest of ADR 0075 stands.

**Rejected.**
- *Plain EARS "shall".* It cannot say SHOULD or MAY, so it would undo ADR
  0075's evidence rule.
- *EARS in place of the scenarios.* A rule with no examples is harder to test
  and to review.
