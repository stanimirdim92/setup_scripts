# Extracted spec/plan/task templates to `references/templates/`

**Decision.** A ChatGPT-drafted proposal suggested a much larger doc set
for an "AI agent harness" (`ARCHITECTURE.md`, `DESIGN.md`, `CONVENTIONS.md`,
`COMMANDS.md`, `TESTING.md`, `SECURITY.md`, `DEVELOPMENT.md`, `docs/adr/`,
`.ai/workflows/`, `.ai/agents/`, `.ai/rules/`, `.ai/templates/`,
`.ai/repo-map.md`). Checked it against what's already here instead of
adopting it wholesale: that proposal is shaped for a product codebase
(app/domain/services layout, tenant isolation, lint/test commands) —
this repo configures the harness other repos use, it isn't one. Mapped
each item:

- `CONVENTIONS.md`/`COMMANDS.md`/`TESTING.md`/`DEVELOPMENT.md`/
  `ARCHITECTURE.md`/`DESIGN.md` — **rejected outright**, not a gap. These
  are per-target-project files (a Laravel repo's lint/test commands
  aren't this repo's business) and belong in that project's own
  `CLAUDE.md`, not here.
- `SECURITY.md` — already covered by `references/security-checklist.md`.
- `docs/adr/*.md` (one file per decision) — **rejected as a second, competing
  convention**, not adopted alongside the existing one: `TECHNICAL_DECISIONS.md`
  (this file) already serves ADR's exact purpose — decision + reasoning +
  rejected alternatives, per entry — as one running file. Forking into
  per-decision files would mean two places recording the same kind of
  thing with no rule for which one wins; picked the one already working
  (rule 6: surface conflicts, don't blend them).
- `.ai/workflows/`, `.ai/agents/`, `.ai/rules/` — already exist as
  `commands/`, `agents/`, and `skills/`+`references/` respectively, just
  under this repo's own naming.
- `.ai/repo-map.md` — N/A, no app tree here to map.
- `.ai/templates/` (spec/plan/task templates as standalone files) — **the
  one genuine gap**. The shape existed, but only as prose embedded inside
  `spec-driven-development`/`planning-and-task-breakdown`'s own `SKILL.md`
  files, duplicated between the two (e.g. `spec-driven-development` kept a
  second, lighter task-template copy "for convenience"). Extracted into
  `references/templates/spec.md`, `plan.md`, `task.md` and pointed both
  skills at them instead, the same de-duplication pattern
  `reviewer-triggers.md` already uses for reviewer-dispatch conditions —
  one canonical copy, not two that can quietly drift apart.

**Rejected — a `docs/adr/` template too, for decisions this file doesn't
already cover.** Nothing here suggested `TECHNICAL_DECISIONS.md`'s shape
is insufficient; adding a parallel ADR template would invite exactly the
two-conventions-for-one-thing problem this decision otherwise avoided.

> **Superseded by `0015-adopted-docs-adr-split-technical-decisions.md`.**
> The rejection above was reversed by direct instruction — this file is
> itself one of the per-decision files that rejection argued against
> forking into. Left as originally written, not edited, per this
> machine's own rule that a reversed decision stays recorded as a
> rejected entry on the new decision rather than being erased from the
> old one.
