# Reviewers label findings with the release dispositions

**Context.** A review finding carried three vocabularies. Each reviewer had
its own severity scale: Critical, Important and Suggestion, or Critical, High,
Medium, Low and Info for the security auditor. `/review` then translated it
into a release disposition (ADR 0033), and ADR 0074 added a SARIF level on
top. The translation table lived in two files, `commands/review.md` and
`references/component-response-contracts.md`. ADR 0074 had to change both
copies, which is how such copies drift apart.

**Decision.** Reviewers label each finding BLOCKER, REQUIRED or ADVISORY
directly. The label is set once and carried unchanged to `/ship`.
- One table defines the three: `component-response-contracts.md`
  §Dispositions, with what each means, how `/ship` resolves it, and its
  SARIF level. Every persona, `/review` and `/ship` point to it.
- The security auditor's five levels fold into three: Critical and High
  become BLOCKER, Medium becomes REQUIRED, Low and Info become ADVISORY.
  These were already the mapped dispositions, so no finding changes weight.
- The SARIF `properties` drop `nativeSeverity`.

**Consequence.** One vocabulary from review to release. The security
auditor no longer separates Critical from High, or Low from Info. Neither
distinction changed a release decision.

Supersedes the translation step of ADR 0033; the dispositions and their
release rules stand.
