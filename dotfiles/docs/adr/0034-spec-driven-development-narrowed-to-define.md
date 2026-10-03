# `spec-driven-development` narrowed to the DEFINE stage

**Decision.** Deleted `spec-driven-development`'s Phase 2 (Plan), Phase 3
(Tasks), and Phase 4 (Implement) sections. The skill now owns the Phase 0
capability scope check and specification only, then hands off: `/plan` owns the
plan and task breakdown, `/build` implementation, `/test` verification,
`/review` findings, `/ship` the verdict. Its phase diagram was replaced with the
six-stage command chain so a reader entering at `/spec` sees where the work goes
next.

Those three sections restated methodology `planning-and-task-breakdown` already
owns, and said so — each carried a note that "if they ever diverge,
`planning-and-task-breakdown` takes precedence." A section that documents its own
subordination to another file is a duplicate with a disclaimer, not a summary,
and rule 6 says pick one rather than keeping both. It also cost tokens at the
worst point: `/spec` is the first stage of a pipeline run, so this skill is
loaded before any other.

**Rejected — keep them as a lightweight summary with the precedence note.** That
is exactly what they were, and it did not prevent drift: the inline task template
and output conventions had to be maintained in two places, and the "Ready for
/test" checkbox in `references/templates/plan.md` was stale against the same
handoff this change clarifies.

**Rejected — delete the phase framing entirely and leave only prose.** The stage
diagram is what tells a reader at `/spec` that planning and implementation are
separate invocations they must make. Removing the duplicate methodology without
leaving the map would make the handoff less clear, not more.
