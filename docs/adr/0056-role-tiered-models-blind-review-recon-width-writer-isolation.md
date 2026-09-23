# Models tiered by role; a blind reviewer; recon gains width; writer isolation made structural

**Decision.** Four changes, made together because the 2026 evidence reviewed in
`docs/observation-log.md`'s source material points at the same conclusion from
four directions: this harness was spending the same resources on judgment and on
retrieval, and reading every change exactly once.

1. **Models are tiered by role, not uniform, and the session runs the high
   tier.** Every persona ran `claude-sonnet-5`. The four reviewers now run
   `opus[1m]`, and `/spec`, `/plan` and the `jira-ticket` skill declare it
   too — slash commands and skills accept `model:` because commands are skills,
   which is what makes those three non-persona stages reachable at all.
   `repo-recon`, `executor` and `test-engineer` stay on `claude-sonnet-5`.
   `settings.json`'s `model` moves from the floating `sonnet` alias to
   `opus[1m]`, so the stages that live in the main session — `/build`,
   `/review`, `/test`, `/ship` — inherit the high tier without each declaring
   one, and the pinned form follows [0002](0002-model-split-sonnet-orchestrator-tiered-subagents.md)'s
   rule that delegation targets a version deliberately chosen rather than
   whatever an alias floats to.

   **Effort is left at its default.** No persona, command or skill declares
   `effort:`, and the per-model `modelSettings` overrides are gone; the
   top-level `effortLevel` in `settings.json` governs everything. An earlier
   draft of this decision set `xhigh` across the board. That was a second
   variable moved in the same change as the model tiers, with nothing able to
   attribute an outcome to either — and the tier is the lever with evidence
   behind it. One variable at a time; raise effort later from log data if the
   tier alone does not deliver.
2. **`blind-reviewer` is added and always runs.** It receives the integrated
   diff and nothing else — no goal, no acceptance criteria, no build evidence.
   `/review` now dispatches two reviewers on every run, from opposite
   directions, plus any specialist the trigger matrix fires.
3. **`repo-recon` may fan out.** When the evidence spans several separately
   bounded areas, `/spec` and `/plan` dispatch one recon per area concurrently.
   Width only; the areas must be established disjoint before dispatch.
4. **Writer isolation is structural.** `executor` and `test-engineer` carry
   `isolation: worktree` in frontmatter, and `settings.json` sets
   `worktree.baseRef: "head"`.

## This is 0036's recorded risk, called in

[0036](0036-specialist-reviewers-to-sonnet-and-narrowed-triggers.md) moved
`security-auditor` and `distributed-systems-reviewer` from Opus/high down to
Sonnet/medium, and recorded itself as "the riskiest change in this pass":
three reductions landing on one axis at once — fewer invocations, a lower
reasoning tier, less reference material loaded — on "precisely the two
reviewers whose misses are most expensive". It named `/review`'s escalation
path as "the only compensating control", and noted that control depends on the
narrowed trigger matching in the first place.

This reverses exactly one of those three: the tier. The narrowed triggers stand,
and so does the narrowed reference loading — both were sound, and both reduce
cost without reducing what a reviewer sees once it runs. The tier was the
reduction that made a specialist *worse at the job it had been summoned for*,
and it was the one with no recoverable failure mode.

It also adds a second compensating control that does not depend on a trigger
matching: `blind-reviewer` runs on every review, so the case 0036 worried
about — a boundary change whose trigger failed to match — now gets a second
full reading regardless.

`code-reviewer` moves up with them, which 0036 did not cover.
[0002](0002-model-split-sonnet-orchestrator-tiered-subagents.md)'s original
instinct — that subagents, not the orchestrator, are where expensive-to-undo
judgment happens — is restored for the reviewers and deliberately not for the
writers, whose output is checked twice downstream.

## Why reviewers and not executors get the expensive model

Review is the judgment-heaviest work in the pipeline and the place a miss costs
most: a defect that survives `/review` reaches `/ship` with a disposition
attached to it. Implementation, by contrast, is checked twice afterwards — by
the executor's own verification and by review. Spending the tier where the work
is irreversible and unchecked, rather than where it is checked twice, is the
whole shape of the decision.

The supporting evidence runs both ways and that is the point. AgentCARD
(arXiv 2606.20629) reports heterogeneous role-specialised teams matching top
single-model accuracy at up to 12x lower cost; Anthropic's research system runs
an Opus lead over Sonnet subagents. Neither says "use the big model" or "use the
small one" — both say stop paying the same price for retrieval and for judgment.

`/spec`, `/plan` and `jira-ticket` join the reviewers because they share the
property: their output is a durable artifact that every later stage consumes and
no later stage re-derives. A wrong requirement in a spec is implemented
faithfully, reviewed against itself, and shipped.

## Why a second reviewer that is told nothing

Cognition's April 2026 reversal of its own "Don't Build Multi-Agents" position
names a clean-context review loop as one of three multi-agent patterns that
demonstrably work, reporting roughly two bugs per pull request with 58% of them
severe. The mechanism is the part worth copying: a reviewer who knows what the
change was supposed to do reads the code as confirming it. The description
supplies the meaning, and the implementation is graded against a summary of
itself.

