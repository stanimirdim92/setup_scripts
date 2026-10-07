---
description: Start spec-driven development — write a structured specification before writing code
argument-hint: "[ticket or feature description]"
model: opus[1m]
---

Invoke the `spec-driven-development` skill before drafting; its methodology is
required, not optional background.

Resolve the requested ticket or feature from the argument and conversation.
Reuse the intake, user decisions, and current repository evidence; ask only for
material information still missing. Do not repeat a questionnaire or ask the
user to supply facts the repository establishes.

For ticket-backed work, accept Jira intake only when its complete output is in
the current conversation, in `docs/specs/<TICKET>-intake.md`, or the user
manually supplies it in this conversation.
If it is absent, incomplete, or stale for the requested scope, refetch the main
ticket and every discovered ticket/subticket by following `jira-ticket` §§1–3,
including its source-coverage and blocker rules, before repository recon or
drafting. Do not reconstruct intake from memory or an agent summary. If Jira is
unavailable and the user has not supplied the complete intake, report the
specific blocker and request that intake.

## Repository evidence

Follow `../references/repository-precedent.md` §1 for reuse, bounded checks,
or `repo-recon` dispatch. Keep repository-defined commands exact and distinguish
finding a command in source from executing it successfully.

## Draft or revise

Use the skill's scope check, form selection, capability-map rules, and Output
Files rules, including project overrides. Read existing target artifacts before
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

Save the spec, then check its shape:

```bash
python3 "$HOME/.claude/skills/spec-driven-development/scripts/check-spec.py" docs/specs/<TICKET>-SPEC.md
```

Fix every FAIL before presenting the spec. A FAIL means a form a later stage
reads mechanically is missing: a `Source:` line, a scenario's THEN, an RFC 2119
keyword. Read each warning and fix the ones that are slips. Report the result.

Report the spec's path, status, and remaining blockers. `/spec` ends
here; it does not invoke `/plan` or implementation. After approval and commit,
recommend `/clear` before `/plan`: `/plan` reads the committed spec, and a fresh
context stops every planning request from re-reading this stage's conversation
(ADR 0084). Preserve the durable handoff described by the skill so `/plan`
works without the conversation transcript.
