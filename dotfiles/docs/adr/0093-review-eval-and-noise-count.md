# A review eval from shipped bugs, and a count of review noise

**Context.** The harness measured specs (spec-eval) and plans (plan
coverage), but not review. Nothing showed whether a reviewer change caught
more real bugs or only raised more findings. Anthropic's Claude Code team keeps
a set of past incidents as an eval for its reviewer, and tracks each comment
by how the author answered it (claude.dev, "Solving code review at
Anthropic", 2026-10).

**Decision.**
- `tools/evals/review-eval/run.py` builds a case from a bugfix commit. Blame
  on the lines the fix changed finds the commit that wrote the bug. The eval
  runs a standalone `/review` on that commit, on the code before it. The case
  counts as caught when a BLOCKER or REQUIRED finding lands within 3 lines of
  those lines. A clean case is a commit nobody had to fix; each BLOCKER or
  REQUIRED finding there is noise.
- Runs compare item by item against a baseline, with the same verdicts as
  spec-eval. Cases and output are gitignored, since they name a private
  project's commits.
- `/ship` writes each finding's resolution into the review SARIF file: fixed,
  refuted, accepted, deferred, follow-up, declined or open.
  `tools/run/review-noise.py` counts these per reviewer. Noise is refuted
  findings over closed ones. It also compares the BLOCKER check's verdicts
  (ADR 0092) with how the findings ended, and counts review rounds per ticket
  (ADR 0089).

**Cost.** Each review-eval case is one paid `/review` run. A bug that only
shows with production data is not a fair case; the README says how to pick
cases. The noise count is only as good as the resolutions `/ship` records.
