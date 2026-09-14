# Observation log

Raw run evidence from real tickets driven through the harness. One row per
failure, not per ticket: a clean run needs no entry beyond its metrics.

How this differs from the other durable records (defined in
`dotfiles/claude/references/documentation-practices.md`, not restated here):
`IDEAS.md` holds what is undecided, `docs/adr/*.md` what was decided,
`MEMORY.md` current durable facts. This file holds **measurements** — the
input those three are supposed to be argued from. It is append-mostly;
prune a row only once its finding has graduated into an ADR or a fix.

## Why it exists

Harness v1 is a checkpoint, and the standing decision is to accumulate real
runs before adding gates, personas, or hooks. That only works if the runs are
written down. Three tickets shipped to production with the harness **before**
this file existed and their evidence was not recorded — that gap is the reason
for the file, and those three cannot be reconstructed.

## Failures

Add a row when a run needed human correction, produced a wrong or unusable
artifact, hit a cap, or a gate fired when it should not have (and the reverse:
a gate that should have fired and did not).

| Date | Ticket | Stage / persona | What failed | Cost | Repeated? | Fix or status |
|---|---|---|---|---|---|---|
| 2026-09-14 | LD-380 | `jira-ticket` | Two cross-ticket contradictions not surfaced. LD-238 says the user "receives an email once the advertiser is ready"; LD-380 says "No email or other notification is sent" — flat contradiction, unflagged. LD-362's comment thread decides the `list content not complete` frame becomes the incomplete-Google-data fallback (`—` / "No category"); that decision reached neither the intake nor LD-380's state table. The third contradiction, Outscraper vs Google Places, **was** caught and routed to `/spec`. | None — found by reading the run, not by the harness. Would have surfaced in `/review` or QA at the earliest. | first | Open. §2 asks for requirement-bearing comments to be *retained*; it never asks for conflicting statements across tickets to be *reconciled*. One caught of three suggests the behavior is incidental, not instructed. |
| 2026-09-14 | LD-380 | `/plan` | Reported an access blocker that did not happen. Its report states the harness references "resolve through `.claude/*` symlinks to `/home/user/setup_scripts/dotfiles/claude/...`, which is outside this session's allowed working directory and unreadable (Read/Bash both refused it)." The transcript shows it read `plan-quality-gates.md` twice, plus `templates/plan.md`, `templates/task.md` and `repository-precedent.md`, and records no refusal for any of them. | None — the outcome was right for the other reason it gave (no codebase to plan against), so the false claim rode alongside a correct block. | first | Open. Nothing examines a command stage's *reasons*, only its artifacts. `require-handoff-report.sh` gates executor and test-engineer reports for shape; this report would have passed any shape check. |

- **Stage / persona** — `/spec`, `/plan`, `/build`, `/review`, `/ship`, `/test`,
  or the persona name when it is a subagent failure.
- **Cost** — what the failure cost: wasted turns, rework loops, tokens, or
  wall-clock. Measured, never estimated (`references/agent-run-metrics.md`).
- **Repeated?** — first time, or a recurrence of a row already here. A
  recurrence is the signal that turns an observation into an ADR.

## Run metrics

One row per pipeline run, failure or not. These are what calibrate the
uncalibrated numbers — `maxTurns` 40/60 above all — and what the freeze is
waiting on.

| Date | Ticket | Stages run | Recon dispatched? | Max turns used | Fan-out (concurrent/queued) | Tokens | Cost | Large reads (>350) |
|---|---|---|---|---|---|---|---|---|
| 2026-09-14 | LD-380 | `jira-ticket`, offline sources | n/a — intake does not inspect the repository | n/a | n/a | 8.0k out · 256k cache read | $0.38 | 0 |
| 2026-09-14 | LD-380 | `/spec` | **No** — bounded check inline (37 tool calls, 0 subagents) | n/a, no subagent ran | n/a | 109k out · 3.07M cache read | $0.85 | 0 |
| 2026-09-14 | LD-380 | `/plan` | No — refused at the precondition check | n/a | n/a | — | $0.26 | 0 |
| 2026-09-14 | LD-380 | `/spec` revision + approval | No | n/a | n/a | — | $0.78 | 0 |
| 2026-09-14 | LD-380 | `/plan` on the approved spec | No — blocked before evidence gathering | n/a | n/a | — | $0.35 | 0 |

**Run of 2026-09-14 — what it does and does not establish.** Three fresh
sessions, harness mounted project-locally, real model, offline Jira snapshots
of the nine LD-380 tickets. Gates that held: `/spec` wrote `Status: Draft` and
did not self-approve; it recorded Tech Stack, Commands, Project Structure and
Code Style as **Not established** rather than inventing them; `/plan` refused
the unapproved spec, named both open questions, and wrote no artifact.
Batching in `/spec` was 2.18 calls per request, 41% of requests batched,
largest batch 10.

**Second half of the run, after the approver resolved both open questions**
(Google Places confirmed; enrichment failure reverts, no new status value).
The revision path held: `/spec` preserved REQ-001..005 and DEC-001/002, added
DEC-003 for the new decision, removed both `OPEN QUESTION` blocks, transitioned
Draft to Approved with the approver's name and date, and left an unrelated
working-tree modification alone rather than sweeping it in. `/plan` then
verified all four preconditions — Approved status, stable ids, clean tree, and
a spec revision pin (`git-commit:fc1f6dc...`) — and blocked on the one that
failed, writing no artifact.

**The strongest signal is external to the run.** LD-380 is live, and the
approver reports that the spec produced here matches the one written about two
weeks earlier by an earlier version of this harness, before the worktree option
existed. Two harness versions, two sessions, independently reaching the same
specification of a shipped ticket.

It does **not** establish anything about repository evidence or `repo-recon`:
the project was an empty fixture, so there was nothing to survey and no
subagent ran. `maxTurns` is still uncalibrated for the same reason. Two caveats
on the setup itself: `--allowedTools` is an auto-approval allowlist, not a
restriction — `Bash` ran 12 times despite not being listed (`--tools` is the
restricting flag, which `tools/tests/workflow/run.py` uses correctly) — and the
fixture's `settings.json` carried the env pins but not the global `PreToolUse`
hooks, so the destructive-bash and force-push guards were not in force.

Source every number:

- turns, tokens, batching, large reads — `tools/run-metrics.sh --since <start> --until <end> <transcript>`
- cost and duration — `/cost`, or the statusline payload delta across the run
- fan-out and queueing — `/build`'s own completion report, which states which
  condition each queued workstream failed

## What to look for

Per `references/agent-run-metrics.md`, after roughly 10–20 comparable tickets:

- `maxTurns` — how close real runs come to 40 (`repo-recon`) and 60 (reviewers),
  and whether any run reported a capped partial
- recon — how often `/spec` and `/plan` dispatch rather than bounded-check, and
  whether the bounded checks were adequate in hindsight (ADR 0051's revisit
  condition)
- large reads — main-session whole-file reads in areas a bounded check or recon
  should have covered (the read-size gate parked in `IDEAS.md`)
- rework loops — REVIEW → TEST → REVIEW and TEST/REVIEW → BUILD → REVIEW counts
- handoff gate — how often `require-handoff-report.sh` blocks, and whether the
  block was correct or a regex false positive

Do not change global policy from one unusual run.
