# Adopted `docs/adr/*.md`, split `TECHNICAL_DECISIONS.md`

**Decision.** Reverses the rejection recorded in
`0014-extracted-spec-plan-task-templates.md`, which rejected forking
`TECHNICAL_DECISIONS.md` into per-decision `docs/adr/*.md` files as "a
second, competing convention." Per direct instruction, `TECHNICAL_DECISIONS.md`
was split into this `docs/adr/` directory — one file per decision,
numbered in the order the decisions were originally recorded — and the
source file removed. No new rationale is recorded here beyond the
instruction itself: `dotfiles/claude/references/documentation-practices.md`
and `dotfiles/claude/CLAUDE.md` already described `docs/adr/*.md` as this
machine's convention before this split executed, so the convention doc
and the actual repo layout were out of sync until this decision closed
that gap. The "one running file vs. one file per decision" tradeoff that
`0014` weighed was not reopened or re-litigated — just overridden.

Cross-references inside the split-out files that used to say "see ...
above" (pointing at another section of the same running file) were
rewritten to name the specific file they point at, since the sections no
longer share a document. `docs/agents.md` and
`dotfiles/claude/agents/vector-database-engineer.md`, which cited
`docs/TECHNICAL_DECISIONS.md` directly, were repointed at the specific
new file covering the decision each one actually cites. `README.md`'s
own reference to the new location (introduced ahead of this split) said
`docs/adrs/*.md`; corrected to singular `docs/adr/*.md` to match
`dotfiles/claude/CLAUDE.md` and `documentation-practices.md`, which
already used the singular form — one spelling, not two.

**Rejected — none.** This entry documents an instructed reversal, not a
freshly weighed choice between alternatives. `0014`'s original rejection
paragraph is left in place rather than deleted or reworded, per
`documentation-practices.md`'s own rule that a reversed decision stays
recorded as a rejected entry on the *new* decision, not erased from the
old one.
