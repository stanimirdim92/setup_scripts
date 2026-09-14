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
| — | — | — | — | — | — | — |

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
| — | — | — | — | — | — | — | — | — |

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
