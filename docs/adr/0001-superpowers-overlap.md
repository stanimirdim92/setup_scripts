# Superpowers overlap

**Decision.** Two vendored skills collided by name/job with skills the
`superpowers` marketplace plugin already ships: `test-driven-development`
and `debugging-and-error-recovery`, against superpowers' own
`test-driven-development` and `systematic-debugging`. Running both meant
ambiguity over which one actually fires on a given trigger — rule 6
territory: pick one, don't blend them. Dropped the vendored copies.
`/test` and any debugging work now go through the `superpowers` plugin's
`test-driven-development` and `systematic-debugging` skills. `/spec` and
`/plan` also now open with a `superpowers` step instead of jumping
straight to the vendored one: `brainstorming`'s spike/bounded/
architectural classification (with its own approval gate) runs before
`spec-driven-development` writes anything, and
`dispatching-parallel-agents`'s independence test runs once
`planning-and-task-breakdown` has the dependency graph, to flag which
tasks `/build` can dispatch concurrently.

**Rejected — swapping in more of superpowers.** `writing-plans`,
`requesting-code-review`/`receiving-code-review`, and
`finishing-a-development-branch` cover the same ground as
`planning-and-task-breakdown` and `code-review-and-quality` without being
clearly better, so they weren't swapped in — only the two actual
name/job collisions and the two compositional additions above were made.
