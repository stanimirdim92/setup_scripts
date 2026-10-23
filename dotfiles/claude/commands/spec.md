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

An intake design reference marked partially read or unread is finished here,
before drafting. Open each pinned Figma node with the available Figma tools:
`get_metadata` and `get_screenshot` are enough, and no code is generated. A
node that still cannot be read stays an Assumption under the skill's
design-backed rule.

Design edits are out of `/spec` scope. Read designs with `get_metadata`,
`get_screenshot` or `get_design_context`. Write tools such as `use_figma` need
an edit seat. When the owner asks for a design edit, try it once. On a seat or
access error, stop and give paste-ready comment text for the designer. Ask the
owner to re-authenticate only when the error names authentication.

## Decision brief

Some questions decide whether a requirement exists at all: a ticket/design
conflict, or a feature the design drops. When an intake Blocker or an
`OPEN QUESTION` is of that kind, present a decision brief before drafting.
The brief holds the questions only, in the skill's question shape, on about
one page. Number them Q1, Q2, … and end with the `decisions:` line from
§Approval state. Draft requirements only after the owner answers. All other
spec content, checks and gates stay as written. Unattended runs skip the brief
and follow §Unattended.

## Repository evidence

Follow `../references/repository-precedent.md` §1 for reuse, bounded checks,
or `repo-recon` dispatch. Keep repository-defined commands exact and distinguish
finding a command in source from executing it successfully.

## Draft or revise

Use the skill's scope check, form selection, capability-map rules, and Output
Files rules, including project overrides. Read existing target artifacts before
writing. Revise in place only for the same work; ask if the target is ambiguous
or belongs to different work rather than overwriting it. Revise an existing
spec with targeted edits to the affected sections, not a whole-file rewrite.
The content rules and the skill's §Keeping the Spec Alive search still apply.

The selected template owns the heading, header, and document shape. Keep the
skill's requirement ids, source lines, and scenario forms. For an existing spec,
preserve stable ids and use the status transitions in
`../references/spec-quality-gates.md` §2; do not reset its header as if new.

Before asking for approval, run the skill's Approval Check and the applicable
checks in `../references/spec-quality-gates.md`. A draft may expose questions
for discussion, but must not be presented as ready for approval while unresolved.

In this conversation, decide some questions by default. Use the risk and
recommendation rules in §Unattended.

- Low risk: decide it with the recommended option.
- Low or Medium, and the ticket text or repository precedent already settles
  it: decide it that way and cite the line.
- Record each as a `DEC-###` with the alternative that lost and
  `Decided by: default (interactive)`. Remove the block.
- Medium questions nothing settles, and every High question, stay
  `OPEN QUESTION` blocks.
- List each default in the report, one line each, under
  `Defaults taken (override by id)`, before the approval request. An override
  rewrites that `DEC-###` as §Unattended's last paragraph describes.

## Approval state

New specs start as Draft. Only explicit human approval sets Approved and its
approval metadata; passing the check, silence, or an instruction to continue
does not grant approval. Editorial revisions retain existing approval;
behavioral revisions require reapproval under the shared transition rules.

Save the spec, then check its shape:

```bash
python3 ~/.claude/skills/spec-driven-development/scripts/check-spec.py docs/specs/<TICKET>-SPEC.md
```

Fix every FAIL before presenting the spec. A FAIL means a form a later stage
reads mechanically is missing: a `Source:` line, a scenario's THEN, an RFC 2119
keyword, or approval lines that disagree with Status. Read each warning and fix
the ones that are slips. Report the result.

Report the spec's path, status, and remaining blockers. When `OPEN QUESTION`
blocks remain, number them Q1, Q2, … in spec order and end the report with one
line the user can fill in and send back:
`/spec <TICKET> decisions: Q1=…, Q2=…`. A rerun with that line revises the
same spec in place with those decisions; it does not repeat recon.

When the user approves in this conversation, set `Status: Approved`,
`Approved by` and `Approved at` in one edit. Read the header back from disk and
quote its Status and Approved lines in the report. Rerun the shape check, and
commit the spec file alone in the same turn. Approval is the user's; the commit
only stops an approved spec from staying uncommitted, which blocks `/plan`.
On the default branch of the main checkout, first warn in one line that ticket
work belongs in the ticket worktree (`AGENTS.md` §Worktrees).

On approval, draft a short decision-summary comment for the Jira ticket in the
report: the spec path, and each `DEC-###` in one line. The comment is visible
outside the team. Post it only when the project's `CLAUDE.md` holds the exact
line `Jira decision comments: on`. Otherwise leave it as a draft for the owner.
After posting, record the comment id in the spec header as
`Jira comment: <id>` before the commit. On reapproval, update that comment
instead of adding a new one.

`/spec` ends here; it does not invoke `/plan` or implementation. After approval and commit,
recommend `/clear` before `/plan`: `/plan` reads the committed spec, and a fresh
context stops every planning request from re-reading this stage's conversation
(ADR 0084). Preserve the durable handoff described by the skill so `/plan`
works without the conversation transcript.

## Unattended (ADR 0115)

`/spec <TICKET> unattended` runs with nobody in the conversation.
`tools/run/ticket.py` starts it and carries the questions to the owner.

- Write each choice that needs an `OPEN QUESTION` in the skill's format. Mark
  the option you recommend `(recommended)`. Add a line `Risk: High`,
  `Risk: Medium` or `Risk: Low` for the area the choice changes, from
  `../references/risk-tiers.md`. When unsure, take the higher tier.
- Recommend in this order. First, the option the repository already follows
  (`../references/repository-precedent.md`). Next, the option that keeps
  existing behavior and data and can be undone. Last, the smaller change.
  Name the reason after `(recommended)`.
- Low or Medium: decide it with the recommended option. Record a `DEC-###`
  under Material Decisions with the alternative that lost and the line
  `Decided by: default (unattended, ADR 0115)`. Remove the block.
- High: keep the block. The owner answers it.
- The owner already answered it for this ticket, in an earlier or archived
  spec (`Decided by: owner`, or an Approved spec): reuse that answer as a
  `DEC-###` with `Decided by: owner, <date>, <source>`. That answer is the
  explicit approval a project rule asks for. Ask again only when a fact the
  answer rests on has changed, and name that fact.
- An earlier or archived spec for the ticket also carries fixes, such as a
  scenario corrected after a `/plan` SPEC CONFLICT. Keep them; do not bring
  back the wording they replaced.
- A question only the owner can answer, such as domain history, is an
  `OPEN QUESTION` too, with its risk.
- Do not ask in the chat, and never set Approved.

A later `/spec <TICKET> decisions: …` from `ticket.py` records each answer as
a `DEC-###` decided by the owner. When it names a default the owner changes
("the owner decides instead of the default: …"), rewrite that `DEC-###` with
the owner's choice, the default as the alternative that lost, and
`Decided by: owner`. `ticket.py` sets Approved only when the owner's own
reply names the ticket. That reply is the explicit human approval.
