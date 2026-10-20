# Spec: The ticket runner stops only for a real decision

Status: Draft
Ticket: N/A (harness work; key HR-1 for the runner's own tooling)
Change kind: Modify
Supersedes: N/A (extends ADR 0115; no requirement replaced)
Approved by: —
Approved at: —

## Objective

On 2026-10-20 the first real ticket (LD-503) stopped ten times between
the label and `/ship`. Two stops were real decisions. One was a harness
rule (`/build` could not hand tasks to `/test`). One was a headless
difference (`/test` left an agent in the background). Six were the runner:
four of them because it recognised a stage's intent from prose, and the
wording changed each time. The owner restarted the run by hand every time.

This change makes a ticket run from the label to `/ship` with at most one
owner intervention per real decision, and no restart caused by the runner.

In scope: the contract between the stage commands and the runner, the
runner's pre-flight check, its status command, the decision format for
build and test time, one conflict path, and the measures that show the
result. Out of scope: the leadbuster schema fingerprint and test template
(a project change, tracked separately), push notifications, and any new
pipeline stage.

## Change Impact

- Added behavior: REQ-001 (the `HANDOFF` footer), REQ-004 (pre-flight),
  REQ-005 (the `--status` command), REQ-006 (build-time decisions as
  numbered options), REQ-008 (measures).
- Modified behavior: REQ-002 — the runner stops reading prose. Today it
  matches phrases in a report (`build_conflict`, `SPEC_SIGNALS`); after
  this it reads the footer alone. REQ-003 — the three conflict paths in
  `ticket.py` (plan, build at start, build at stop) become one.
- Removed behavior: the prose detectors in `ticket.py` (`SPEC_SIGNALS`,
  the routed-item parser). A report without a footer stops the run with a
  named reason instead of being guessed at.
- Explicitly preserved behavior: ADR 0115 as amended — High-risk questions
  wait for the owner, a default fix keeps the approval, the same conflict
  twice stops, the one Slack thread per ticket, the lock, retries and
  stall, `--watch`, `TICKET STOP` / `TICKET NOTE` / `TICKET ANSWERS`, no
  push ever. pipeline.py's stage order and round cap (ADR 0114).
- Compatibility/migration constraints: a ticket already in flight keeps
  working; the footer is additive to the reports, and a report without one
  is handled by REQ-002 scenario 3.

## Requirements

### Requirement: REQ-001 — Every stage report ends with a HANDOFF footer
Source: LD-503 stops 4, 6, 7 and 9 (prose recognised wrongly); owner decision 2026-10-20 ("a contract, not prose")

When `/plan`, `/build`, `/test` or `/review` ends, the command MUST write a
final line of the form
`HANDOFF: result=<COMPLETE|BLOCKED|PASS|FAIL|CLEAN|FINDINGS> route=<none|/spec|/plan|/build|/test|owner> ids=<REQ/DEC/TD ids or -> decide=<n options or 0>`,
after the report's own result line. `route` names the one stage, or the
person, that acts next. `ids` names what the blocker is about.

#### Scenario: A build blocked on the spec
- GIVEN `/build` stops because an acceptance criterion contradicts the code
- WHEN it writes its report
- THEN the last line is `HANDOFF: result=BLOCKED route=/spec ids=REQ-008 decide=2`

#### Scenario: A build that hands tasks on
- GIVEN every task `/build` owns is done and the plan has a `/test` task and an owner task
- WHEN it writes its report
- THEN the last line is `HANDOFF: result=COMPLETE route=/test ids=T007,T008 decide=0`

#### Scenario: A clean plan
- GIVEN `/plan` produced a plan with no `SPEC CONFLICT` and no `OPEN QUESTION`
- WHEN it writes its report
- THEN the last line is `HANDOFF: result=COMPLETE route=none ids=- decide=0`

#### Scenario: A blocker that is the owner's
- GIVEN `/build` stops because the test database cannot run the suite
- WHEN it writes its report
- THEN the last line is `HANDOFF: result=BLOCKED route=owner ids=- decide=1`

### Requirement: REQ-002 — The runner acts on the footer alone
Source: LD-503 stops 4, 6, 7, 9; AGENTS.md rule 5 (deterministic before probabilistic)

When a stage ends, `ticket.py` and `pipeline.py` MUST decide the next step
from the `HANDOFF` line alone. They MUST NOT match phrases elsewhere in the
report. If the report has no `HANDOFF` line, then the runner MUST stop
with the reason `no HANDOFF line` and the report's path.

#### Scenario: Route to the spec
- GIVEN a report ending in `route=/spec ids=REQ-008`
- WHEN the runner reads it
- THEN it takes the conflict path (REQ-003) with the report's blocker section and the ids

#### Scenario: Route to the owner
- GIVEN a report ending in `route=owner decide=1`
- WHEN the runner reads it
- THEN it posts the decision as numbered options (REQ-006) and waits; nothing is retried

#### Scenario: No footer
- GIVEN `/test` ends with prose and no `HANDOFF` line (an agent left in the background)
- WHEN the runner reads it
- THEN it stops with `no HANDOFF line`, names the file, and the next start runs the same stage again

#### Scenario: Footer and result line disagree
- GIVEN a report with `BUILD COMPLETE` and `HANDOFF: result=BLOCKED`
- WHEN the runner reads it
- THEN it stops with `HANDOFF disagrees with the result line` and names the file

### Requirement: REQ-003 — One conflict path for every stage
Source: LD-503 stops 2, 5 and 7 (three code paths, three bugs); AGENTS.md rule 2

When any stage routes to `/spec`, the runner MUST take one path:
`/spec <T> unattended` with the blocker section and the owner's notes;
then, if the spec's status is still `Approved` and no `OPEN QUESTION`
remains, `/plan` again and the pipeline from its last finished stage;
otherwise the ask to the owner. The same conflict (by its ids) a second
time, or the sixth conflict on a ticket, MUST stop the run.

#### Scenario: Build conflict fixed by default
- GIVEN `/build` routes REQ-008 to `/spec` and `/spec` resolves it as a Low-risk DEC
- WHEN the runner continues
- THEN the owner's approval stands, `/plan` runs, and `/build` resumes after the stages already noted on this HEAD

#### Scenario: The same conflict again
- GIVEN REQ-008 was already taken to `/spec` on this ticket
- WHEN a report routes REQ-008 to `/spec` again
- THEN the runner stops with `the same conflict came back` and the owner is asked

#### Scenario: A conflict found at start
- GIVEN the last run stopped with a report routing to `/spec`, and the spec is unchanged since
- WHEN a new run starts
- THEN it takes the conflict path before any stage runs

### Requirement: REQ-004 — A pre-flight check before the first stage
Source: LD-503 stops 3 (dirty tree), 8 (schema drift), 10 (branch 85 commits behind); owner decision 2026-10-20

When a run starts, or when `ticket.py <T> --check` is called, the runner
MUST report in one message, before any model call that costs more than a
Slack read: the tree state, the commits the branch is behind the default
branch, whether the project's test command can start (the project's own
readiness script, when it has one), the gitignored files the worktree
needs, the Slack and Jira access, and the lock. A failed item MUST stop the
run with that item named; `--check` alone MUST only report.

