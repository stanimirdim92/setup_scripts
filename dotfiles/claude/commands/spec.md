---
description: Start spec-driven development — write a structured specification before writing code
argument-hint: "[ticket or feature description]"
---

Invoke the `spec-driven-development` skill before drafting; its methodology is
required, not optional background.

Resolve the requested ticket or feature from the argument and conversation.
Reuse the intake, user decisions, and current repository evidence; ask only for
material information still missing. Do not repeat a questionnaire or ask the
user to supply facts the repository establishes.

## Repository evidence

Follow `../references/repository-precedent.md` §1 for reuse, bounded checks,
or `repo-recon` dispatch. Keep repository-defined commands exact and distinguish
finding a command in source from executing it successfully.

## Draft or revise

Use the skill's scope check, form selection, and Output Files rules, including
per-module paths and project overrides. Read existing target artifacts before
writing. Revise in place only for the same work; ask if the target is ambiguous
or belongs to different work rather than overwriting it.

The selected template owns the heading, header, and document shape. Keep the
skill's requirement ids, source lines, and scenario forms. For an existing spec,
preserve stable ids and use the status transitions in
`../references/spec-quality-gates.md` §2; do not reset its header as if new.

Before asking for approval, run the skill's Approval Check and the applicable
checks in `../references/spec-quality-gates.md`. A draft may expose questions
for discussion, but must not be presented as ready for approval while unresolved.

## Approval state

New specs start as Draft. Only explicit human approval sets Approved and its
approval metadata; passing the check, silence, or an instruction to continue
does not grant approval. Editorial revisions retain existing approval;
behavioral revisions require reapproval under the shared transition rules.

Save the spec and report its path, status, and remaining blockers. `/spec` ends
here; it does not invoke `/plan` or implementation. After approval, the user
may invoke `/plan` in this session or a new one. Preserve the durable handoff
described by the skill so either works without the conversation transcript.
