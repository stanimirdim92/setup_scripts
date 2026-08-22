---
description: Break work into small verifiable tasks with acceptance criteria and dependency ordering
argument-hint: "[ticket or feature description]"
---

Invoke the `planning-and-task-breakdown` skill.

Read the existing spec (docs/specs/[TICKET]-SPEC.md or equivalent) and the relevant codebase sections. Then:

1. Enter plan mode — read only, no code changes
2. Identify the dependency graph between components
3. Slice work vertically (one complete path per task, not horizontal layers)
4. Write tasks with acceptance criteria and verification steps
5. Add checkpoints between phases
6. Present the plan for human review

Save the plan to docs/tasks/[TICKET]-plan.md and task list to docs/tasks/[TICKET]-todo.md.

## After approval

Stop. Do not implement from `/plan`.

Implementation must go through `/build`, which owns executor dispatch,
review, and the GO/NO-GO verdict.
