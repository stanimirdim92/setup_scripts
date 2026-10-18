# Review findings are fixed overnight

**Context.** At Anthropic every finding is answered, and "often an agent
fixes overnight" (claude.dev, "Solving code review at Anthropic", 2026-10,
layer 2). In the harness a finding went back to `/build` by hand. `/build`
had no mode for it: it dispatched planned tasks, and a finding is not one.
The owner said yes to overnight fixes.

**Decision.**
- `/build <TICKET> review fixes` takes the open BLOCKER and REQUIRED findings
  from the newest review SARIF, leaving out pre-existing ones. The executor
  fixes each test-first. When the code is already right it changes nothing
  and reports the finding as disputed with evidence. Commits carry
  `Task: <finding ids>`, so the ledger check accepts them. The plan does not
  change.
- `tools/run/batch-fix.py` runs it unattended for every eligible ticket, then
  `/review` for the next round. It skips a ticket at the round cap, since
  round 4 means the approach needs the owner (ADR 0089). It also skips a
  ticket whose candidate moved after its review, and one whose open findings
  are not BLOCKER or REQUIRED.
- It never pushes and never runs `/ship`. The morning report lists each
  ticket's new review line, cost and log.

**Rejected — fix inside `/review`.** The reviewer would grade its own fix.
`/build` and `/review` stay separate sessions.

**Cost.** Two headless runs per eligible ticket, each capped by
`--max-budget-usd` (default 5). Tickets with nothing open cost nothing.
