# Review reports start with a count

**Context.** A `/review` report opened with the candidate and the trigger
decisions. The reader had to scan every reviewer's section to learn whether
there was anything to fix. Anthropic's good `REVIEW.md` files ask for "a
summary that starts with a count and says plainly when there's nothing to
fix" (claude.dev, "Solving code review at Anthropic", 2026-10, layer 1).

**Decision.**
- `/review`'s report starts with one line:
  `**Findings: N BLOCKER · N REQUIRED · N ADVISORY**`, with `· N pre-existing`
  when there are any, or `**Nothing to fix.**` when every count is zero.
- Every reviewer persona starts its own report the same way.
  `blind-reviewer` also counts its intent-dependent findings.

**Cost.** None beyond one line per report.