`code-reviewer` is deliberately intent-informed — its rule 2 requires the goal
and the acceptance criteria — and that is the right design for checking a change
against what was asked. It is the wrong design for noticing that the change does
something else entirely. So the answer is a second reviewer rather than a change
to the first: the same diff, read twice, from directions that cannot both be
taken by one reader.

Two of `blind-reviewer`'s outputs have no equivalent elsewhere. Its required
"what this change appears to do" is a reading of the diff produced without the
goal, which `/review` compares against the real goal — a material mismatch is
either wrong code or code too unclear to read correctly, and both are findings.
Its **intent-dependent** class marks code whose correctness genuinely turns on
information it was not given; `/review` holds the acceptance criteria and is the
only participant that can settle those, so it must, and an unresolved one is
recorded as work skipped.

## Why recon gains width but not depth

Anthropic's multi-agent research system measures +90.2% over a single agent on
breadth-first read tasks with 3-5 parallel subagents, and identifies vague task
descriptions as the failure that makes subagents "perform the exact same
searches". This harness used subagents only for context isolation and never for
breadth: the dispatch count was 0 or 1, always.

Surveying an unfamiliar multi-module area is precisely a breadth-first read
task, and `repo-recon`'s contract — one defined area, pointers back — already
supports it unchanged. Three recons over three areas is the existing contract
used three times, not a new capability. The disjointness condition is what keeps
it from reproducing the failure Anthropic named, and the reconciliation stays
with the caller because a disagreement between two reports is evidence about the
repository, not noise (rule 6).

This does not touch depth. [0055](0055-multi-agent-enforcement-and-parallel-when-safe.md)
rejected nesting and `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=1` still enforces it.

## Why `isolation: worktree` needed a second change to be safe

An analysis of 33,596 agent-authored pull requests across 2,807 repositories
(arXiv 2607.04697) measures a 41.7% textual conflict rate between
temporally-overlapping pull requests from different agents. `/build` already
required worktree isolation for concurrent writers — in prose, as a condition
the orchestrator had to remember. The frontmatter field makes it a property of
the persona instead.

Adding that field alone would have been a regression. Subagent worktrees branch
from the repository's **default branch** unless `worktree.baseRef` is `"head"`;
the docs name in-progress work as the case for `"head"` explicitly. Executors
work on a ticket branch carrying earlier workstream commits and an approved spec
that is not on `main` yet. Every executor would have been handed a checkout
without any of it, and the worktree would have been created successfully, so the
failure would have surfaced as an executor unable to find code that exists.

## Rejected alternatives

**Rejected — splitting `repo-recon` into a cheap inventory persona and an
expensive judgment one.** The obvious cost lever, and it was declined for now on
two grounds. Its "verify claimed reuse" step reads an implementation and judges
whether it satisfies a requirement, which is judgment wearing retrieval's
clothes, and a cheap wrong answer there is expensive downstream. And splitting
one persona into two to save money we have not yet measured inverts the order:
`docs/observation-log.md` and `tools/run-metrics.sh` now exist, so the split
can be proposed from cost data rather than from intuition. Revisit when the log
shows recon cost is material.

**Rejected — cheaper models for retrieval generally.** Same reasoning, applied
wider. The uniform model was wrong because it ignored role; replacing it with a
different uniform rule ("retrieval is cheap") repeats the error in the other
direction.

**Rejected — making `code-reviewer` blind instead of adding a persona.**
Checking a change against its acceptance criteria is a real job and nothing else
in the pipeline does it. Blinding that reviewer would trade one blind spot for
another at no saving.

**Rejected — giving `blind-reviewer` the build evidence but not the goal.**
Build evidence names the tests that ran and frequently the behavior they assert,
which reconstructs the intent by another route. The packet is the diff or the
exercise is theatre.

**Rejected — `isolation: worktree` without `worktree.baseRef: "head"`.** See
above: correct-looking configuration, silently wrong checkouts.

**Rejected — letting reviewers execute the test suite.** Execution catches what
reading misses, and Anthropic's own worker model "missed a subtle thread-safety
bug" for want of it. But a reviewer with a shell is no longer read-only by tool
grant, which [0055](0055-multi-agent-enforcement-and-parallel-when-safe.md)
established as the guarantee rather than an instruction. `/test` and
`test-engineer` already own execution.

## Consequences

- Everything costs more per run, not only review: the main session now runs the
  high tier too, so `/build`, `/review`, `/test` and `/ship` are on it whether
  or not they dispatch anything. Review compounds that — two reviewers minimum,
  both on the expensive tier, where one mid-tier reviewer ran before. The trade is deliberate and the
  numbers belong in `docs/observation-log.md`.
- `/review` gains real work it cannot skip. Intent-dependent findings must be
  settled against the acceptance criteria, and "what this change appears to do"
  must be compared against the actual goal.
- `tools/validate-frontmatter.py` now checks all four decisions: the model tier
  per role, `isolation: worktree` on both writers, and `worktree.baseRef` in
  settings. A drift away from any of them fails CI rather than being discovered
  in a run.
- Fan-out on `/spec` and `/plan` is now possible, so a recon dispatch count
  above 1 is expected in the log rather than anomalous.
- `maxTurns` 40/60 were calibrated against nothing and are now inherited by a
  different model at a higher effort. They were already first guesses; they are
  now first guesses about a changed system.
