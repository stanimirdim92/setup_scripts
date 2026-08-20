---
name: jira-ticket
description: "Jira ticket intake only. Use when the user asks to work on a Jira ticket. Fetch the ticket, extract its requirements and relevant context, surface true blockers, then return /spec as the next action. A Jira key used only as context or an example does not trigger this skill. Never invoke /spec automatically."
---

# Jira Ticket — Intake Only

Fetch and understand the Jira ticket, then prepare the handoff to `/spec`.

Do not inspect the repository, plan, implement, test, or review from this skill.

## 1. Intake

Resolve the ticket:

- Exact key or Jira URL → use it directly.
- Description without a key → search Jira and use the clear match.
- If multiple plausible matches exist, ask the user.
- Never guess between ambiguous candidates.

## 2. Fetch the ticket

Prefer Jira access in this order:

1. A configured `jira` CLI, if available.
2. Configured Atlassian/Jira MCP tools.
3. User-provided ticket contents.

For Atlassian MCP:

- Resolve the accessible Atlassian resource/cloud ID if not already known.
- Reuse the resolved cloud ID for the session.
- Fetch the Jira issue including status, description, acceptance criteria,
  comments, links, parent, and other relevant fields.
- Prefer markdown-formatted content when supported.

After fetching the ticket:

- Check for direct subtasks/child issues.
- Query direct children explicitly when needed (e.g.
  `parent = [TICKET] ORDER BY key ASC`) rather than assuming the main issue
  response includes them.
- Fetch at least each child's key, summary, status, and issue type.
- If a child issue materially adds requirements or constraints not present on
  the parent, read its relevant content too.

If no Jira integration is available, say so plainly and ask the user to paste:

- description
- acceptance criteria
- relevant comments
- linked/parent issue context if needed

### Fetch failures

If Jira access exists but fetching fails, report the actual failure.

Distinguish between:

- integration not configured
- authentication failure
- insufficient permissions
- invalid/wrong cloud or site
- ticket not found
- tool/API failure

Do not silently treat a failed configured integration as if Jira were not
configured.

## 3. Read the ticket

Read:

- summary/title
- status
- description
- acceptance criteria / Definition of Done
- relevant comments
- direct subtasks/child issues
- parent or linked issues when they materially affect the ticket
- attachments explicitly referenced as requirements

For subtasks/child issues:

- always include their key, title, and status in the intake
- read their details when they materially refine, constrain, or decompose the parent scope
- do not recursively traverse grandchildren unless they materially affect the
  requested work

Do not fetch unrelated Jira context.

## 4. Restate what the ticket requires

Translate the Jira content into a concrete requirements list.

Preserve distinctions between:

- explicit requirements
- acceptance criteria
- constraints
- open questions
- relevant context

Do not invent missing requirements.

## Sparse Tickets

Jira does not need to contain a full technical specification.

If implementation details are missing but can reasonably be discovered from
the repository, existing behavior, tests, or architecture, record them as
questions for `/spec` rather than asking the user.

Examples:

- which module owns the behavior
- current DB/API shape
- existing implementation pattern
- whether a migration is needed
- which tests cover it

Only stop for clarification when the missing information is a real product,
business, security, permissions, or externally observable behavior decision
that `/spec` cannot safely infer.

Do not ask the user to answer repository questions.

## Required References

If the ticket explicitly depends on an attachment or linked specification
(e.g. "use this prompt verbatim"), read it before handoff when possible.

If an authoritative required reference cannot be retrieved, name the missing
item and stop instead of pretending intake is complete.

## 5. Output

Return a concise Jira intake summary.

Use this structure:

### [TICKET] — [Title]

**Status:** [status]

**Subtasks / Child Issues**
- [KEY] — [Title] — [Status]
- ...
- None. <!-- if none -->

**Requirements**
- ...

**Acceptance Criteria**
- ...
- ...
- Not specified in Jira. <!-- if none -->

**Constraints**
- ...
- None explicitly specified. <!-- if none -->

**Relevant Context**
- ...
- None. <!-- if none -->

**Questions for `/spec`**
- ...
- None. <!-- if repository recon is not needed -->

**Blockers**
- ...
- None. <!-- if no true blocker exists -->

**Next action:** `/spec`

## 6. Handoff

For implementation or fix work, the expected pipeline is:

`/jira-ticket` → `/spec` → `/plan` → `/build`

Never skip phases.

This skill does **not** invoke `/spec` automatically.

The intake summary above is the handoff payload for `/spec`.

Preserve:

- explicit Jira requirements as requirements
- contextual information as context
- repository-resolvable unknowns as questions for `/spec`
- true product ambiguities or unavailable authoritative references as blockers
- direct subtasks/child issues and their status

Do not make `/spec` refetch Jira information already collected during intake.

After producing the summary, return `/spec` as the next action and stop.

## Hard Stop

Once the ticket has been restated and any intake-level ambiguity has been
surfaced:

**STOP.**

Do not:

- invoke `/spec`, `/plan`, or `/build`
- inspect the repository
- perform recon
- propose architecture
- produce an implementation plan
- modify files
- execute commands for implementation
- run tests
- review implementation
- commit, push, or open a PR
- update Jira

Return `/spec` as the next action instead.
