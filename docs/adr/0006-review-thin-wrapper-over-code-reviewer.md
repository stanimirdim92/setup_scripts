# `/review`: thin wrapper over `code-reviewer`, not a second rubric

**Decision.** `/review` invoked the `code-review-and-quality` skill
directly — a 320-line five-axis framework loaded fresh into context on
every call — duplicating the same five-axis rubric the much smaller
`code-reviewer` agent already implements (the one `/build` dispatches).
Two rubrics for the same review is a rule-6 case, not two legitimately
different reviews. Fixed by making `/review` dispatch `code-reviewer`
directly, plus specialist fan-out per the trigger matrix in
`0005-reviewer-trigger-matrix-single-source.md` — the same pattern
`/build` already uses for its review step, so there's one five-axis
rubric in the repo, not two.

**Rejected — delete `code-review-and-quality` entirely.** The skill is
still referenced by `git-workflow-and-versioning` (splitting-strategy
detail for large diffs) and `references/definition-of-done.md`. Kept as
a reference; only `/review`'s direct invocation of it was removed.
