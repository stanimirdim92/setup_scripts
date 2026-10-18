# Person-time and shipped bugs are counted per ticket

**Context.** Anthropic loosens automation only with evidence: lighter
approval paths stay open while the revert and incident numbers hold
(claude.dev, "Solving code review at Anthropic", 2026-10, layers 5 and 7).
The owner wants to automate more of the pipeline (ADR 0109). Nothing
measured how often a ticket stopped for a person, or whether fewer stops
cost bugs.

**Decision.**
- `ticket-stats.py <TICKET>` counts a ticket's person stops from what the
  pipeline already records. It counts DEC headings in the spec, OPEN items,
  and approvals (commits that set `Approved at:` in the spec or plan, so a
  reapproval counts). It also counts review rounds and how findings ended.
- `/ship` prints its row under "Human time" for the "Per ticket" table in
  `observation-log.md`. The owner adds it to the harness repository.
- The table's last column counts bugs found later: a bug ticket whose
  "Escaped From" names this ticket adds one (ADR 0110).
- Automation is loosened only while that column stays at 0.

**Rejected — a timer.** Wall-clock time mixes waiting with deciding. The
number of stops is what automation can reduce.

**Cost.** One script run at `/ship` and one row per ticket.
