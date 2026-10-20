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
- The recommended option is the one the repository already follows. Without
  a precedent, it is the option that keeps behavior and data and can be
  undone, then the smaller change.
- It posts one message per ticket: the High questions, numbered, and the
  defaults it took. The owner replies in the thread, for example
  `TICKET ANSWERS: 1A ok`. Only replies that start with `TICKET ANSWERS:`
  are read, so the owner can discuss with the PO in the same thread. Numbers
  with a letter answer questions. `ok`, `go`, `approved` or the ticket id,
  with or without the dash, approves the spec.
- Only replies whose author matches `HARNESS_SLACK_OWNER` count. The runner
  sets Approved only when that reply names the ticket and nothing is open.
  The reply is the explicit human approval `spec-quality-gates.md` §2 asks
  for, and the spec records the thread.
- `/plan` runs next. The runner approves the plan when `check-plan.py` passes
  and the plan has no `SPEC CONFLICT` and no `OPEN QUESTION`. This amends
  `/plan`'s human-approval rule for this one case.
- A `SPEC CONFLICT` goes back to `/spec <TICKET> unattended` with the
  conflict section. When `/spec` fixes it by default (Low or Medium risk, no
  `OPEN QUESTION` left), the owner's approval stands, the owner gets a note in
  the run thread and `/plan` runs again. A High-risk fix or a behavior change
  stays an `OPEN QUESTION`: the spec returns to Draft and the owner answers
  and approves again. After two conflicts the run stops.
- `pipeline.py` runs `/build`, `/test` and `/review` with fix rounds
  (ADR 0114). Then `/ship` runs with the last review message, and its GO,
  NO-GO or SHIP BLOCKED line is posted. The run never pushes.
- Slack goes through `claude -p` and the owner's Slack connector, so the
  runner keeps no token. The channel and the owner live in environment
  variables, not in this public repository. `HARNESS_SLACK_MENTION` adds an
  @-mention of the owner, so each message notifies them on every device.

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

**Amended 2026-10-20 — the run survives what is not the task's fault.** The
owner asked for the run to need fewer restarts. Taken from Symphony
(openai/symphony, SPEC.md) and the headless `claude -p` practice:

- A stage that fails for a passing reason (rate limit, dropped connection,
  crash, or no event from the agent for 60 minutes, `HARNESS_STALL_MIN`) is
  retried up to 5 times (`HARNESS_RETRIES`), 10 s · 2ⁿ apart up to 5 minutes,
  resuming the same session by its id so the work so far is kept. An auth,
  billing, budget or turn-cap error stops at once. The owner set the stall
  at 60 minutes, not Symphony's 5: a long test run makes no events.
- One run per ticket. `<TICKET>-ticket.lock` names the process; a second
  start is refused while it lives and takes over when it is gone. A run goes
  on from where the last one stopped: `pipeline.py` notes each finished stage
  and, started again on the same HEAD, goes on from the next one.
- The Jira status is a stop switch, as moving an issue out of an active state
  is in Symphony: Done, or a status named in `HARNESS_JIRA_STOP`, stops the
  run before its next stage, like `TICKET STOP`. The runner reads Jira with
  the read-only tools on the small model.
- Jira mirrors the run, as the Jira-to-PR pipelines do (In Progress at
  start, the PR link and In Review at the end): the start moves the ticket
  to In Progress, the Slack questions and a stop go on it as comments, and
  the `/ship` result is a comment with branch, HEAD and spend; GO moves it
  to Code Review. The runner may only move the status and comment
  (`JIRA_WRITE_TOOLS`); it edits no field and opens no issue, and
  `HARNESS_JIRA_WRITE=0` keeps Jira read-only. This amends "Nothing here
  writes to Jira" above for these two writes.

- `ticket.py --watch` starts runs from Jira, as Symphony polls its board:
  every 90 s it searches for open issues with the label `harness-run` and
  starts one run per issue, two at once, most urgent first. The label is the
  claim (the DIY pipelines use a label too, so a person chooses what the
  harness takes): put on, it starts; taken off, the run stops before its
  next stage. A run that stopped starts again only after the label is taken
  off and put back, so a failure does not loop. One watcher per checkout
  serializes the starts; the per-ticket lock covers runs started by hand.

Rejected — a Jira automation webhook into the owner's machine. It needs a
public endpoint; polling needs nothing and 90 s is soon enough.

Rejected — restore a live session across a runner crash. Symphony does not
either; the retry covers the common case (the API, the network) and the lock
takeover covers the rest.