#### Scenario: Everything ready
- GIVEN a clean worktree, up to date, with a working test command
- WHEN the run starts
- THEN one line per item says `ok` and the first stage starts

#### Scenario: The test command cannot start
- GIVEN the project's readiness script reports the schema snapshot does not match
- WHEN the run starts
- THEN the runner stops before the first stage with `test command cannot start: <its message>` and posts it to the thread

#### Scenario: Branch behind the default branch
- GIVEN the ticket branch is 85 commits behind `main` and the merge is clean
- WHEN the run starts
- THEN the runner merges `main`, commits the merge, reports `merged main: 85 commits` and goes on (DEC-001)

#### Scenario: Merge conflict the merge stage resolves
- GIVEN the merge conflicts in two files
- WHEN the run starts
- THEN a `claude -p` merge stage resolves them, the project's fast checks pass, the merge is committed, and the report names the two files

#### Scenario: Merge conflict that stays
- GIVEN the merge stage cannot resolve a conflict, or its checks fail
- WHEN the run starts
- THEN the runner aborts the merge, stops with `route=owner` and names the conflicted files; the branch is as before

### Requirement: REQ-005 — A status command
Source: owner 2026-10-20 ("say which file to look at"; eleven messages asking where the run was)

When `ticket.py <T> --status` is called, the runner MUST print, without a
model call: the last stage and its result, what the run waits for (the
owner, Slack, a stage, nothing), the path of the last report, the cost so
far, the decisions recorded (DEC ids with who decided), the lock holder,
and the Jira status. When a `--watch` child exits, `--watch` MUST print the same block for it.

