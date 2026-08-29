# A third concurrent executor as a conditional exception, not a raised cap

**Decision.** `/build` keeps **2 concurrent executors as the default** and allows
a **third only when all four of these hold**, never a fourth: the workstreams are
genuinely independent, each is dependency-ready with its gating checkpoint
already passed, every writer is dispatched with `isolation: worktree`, and the
session is not near its rate limit. `/build` must state in its completion report
how many executors ran concurrently and, for a third, that the conditions held.
Exceeding the cap is a reportable slip, named as such.

This partially supersedes
[0031](0031-parallel-executors-via-worktree-isolation.md), whose
**Rejected — raise the cap above 2** said "nothing measured says 2 is the
bottleneck… revisit with an actual measurement." That measurement now exists, so
this is the revisit 0031 asked for rather than a reversal of its reasoning. Its
correctness rule is untouched: worktree isolation is still what makes any
concurrency safe, and integration is still strictly sequential.

**The evidence cuts both ways, which is why this is a condition and not a new
cap.** A real run dispatched three worktree-isolated executors across an
11-task, ~50-file build and completed correctly — so 3 is *safe* when isolated.
But `/usage` from the same period showed 14% of usage consumed while 4+ sessions
ran in parallel: concurrent executors share one rate limit, so past the throttle
point 3-wide finishes no faster than 2-wide plus queueing, and often slower.
Safety and benefit are separate questions, and the second one is conditional on
headroom that varies by session. A raised hard cap would encode the safety
finding while ignoring the throughput finding.

**Why the reporting requirement is part of the decision.** In that same run the
orchestrator dispatched 3, then wrote that this "exceeds the plan's max-2
concurrent guidance — a slip on my part," and explained why the workstreams were
independent. That self-report is what made the run auditable at all, and it is
the behavior being made mandatory here. A concurrency policy nobody reports
against cannot be checked afterwards, and the run metrics in
`references/agent-run-metrics.md` have no field that would otherwise capture it.

**Rejected — raise the hard cap to 3.** It takes the safety evidence and
discards the throughput evidence. Under throttling a third executor spends a
full extra token stream for no wall-clock gain, and "could run in parallel"
would become "should" by default — the opposite of the sequential-first posture
0031 kept.

**Rejected — keep the flat cap at 2.** The run demonstrates that three
worktree-isolated, genuinely independent workstreams complete correctly, so a
flat 2 leaves real wall-clock on the table in exactly the case the conditions
describe.

**Rejected — let `/build` judge concurrency case by case without stated
conditions.** That is what already happened, and it worked only because the
orchestrator volunteered its reasoning. Discretion that depends on an agent
choosing to confess is not policy.

**Revisit if** run metrics show a third executor being dispatched into throttled
windows (the rate-limit condition is not being evaluated honestly), or show
merge failures concentrating in 3-wide runs (integration cost rises with width
faster than assumed). Both are visible from `tools/run-metrics.sh` plus `/usage`.
