# `/build` → `/test` → `/review`: split implementation from verification and review

**Decision.** `/build` no longer reviews, verifies, or issues a verdict.
Per direct instruction, the SDLC chain's back half is now three distinct
gates instead of one command doing implementation, review, and verdict
together:

- **`/build`** — implements only. Dispatches `executor` per workstream
  (unchanged: sequential, one active writing executor at a time, per
  [0003](0003-executor-concurrency-sequential-only.md)). The dispatched
  `executor` owns incremental/TDD execution discipline directly (it has no
  `Skill` tool, so the discipline is inlined in `agents/executor.md` rather
  than invoked as a skill). `/build` explicitly does not perform the
  VERIFY phase, does not dispatch reviewers, and does not issue GO/NO-GO —
  the next stage is `/test`.
- **`/test`** — the independent VERIFY gate. Runs/adds verification against
  acceptance criteria at the right test level, reports **VERIFY PASS** or
  **VERIFY FAIL**. On FAIL, hands the exact reproduction/expected-vs-actual
  evidence back to `/build`. This is a new pipeline stage with no prior
  ADR — previously `/test` wrapped `superpowers:test-driven-development` as
  a thin skill-alias (per the original addyosmani vendoring); it's now this
  repo's own independent verification gate instead, unrelated to
  `test-driven-development`'s TDD-authoring concern.
- **`/review`** — the independent REVIEW gate, gated behind `/test`
  reporting VERIFY PASS. Dispatches `code-reviewer` always, plus
  `security-auditor`/`distributed-systems-reviewer` per
  `references/reviewer-triggers.md`, capped at 2 concurrent, then issues
  the GO/NO-GO verdict. NO-GO sends fixes back through `/build`, which
  re-triggers `/test` then `/review` again.

**This does not reverse [0004](0004-reviewer-batch-cap-no-high-risk-exception.md),
[0005](0005-reviewer-trigger-matrix-single-source.md),
[0006](0006-review-thin-wrapper-over-code-reviewer.md), or
[0009](0009-infra-security-reviewers-merged-into-security-auditor.md).**
Their actual policies — the 2-reviewer concurrency cap with no high-risk
exception, one trigger matrix read by whichever command dispatches
reviewers, `/review` as a thin wrapper over `code-reviewer` rather than a
second rubric, and the `security-auditor` merge — all still hold exactly
as decided. Only the enforcement point moved: these lived inside `/build`'s
own review step before, and live in `/review` now. Left their Status as
Accepted rather than Superseded, since nothing about what they decided
changed — only where it's enforced.

`docs/agents.md`'s "Worked example: valid orchestration" section, its
persona-table cross-references, and its `/test`/`/build`/`/review`
descriptions were updated to match (previously described `/build` doing
the fan-out and verdict `/review` now does).

**Rejected — marking 0004/0005/0006/0009 Superseded.** Considered it for
consistency with "the mechanism moved," but Superseded specifically means
a decision was reversed by a later one — these weren't; the same policies
are still in effect, just relocated. Marking them Superseded would
incorrectly tell a future reader that reviewer-triggers.md's dispatch
rule, the 2-cap, or the security-auditor merge no longer apply.