#### Scenario: Stopped on a decision
- GIVEN a run stopped on `route=owner decide=1`
- WHEN `--status` runs
- THEN it prints `waits for: you — B1 (1 option set), reply in the thread` and the report path

#### Scenario: Nothing recorded yet
- GIVEN no state file for the ticket
- WHEN `--status` runs
- THEN it prints `no run yet` and exits 0

### Requirement: REQ-006 — Build-time and test-time decisions are numbered options
Source: LD-503 stops 1 and 4 (free-text notes that `/build` could not act on); the spec's Q/D format (ADR 0115)

When a report has `decide=n` with n > 0, the runner MUST post the decision
to the thread as `B<k>` with its numbered options and the recommended one
starred, and MUST accept `TICKET ANSWERS: B1=2` as the answer. The answer
MUST go to the stage the footer routes to (`/spec` as a decision, the next
`/build` as an owner note). A reply that names an unknown option MUST be
refused with the list of valid ones.

#### Scenario: Answer picks an option
- GIVEN a `B1` with options 1 (accept MySQL's plan, recommended) and 2 (change the subquery)
- WHEN the owner replies `TICKET ANSWERS: B1=1 ok`
- THEN `/spec` records DEC-010 with option 1 and the run goes on

#### Scenario: Free text still works
- GIVEN the same `B1`
- WHEN the owner replies `TICKET NOTE: accept MySQL's plan`
- THEN the note goes to the next stage as today, and the `B1` stays open in the status until a stage resolves it

### Requirement: REQ-007 — One inbox
Source: LD-503 stops 3 and 7 (notes read after the first stage; the stop thread not read); AGENTS.md rule 2

The runner MUST read the owner's word from one inbox before every stage,
including the first stage of a run and the first stage of `pipeline.py`.
The inbox MUST take, in one place: the Slack thread replies, `--note`, the
Jira status, and the Jira label. A reply the runner itself posted MUST NOT
count. A read reply MUST get a 👀 reaction.

#### Scenario: Note written while stopped
- GIVEN a `TICKET NOTE` written under the stop message
- WHEN the next run starts
- THEN the first stage's prompt carries it, and the reply shows 👀 before that stage starts

#### Scenario: Own message
- GIVEN the runner's own "Reply here with a TICKET NOTE" in the thread
- WHEN the inbox is read
- THEN it is not a note

### Requirement: REQ-008 — The result is measured per ticket
Source: ADR 0112, 0113 (person stops, cost); the objective's target

When `/ship` ends, `ticket-stats.py` MUST report, per ticket: owner
interventions (replies the runner acted on), runner restarts (starts after
a stop whose cause was the runner, by the stop reason), stage restarts
from retries, conflicts taken to `/spec`, and cost. The runner MUST write
each stop with a cause class (`decision`, `environment`, `harness`,
`runner`, `retry`) to the state, so the report needs no reading of logs.

#### Scenario: LD-503 replayed
- GIVEN the ten LD-503 stop reports as fixtures
- WHEN the runner's tests replay them
- THEN the runner stops for `decision` and `environment` only, and the count of `runner` stops is 0

## Material Decisions

### DEC-001 — A branch behind the default branch is merged at pre-flight
- Decision: when the ticket branch is behind the default branch, the pre-flight merges the default branch into it and commits the merge (`Merge <default> into <branch>`, `Refs: <T>`). A merge conflict is resolved by a `claude -p` merge stage in the worktree, which keeps the ticket's behavior and the default branch's everything else, runs the project's fast checks, and commits. If that stage cannot resolve it, or its checks fail, the run stops with `route=owner` and the conflicted files named. The runner never pushes the merge.
- Alternatives: report only and let the owner merge (first answer, withdrawn the same day: a later branch may need the merge, and a conflict is work the runner can do); stop and ask on every lag (one more stop per run).
- Reason: REQ-004 scenario 3 needs a rule; the schema stop on LD-503 came from an 85-commit lag.
- Source: owner decision 2026-10-20, in reply to Q1 ("merge main; if there is a conflict, fix it")
- Affects: REQ-004

### DEC-002 — The footer is the contract; prose detection is removed, not kept as a fallback
- Decision: `ticket.py` removes `SPEC_SIGNALS` and the routed-item parser once the four commands write the footer. No fallback.
- Alternatives: keep the prose detector as a fallback for an old report (two paths again; the fallback would hide a missing footer).
- Reason: REQ-002; AGENTS.md rules 2 and 5. A missing footer is a command bug and must be seen.
- Source: owner decision 2026-10-20 ("a contract, not prose"); repository precedent `has_conflict()` (ADR 0115: only a heading counts, never prose)
- Affects: REQ-001, REQ-002

## Tech Stack
Python 3 standard library only (as `ticket.py` and `pipeline.py` today); the
commands are Markdown under `dotfiles/claude/commands`; Slack and Jira
through `claude -p` and the owner's connectors.

## Commands
- Tests: `python3 dotfiles/tools/tests/test-ticket.py && python3 dotfiles/tools/tests/test-pipeline.py`
- Checks: `python3 dotfiles/tools/checks/harness-map.py --check`, `python3 dotfiles/tools/tests/test-stale-instructions.py`
- Spec shape: `python3 dotfiles/claude/skills/spec-driven-development/scripts/check-spec.py dotfiles/docs/specs/HR-1-SPEC.md`

## Project Structure
- `dotfiles/tools/run/ticket.py`, `pipeline.py` — the runner
- `dotfiles/claude/commands/{plan,build,test,review}.md` — the stage commands that gain the footer
- `dotfiles/claude/references/templates/` — report shapes
- `dotfiles/tools/tests/test-ticket.py`, `test-pipeline.py`, `fixtures/ld-503/` (new) — tests and the replayed reports
- `dotfiles/tools/checks/harness-map.py` — the Runners section follows the new switches

## Code Style
As the files around: short functions, one-line docstrings, few comments,
state in one JSON file per ticket, `claude -p` for every model call.

## Testing Strategy
- REQ-001: a test per command file that the report template carries the footer line; a `HANDOFF` parser test on the four scenario lines.
- REQ-002, REQ-003: `test-ticket.py` with fixture reports; the no-footer and disagreeing-footer cases.
- REQ-004, REQ-005: `test-ticket.py` with a fixture repository; `--check` and `--status` output asserted line by line.
- REQ-006, REQ-007: `FakeOut` threads; own posts, notes before the first stage, `B1=2` parsing.
- REQ-008: the ten LD-503 reports under `dotfiles/tools/tests/fixtures/ld-503/`, replayed end to end; the stop classes asserted.
- All evidence is traceable to the REQ id in the test name.

## Invariants and Mechanism Proof
- Invariant: a stage's next step is a pure function of its `HANDOFF` line and the ticket state. Enforced in `ticket.py` by one `route()` function; every caller goes through it; tests cover every `result`/`route` pair.
- Invariant: one run per ticket (the lock, ADR 0115) — unchanged.

## Data Lifecycle
The state file gains `stops: [{at, stage, class, reason, report}]` and
`decisions: {B1: {options, chosen}}`. Nothing is deleted; a finished
ticket keeps its state for `ticket-stats.py`. N/A otherwise.

## Boundaries
- Always: run both test files before a push; regenerate the Harness Map when a switch or variable changes; keep the owner's ids out of the repo.
- Ask first: any change to ADR 0115's decisions (who approves, what waits); a new pipeline stage.
- Never: push from the runner; read prose to route a stage; a second conflict path.

## Open Questions

None. Q1 (a branch behind the default branch) was answered on 2026-10-20: DEC-001 (merge; a conflict is resolved by a merge stage, else the owner).
