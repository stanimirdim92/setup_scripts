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
| 2026-09-14 | LD-380 | `/plan` | Ran its full precondition check and wrote its report having never read `plan-quality-gates.md`, `templates/plan.md` or `templates/task.md` — all three denied (`is_error`) on every route it tried: the `.claude/*` symlink path, the resolved absolute path, `cat` via Bash, then a repeat `Read`. 15 of the stage's 23 tool results were denials. It disclosed this, but as a "secondary (non-blocking) note" under a blocker that happened to be fatal anyway. Had the primary blocker been absent, it would have written a plan shaped only by the skill body, with no template and no quality gates, and nothing would have flagged it. | None. The primary block was correct and stopped everything. | first | **Cause was the fixture, not the harness.** The fixture mounted `.claude/` as symlinks into the dotfiles checkout and the nested session was never given that directory, so the resolved paths sat outside its working directory. A real install links `~/.claude`, which Claude Code reads natively. Verified on the approver's own machine the same day: `Read ~/.claude/references/plan-quality-gates.md` from an unrelated project returns the file, no denial. The three shipped tickets ran with their gates intact. What survives as a harness observation is narrower and unproven in production: a stage that loses a reference discloses it in a footnote and keeps going. `tools/check-references.py` covers references that do not resolve; nothing covers one that resolves and is refused, and there is now no evidence that happens outside a misbuilt fixture. |

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
| 2026-09-14 | LD-380 **re-run**, adr/0056 harness | `jira-ticket` (opus) | n/a | n/a | n/a | — | $0.85 | 0 |
| 2026-09-14 | LD-380 **re-run**, adr/0056 harness | `/spec` (opus) | **No** — bounded check inline (22 tool calls, 0 subagents) | n/a | n/a | — | $1.38 | 0 |

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
failed, writing no artifact. It did so without access to its own references — a
fixture defect, see the failure row above.

**The strongest signal is external to the run.** LD-380 is live, and the
approver reports that the spec produced here matches the one written about two
weeks earlier by an earlier version of this harness, before the worktree option
existed. Two harness versions, two sessions, independently reaching the same
specification of a shipped ticket.

**Re-run on the 0056 harness, same ticket, same offline intake, same empty
fixture.** The only variables were the model tiers and the session default.
Draft against draft:

| | old (sonnet) | new (opus) |
|---|---|---|
| Requirements | 5 | 23 |
| Scenarios | 19 | 62 |
| Spec size | 23.9 KB | 50.0 KB |
| `DEC-` blocks | 2 | **0** |
| Open questions | 2 | 8 |
| Cost, jira + spec | $1.24 | **$2.23** (1.8x) |
| Wall clock | 514 s | **369 s** (0.7x) |

The result that matters is not the size. Three contradictions are buried in the
LD-362 and LD-238 comment threads; the first run caught one, the re-run caught
all three. It names the notification conflict outright — "This contradicts
LD-238, which states the user is emailed when the advertiser is ready" — which
the first run missed entirely, and it recovered the incomplete-provider-data
fallback that was decided in an LD-362 comment and never reached the story,
writing it as its own scenario.

The behavioral change underneath is the `DEC-` count falling to zero. The first
run resolved the Outscraper-versus-Google-Places question itself, citing
LD-381's title, and recorded `DEC-001`. The re-run refused and raised it as an
open question instead. The re-run was right: that call was the approver's, and
when it was put to them they made it. `repository-precedent.md` §2 says to raise
an `OPEN QUESTION` rather than silently decide where the evidence is mixed —
the first run broke that rule and the second kept it.

**Corrected once more, by the artifact neither run could see.** The comparison
above set two repo-less specs against each other. The spec actually approved on
2026-09-06 was written with the codebase in front of it, and it dissolves two of
the three "contradictions" the re-run was credited with catching. LD-238's email
belongs to the pre-existing `/v1/advertiser-request` endpoint, which this ticket
does not touch — its DEC-005 says so, with the repository as evidence. The
provider question it decided outright (DEC-001), because the approver had
decided it in session. Raising a question you cannot settle is right; resolving
one you can is better, and the comparison scored the weaker behaviour as the win.

Worse for the re-run: LD-382 lists four duplicate signals, and
`AdvertiserRepository::exists()` implements two. The re-run's spec specified all
four, phone scenario included, and would have sent an executor to build a
matching path the approver had explicitly declined. The 2026-09-06 spec narrowed
it and recorded DEC-006. No care in a repo-less run substitutes for reading the
code; `repo-recon` remains the untested half of this harness and this is what it
is for.

What survives from the comparison: on the same evidence, the 0056 harness read
the comment threads more thoroughly than its predecessor. What does not survive
is the implication that it produced a better spec than the one that shipped.

**Settled the same day, by review rather than by count.** The question left open
here was whether 23 requirements and 8 blocking questions on an already-shipped
ticket were thoroughness or over-specification. The approver read the spec
against the implementation that shipped two weeks ago and reported: every open
question valid, most of them *not* caught during that implementation; the
requirements valid; and the spec identified work missing from what actually went
to production.

That is a stronger result than the comparison that produced it. The re-run was
measured against the earlier spec, which is a test of consistency. This is a
test against reality — the spec found real gaps in shipped code that a human
team, working the same tickets, did not. It is one ticket and one reviewer, so
it does not generalise on its own; it does mean the 0056 tiering is no longer
resting only on the papers it was argued from.

The gaps it named are live work: LD-381, LD-382 and LD-383 are In Progress and
LD-386 (QA) is still To Do.

It does **not** establish anything about repository evidence or `repo-recon`:
the project was an empty fixture, so there was nothing to survey and no
subagent ran. `maxTurns` is still uncalibrated for the same reason. Two caveats
on the setup itself: `--allowedTools` is an auto-approval allowlist, not a
restriction — `Bash` ran 12 times despite not being listed (`--tools` is the
restricting flag, which `tools/tests/workflow/run.py` uses correctly) — and the
fixture's `settings.json` carried the env pins but not the global `PreToolUse`
hooks, so the destructive-bash and force-push guards were not in force (added
before the approval and plan stages).

**A correction, recorded because the log is worth nothing if it launders its own
mistakes.** An earlier revision of this file claimed `/plan` "reported an access
blocker that did not happen." That was wrong. The check behind it counted
`tool_use` attempts and never read `is_error` on the results; every one of those
reads had failed. `/plan`'s report was accurate in full. The finding above
replaces it — and was itself then narrowed, once the approver ran the same read
on a real install and got the file: the denial was the fixture's doing, not the
harness's. Two corrections to one row in one day is the honest cost of a log
that records what happened rather than what was assumed.

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
