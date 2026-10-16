# A ticket ledger check after planning

**Context.** On LD-365 the spec, plan and todo stopped agreeing for three
weeks, and no gate noticed.
- The spec gained DEC-014 to DEC-021 in conversation. The plan pin was only
  compared when `/build` started, and that work never went through `/build`.
- The plan deferred the REQ-009 timezone gap "for /review to weigh". No
  `/review` ran, and nothing else listed the gap.
- The todo had no `Status:` lines. `check-plan.py` would have failed it, but
  it runs only at `/plan`.
- DEC-020 dropped columns that DEC-006 and a Boundaries `Never:` line
  protected. Nothing compared the new decision with the old rules.
- Failed jobs, an open question and a known failing test lived only in chat.

**Decision.**
- `docs/tasks/<TICKET>-open.md` is the register for every item the other
  files do not track. A deferral in the plan or todo names its `OPEN-###` id
  (`plan-quality-gates.md` §6, `templates/open-items.md`).
- `check-ledger.py` compares the spec, its plan pin, the todo, the register
  and the ticket's commits. `/review` runs it and reports each FAIL as a
  REQUIRED finding. `/ship` runs it with `--ship`, and any FAIL blocks.
- `/build` §4 tells a session how to record work outside `/build`. AGENTS.md
  sends remaining work to the register, not only to a compaction summary.
- The DEC check and the commit check only warn. Both match text, so both
  can be wrong.

**Rejected.**
- A todo task with `Status: Done` for every unplanned commit. It adds a task
  after approval, which §1 counts as a plan change. It also conflicts with
  the trailer rule that omits `Task:` on unplanned commits.
- Failing a `Done` task with unticked acceptance boxes. No rule tells an
  executor to tick them; `Status:` is the progress record.
- Scanning the spec for "deferred". On LD-365 those lines were design prose.
  The spec has its own Open Questions gate.
- A hook after each commit. A check at the gates covers the same ground with
  less noise.

**Cost.**
- One more file per ticket, and one more check at `/review` and `/ship`.
- Older tickets fail the check until their records are brought up to date.
  LD-365 shows 17 failures.
