---
description: Break work into small verifiable tasks with acceptance criteria and dependency ordering
argument-hint: "[ticket or feature description]"
---

Invoke the `planning-and-task-breakdown` skill.

Read the approved spec and the repository context relevant to the affected area.
Let the skill own the planning methodology: project-rule discovery, repository
precedent, dependency graph, behavioral slicing, workstreams, task sizing,
context pointers, verification, and risk-based checkpoints.

Save:

- the implementation plan to `docs/tasks/[TICKET]-plan.md`;
- the task list to `docs/tasks/[TICKET]-todo.md`.

Present the result for human review.

## After approval

Stop. Do not implement from `/plan`.

Implementation goes through `/build`.
Independent verification goes through `/test`.
Independent review and the final GO/NO-GO verdict go through `/review`.
