# `/build` selects a compact execution skill for each executor

**Decision.** Executors are now skill-capable, but skill selection remains owned
by `/build`. Every fresh workstream executor loads the first-party
`executor-development-discipline` skill through the executor's `skills`
frontmatter. A resumed executor reuses that methodology and invokes only a newly
selected task-specific skill when the new task materially requires it.

The baseline skill contains the bounded parts of incremental implementation and
TDD needed inside BUILD: thin behavioral slices, Red-Green-Refactor, focused and
workstream verification, evidence-driven retries, and atomic commits. Executor
role boundaries, task scope, permissions, stop conditions, and reporting remain
in `agents/executor.md`.

`/build` may select a specialized implementation skill for a task, such as API
design, migration, or security hardening. It passes skill names rather than skill
bodies. Executors do not browse the skill catalog, choose broader workflow
skills, or invoke planning, independent verification, review, or release
methodology.

This partially supersedes [0021](0021-reconcile-superpowers-overlap-with-current-sdlc.md),
which recorded that the executor intentionally had no Skill tool and inlined TDD.
The separation of BUILD from the independent `/test` VERIFY gate remains
unchanged.

**Why.** Keeping detailed implementation methodology in both
`test-driven-development` and `executor.md` created a drift-prone duplicate.
Passing full skill bodies in every task packet would waste context, while letting
executors discover skills autonomously would weaken orchestration and role
boundaries. Command-selected progressive loading preserves one bounded source of
execution methodology without broadening the executor.

**Rejected — load the full incremental and TDD skills for every executor.** Those
skills include broader routing and orchestration guidance that is irrelevant or
conflicting inside the constrained executor role.

**Rejected — let executors choose from the full catalog.** Skill routing is an
orchestration decision. Self-selection adds discovery cost and permits role
drift.

**Rejected — paste selected skills into every task packet.** Fresh executors can
load named skills directly, and resumed executors retain already-loaded
methodology. Copying skill bodies duplicates context and obscures the packet's
task-specific information.
