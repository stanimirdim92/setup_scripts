# Reconcile Superpowers overlap with the current SDLC

**Decision.** The current SDLC no longer follows several routing choices recorded
in [0001](0001-superpowers-overlap.md), so those parts are explicitly
superseded instead of leaving live config and ADR history in conflict.

Current ownership is:

- The local `test-driven-development` skill is the canonical TDD methodology for
  implementation. `executor` intentionally has no `Skill` tool, so it inlines
  the RED/GREEN/REFACTOR discipline that `/build` requires.
- `/test` is not a TDD alias. Per
  [0020](0020-build-test-review-pipeline-split.md), it is the independent VERIFY
  gate after implementation.
- `/spec` no longer requires a mandatory `superpowers:brainstorming` hop before
  `spec-driven-development`.
- `/plan` no longer invokes `dispatching-parallel-agents`. The local
  `planning-and-task-breakdown` skill classifies dependencies/workstreams and
  `/build` owns actual concurrency.
- `superpowers:systematic-debugging` remains the preferred plugin route for
  debugging; that part of 0001 is not reversed.

This records the behavior the live files already implement rather than
reintroducing old composition merely to make the ADR match.

**Rejected — deleting or rewriting ADR 0001.** Historical decisions stay on the
record. The index marks it partially superseded and this ADR states exactly
which parts changed.

**Rejected — making `/test` invoke TDD again.** TDD is developer feedback inside
BUILD. VERIFY is an independent attempt to prove the integrated result and has a
different responsibility.

**Rejected — restoring mandatory brainstorming/parallel-agent plugin hops.**
Those hops duplicate local SPEC/PLAN ownership, increase context/tool cost, and
make the global workflow depend on plugin-specific routing that the current
commands deliberately removed.
