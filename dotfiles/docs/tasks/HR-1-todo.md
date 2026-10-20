# HR-1 — task packets

Plan: dotfiles/docs/tasks/HR-1-plan.md · Spec: dotfiles/docs/specs/HR-1-SPEC.md

## T001: Every stage report ends with a HANDOFF line, and pipeline.py parses it

**Status:** Done

**Requirements:** REQ-001, TD-001

**Acceptance criteria:**
- [ ] `plan.md`, `build.md`, `test.md`, `review.md` each say, in their report section, that the last line is `HANDOFF: result=… route=… ids=… decide=…`, with the values each command may use (REQ-001)
- [ ] `pipeline.handoff(text)` returns `{result, route, ids: [..], decide: int}` for the four spec scenario lines, and `None` when the line is missing (REQ-001)
- [ ] `handoff()` rejects a `route` outside `none|/spec|/plan|/build|/test|owner` and a `result` outside the closed set, naming the value (REQ-001)
- [ ] `pipeline.py` writes the parsed handoff into `<T>-pipeline-stop.json` when it stops (TD-001)

**Verification:**
- [ ] Tests pass: `python3 dotfiles/tools/tests/test-pipeline.py`
- [ ] Build/static check succeeds: `python3 dotfiles/tools/tests/test-stale-instructions.py`

**Dependencies:** None

**Workstream:** ws-main

**Context pointers:**
- Project/module rules: `dotfiles/claude/AGENTS.md` §Writing for humans (the command prose)
- Closest precedent: the result lines `BUILD COMPLETE` / `VERIFY PASS` / `Findings: n BLOCKER` and `pl.line()`, `pl.review_counts()` in `dotfiles/tools/run/pipeline.py`
- Shared contract/invariant: `dotfiles/docs/specs/HR-1-SPEC.md` REQ-001

**Files/areas likely touched:**
- `dotfiles/claude/commands/plan.md`
- `dotfiles/claude/commands/build.md`
- `dotfiles/claude/commands/test.md`
- `dotfiles/claude/commands/review.md`
- `dotfiles/tools/run/pipeline.py`
- `dotfiles/tools/tests/test-pipeline.py`

**Change-surface search:** `rg -n "BUILD COMPLETE|VERIFY PASS|Findings: |review count line" dotfiles/claude/commands dotfiles/tools/run dotfiles/claude/references`

**Estimated scope:** S

## T002: The runner routes from the parsed footer alone

**Status:** Done

**Requirements:** REQ-002, TD-001

**Description:** `Run.route(handoff, report)` is the one function called after a stage ends. `pipeline.py` branches on `handoff()` for its own order and stops with the parsed line in the stop file. `SPEC_SIGNALS`, `build_conflict()` and the routed-item parser are deleted. `has_conflict()` for a plan stays until T001 lands the footer in `/plan`, then goes too.

**Acceptance criteria:**
- [ ] A report ending in `route=/spec ids=REQ-008` takes the conflict path with the report's blocker section and the ids (REQ-002)
- [ ] A report ending in `route=owner decide=1` posts the decision and waits; nothing is retried (REQ-002)
- [ ] A report without a `HANDOFF` line stops with `no HANDOFF line` and the report's path; the next start runs the same stage again (REQ-002)
- [ ] A report whose result line and footer disagree stops with `HANDOFF disagrees with the result line` and the path (REQ-002)
- [ ] `rg -n "SPEC_SIGNALS|build_conflict|routed" dotfiles/tools/run/ticket.py` prints nothing (REQ-002, DEC-002)

**Verification:**
- [ ] Tests pass: `python3 dotfiles/tools/tests/test-ticket.py && python3 dotfiles/tools/tests/test-pipeline.py`
- [ ] Build/static check succeeds: `python3 dotfiles/tools/checks/harness-map.py --check`

**Dependencies:** T001

**Workstream:** ws-main

