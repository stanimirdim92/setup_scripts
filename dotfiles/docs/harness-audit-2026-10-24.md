# Harness audit, 2026-10-24: every command, its references and its agents

The harness has many moving parts: 7 commands, 7 personas, 18 references,
19 skills, 10 hooks, 11 scripts and 2 runners. This audit reads all of them
together and asks one question per edge: does the file on one side still say
what the file on the other side expects?

Method. Every command, agent and reference was read in full. The skill files a
command invokes were read in full (`spec-driven-development`,
`planning-and-task-breakdown`, `jira-ticket`, `executor-development-discipline`)
or by section. The runners (`tools/run/ticket.py`, `tools/run/pipeline.py`)
were read for the prompts they send and the lines they parse. Then the
mechanical checks ran: `check-references.py` (114 files, 0 broken),
`validate-frontmatter.py` (8 files, 0 problems), `validate-artifact-paths.py`
(26 files, 0 errors), `harness-map.py --check` (current), every `--help` of
the 11 scripts against the flags the commands use (all match), every ADR
number named in a command, agent, reference or skill (all exist), and every
skill-local `references/*.md` link (all exist).

Result in one line: the files link correctly and the scripts match their
callers. The problems are in meaning, not in links: two edges the runner
cannot follow, one `/build` mode the runner invokes that no command defines,
and one reference that documents the harness as it was six ADRs ago.

Part 1 is the map. Part 2 is the findings, ranked. Part 3 is the plan.

**Status, same day.** Steps 1–5 of the plan are done, one commit each,
every suite green after each and all together (7 bash hook tests, 18
python tests, the 5 checks, `test-pipeline.py` 38, `test-ticket.py` 92).
A-1, A-2, B-1 to B-5 and C-8 are closed; C-6 and C-7 stay open by
choice; step 6 (a real ticket) is the proof still owed.

---

## Part 1. The map

### Pipeline

```
intake (jira-ticket skill)
  -> /spec   -> /plan  -> /build -> /test -> /review -> /ship
                 ^          |        |         |          |
                 |          v        v         v          v
                 +--------- /spec (behavior)   /build (a fix)   owner (decide=n)
/explain: a reading aid after /build or /review, outside the gates
```

Interactive: the owner invokes each stage after `/clear` (ADR 0084).
Unattended: `ticket.py` drives intake, `/spec`, `/plan`, then `pipeline.py`
for `/build` → `/test` → `/review` with fix rounds, then `/ship`. Every stage
report ends with `HANDOFF: result=… route=… ids=… decide=…`
(`references/stage-handoff.md`); the runners route from that line alone.

### Intake: `jira-ticket` skill (`/jira-ticket <KEY>`)

| | |
|---|---|
| Owns | Fetch the ticket and its whole hierarchy; write `docs/specs/<T>-intake.md`; stop |
| Reads | Jira (CLI, MCP or pasted), Figma nodes named by any ticket in scope |
| References | none |
| Agents | none |
| Output | the intake file with Source Coverage, Requirements, AC, Blockers, `Next action: /clear, then /spec` |
| Runner | `ticket.py` runs `/jira-ticket <T>` first, stops `harness` when the file is missing |

