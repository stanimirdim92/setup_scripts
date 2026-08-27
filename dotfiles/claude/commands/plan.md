---
description: Break work into small verifiable tasks with acceptance criteria and dependency ordering
argument-hint: "[ticket or feature description]"
---

Invoke the `planning-and-task-breakdown` skill.

Read the approved spec and repository context relevant to the affected area.
Reconcile every planned behavior and acceptance criterion against the approved
spec. On contradiction, infeasibility, or a proposed new/stronger behavior,
stop with `SPEC CONFLICT` and return the decision to `/spec`.

Let the skill own planning methodology: project-rule discovery, repository
precedent, dependency graph, behavioral slicing, workstreams, task sizing,
context pointers, verification, and risk-based checkpoints.

Save:

- `docs/tasks/[TICKET]-plan.md`;
- `docs/tasks/[TICKET]-todo.md`.

Present the result for human review.

After approval, stop. Implementation goes through `/build`. Independent
verification is risk-triggered through `/test`; `/review` decides whether it is
required for the built candidate. Final release readiness goes through `/ship`.