**Context pointers:**
- Project/module rules: `dotfiles/claude/AGENTS.md` rules 2 and 5
- Closest precedent: `has_conflict()` in `dotfiles/tools/run/ticket.py` (a heading counts, prose never; ADR 0115)
- Shared contract/invariant: `pipeline.handoff()` (T001); the stop file `<T>-pipeline-stop.json`

**Files/areas likely touched:**
- `dotfiles/tools/run/ticket.py`
- `dotfiles/tools/run/pipeline.py`
- `dotfiles/tools/tests/test-ticket.py`
- `dotfiles/tools/tests/test-pipeline.py`
- `dotfiles/tools/run/README.md`

**Change-surface search:** `rg -n "build_conflict|SPEC_SIGNALS|last_build_conflict|has_conflict|conflict_text" dotfiles/tools`

**Estimated scope:** M

## T003: One conflict path for every stage

**Status:** Done

**Requirements:** REQ-003

**Description:** `Run.resolve(conflict, ids, stage)` replaces the three call sites (`make_plan`, `go()` at start, `go()` after a stop). It runs `/spec <T> unattended` with the blocker and the owner's notes, keeps the approval when the spec stays `Approved` with no `OPEN QUESTION`, then `/plan` and the pipeline from its last finished stage; else the ask. `may_resolve()` keeps the same-conflict and sixth-conflict stops.

**Acceptance criteria:**
- [ ] A build conflict fixed by default keeps the approval; `/plan` runs; `/build` resumes after the stages noted on this HEAD (REQ-003)
- [ ] The same ids routed to `/spec` a second time stop with `the same conflict came back` (REQ-003)
- [ ] A new run whose last stop routed to `/spec`, with the spec unchanged since, takes the conflict path before any stage (REQ-003)
- [ ] `rg -n "back_to_spec" dotfiles/tools/run/ticket.py` shows one definition and calls only from `resolve()` and `make_plan()` (REQ-003)

**Verification:**
- [ ] Tests pass: `python3 dotfiles/tools/tests/test-ticket.py`

**Dependencies:** CP-001

**Workstream:** ws-main

**Context pointers:**
- Project/module rules: `dotfiles/claude/commands/spec.md` §Unattended (ADR 0115)
- Closest precedent: `back_to_spec()`, `may_resolve()`, `conflict_digest()` in `dotfiles/tools/run/ticket.py`
- Shared contract/invariant: ADR 0115 as amended on 2026-10-20 (a default fix keeps the approval)

**Files/areas likely touched:**
- `dotfiles/tools/run/ticket.py`
- `dotfiles/tools/tests/test-ticket.py`

**Estimated scope:** M

## T004: One inbox, read before every stage

**Status:** Done

**Requirements:** REQ-007

**Description:** `Run.inbox()` is the one reader: the ticket's Slack thread from the last seen reply on, `--note` once, the Jira status and label, own posts skipped, 👀 on each reply read. It runs in `stage()`, before the pipeline, and the pipeline's first stage reads the inbox file too. `check_inbox()`, `jira_stop()` and the `--note` merge fold into it.

**Acceptance criteria:**
- [ ] A `TICKET NOTE` written under the stop message while stopped reaches the first stage's prompt of the next run, and its reply shows 👀 before that stage starts (REQ-007)
- [ ] The runner's own "Reply here with a TICKET NOTE" is not a note (REQ-007)
- [ ] One function reads Slack, `--note`, Jira status and label; `rg -n "check_inbox|jira_stop" dotfiles/tools/run/ticket.py` shows no second reader (REQ-007)
- [ ] `pipeline.py` reads the inbox file before its first stage (REQ-007)

**Verification:**
- [ ] Tests pass: `python3 dotfiles/tools/tests/test-ticket.py && python3 dotfiles/tools/tests/test-pipeline.py`

**Dependencies:** CP-001

**Workstream:** ws-main

**Context pointers:**
- Closest precedent: `check_inbox()`, `jira_stop()`, `Run.post()`/`mine()`, `Slack.owner_replies(ts, after)` in `dotfiles/tools/run/ticket.py`
- Shared contract/invariant: the inbox file `<T>-inbox.json` (`HARNESS_INBOX`), ADR 0114

