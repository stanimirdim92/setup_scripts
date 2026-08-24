# `security-auditor.md`'s provenance corrected: vendored from addyosmani/agent-skills, not written fresh

**Decision.** Per direct disclosure, `agents/security-auditor.md` is a
near-verbatim copy of `addyosmani/agent-skills`' `agents/security-auditor.md`
— confirmed by diffing this repo's file against a fresh clone of the
upstream source. Only three differences exist:

1. `tools: Read, Grep, Glob, Bash`, `model: claude-opus-5`, `effort: high`
   added (upstream ships neither `tools` nor `model`) — the same adaptation
   [0009](0009-infra-security-reviewers-merged-into-security-auditor.md)
   already describes.
2. Rule 3 reworded from "Provide proof of concept or exploitation scenario
   for Critical/High findings" to "State a concrete exploitation path for
   Critical/High; include exploit code only when necessary to establish the
   finding" (the ChatGPT-suggested tweak from commit `4b4f65d`).
3. The Composition section's "Invoke via" line repointed from upstream's
   `/ship` (a command this repo doesn't have) to this repo's actual
   `/review` dispatch step.

`0009`'s account — "`infra-reviewer` and `security-reviewer` are replaced by
a single `security-auditor` agent," describing the new file's content as if
independently written to cover both retired agents' scope — never mentions
this upstream source. That's an incomplete record, not a reversed decision:
`0009`'s frontmatter-adaptation details and the "resolved" note about
dropping pattern-consistency review are still accurate and still stand.
Left `0009`'s text untouched per this repo's own reversal convention (it
governs edits to a superseded decision; this is a factual correction to an
incomplete one, and the file itself is still substantively right about
what changed structurally — just silent on where the replacement's content
actually came from). Updated `README.md`'s agents-directory bullet instead,
moving `security-auditor` from the "first-party" group into the "vendored"
group alongside `code-reviewer` and `test-engineer` (all three MIT-licensed
under the same `ADDYOSMANI_AGENT_SKILLS_LICENSE` already present in this
repo — no new license file needed, the coverage was already there, just the
attribution in prose wasn't).

**Why this matters beyond bookkeeping.** It explains a real finding from an
earlier harness deep-review: `security-auditor`'s inline "Review Scope"
checklist doesn't reference `references/security-checklist.md`,
`ai-security.md`, or `supply-chain.md` at all, despite those existing
specifically as this repo's security single-source-of-truth. The sequencing
is now clear — `security-auditor` (vendored, predates those reference
files) was never reconciled with them once they were added later (commit
`88ed7c6`, "Add AI Security and Supply-Chain References"). This is a gap to
close, not a mystery: whether and how to point the vendored checklist at
the newer reference docs without breaking what upstream intended is a
separate decision, not made here.

**Rejected — re-deriving `security-auditor` as a fresh first-party file now
that its origin is known.** The vendored content is sound and the license
already covers it; rewriting it from scratch would discard a working,
upstream-maintained persona for no benefit over just correcting the record
and, separately, reconciling it with the newer reference docs.
