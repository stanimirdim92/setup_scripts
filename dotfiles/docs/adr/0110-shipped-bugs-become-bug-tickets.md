# A shipped bug becomes a bug ticket the pipeline fixes

**Context.** ADR 0100 added a "Shipped bugs" table and an eval case per bug.
The notes then suggested circuit breakers: tighten `/review` when shipped-bug
rows rise. The owner chose a simpler rule: "if bugs slip, we raise a
bug-ticket and you must pick it to solve it." ADR 0100 also admitted its
table "is only as complete as the owner keeps it."

**Decision.**
- A bug found after merge is raised as a bug ticket. The agent takes it
  through the normal pipeline: intake, `/spec` with the bugfix template,
  `/plan` with its Root-Cause Trace (ADR 0097), and `/build` with a failing
  reproduction test first. `/test` shows the bug on the base and gone on the
  candidate (ADR 0104), then `/review` and `/ship` run as usual.
- The bugfix spec gets an `## Escaped From` section for such a bug: the
  ticket and commit that shipped it, the layer that should have caught it,
  and why it missed.
- When the fix ships, `/ship` prints the "Shipped bugs" row and the
  review-eval command from that section. The record now comes out of the
  pipeline instead of from memory. `/ship` prints them and the owner commits
  them to the harness repository.
- No circuit breaker. The eval cases score the next reviewer change, and the
  repeated-class check (ADR 0105) turns a recurring miss into a rule.

This amends ADR 0100: the table and eval cases stay, and how rows are produced
changes.

**Cost.** Nothing new per bug beyond the fix itself. A spec section and two
printed lines at `/ship`.
