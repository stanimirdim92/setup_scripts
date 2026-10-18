# Bugs found after merge are logged by layer and become eval cases

**Context.** The observation log recorded harness failures, but a bug found
after merge had no place. Nobody asked which check should have caught it.
Anthropic's incident reviews ask "which layer should have caught the issue",
and they turn incidents and reverts into the reviewer's eval set (claude.dev,
"Solving code review at Anthropic", 2026-10, layer 7).

**Decision.**
- `observation-log.md` has a "Shipped bugs" table: when it was found, the
  ticket that shipped it, the bug, the fix commit, the layer that should have
  caught it, and why that layer missed.
- The layers are the seven from the life-of-a-change notes, from
  verification before review to detection and rollback.
- Every row becomes a review-eval case with
  `review-eval/run.py --new … --fix <fix sha>` (ADR 0093). The next change to
  a reviewer is then scored against bugs that really shipped.

**Cost.** One row and one case per shipped bug. The table is only as complete
as the owner keeps it.
