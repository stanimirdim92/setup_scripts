# Implementation Plan: The ticket runner stops only for a real decision

Status: Draft
Spec: dotfiles/docs/specs/HR-1-SPEC.md
Modules: N/A
Not yet planned: None
Spec status: Approved
Spec revision: git-commit:b6cc02fee4dafe307c053f1cb3ea6d27501f9890:dotfiles/docs/specs/HR-1-SPEC.md
Approved by: —
Approved at: —

## Technical Approach

### Current Flow
`ticket.py` runs each stage with `claude -p` through `pipeline.claude()`
and reads the stage's prose to decide what comes next: `has_conflict()`
for a plan (a heading), `build_conflict()` and `SPEC_SIGNALS` for a
build report (phrases), `pl.line()` for `BUILD COMPLETE` / `VERIFY PASS`
/ the review count line. Three places send a conflict to `/spec`
(`make_plan`, `go()` at start, `go()` after a pipeline stop). The inbox is
read in `check_inbox()` before `stage()` and before the pipeline; notes
from `--note` join there. No pre-flight: the dirty tree, the schema and
the lag behind `main` were each found by a failed stage. No status
command; the owner reads the terminal or asks.

### Proposed Flow
1. Each of `/plan`, `/build`, `/test`, `/review` ends its report with
   one `HANDOFF:` line (REQ-001). The commands' templates carry it.
2. `pipeline.handoff(text)` parses that line into `{result, route, ids,
   decide}`; a missing or disagreeing line is an error the stage returns
   (REQ-002). `pipeline.py` and `ticket.py` branch on the parsed dict only.
3. `Run.route(handoff, report)` is the one function after a stage:
   `route=/spec` → `Run.resolve(conflict)` (REQ-003); `route=owner` →
   `Run.decide(report)` posts `B<k>` (REQ-006); `route=/test|/plan|
   /build|none` → the pipeline's next step. The three conflict call sites
   become calls to `resolve()`.
4. `Run.inbox()` is the one reader (REQ-007): Slack threads from the last
   seen reply, `--note` once, Jira status and label, own posts skipped,
   👀 on each reply read. It runs in `stage()`, before the pipeline, and
   `pipeline.py` reads the inbox file before its first stage.
5. `preflight(args)` (REQ-004) runs before the first stage and under
   `--check`: tree, lag behind the default branch (merge per DEC-001, a
   conflict to the merge stage), the project's readiness script, the
   `.worktreeinclude` files, Slack/Jira reads, the lock. One block of
   lines; a failed item stops before any stage.
6. `status(args)` (REQ-005) prints from the state file and the handoff
   dir; `--watch` prints it when a child exits.
7. Every stop is written to the state with a class; `ticket-stats.py`
   reports the counts; the LD-503 reports replay as fixtures (REQ-008).

### Components and Responsibilities
- `dotfiles/claude/commands/{plan,build,test,review}.md`: write the `HANDOFF:` line (NEW rule).
- `dotfiles/tools/run/pipeline.py`: `handoff()` (NEW), `HEADLESS`, stage order; branches on the parsed handoff.
- `dotfiles/tools/run/ticket.py`: `Run.route()`, `Run.resolve()`, `Run.decide()`, `Run.inbox()`, `preflight()`, `status()` (NEW); the prose detectors removed.
- `dotfiles/claude/skills/spec-driven-development/scripts/ticket-stats.py`: the per-ticket counts (REQ-008).
- `dotfiles/tools/tests/fixtures/ld-503/`: the replayed reports (NEW).
- `dotfiles/tools/checks/harness-map.py`: `SWITCHES` and `ENV` follow (`B<k>=`, `--check`, `--status`).

### Affected Areas
- `dotfiles/claude/commands/plan.md`, `build.md`, `test.md`, `review.md`
- `dotfiles/claude/references/templates/` (report shape where one exists)
- `dotfiles/tools/run/ticket.py`, `pipeline.py`, `ticket-stats.py`, `README.md`
- `dotfiles/tools/tests/test-ticket.py`, `test-pipeline.py`, `test-ticket-stats.py`, `fixtures/ld-503/`
- `dotfiles/tools/checks/harness-map.py`, `dotfiles/docs/harness-map.html`
- `dotfiles/docs/adr/0115-ticket-runner-end-to-end.md` (amendment), `dotfiles/docs/HANDOFF.md`

## Decisions and Provenance
- The footer is one line, key=value, at the end of the report — spec REQ-001; mirrors the commands' own result lines (`BUILD COMPLETE`, `VERIFY PASS`), which the runner already reads mechanically.
- Prose detectors are removed, not kept as a fallback — spec DEC-002.
- One `route()` after every stage; the pipeline calls it through the inbox file, not by importing `ticket.py` — mirrors today's `HARNESS_INBOX` handshake (ADR 0114/0115).
- Pre-flight merges the default branch; a conflict goes to a `claude -p` merge stage — spec DEC-001.
- The stop class is written by the code that stops, never inferred later — AGENTS.md rule 5.

### TD-001 — Where the pipeline learns the next step
- Choice: `pipeline.py` parses the footer itself for its own order (build → test → review) and writes `{handoff}` into the stop file; `ticket.py` reads the stop file for `route`. No new channel.
- Alternatives: `pipeline.py` asks `ticket.py` through the inbox file after every stage (a round trip and a 300 s wait per stage); `ticket.py` runs the three stages itself (removes `pipeline.py`, a larger change than asked).
- Reason: the stop file already carries `why` and `stage_file`; adding the parsed handoff keeps one writer and one reader (REQ-002).
- Source: REQ-002, ADR 0114
- Affects: T001, T002

