# Vendored `shipping-and-launch` skill, deliberately no `/ship` command

**Decision.** Vendored `addyosmani/agent-skills`' `shipping-and-launch` skill
into `dotfiles/claude/skills/shipping-and-launch/SKILL.md` (MIT, same
`ADDYOSMANI_AGENT_SKILLS_LICENSE` already covering the other engineering
skills) — direct-invocation only, no command wraps it.

This came out of checking whether this repo needed upstream's `/ship`
command (a parallel fan-out of `code-reviewer`/`security-auditor`/
`test-engineer` into a GO/NO-GO + rollback plan). It doesn't: this repo's
`/build`→`/test`→`/review` pipeline already dispatches those same three
personas — sequentially, with the concurrency discipline
[0004](0004-reviewer-batch-cap-no-high-risk-exception.md) deliberately
chose over upstream's full-parallel default. Adding `/ship` as upstream
built it would have meant a second orchestration path to the same three
specialists — exactly the "two things doing one job" problem
[0006](0006-review-thin-wrapper-over-code-reviewer.md)/[0025](0025-security-auditor-provenance-corrected.md)/[0026](0026-security-auditor-reconciled-with-reference-docs.md)
spent this session closing elsewhere, reopened by a different command.
Confirmed no concrete bypass-the-pipeline use case exists that would
justify it anyway.

But `/ship`'s prompt separately says "Invoke the shipping-and-launch
skill" — and that skill's actual content (310 lines: pre-launch checklist
across code/security/perf/a11y/infra/docs, feature-flag lifecycle,
staged-rollout with concrete advance/hold/rollback metric thresholds,
monitoring/observability setup, a rollback-plan template, post-launch
verification) is genuinely new capability, not a duplicate of anything
already vendored here. This repo's pipeline stops at `/review`'s GO/NO-GO
verdict — nothing here covers what happens between "reviewed" and "safely
live in production." Verified it isn't secretly re-deriving existing
content: its own "See Also" section already points out to
`definition-of-done.md` and `security-checklist.md` (both real files here)
instead of re-explaining them — the skill vendors clean.

Two of its four "See Also" links (`performance-checklist.md`,
`accessibility-checklist.md`) don't exist in this repo — neither was ever
vendored (`performance-checklist.md` was explicitly deleted, see commit
`6bc1912`). Hedged both with a "not currently vendored" note per this
repo's established pattern (commit `2739610`) rather than leaving dangling
links or fabricating the files.

**Rejected — vendoring the `/ship` command alongside the skill.** The
skill is direct-invocation content (pre-launch checklist, rollback
planning) useful on its own; the command's actual job (parallel-dispatch
three specialists to a verdict) is already this repo's `/test`+`/review`,
just built differently. Wiring `/ship` would mean either duplicating that
dispatch logic a second time or making `/ship` secretly just call
`/test`+`/review` — a thin wrapper with no realized use case behind it,
which is exactly the kind of speculative feature `CLAUDE.md` rule 2
("no flexibility that wasn't requested") exists to catch. Revisit if a
concrete bypass-the-pipeline need actually comes up.
