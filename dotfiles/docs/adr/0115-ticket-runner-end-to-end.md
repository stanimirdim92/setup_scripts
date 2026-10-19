# One ticket runs end to end; only High-risk questions wait

**Context.** The owner wants to give the harness a ticket and get it back at
`/ship`. ADR 0109 proposed this and named the blocker: open questions. It left
four points for the owner, who answered them on 2026-10-19:

- A question on Low or Medium risk takes the recommended option. Only a
  High-risk question waits for the owner.
- The owner approves the spec. A clean plan under that spec goes on without a
  second approval.
- Questions and results go to a Slack channel the owner picks, and to the
  terminal when a session runs it.
- The run goes through `/ship`. Commits are allowed. Push stays blocked; the
  owner pushes.

**Decision.**
- `tools/run/ticket.py <TICKET>` runs in the ticket's checkout. Each run moves
  the ticket as far as it can, then stops. Run it again after answering.
- It runs intake and `/spec <TICKET> unattended`. In that mode `/spec` marks
  each open question with a recommended option and a risk tier from
  `risk-tiers.md`. Low and Medium questions become a `DEC-###` with
  "Decided by: default". High questions stay `OPEN QUESTION` blocks.
- It posts one message per ticket: the High questions, numbered, and the
  defaults it took. The owner replies in the thread, for example `1A AB11`.
  Numbers with a letter answer questions. The ticket id, with or without the
  dash, approves the spec.
- Only replies whose author matches `HARNESS_SLACK_OWNER` count. The runner
  sets Approved only when that reply names the ticket and nothing is open.
  The reply is the explicit human approval `spec-quality-gates.md` §2 asks
  for, and the spec records the thread.
- `/plan` runs next. The runner approves the plan when `check-plan.py` passes
  and the plan has no `SPEC CONFLICT` and no `OPEN QUESTION`. Any other plan
  is posted and the run stops. This amends `/plan`'s human-approval rule for
  this one case.
- `pipeline.py` runs `/build`, `/test` and `/review` with fix rounds
  (ADR 0114). Then `/ship` runs with the last review message, and its GO,
  NO-GO or SHIP BLOCKED line is posted. The run never pushes.
- Slack goes through `claude -p` and the owner's Slack connector, so the
  runner keeps no token. The channel and the owner live in environment
  variables, not in this public repository.

**Rejected — answer every question with its default.** A High-risk default
can lose data or open a security hole, and nobody would have read it.

**Rejected — approve the spec automatically too.** The spec is the contract.
Every later stage checks its work against it.

**Rejected — batch every ticket into one morning message.** ADR 0109 proposed
it. One thread per ticket keeps each reply tied to one spec, and the owner can
answer them at different times. A batch can come later if threads pile up.

**Cost.** One `claude -p` call per Slack read or post, on top of the stages.
A default the owner would have answered differently costs a spec revision
later; the message lists every default taken so the owner can catch it.
