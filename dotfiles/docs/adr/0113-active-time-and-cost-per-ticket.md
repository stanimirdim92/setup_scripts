# Active time and cost are counted per ticket

**Context.** ADR 0112 counts how often a ticket stopped for a person. It does
not say how long those stops took, or what the ticket cost in model spend.
The owner wants both numbers per ticket. ADR 0112 rejected a timer because
wall-clock time mixes waiting with deciding. The cost of one stage was
measured once by hand (LD-380, $9.75 in `HANDOFF.md`), never per ticket.

**Decision.**
- `ticket-stats.py` reads the ticket's Claude Code transcripts. They are
  every session in `.claude/worktrees/<TICKET>`, plus project sessions where
  a typed prompt names the ticket.
- Active time adds, for each typed prompt, the gap since the session's
  previous record. Each gap counts at most 10 minutes (`--idle-cap`). A
  longer gap was a break, so only the cap counts. Tool results, meta records
  and harness notices are not prompts.
- Tokens count one usage per model reply, with subagent transcripts
  included. This matches `run-metrics.sh`.
- Cost prices every reply from `model-prices.json` next to the script:
  input, output, cache reads, and 5-minute and 1-hour cache writes. Fast mode
  doubles the price where the file lists it.
- A model missing from the price file is reported as unpriced tokens. The
  script never guesses a price.
- When no transcript is found, the three columns say so instead of 0.
- The "Per ticket" table gains Active time, Tokens and Cost before the
  Shipped bugs column.

**Rejected — wall-clock time from /spec to /ship.** It counts nights and
waiting, as ADR 0112 said. The capped gap counts only time near a prompt.

**Rejected — `/cost` from each session.** A person has to copy it by hand,
and it is gone once the session ends. The transcripts keep the same usage.

**Cost.** A price file to update when list prices change. The dollar figure
is list price, not the invoice, and the row prints the price date.
Reading time before the first prompt of a session is not counted.

**Amended 2026-10-23 — four times instead of one (LD-507).** On LD-507
active time said 32 minutes for a ticket that ran from 07:27 to 11:01. Each
gap restarted at every agent record and stopped at 10 minutes, so reading,
long reviews and everything after the last prompt were lost. The column is
now four: Elapsed, Agent, Waiting and You. You keeps the capped gap, now 30
minutes, and also counts AskUserQuestion answers and queued prompts. Work
outside Claude leaves no record, so `--extra MIN` adds what the owner
reports, and the script prints the table header with the row.
