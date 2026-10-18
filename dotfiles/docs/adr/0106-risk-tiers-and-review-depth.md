# Risk tiers set review depth

**Context.** Anthropic sorts every change into a written risk tier, set by
the change and not by its author. Low needs no person once checks pass,
Medium needs one, High needs two. Review effort follows: Quick, Standard or
Deep, with Deep "where a missed bug costs more than the review time"
(claude.dev, "Solving code review at Anthropic", 2026-10, layers 2 and 5).
The harness had triggers for specialists and for `/test`, but no written
tier, no depth, and no "Risk" line in the `/ship` report. The owner said yes
to tiers and to the depth knob.

**Decision.**
- `references/risk-tiers.md` is the single source. High covers "Always a
  person" paths, persistent data, security boundaries, concurrency and
  delivery, shared contracts, and money. Low covers exempt changes, copy, and
  additive changes behind an off flag. Medium covers the rest. When unsure,
  take the higher tier.
- The tier picks the depth: Low is Quick, Medium is Standard, High is Deep.
  A `## Review depth` heading in the base branch's `REVIEW.md` sets a floor.
  Nobody can lower the depth below the tier.
- Depth changes four things. Deep checks REQUIRED findings independently as
  well as BLOCKERs, and dispatches a specialist whose trigger might match.
  Quick caps ADVISORY findings at 3 per reviewer. At Deep, `/test`
  mutation-probes every changed condition and runs the full suite.
- `/review` records **Risk · Depth** with the line that matched. `/ship` puts
  it first and says what the owner reads: the summary, the diff, or every
  changed file with a second person.
- Security review and required specialists run at every depth.

**Rejected — let the author or the ticket set the tier.** That is the
trusted-author shortcut. With one developer and agents writing the code, it
would mean the agent grading its own risk.

**Cost.** Deep adds independent checks on REQUIRED findings and a longer
`/test`. Quick saves only ADVISORY noise, because security review and `/test`
on production changes stay on.
