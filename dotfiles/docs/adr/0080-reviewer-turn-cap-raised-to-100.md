# Reviewer turn cap raised to 100

**Context.** ADR 0055 capped the read-only personas: `repo-recon` at 100
turns and the four reviewers at 60. Both numbers were first guesses, as 0055
and 0056 say, waiting on real run data. A reviewer that reaches its cap stops
early and reports what it did not cover, so a low cap trades review coverage
for a bounded cost.

**Decision.** `code-reviewer`, `blind-reviewer`, `security-auditor` and
`distributed-systems-reviewer` get `maxTurns: 100`, the same as `repo-recon`.
Every read-only persona now has one cap. The rule from 0055 stays: a
read-only persona must have a cap, and `validate-frontmatter.py` fails one
without it. Writers (`executor`, `test-engineer`) stay uncapped.

**Consequence.** A large diff gets a fuller review before the cap ends it.
The cost of a runaway review rises from 60 to 100 turns.
`run-metrics.sh` reports turns per agent; if reviews regularly end far below
100, the cap can come down again.

Amends ADR 0055 point 5. The rest of 0055 stands.
