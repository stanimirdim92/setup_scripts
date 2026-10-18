# Reviewers answer every REVIEW.md rule

**Context.** `REVIEW.md` reached every reviewer (ADRs 0091, 0094), but nothing
showed that a reviewer applied it. A rule could be skipped without a trace.
Anthropic checks "separately whether the reviewer actually follows it"
(claude.dev, "Solving code review at Anthropic", 2026-10, layer 1). The owner
asked for this to be fixed.

**Decision.**
- `code-reviewer` answers every "Always check" rule of the project's
  `REVIEW.md` in a checklist: checked, with the `file:line` it looked at, or
  not applicable, with the reason.
- `/review` compares the checklist with the rules. A missing rule goes back to
  `code-reviewer` once, with only that rule and the diff. If it is still
  missing, `/review` reports a REQUIRED `RULE-#` finding: "REVIEW.md not
  followed: <rule>".
- The checklist appears in the `/review` report.

**Cost.** A longer `code-reviewer` report, and at most one extra short run when
a rule was skipped. The review eval can later add cases that test a rule
directly.