**Files/areas likely touched:**
- `dotfiles/tools/run/ticket.py`
- `dotfiles/tools/run/pipeline.py`
- `dotfiles/tools/tests/test-ticket.py`

**Estimated scope:** M

## T005: Build-time and test-time decisions as numbered options

**Status:** Done

**Requirements:** REQ-006

**Description:** When a footer has `decide=n` (n > 0), `Run.decide(report)` takes the numbered options from the report's blocker section, posts `B<k>` to the thread with the recommended option starred, records `decisions[B<k>]` in the state, and `parse_reply()` accepts `B1=2`. The answer goes to the routed stage: as a decision line to `/spec`, as an owner note to the next `/build`. A free-text `TICKET NOTE` still works and leaves the `B<k>` open in `--status`.

**Acceptance criteria:**
- [ ] A `B1` with two options is posted with the recommended one starred, and `TICKET ANSWERS: B1=1 ok` makes `/spec` record the DEC with option 1 (REQ-006)
- [ ] `TICKET ANSWERS: B1=7` is refused with the valid options listed (REQ-006)
- [ ] A `TICKET NOTE` on the same decision reaches the next stage and the `B1` stays open in the state (REQ-006)
- [ ] The ask text and the Harness Map `SWITCHES` name `B<k>=` (REQ-006)

**Verification:**
- [ ] Tests pass: `python3 dotfiles/tools/tests/test-ticket.py`
- [ ] Build/static check succeeds: `python3 dotfiles/tools/checks/harness-map.py --check`

**Dependencies:** T002, T004

**Workstream:** ws-main

**Context pointers:**
- Closest precedent: `open_questions()`, `ask_text()`, `split_redo()`, `parse_reply()` in `dotfiles/tools/run/ticket.py` (the Q/D format)
- Shared contract/invariant: `HANDOFF` `decide=n`; the state key `decisions`

**Files/areas likely touched:**
- `dotfiles/tools/run/ticket.py`
- `dotfiles/tools/tests/test-ticket.py`
- `dotfiles/tools/checks/harness-map.py`
- `dotfiles/docs/harness-map.html`
- `dotfiles/tools/run/README.md`

**Estimated scope:** M

## T006: Pre-flight before the first stage, with the merge of the default branch

**Status:** Pending

**Requirements:** REQ-004

