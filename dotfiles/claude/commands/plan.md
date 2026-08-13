---
description: Break work into small verifiable tasks with acceptance criteria and dependency ordering
---

Invoke the `planning-and-task-breakdown` skill.

Read the existing spec (SPEC.md or equivalent) and the relevant codebase sections. Then:

1. Enter plan mode — read only, no code changes
2. Identify the dependency graph between components
3. Flag any 2+ tasks that are independent (no shared state, no sequential dependency) using the `superpowers:dispatching-parallel-agents` skill's independence test — these are what `/build` can dispatch concurrently
4. Slice work vertically (one complete path per task, not horizontal layers)
5. Write tasks with acceptance criteria and verification steps
6. Add checkpoints between phases
7. Present the plan for human review

Save the plan to tasks/plan.md and task list to tasks/todo.md.

## After approval

The only next action is invoking `/build` — never implement a task
directly from here, even if the plan-mode exit prompt itself says
something like "you can start coding now." That's the tool's own generic
wording, not permission to skip the dispatch/review/verdict layer `/build`
provides. If the user's next message isn't `/build`, ask before writing
any code.
