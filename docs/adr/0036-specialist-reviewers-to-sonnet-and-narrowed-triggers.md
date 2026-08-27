# Specialist reviewers moved to Sonnet/medium with narrowed triggers

**Decision.** `security-auditor` and `distributed-systems-reviewer` now default
to `model: claude-sonnet-5`, `effort: medium` instead of `claude-opus-5`,
`effort: high`. `references/reviewer-triggers.md` was narrowed from file/feature
categories to *changed semantics*: a specialist fires only when the diff
materially alters a trust boundary or a distributed failure boundary, not merely
because auth code, a config file, an HTTP call, or a worker was touched.
`security-auditor` also now reads only the reference sections matching the
changed risk rather than loading `security-checklist.md`, `ai-security.md`, and
`supply-chain.md` by default. `/review` may escalate a specialist upward, but
only when the matched risk is both high-impact and materially ambiguous.

[0002](0002-model-split-sonnet-orchestrator-tiered-subagents.md) explicitly
excluded these two personas from its model split and said their tier was "a
separate call, revisit it separately if it comes up." This is that call.

**Why.** The old triggers fired on category presence, so a config edit or an
ordinary outbound HTTP call could summon an Opus/high reviewer that then found
nothing a boundary had actually changed. Cost was paid per category touched
rather than per risk introduced. Narrowing the trigger reduces how often the
specialist runs; the tier change reduces what each run costs.

**This is the riskiest change in this pass and is recorded as such.** Three
reductions land on the same axis at once — fewer invocations, a lower reasoning
tier, and less reference material loaded — on precisely the two reviewers whose
misses are most expensive (auth bypass, tenant leakage, data loss, lost or
duplicated effects). They compound. The escalation path in `/review` is the only
compensating control, and it depends on the trigger having matched in the first
place, so a narrowed trigger that fails to match is not recoverable by
escalation.

**Rejected — narrow the triggers but keep Opus/high.** The defensible
conservative option, and the one to fall back to if this proves wrong: it takes
the invocation-count saving, which is the larger of the two, while leaving
reasoning depth intact where the trigger did match. Rejected here only because
a correctly narrowed trigger means the remaining matches are genuine and the
escalation path covers the ambiguous ones — an assumption that needs measuring,
not assuming.

**Rejected — lower the tier but keep broad triggers.** Keeps the reviewer firing
on changes with no altered boundary, just more cheaply, and dilutes the signal:
reviewers that habitually return nothing train the reader to skim them.

**Revisit if** a security or reliability defect reaches `/ship` or production on
a candidate where the specialist ran and missed it (tier too low), or where the
specialist did not run at all (trigger too narrow). Either outcome should restore
Opus/high before anything else is tried; log which of the two failed.