## Contracts and Data Changes

### Contract: HANDOFF line
- Owner: the stage commands (`dotfiles/claude/commands/*.md`)
- Consumers: `pipeline.py`, `ticket.py`, `ticket-stats.py`
- Authoritative definition: `dotfiles/docs/specs/HR-1-SPEC.md` REQ-001; the parser `pipeline.handoff()`
- Compatibility: additive (a report without it is an error per REQ-002, by DEC-002)
- Stabilization checkpoint: CP-001

### Contract: ticket state file
- Owner: `ticket.py`
- Consumers: `ticket-stats.py`, `--status`
- Authoritative definition: `dotfiles/tools/run/ticket.py` `Run.save()`; keys `stops`, `decisions` added
- Compatibility: additive
- Stabilization checkpoint: CP-001

## Workstreams
- ws-main: everything; sequential, one executor. The runner and its tests are one surface.

## Task Index
- [ ] T001 (S, ws-main, deps: —) [REQ-001, TD-001]: the four commands end every report with the `HANDOFF:` line, and `pipeline.handoff()` parses it
- [ ] T002 (M, ws-main, deps: T001) [REQ-002, TD-001]: the runner routes from the parsed footer alone; prose detectors removed; no-footer and disagreeing-footer stops

### CP-001 — Checkpoint: the stage contract is established
- [ ] `python3 dotfiles/tools/tests/test-pipeline.py && python3 dotfiles/tools/tests/test-ticket.py` pass
- [ ] `python3 dotfiles/tools/checks/harness-map.py --check` and `python3 dotfiles/tools/tests/test-stale-instructions.py` pass
- [ ] No regex over report prose remains in `ticket.py` (`rg -n "SPEC_SIGNALS|build_conflict|routed" dotfiles/tools/run/ticket.py` is empty)

- [ ] T003 (M, ws-main, deps: CP-001) [REQ-003]: one `resolve()` path for a conflict from any stage; the same conflict again or the sixth stops
- [ ] T004 (M, ws-main, deps: CP-001) [REQ-007]: one `inbox()` read before every stage, the pipeline's first included; own posts skipped; 👀 on each reply
- [ ] T005 (M, ws-main, deps: T002, T004) [REQ-006]: `decide=n` becomes a `B<k>` post with numbered options; `TICKET ANSWERS: B1=2` answers it; the answer reaches the routed stage
- [ ] T006 (M, ws-main, deps: T004) [REQ-004]: `preflight()` before the first stage and under `--check`; merge of the default branch per DEC-001 with the merge stage
- [ ] T007 (S, ws-main, deps: T006) [REQ-005]: `--status` prints the run's state without a model call; `--watch` prints it when a child exits
- [ ] T008 (M, ws-main, deps: T003, T005, T006) [REQ-008]: stop classes in the state, `ticket-stats.py` counts, the LD-503 reports replayed as fixtures with 0 `runner` stops

## Requirement Coverage
- REQ-001 → T001 → command-file tests for the footer line; `handoff()` parser tests on the four scenario lines
- REQ-002 → T002 → fixture reports through `route()`; the no-footer and disagreeing-footer cases
- REQ-003 → T003 → the three conflict scenarios in `test-ticket.py`
- REQ-004 → T006 → `--check` output asserted line by line on a fixture repository; merge, resolved conflict, unresolved conflict
- REQ-005 → T007 → `--status` output on a stopped run and on no run
- REQ-006 → T005 → `B1=1 ok` and a free-text note on the same decision
- REQ-007 → T004 → note before the first stage; own post skipped; 👀 counted
- REQ-008 → T008 → `test-ticket-stats.py` on a state file; the LD-503 replay with its stop classes

Unmapped requirements: None
Orphan tasks: None

## Verification Strategy
- Task-focused: `python3 dotfiles/tools/tests/test-ticket.py` or `python3 dotfiles/tools/tests/test-pipeline.py` (the file the task changes)
- Workstream: both test files
- Integrated: `python3 dotfiles/tools/tests/test-ticket.py && python3 dotfiles/tools/tests/test-pipeline.py && python3 dotfiles/tools/tests/test-ticket-stats.py && python3 dotfiles/tools/checks/harness-map.py --check && python3 dotfiles/tools/tests/test-stale-instructions.py`
- Data/migration: a state file written before this change loads and `--status` reads it (T007 test)
- Manual/operational: one real ticket through `--watch` after T008; the owner counts interventions against the state's `stops`

## Risks and Mitigations

| Risk | Trigger/evidence | Mitigation | Task/checkpoint |
|---|---|---|---|
| A command forgets the footer on one path | `no HANDOFF line` stops in a real run | The commands' templates carry it; each command file has a test that its report shape names it; the stop names the file | T001, CP-001 |
| The model writes the footer with a wrong `route` | A conflict sent to the wrong stage | `route` is a closed set; an unknown value stops with the line quoted; the replay fixtures cover the four real routes | T002, T008 |
| The merge stage changes ticket behavior while resolving a conflict | Tests that passed before the merge fail after | The merge stage runs the project's fast checks and aborts the merge on failure; the branch is as before | T006 |
| Removing the prose detectors breaks an in-flight ticket | A report from before the change | DEC-002: it stops with the file named; the owner restarts the stage once | T002 |

## Open Questions
None

---
Handoff: Awaiting plan approval
