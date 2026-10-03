# `security-auditor.md` reconciled with `security-checklist.md`/`ai-security.md`/`supply-chain.md`

**Decision.** Replaced `security-auditor.md`'s inline "Review Scope" section
(6 numbered categories — Input Handling, Authentication & Authorization,
Data Protection, Infrastructure, Third-Party Integrations, AI/LLM Features
— each with its own bullet checklist) with pointers to
`references/security-checklist.md`, `references/ai-security.md`, and
`references/supply-chain.md`, per [0025](0025-security-auditor-provenance-corrected.md)'s
finding that this vendored file predates those reference docs and was
never reconciled with them.

Verified before cutting anything: read both `security-checklist.md` (388
lines) and `ai-security.md` (154 lines) in full and confirmed every one of
the 6 inline categories maps onto sections in those files with equal or
greater depth — no coverage loss. `security-auditor` has a plain `Read`
tool (no `Skill` tool needed to pull this in, unlike the
`code-reviewer`/`code-review-and-quality` gap a harness review flagged
separately), so it can genuinely read these files during a live review.

This closes the specific drift instance already found: `security-auditor`'s
old inline list had no way to reflect `security-checklist.md` being
retitled from "OWASP Top 10:2021" to "OWASP Top 10:2025" — pointing at the
file instead of duplicating its content means future updates reach this
agent automatically, the same single-source-of-truth pattern
[0005](0005-reviewer-trigger-matrix-single-source.md) already established
for `reviewer-triggers.md`.

Left `Severity Classification`, `Output Format`, `Rules`, and `Composition`
untouched — none of that duplicates the reference docs; it's the agent's
own process/report-shape content, not a security checklist.

**Rejected — reconciling `security-and-hardening/SKILL.md` in the same
pass.** The same deep-review found near-identical duplication there (~150
lines of inline OWASP patterns and AI/LLM content, plus a stale "2021"
reference the reference docs already moved past) — a real, separate
instance of the same problem, not fixed here. Scoped this change to
`security-auditor.md` specifically since that's what was asked; the skill
is a larger, differently-structured file (code examples alongside
checklist items, not a pure checklist) and deserves its own pass rather
than a rushed version bundled into this one.
