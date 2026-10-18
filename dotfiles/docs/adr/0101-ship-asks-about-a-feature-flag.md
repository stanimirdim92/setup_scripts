# /ship asks how new behavior is turned off

**Context.** `/ship` required a rollback plan, and its Infrastructure check
asked that flags have defaults and owners. It never asked whether risky new
behavior ships behind a flag at all. A flag turns behavior off without a
deploy, which is faster than any rollback. Anthropic ships new behavior
behind a flag, to its own staff first (claude.dev, "Solving code review at
Anthropic", 2026-10, layer 6).

**Decision.**
- `/ship` has a third release-readiness attestation, Feature flag: the flag
  that hides new user-facing or risky behavior and how to turn it off, or why
  it ships without one.
- A change that touches an "Always a person" path (ADR 0096) or migrates data
  and ships without a flag must state the reason.
- A change with no new behavior (refactor, docs, tests) records
  `PASS — not applicable`.
- The attestation does not require a flag. The user decides; `/ship` makes
  sure the question was answered.

**Cost.** One more line in every `/ship` report.
