# REVIEW.md is read from the base branch

**Context.** ADR 0091 had `/review` read the project's `REVIEW.md` from the
candidate. A change could then edit `REVIEW.md` to lower its own bar: skip a
path, lower a severity, cap findings. Claude Code Review, Anthropic's managed
reviewer, reads the file "from the pull request's base branch or from the
default branch, never from the pull request's own changes"
(code.claude.com/docs/en/code-review). Its documented example also fixes the
headings, and its re-reviews post fewer nits and pre-existing findings and
say how many they left out.

**Decision.**
- `/review` reads `REVIEW.md` from the candidate base with `git show`. A change
  to the file applies from the next change on, not to its own review.
- The template uses the documented headings: "What Important means here",
  "Cap the nits", "Do not report", "Always check". One file then serves both
  the harness and Claude Code Review.
- From review round 2 (ADR 0089), `/review` reports no new ADVISORY or
  pre-existing finding. It counts them and ends the summary with
  "<n> found and not reported in this round".

**Cost.** A `REVIEW.md` fix waits one change before it takes effect. A real
nit or pre-existing defect found late is only counted, not described.

Amends ADR 0091.
