---
name: laravel-worktree-isolation
description: Set up a Laravel repository so its test suite runs isolated per git worktree, with a separate database and Redis keyspace, enabling parallel ticket work. Use when one worktree's tests corrupt another's, or when a project's test database is built from a schema dump rather than migrations.
---

Resolve this file's symlink before opening the relative links below.

Read [Codex workflow conventions](../../references/workflow-runtime.md), then
follow the shared [Laravel worktree isolation skill](../../../claude/skills/laravel-worktree-isolation/SKILL.md).

Establish the project's facts before writing anything, produce the scripts
inside the target repository rather than in dotfiles, and run the skill's
Verification section rather than reporting the setup as complete untested.
