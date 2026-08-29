---
description: Break work into small verifiable tasks with acceptance criteria and dependency ordering
argument-hint: "[ticket or feature description]"
---

Invoke the `planning-and-task-breakdown` skill.

Read the approved spec.
Reconcile every planned behavior and acceptance criterion against the approved
spec. On contradiction, infeasibility, or a proposed new/stronger behavior,
stop with `SPEC CONFLICT` and return the decision to `/spec`.

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