**Description:** `preflight(args)` runs at start and under `ticket.py <T> --check`. Items, one line each: tree clean; commits behind the default branch (merge and commit per DEC-001; a conflict to a `claude -p` merge stage that runs the project's fast checks; an unresolved one aborts the merge and stops with `route=owner`); the project's readiness script when present (`bin/worktree-doctor.sh --infrastructure` or the one the project names); `.worktreeinclude` files present; a Slack read and a Jira read answer; the lock. `--check` only reports.

**Acceptance criteria:**
- [ ] A ready worktree prints one `ok` line per item and the first stage starts (REQ-004)
- [ ] A readiness script that fails stops before the first stage with `test command cannot start: <its message>`, posted to the thread (REQ-004)
- [ ] A branch 85 commits behind, clean merge: the merge is committed with `Refs: <T>`, the line reads `merged main: 85 commits` (REQ-004, DEC-001)
- [ ] A conflict the merge stage resolves: the project's fast checks pass, the merge is committed, the files are named (REQ-004, DEC-001)
- [ ] A conflict that stays: the merge is aborted, the run stops with `route=owner` and the files, the branch is as before (REQ-004, DEC-001)
- [ ] `--check` alone changes nothing except the merge, and says so (REQ-004)

**Verification:**
- [ ] Tests pass: `python3 dotfiles/tools/tests/test-ticket.py`

**Dependencies:** T004

**Workstream:** ws-main

**Context pointers:**
- Project/module rules: `dotfiles/claude/AGENTS.md` §Worktrees ("pull first"; reconcile infrastructure without merging unrelated ticket work — DEC-001 overrides this for the runner, by the owner's decision)
- Closest precedent: `ticket_checkout()`, `claim()`, `default_branch()` in `dotfiles/tools/run/ticket.py`; `checkout_problem()` in `pipeline.py`
- Shared contract/invariant: DEC-001; the runner never pushes

**Files/areas likely touched:**
- `dotfiles/tools/run/ticket.py`
- `dotfiles/tools/tests/test-ticket.py`
- `dotfiles/tools/run/README.md`

**Change-surface search:** `rg -n "status', '--porcelain'|default_branch\(|worktreeinclude" dotfiles/tools/run`

**Estimated scope:** M

## T007: A status command

**Status:** Pending

**Requirements:** REQ-005

**Acceptance criteria:**
- [ ] `ticket.py <T> --status` prints, without a model call: last stage and result, what the run waits for, the last report's path, cost so far, the DEC ids with who decided, the lock holder, the Jira status as last read (REQ-005)
- [ ] A stopped `route=owner decide=1` run prints `waits for: you — B1 (1 option set), reply in the thread` and the report path (REQ-005)
- [ ] No state file: `no run yet`, exit 0 (REQ-005)
- [ ] A state file written before this change (no `stops`, no `decisions`) loads and prints (REQ-005)
- [ ] `--watch` prints the same block when a child exits (REQ-005)

**Verification:**
- [ ] Tests pass: `python3 dotfiles/tools/tests/test-ticket.py`

**Dependencies:** T006

**Workstream:** ws-main

**Context pointers:**
- Closest precedent: `stop()`, `claim_holder()`, `shipped()` in `dotfiles/tools/run/ticket.py`

**Files/areas likely touched:**
- `dotfiles/tools/run/ticket.py`
- `dotfiles/tools/tests/test-ticket.py`
- `dotfiles/tools/run/README.md`

**Estimated scope:** S

## T008: Stop classes, per-ticket counts, and the LD-503 replay

**Status:** Pending

**Requirements:** REQ-008

**Description:** Every stop writes `{at, stage, class, reason, report}` to the state, class in `decision | environment | harness | runner | retry`, set by the code that stops. `ticket-stats.py` reports owner interventions, runner restarts, stage retries, conflicts to `/spec`, and cost per ticket. The LD-503 reports from 2026-10-20 (the owner's `handoff/LD-503-*` files: three `BUILD BLOCKED`, one `BUILD COMPLETE`, the `/test` report without a result line, the plan with a conflict) become fixtures under `dotfiles/tools/tests/fixtures/ld-503/`, with the owner's ids and channel removed, and replay through `route()`.

**Acceptance criteria:**
- [ ] Each stop in the state carries a class, and `--status` shows it (REQ-008)
- [ ] `ticket-stats.py` prints the five counts and the cost for a ticket from its state file (REQ-008)
- [ ] The LD-503 fixtures replayed through the runner give stops of class `decision` and `environment` only; `runner` stops = 0 (REQ-008)
- [ ] The fixtures carry no Slack channel id, email or Slack user id (REQ-008; Boundaries)

**Verification:**
- [ ] Tests pass: `python3 dotfiles/tools/tests/test-ticket.py && python3 dotfiles/tools/tests/test-ticket-stats.py`

**Dependencies:** T003, T005, T006

**Workstream:** ws-main

**Context pointers:**
- Project/module rules: ADR 0112, ADR 0113 (what `ticket-stats.py` counts today)
- Closest precedent: `dotfiles/claude/skills/spec-driven-development/scripts/ticket-stats.py`, `dotfiles/tools/tests/test-ticket-stats.py`
- Shared contract/invariant: the state file keys `stops`, `decisions` (plan §Contracts)

**Files/areas likely touched:**
- `dotfiles/tools/run/ticket.py`
- `dotfiles/claude/skills/spec-driven-development/scripts/ticket-stats.py`
- `dotfiles/tools/tests/test-ticket.py`
- `dotfiles/tools/tests/test-ticket-stats.py`
- `dotfiles/tools/tests/fixtures/ld-503/`

**Estimated scope:** M
