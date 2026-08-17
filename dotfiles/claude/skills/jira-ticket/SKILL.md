---
name: jira-ticket
description: "Intake ONLY for a Jira ticket (e.g. LD-123). Use whenever the user provides a Jira ticket key or asks to work a ticket. Does not recon, plan, implement, test, or deliver — hands off to /spec, which hands off to /plan, which hands off to /build. Never continue past intake from inside this skill."
---

# Jira Ticket — Intake

This skill covers intake only. Fetch the ticket, read it, restate it, surface
ambiguity — then stop and hand off. Recon, planning, implementation, testing,
quality gates, and delivery are `/spec`'s, `/plan`'s, and `/build`'s jobs, not
this skill's — do not execute those phases from here even if the next step
feels obvious.

## Phase 1 — Intake

1. Resolve the ticket key, in order:
   - If the user gave an exact key (e.g. `LD-123`), use it directly.
   - If the user described the ticket instead of naming it (e.g. "my next
     high-priority bug", "the ticket about X"), and a `jira` CLI or the
     Atlassian MCP's JQL search is available, run a JQL search to find
     candidates and confirm the match with the user before fetching — don't
     guess which ticket they mean.
2. Fetch the ticket, in order:
   - Prefer a `jira` CLI if this environment has one configured — check for
     it before reaching for MCP.
   - Otherwise use the Atlassian/Jira MCP tools if configured (in Claude
     Code: `getAccessibleAtlassianResources` to resolve the cloud ID — cache
     it for the session — then `getJiraIssue` with `comment` in fields and
     `responseContentFormat: "markdown"`).
   - If neither is available, say so plainly and ask the user to paste the
     full ticket (description, acceptance criteria, comments).
   - If a fetch is attempted but fails, distinguish "not configured" from
     "configured but the fetch failed" (auth, permissions, wrong cloud ID,
     ticket not found) — surface the actual failure, don't silently fall
     back to asking the user to paste it as if nothing was configured.
3. Read description, acceptance criteria, comments, and linked issues (fetch
   linked/parent issues if they add context).
4. Restate the ticket as a concrete requirements list. If anything is ambiguous or
   contradicts the codebase, ask the user now.

## Handoff

Invoke `/spec` next. The pipeline from there:

- `/spec` turns the restated requirements into `SPEC.md`, gets it approved.
- `/spec`'s downstream is `/plan` — reads the spec, produces
  `tasks/[TICKET]-plan.md` + `tasks/[TICKET]-todo.md`, gets the plan approved.
- `/plan`'s only next action after approval is `/build` — never implement
  directly from `/plan` either (see `/plan`'s own "After approval" note).
- `/build` dispatches `executor` subagents per workstream, fans out
  independent review, and renders a GO/NO-GO verdict.

Do not implement, recon, or plan from inside this skill — that shortcuts the
dispatch/review/verdict layer `/build` provides.

## Project conventions for later phases

Not this skill's job to apply these, but `/spec`, `/plan`, and `/build`'s
dispatched executors need them, and they're project-specific — this skill is
global, so don't assume any single project's answer. Check the current
project's own `CLAUDE.md`/`AGENTS.md` and any project-local architecture skill
(e.g. a `module-architecture`-style skill) for:

- Module/directory layout and layering rules.
- Branch naming convention (match existing branch names in `git log`/`git branch -a`).
- Commit message convention (match existing commits in `git log`).
- Whether Jira is read-only for this project (never push, open a PR, or post a
  Jira comment without explicit user confirmation — offer a drafted
  done-comment and post it only if approved, unless the project says otherwise).
