---
name: jira-ticket
description: "Jira ticket intake only. Use when the user asks to work on a Jira ticket. Fetch requirements and relevant context, surface and record blockers, and hand off to /spec without invoking it. A Jira key used only as context or an example does not trigger this skill."
---

Resolve this file's symlink before opening the relative links below.

Read [Codex workflow conventions](../../references/workflow-runtime.md), then
follow the shared [Jira intake skill](../../../claude/skills/jira-ticket/SKILL.md).
Finish intake and report `$spec`, in a new session, as the next action. Do not invoke it.
