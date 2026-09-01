---
description: Break work into small verifiable tasks with acceptance criteria and dependency ordering
argument-hint: "[ticket or feature description]"
---

Invoke the `planning-and-task-breakdown` skill.

## Require an approved spec

Read the spec from disk — including its `Status` header, not your memory of
approval earlier in the conversation. Proceed only on `Status: Approved`.
`Draft`, `Needs reapproval` or `Superseded` stops planning immediately: report
the status and return the spec to `/spec`. A spec whose requirements have no
`REQ-###` ids is also not plannable; return it for ids
(`../references/spec-quality-gates.md` §2-3).

Reconcile every planned behavior and acceptance criterion against the approved
spec. On contradiction, infeasibility, or a proposed new/stronger behavior,
stop with `SPEC CONFLICT` and return the decision to `/spec`.

## Requirement coverage

Map every spec requirement to the tasks that deliver it, and give every task at
least one `REQ-###`. Record the map in the plan's Requirement Coverage table and
report both lines explicitly:

- `Unmapped requirements: None` — a requirement with no task is a dropped
  requirement; it surfaces in production rather than at this gate.
- `Orphan tasks: None` — a task with no requirement is scope the spec never
  asked for. Remove it, or return a `SPEC CONFLICT` if the behavior is genuinely
  needed, so it gets specified and approved instead of entering through the plan.

Neither line may read anything other than `None` at handoff.

## Repository recon

Dispatch one `repo-recon` agent for the affected area before planning. Give it
the area, `/plan` as the calling stage, and any specific questions you already
have. Do not survey the repository in this context — that survey is the largest
avoidable cost of this command, and the agent's reads stay in its own context.

Reuse a `repo-recon` report already in this conversation when it covers the
same area and nothing has changed since. Dispatch again only for a different
area, after the repository has changed, or when the report's **Not surveyed**
section excludes something you now need.

Open a file the report names only when a specific unresolved question turns on
that file's detail. Its **No precedent found for** entries are decisions you
are making without repository guidance — carry them into the plan as risks,
not settled ground.

Let the skill own planning methodology: dependency graph, behavioral slicing,
workstreams, task sizing, context pointers, verification, and risk-based
checkpoints. Project-rule discovery and repository precedent come from the
recon report above, not from the skill re-deriving them.

Save:

- `docs/tasks/[TICKET]-plan.md`;
- `docs/tasks/[TICKET]-todo.md`.

Present the result for human review.

After approval, stop. The request that invoked `/plan` authorizes planning
only, even when it says to build or fix something — that instruction does not
carry forward past this command; wait for a new user request before `/build`.
Implementation goes through `/build`. Independent verification is
risk-triggered through `/test`; `/review` decides whether it is required for
the built candidate. Final release readiness goes through `/ship`.
