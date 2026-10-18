# Paths that always need a person

**Context.** Some files are costly to get wrong however small the change: CI
and deploy workflows, migrations, auth and permission code, billing,
installers, environment files. The reviewer triggers looked at what a diff
does, not where it lands, so a one-line migration could get only the two
default reviewers. Anthropic's Claude Code team makes such paths always need a
person, through CODEOWNERS and branch protection (claude.dev, "Solving code
review at Anthropic", 2026-10, layer 5).

**Decision.**
- A project lists these paths in its `REVIEW.md` under "## Always a person",
  one glob per bullet. A directory's own `REVIEW.md` can add globs relative
  to it.
- `skills/code-review-and-quality/scripts/always-person.py` reads the list
  from the base branch, never from the change (ADR 0094), and prints the
  changed files that match.
- A match runs every specialist reviewer and requires `/test`
  (`reviewer-triggers.md`, `verification-triggers.md`).
- `/ship` puts the matched files first in its report, under "Read these
  yourself". GO stays the user's decision.
- A result that could not be computed blocks `/ship`.

**Cost.** More reviewer runs and a `/test` run for changes on listed paths.
The list is only as good as the project keeps it.