Notes. The skill is invoked as a slash command. That works in an interactive
session; the unattended path has not yet run a real intake through `claude -p`
(LD-503's intake was done by hand). Verify on the first `--watch` ticket.

### `/spec` (model `opus[1m]`)

| | |
|---|---|
| Owns | Requirements, decisions, approval state. Never `Approved` on its own |
| Skill | `spec-driven-development` (required): scope check, OPEN QUESTION format, evidence order, templates, Approval Check |
| References | `repository-precedent.md` §1 (evidence path, `repo-recon` dispatch), `spec-quality-gates.md` §1–5 (approval assertions, status table, REQ chain, invariant proof, lifecycle), `risk-tiers.md` (question risk in unattended mode), `templates/spec.md`, `templates/bugfix-spec.md`, `documentation-practices.md` §Project documentation |
| Agents | `repo-recon` (one per disjoint area, when §1 selects it) |
| Scripts | `check-spec.py` after save |
| Terminal | header `Status: Draft \| Approved \| Needs reapproval \| Superseded`; interactive report ends with `/spec <T> decisions: Q1=…` when questions remain |
| HANDOFF | none. The runner reads the spec file: header and `OPEN QUESTION` blocks |
| Runner | `/spec <T> unattended` → `settle_spec()` posts High questions + defaults as `D<n>`; `TICKET ANSWERS: 1A ok` → `/spec <T> decisions: …`; approval set by `ticket.py` only from the owner's reply naming the ticket. A SPEC CONFLICT from any later stage returns here through `Run.resolve()` |

Consistency. `spec.md` ↔ skill ↔ `spec-quality-gates.md` agree on status
transitions, ids and the decision brief (ADR 0116). The unattended rules in
`spec.md` match `ticket.py`. One asymmetry: `/spec` is the only gate command
without a HANDOFF line; the runner parses the spec document instead. That is
structured (header lines, `OPEN QUESTION:` blocks, `Risk:` lines) and tested,
so it is acceptable; see C-6.

### `/plan` (model `opus[1m]`)

| | |
|---|---|
| Owns | Tasks, workstreams, checkpoints, `TD-###`, spec pin |
| Skill | `planning-and-task-breakdown` (required) |
| References | `plan-quality-gates.md` §1–6 (status, pin, ids, approval checks, spikes, ledger), `repository-precedent.md` §1, `templates/plan.md`, `templates/task.md`, `documentation-practices.md`, `definition-of-done.md` (via the skill), `stage-handoff.md` |
| Agents | `repo-recon` when evidence is missing or stale |
| Scripts | `check-plan.py plan --todo … --spec …` |
| Terminal | `Status: Draft \| Approved \| Needs replan \| Superseded`; `Handoff: Ready for /build`; or a bounded `SPEC CONFLICT` |
| HANDOFF | `COMPLETE route=none` · `BLOCKED route=/spec ids=REQ… decide=n` · `BLOCKED route=owner` |
| Runner | `make_plan()`: takes each pre-authorization's recommended default as a TD; approves when `check-plan.py` passes with no conflict and no open question (ADR 0115); `route=/spec` → `resolve()`; commits plan + todo |

Consistency. The pre-authorization block (ADR 0116) is in `plan.md`, the
skill, the plan template (`TD-002 — Pre-authorized`) and `executor.md` ("a
stop the plan pre-authorizes is not a stop"). Good chain. The external-tool
probe is in `plan.md`, the skill, the template and `plan-quality-gates.md` §4.

### `/build` (no model line: session model)

| | |
|---|---|
| Owns | Orchestration and integration. Never implements |
| Skill | none of its own; selects the executor's extras (`api-and-interface-design`, `deprecation-and-migration`, `security-and-hardening`, `figma-design-to-code`, `vercel-composition-patterns`, `vite`, `vitest`) |
| References | `target-selection.md` (+ §Gate handoffs), `plan-quality-gates.md` §2 (pin diff) and §6 (open items), `verification-triggers.md` (browser criteria go to `/test`), `documentation-practices.md`, `stage-handoff.md` |
| Agents | `executor`, one per workstream, resumed under 15 min idle / 350k context (owner, 2026-10-24); fresh for review fixes |
| Scripts | `junit-diff.py` (test baseline), project `bin/worktree-doctor.sh --infrastructure`, `check-ledger.py` (§4 work outside `/build`) |
| Hooks on the way | `require-worktree-for-writers.sh` at dispatch; the executor's own `block-agent-push.sh`, `require-commit-trailers.sh`, `require-handoff-report.sh` |
| Terminal | **BUILD COMPLETE** \| **BUILD BLOCKED** |
| HANDOFF | `COMPLETE route=none` · `COMPLETE route=/test ids=T…` (handed on) · `BLOCKED route=/spec\|/plan\|owner` |
| Modes | planned tasks · `<T> review fixes` (reads the newest SARIF, fresh executor per finding group) |
| Runner | `pipeline.py` stage 1; on `route=/spec`/`/plan`/`owner` the stop file carries the parsed line and `ticket.py` routes |

Consistency. The executor packet list in `build.md` matches `executor.md`
§Input field for field. The resume rule is the same in `AGENTS.md`,
`build.md` §2 and ADR 0116. **Gap A-2:** `pipeline.py` sends
`/build <T> verify fixes` after a VERIFY FAIL, and `build.md` defines no such
mode; its only fix mode reads a review SARIF, which a VERIFY FAIL never
writes.

### `/test`

| | |
|---|---|
| Owns | The independent VERIFY gate: run the change for real |
| References | `target-selection.md`, `verification-triggers.md`, `risk-tiers.md` (tier and depth; the higher of its own and `/review`'s), `plan-quality-gates.md` §2, `stage-handoff.md` |
| Agents | one `test-engineer` in an isolated worktree; a fresh one for every re-verification; an optional short-lived one for browser checks |
| Skills it selects | `browser-testing-with-devtools` for anything a browser renders, `figma-design-to-code` for "matches the design" |
| Hooks on the way | `require-worktree-for-writers.sh`, `require-isolated-test-runner.sh` (global, evidence-gated), the persona's push/trailer/handoff hooks |
| Terminal | **VERIFY PASS** \| **VERIFY FAIL** \| **VERIFY BLOCKED** |
| HANDOFF | `PASS route=none` · `FAIL route=/build ids=REQ… decide=n` · `FAIL route=/spec` (only a spec decision) · `BLOCKED route=owner` |
| Runner | `pipeline.py` stage 2; `FAIL route=/build` → `/build <T> verify fixes` then `/test` again, two rounds at most; anything else stops and `ticket.py` routes |

Consistency. `test.md` ↔ `test-engineer.md` agree on the packet, the runtime
lines, the mutation probes and the Deep rules (ADR 0116). The persona says
`/test` always sets the Risk · Depth line; `test.md` does. **Gap B-3:**
`test.md` never names the tasks `/build` hands on ("Handed on: T007 → /test");
the verifier only learns them through the BUILD message. **Gap A-1 (half):**
`test.md` says a higher tier set later by `/review` means "re-verify at the
higher depth", but no file says who starts that re-verification.

### `/review`

| | |
|---|---|
| Owns | Whether `/test` is required; which reviewers run; findings with dispositions; the SARIF |
| References | `target-selection.md`, `verification-triggers.md`, `reviewer-triggers.md`, `risk-tiers.md`, `component-response-contracts.md` §Dispositions and §Review SARIF, `templates/review.md` (the project's `REVIEW.md` shape), `plan-quality-gates.md` §6, `stage-handoff.md` |
| Agents | `code-reviewer` + `blind-reviewer` + `security-auditor` always; `distributed-systems-reviewer` by trigger; a fresh opposite reviewer per BLOCKER (ADR 0092); at most 2 concurrently |
| Scripts | `weakened-tests.py --base`, `always-person.py --base`, `stale-instructions.py --base`, `check-ledger.py <T>`, `review-noise.py --classes` |
| Terminal | count line (`**Findings: N BLOCKER · N REQUIRED · N ADVISORY**` or `**Nothing to fix.**`), **REVIEW BLOCKED**; SARIF at `<git-common-dir>/review/<T>-<sha>.sarif` |
| HANDOFF | `CLEAN route=none` · `FINDINGS route=/build ids=…` · `… route=/test` (browser checks remain, no BLOCKER/REQUIRED) · `BLOCKED route=owner` |
| Runner | `pipeline.py` stage 3: `said_ok` = count line with 0 BLOCKER and 0 REQUIRED and no REVIEW BLOCKED; `CLEAN` → done, ready for `/ship`; otherwise `/build <T> review fixes` up to 3 reviews |

Consistency. The reviewer packets in `review.md` match `reviewer-triggers.md`
and the four persona files. Dispositions are defined once
(`component-response-contracts.md` §Dispositions) and every persona points
there. **Gap A-1:** `review.md` emits `route=/test` and the runner has no
REVIEW → TEST edge. **Gap B-1:** `CLEAN` versus `FINDINGS` is undefined for
an ADVISORY-only review; the runner's `said_ok` treats it as clean, so a
reviewer that writes `FINDINGS` for ADVISORY-only stops the pipeline as a
disagreement.

### `/ship`

| | |
|---|---|
| Owns | GO / NO-GO / SHIP BLOCKED. Synthesizes; dispatches nothing |
| References | `target-selection.md` §Gate handoffs, `plan-quality-gates.md` §6, `risk-tiers.md` (what the owner reads), `component-response-contracts.md` §Dispositions and §Review SARIF (resolutions), `stage-handoff.md` |
| Scripts | `check-ledger.py <T> --ship`, `ticket-stats.py <T>`, `base-check.sh --base origin/<b> -- <integrated commands>`, `review-noise.py --repeats` |
| Terminal | `## Ship Decision: GO \| NO-GO \| SHIP BLOCKED` with the fixed block |
| HANDOFF | `GO route=none` · `NO-GO route=/build ids=…` or `route=owner` · `BLOCKED route=owner decide=n` (open items) or `route=/build` — added today |
| Runner | `ticket.py`: `ship_result()` from the heading, `pl.verdict()` against the line; `route=owner decide=n` → `B<k>` and `/ship` runs again with the answer; GO/NO-GO final, Jira comment, GO moves the ticket |

Consistency. `ship.md` ↔ `component-response-contracts.md` §5 `/ship` block
agree on the report shape. The open-item rule (never decide one itself,
ADR 0116) is in `ship.md`, `templates/open-items.md` and `check-ledger.py
--ship`. **Gap B-2:** `component-response-contracts.md` §5 still describes
`/ship` as ending with the multi-select question only, with no HANDOFF line
and no unattended path.

### `/explain`

Reads existing artifacts, writes one HTML page under `.git/explain/`, no
agents, no gate, no HANDOFF. Its sources table names `/build`, `/review`,
`/test` and `/ship` messages "in this conversation"; under the runner those
live in `<git-common-dir>/handoff/`. Not a defect (it is interactive-only),
noted under C-7.

### Personas

| Persona | Model · effort · tools | Hooks | Dispatched by | Report |
|---|---|---|---|---|
| `repo-recon` | sonnet-5-5 · Read/Grep/Glob · 100 turns | — | `/spec`, `/plan` | `## Recon:` with Touch points and Claimed reuse |
| `executor` | sonnet-5-5 · Read/Edit/Write/Bash/Grep/Glob/Skill/figma · skills preloaded | push, trailers, handoff | `/build` only | bullet handoff |
| `test-engineer` | sonnet-5-5 · + chrome-devtools · `isolation: worktree` | push, trailers, handoff | `/test` (direct only on request) | runtime line per surface, evidence per REQ, mutation probes |
| `code-reviewer` | opus[1m] · high · read-only | — | `/review` always | `## Review Summary`, `CODE-N` |
| `blind-reviewer` | opus[1m] · high · read-only | — | `/review` always | `## Blind Review`, `BLIND-N`, "What this change appears to do" |
| `security-auditor` | opus[1m] · high · read-only | — | `/review` every round (ADR 0102) | `SEC-N` |
| `distributed-systems-reviewer` | opus[1m] · high · read-only | — | `/review` by trigger | `DIST-N` |

`validate-frontmatter.py` pins these to ADR 0055 and passes.
`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=1` in `settings.json` enforces
"personas do not dispatch personas" at the runtime, not only by instruction.

### References, and who reads each

| Reference | Readers | State |
|---|---|---|
| `stage-handoff.md` | `/plan` `/build` `/test` `/review` `/ship`, both runners | current (ship added today) |
| `target-selection.md` | `/build` `/test` `/review` `/ship` `/explain` | current |
| `verification-triggers.md` | `/build` `/review` `/test`, `test-engineer`, `docs/agents.md` | current, single source |
| `reviewer-triggers.md` | `/review`, the four reviewers | current |
| `risk-tiers.md` | `/spec` (unattended) `/test` `/review` `/ship` | current |
| `spec-quality-gates.md` | `/spec`, the spec skill, `/plan` | current |
| `plan-quality-gates.md` | `/plan` `/build` `/test` `/review` `/ship`, `AGENTS.md` | current |
| `repository-precedent.md` | `/spec` `/plan`, `repo-recon`, executor skill | current |
| `component-response-contracts.md` | every persona (§Dispositions), `/review` (§SARIF), `/ship` | **stale in §1, §3, §5** (B-2) |
| `definition-of-done.md` | planning skill, `incremental-implementation`, executor skill | current |
| `agent-run-metrics.md` | `/build` (run metrics) | one stale term ("REVIEW NO-GO") |
| `documentation-practices.md` | `/spec` `/plan` `/build`, `repo-recon`, executor skill | current |
| `security-checklist.md`, `ai-security.md`, `supply-chain.md` | `security-auditor` by changed risk | content; not audited line by line |
| `testing-patterns.md` | `test-driven-development` only | content |
| `repository-precedent-example.md` | `repository-precedent.md` | example |
| `templates/*` (6) | `/spec` `/plan` `/review` `/ship` and the skills | current |

### Guards

| Hook | Where | Guards |
|---|---|---|
| `block-destructive-bash.sh` | global PreToolUse Bash | a fixed destructive list |
| `warn-force-push.sh` | global | asks on force-push to main; plain push in a local IDE |
| `require-isolated-test-runner.sh` | global, evidence-gated | bare `php artisan test` with >1 worktree and `bin/worktree-test.sh` present |
| `require-worktree-for-writers.sh` | global PreToolUse Agent\|Task | executor/test-engineer dispatch needs a verified ticket checkout and ready infrastructure |
| `format-edited-file.sh` | global PostToolUse Edit\|Write | the project's own formatter (ADR 0107) |
| `warn-stale-base.sh` | SessionStart | stale default branch or fresh ticket worktree |
| `block-agent-push.sh` | executor, test-engineer | any push or `gh` publish |
| `require-commit-trailers.sh` | executor, test-engineer | `Refs:` trailer on every new commit message |
| `require-handoff-report.sh` | executor, test-engineer Stop | the handback carries verification, commit and tree state (reads `SubagentHandback`, ADR 0116) |
| `worktree-readiness.sh` | sourced library | `bin/worktree-doctor.sh --infrastructure` |

All ten have tests in `tools/tests/` and CI runs them.

---

## Part 2. Findings, ranked

**A** breaks or strands a run. **B** misleads a reader or a model. **C** polish.

### A-1. The runner has no REVIEW → TEST edge, and two files produce one

`review.md` §4: a finding that needs a browser goes to the verifier, and the
handoff line is `route=/test` "when browser checks remain and no BLOCKER or
REQUIRED does". `test.md` §2: "If `/review` later sets a higher tier than the
packet carried, the earlier VERIFY result does not cover it. Re-verify at the
higher depth." `agent-run-metrics.md` even counts the "REVIEW → TEST → REVIEW"
loop. But:

- `pipeline.py` reads `/review` as done when the count line has 0 BLOCKER and
  0 REQUIRED and `result=CLEAN`. A `CLEAN route=/test` report is treated as
  clean: the pipeline exits 0 and `ticket.py` runs `/ship` with browser
  checks never run. A `FINDINGS route=/test` report is a verdict disagreement
  and stops the run.
- `review.md` §2 does not say what to do when its own tier is higher than the
  depth the VERIFY PASS was run at. The sentence that asks for re-verification
  is in `test.md`, which is not running at that point.

Fix. In `review.md` §2: a VERIFY PASS at a lower depth than the tier set here
is stale; record **Independent verification: STALE (depth)** and end with
`result=FINDINGS route=/test ids=- decide=0`, the same route as remaining
browser checks. In `pipeline.py`: on `route=/test` from `/review`, run
`/test <T>` with the REVIEW result supplied (the browser checks and the new
depth are in it), then `/review` again on the same candidate; this verifier
round does not count toward the 3-review cap; cap it at one per candidate so
a verifier that cannot run the check stops with `route=owner`. Add the
fixture (`fixtures/ld-503/10-review-route-test.md`) and the test.
Effort: M. Files: `review.md`, `test.md` (name the REVIEW-supplied packet),
`pipeline.py`, `test-pipeline.py`, `stage-handoff.md` (example).

### A-2. `/build <T> verify fixes` is sent by the runner and defined nowhere

`pipeline.py` line 379 sends `/build <T> verify fixes` with the VERIFY FAIL
report after a production defect. `build.md` has §Review fixes only, whose
step 1 reads the newest review SARIF and requires its sha to be HEAD. After
a VERIFY FAIL there is no SARIF, or an old one, so a literal reading of
`build.md` gives BUILD BLOCKED or a blind fix of the wrong thing. LD-503 got
through this on model judgement, which is what the HANDOFF work removed
everywhere else.

Fix. Add `## Verify fixes` to `build.md`, next to Review fixes: scope is the
`REQ-###` ids the VERIFY FAIL names, each with its reproduction; one fresh
executor per file group; test-first from the verifier's reproduction (the
patch artifact when there is one); the commit carries `Task:` with the REQ
ids; the report ends `COMPLETE route=none` so `/test` runs again; a defect
that turns out to be a spec question is `BLOCKED route=/spec`. Name the mode
in `stage-handoff.md`'s `/build` line and in `tools/run/README.md`. Effort: S.

### B-1. `CLEAN` versus `FINDINGS` is undefined for an ADVISORY-only review

`stage-handoff.md` lists `/review` results as `CLEAN | FINDINGS | BLOCKED`
and says nothing about ADVISORY. `review.md` says `route=none when clean`.
`pipeline.py` decides `said_ok` from BLOCKER + REQUIRED = 0, so it expects
`CLEAN` whenever only ADVISORY findings remain. A reviewer that writes
`FINDINGS` for three ADVISORY findings stops the run with "HANDOFF disagrees
with the result line".

Fix. One sentence in `stage-handoff.md` and `review.md` §4: `CLEAN` means no
BLOCKER and no REQUIRED remains, ADVISORY findings included; `FINDINGS` means
at least one BLOCKER or REQUIRED remains. Add the ADVISORY-only case to
`test-pipeline.py`. Effort: XS.

### B-2. `component-response-contracts.md` documents an older harness

The file says of itself: "Nothing automated checks that this document still
matches its sources." It no longer does:

- §1 "Eight hooks": there are ten. `format-edited-file.sh` (ADR 0107) and
  `require-commit-trailers.sh` (ADR 0073) are missing from the table, and
  the Codex adapter paragraph says it calls "the same eight".
- §1 `require-handoff-report.sh` "reads the writer persona's last assistant
  message": it reads the latest `SubagentHandback` call (ADR 0116).
- §3 `code-reviewer` template lacks the count line (ADR 0099), the REVIEW.md
  checklist (ADR 0103), the Root-cause check (ADR 0097) and the weakened-test
  line that the persona now requires. `repo-recon` template lacks Touch points
  and Claimed reuse.
- §5: the stage table has no HANDOFF column; `/review`'s artifact reads "—"
  although it writes the SARIF; the `/ship` paragraph has no handoff line and
  no unattended path; "Six commands" (seven with `/explain`, which it does
  mention one line later).

Fix, two options. (a) Trim: keep §Dispositions and §Review SARIF, which are
the two sections other files point to, and replace §1, §3, §4 and the rest of
§5 with one-line pointers to the owning files, so there is nothing left to
drift. (b) Refresh now and add a `harness-map.py`-style check that the hook
table lists every file in `hooks/` and the persona table every file in
`agents/`. Recommended: (a) for §1 and §3, (b)'s check only for the counts.
Effort: S for (a).

### B-3. `/test` does not name the tasks `/build` hands on

`build.md` reports **Handed on** tasks (`T007 → /test`) and `COMPLETE
route=/test ids=T007,T008`. `test.md` never mentions them: the verifier gets
the BUILD message and must notice the section. One paragraph in `test.md` §1
("tasks under Handed on are in scope; each becomes a runtime line") and one
packet field in `test-engineer.md` closes it. Effort: XS.

### B-4. `security-auditor` lacks the rule `reviewer-triggers.md` gives it

`reviewer-triggers.md`: on a diff that touches no security boundary, the
auditor "says so in one line and stops". `security-auditor.md` has no such
rule, so it audits every diff at full length (opus, high effort, on every
round). Add the one-line stop to the persona, with the boundary list from the
trigger file. Also add the Composition section the other personas have, to
`security-auditor.md` and `distributed-systems-reviewer.md`. Effort: XS.

### B-5. `docs/agents.md` and `docs/HANDOFF.md` carry stale names

`claude/docs/agents.md` is the orchestration overview and does not mention
the HANDOFF contract or the two runners, which are now the main way a ticket
moves. `docs/HANDOFF.md` §3 still names `check_inbox()` and `back_to_spec()`;
the code has `inbox()` and `resolve()` (renamed under HR-1). Effort: XS each.

### C-6. `/spec` is the one gate without a HANDOFF line

The runner parses the spec file instead (header, `OPEN QUESTION:` blocks,
`Risk:` lines). It is structured and tested. A `HANDOFF: result=COMPLETE|
BLOCKED route=owner decide=<n>` on the `/spec` report would make the runner
uniform and let `settle_spec()` stop parsing blocks for the count. Optional;
do it when `/spec` next changes.

### C-7. `/explain` under the runner

Its sources table says "in this conversation". Under `ticket.py` the stage
messages are in `<git-common-dir>/handoff/`; `/explain` could read them from
there with the same "complete message" rule. Only when someone wants pages
for unattended tickets.

### C-8. Small text drift

`agent-run-metrics.md`: "REVIEW NO-GO findings" (a review has no NO-GO; it is
`FINDINGS`). `tools/run/README.md` `/ship` sentence updated today; the
`pipeline.py` row still ends "Stops before `/ship`", which is right.

### What is sound and should not be touched

- The id chain `REQ → T/TD/CP → CODE/BLIND/SEC/DIST → OPEN` is defined once
  (`plan-quality-gates.md` §3) and every consumer uses it.
- The three "single source" references (`verification-triggers.md`,
  `reviewer-triggers.md`, `risk-tiers.md`) are not duplicated anywhere; the
  commands point at them.
- Every command's script flags match the scripts' `--help`.
- The executor packet, the verifier packet and the reviewer packets are
  written identically on both sides (command and persona).
- The approval rules (`/spec` never sets Approved; `/plan` only on explicit
  approval, with the one runner exception of ADR 0115) are the same in the
  commands, the skills, the quality-gate references and the runner.
- Hooks are tested in CI and their frontmatter is pinned by
  `validate-frontmatter.py`.

---

## Part 3. The plan

Order by what strands a run first. Each step ends green on
`test-pipeline.py`, `test-ticket.py`, `check-references.py`,
`harness-map.py --check` and `test-stale-instructions.py`, and is one
commit.

1. **B-1 + A-2** (one commit, S). `stage-handoff.md`: define `CLEAN`;
   name `/build` modes. `review.md` §4: the CLEAN sentence. `build.md`:
   `## Verify fixes`. `tools/run/README.md`: the mode. Tests: ADVISORY-only
   review passes; a `verify fixes` prompt is what the pipeline sends (already
   asserted) and `build.md` names it (`test_commands_name_the_handoff_line`
   style check).
2. **A-1** (M). `review.md` §2 STALE-depth rule and §4 route; `test.md` §2
   the REVIEW-supplied packet; `pipeline.py` REVIEW → TEST → REVIEW once per
   candidate, outside the 3-review cap; `stage-handoff.md` example; fixture
   10; tests for both paths (verifier runs the check → review again → clean;
   verifier cannot → `route=owner` → `ticket.py` posts `B<k>`). Amend
   ADR 0114 in one paragraph.
3. **B-3 + B-4** (XS). `test.md` and `test-engineer.md` Handed on;
   `security-auditor.md` one-line stop and Composition;
   `distributed-systems-reviewer.md` Composition. `check-rescore.py` needs a
   `Review-eval:` trailer on the reviewer change: "not run - prose only, no
   finding rule changed".
4. **B-2** (S). Trim `component-response-contracts.md` §1 and §3 to pointers;
   refresh §5's table with a HANDOFF column and the `/ship` paragraph; add
   the count check to `harness-map.py` (hooks in `hooks/` = rows in the
   table) or drop the counts from the prose.
5. **B-5 + C-8** (XS). `docs/agents.md` one section "Unattended" pointing at
   `stage-handoff.md` and `tools/run/README.md`; `HANDOFF.md` names;
   `agent-run-metrics.md` term.
6. **Verify on a real ticket** (the proof). The first `--watch` ticket through
   HR-1's runner: confirm `/jira-ticket` runs under `claude -p`, that
   `ticket-stats.py` prints the `run:` line with 0 `runner` stops, and that
   every stage ended on its HANDOFF line without a `harness` stop. The
   observation log gets the row.

Done 2026-10-24: steps 1–5 (`2814e8e`, `8603bff`, `99ff2c5`, `095962c`,
`4b54553`). Open: step 6. Not in this plan: C-6 and C-7 (do with the next change to those commands),
the schema-fingerprint patch (waits for the owner's scripts), and any new
gate (the harness-v1 freeze).
