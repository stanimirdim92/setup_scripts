# docs/agents.md: trimmed to match what's actually built

**Decision.** `docs/agents.md` (added by the direct-edit refactor) described
a `/ship` fan-out command, a `test-engineer` persona, and a
`references/orchestration-patterns.md` catalog — none of which exist in
this repo. Confirmed with the user: trim the doc rather than build the
missing pieces. Rewrote it to describe `/build`'s actual review-fan-out
step (the one real orchestration pattern this repo has) instead of an
aspirational one, and dropped every link to files that don't exist.

**Rejected — build out `/ship` + `test-engineer` + orchestration-patterns.md.**
Would have made the doc true, but `/ship` would duplicate `/build`'s
existing fan-out (same job: dispatch, then review multiple perspectives,
merge a verdict) — a second command for the same pattern is rule-6
territory, not a genuine gap.

**`fastapi` skill removal — confirmed intentional,** no restore.

**`code-reviewer.md` rule 2 — reapplied the earlier fix.** The refactor's
edit had reverted rule 2 to "Read the spec or task description before
reviewing code," which contradicts `/build`/`/review`'s own instruction to
hand reviewers the diff plus a one-line goal and acceptance criteria, not
the full spec (see `references/reviewer-triggers.md`). Confirmed with the
user: reapply the corrected wording rather than keep the reverted one.
