# Change surface in plans, touch points in recon, and a plan-recall eval

**Evidence.** LoLBench (arXiv 2609.37143, read 2026-10-02): 100 tasks built
from real enhancement proposals on 2.4M-line systems, 28 agents. The best
(Claude Code with Opus 5) fully solved 14%. The dominant failure was
incomplete cross-module context: agents' edits landed in the right files
65–80% of the time, but they reached only 37–65% of the files the real change
touched. Adding a reference file list and API specification raised solve
rates by 16–22 points. In this pipeline `/spec` + `/plan` + `repo-recon` are
that perception step and the plan's task packets are that file list, so the
harness's weak point is the completeness of the list, not its existence.

**Decision — change surface in plans.** `plan-quality-gates.md` §4: a task
that changes a shared surface (public interface, route, event, job, config
key, schema or serialized shape, framework registration) lists every consumer
and registration found by a repository search under `Files/areas likely
touched`, records the search under a new `Change-surface search` field, and
marks deliberate non-changes `unchanged — reason`. A surface change without a
recorded search fails the plan's approval check.

**Decision — the search is rerun twice.** The executor reruns its task's
search on the final tree and accounts for every hit
(`executor-development-discipline` §Completion Evidence); `/build` reruns all
selected searches on the integrated tree, because integration can drop a
location one workstream handled.

**Decision — touch points in recon.** `repo-recon`'s report gains a
`Touch points` section — consumers, registrations, persistence and
serialization, tests and docs — each with the search that found it, so `/plan`
can record and rerun it rather than rediscover it.

**Decision — plan-recall eval.** `dotfiles/tools/evals/plan-recall/recall.py` scores a
shipped ticket's plan against its merged change (recall over pre-existing
files, the paper's measure). It is deterministic and free; its scoring logic
runs in CI, and real scores go in `dotfiles/docs/observation-log.md`. It is how the two
decisions above will be judged.

**Rejected — inject reference file trees the way the paper's ablation did.**
The paper derived them from the real solution, which a live ticket does not
have. The search-backed change surface is the closest available equivalent.

**Rejected — raising `/spec` and `/plan` effort now.** The paper ran models at
their second-highest effort and did not vary it. ADR 0066's `medium` stands
until plan recall or the observation log shows perception misses.
