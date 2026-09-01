# Skills trimmed by de-duplication, not by cutting policy

**Decision.** Four skills exceeded the ~5,000-token per-skill post-compaction
re-attachment cap that [0037](0037-fixed-session-context-reduced.md) flagged, as
measured in [0046](0046-plan-technical-approach-spec-pinning-and-plan-gates.md).
This pass reduces them only where content was **duplicated**, and leaves
single-copy policy alone.

Three extractions, all of which also fix a rule-6 violation that predates the
size problem:

1. **`references/repository-precedent.md`.** The `repo-recon` dispatch rules
   existed three times — in `/spec`, in `/plan`, and again in
   `spec-driven-development` — while the evidence-order hierarchy (user
   requirement → project rule → module precedent → repository convention →
   framework default) and the no-precedent rules existed only in the spec skill,
   even though `/plan` and the executor both depend on them. Now one file, with
   per-stage handling of **No precedent found for** (the spec must justify each
   explicitly; the plan carries them as risks) and a worked example report.

2. **Invariant mechanism proof and data lifecycle semantics** moved into
   `spec-quality-gates.md` as §4 and §5. Both are closure gates, and the closure
   pass already pointed at that file — they were inline in the skill for
   historical reasons, not structural ones.

3. **`security-and-hardening`'s Supply-Chain Hygiene section** collapsed to a
   pointer. Its installation-boundary rules, frozen-install matrix and
   script-gate steps restated `references/supply-chain.md` §1-3 almost
   line-for-line, and its three audit bullets are all present in that file's
   review checklist — while the skill's own "See Also" already warned that an
   embedded copy of a synced reference goes stale silently. It had.

**Result** (byte/4 and word×1.33 estimates, as in 0046 — ordering reliable,
absolute numbers approximate):

| Skill | Before | After |
|---|---|---|
| `spec-driven-development` | 7,201 / 5,649 | 6,557 / 5,147 |
| `security-and-hardening` | 5,716 / 4,379 | 5,562 / 4,281 |
| `planning-and-task-breakdown` | 4,944 / 4,040 | 4,929 / 4,020 |
| `code-review-and-quality` | 6,407 / 5,369 | unchanged |
| `api-and-interface-design` | 5,877 / 4,726 | unchanged |

`/spec` and `/plan` also lost 935 bytes between them, which matters more than it
looks: command bodies are paid on every invocation.

**Honest note.** `spec-driven-development` is still over the cap on both
estimates. De-duplication had roughly 2,600 bytes to give and gave them; closing
the remaining gap requires deleting or relocating content that exists once, which
is a different decision.

**Rejected — extracting the Testing Strategy area from
`spec-driven-development`.** At 2,391 bytes it is the largest remaining
self-contained block and the obvious next candidate, and that is why it is worth
recording as a deliberate no. Area 5 is filled in for *every* spec, so putting it
behind a pointer trades a silent-truncation risk for a guaranteed extra file read
on every single run. The cap is not worth optimising past the point where the
skill stops working well.

**Rejected — compressing the multi-language code examples in
`api-and-interface-design` (24% code fences) and `security-and-hardening`
(31%).** These are single-copy illustrations, and the repo's own guidance holds
that one real snippet beats three paragraphs describing it. Cutting them is a
content decision about those vendored skills, not a de-duplication, and it would
change what the skills teach.

**Rejected — trimming `code-review-and-quality`.** Nothing in it is duplicated
elsewhere; it is simply long, and it now carries
`disable-model-invocation: true`, so it loads only when explicitly invoked. It
stays the largest untouched offender by choice.

**Revisit if** a skill is observed actually truncating — the failure mode is
silent, so the trigger is behavioral (a rule in a late section stops being
followed), not another byte count. That is the evidence this pass does not have
and could not manufacture.
