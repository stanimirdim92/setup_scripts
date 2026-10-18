# Reviews catch instruction lines a change makes untrue

**Context.** Agents follow `CLAUDE.md`, `AGENTS.md`, `REVIEW.md`, `.ai/rules`
and the README literally. A change that renames `bin/worktree-test.sh` can
pass every test and still leave "run `bin/worktree-test.sh`" in `CLAUDE.md`.
The next session follows a dead instruction. Anthropic's reviewer flags
"changes that make a line in it out of date" (claude.dev, "Solving code review
at Anthropic", 2026-10, layer 1). The owner chose a script for the mechanical
cases and a reviewer rule for the rest.

**Decision.**
- `skills/code-review-and-quality/scripts/stale-instructions.py` lists the
  instruction lines that still name a file the change deletes or renames, or
  run a `package.json` or `composer.json` script the change removes. It reads
  the instruction files as the candidate leaves them, so a change that also
  fixes the line is clean. It is project-agnostic.
- `/review` runs it and reports each hit as a REQUIRED `STALE-#` finding.
- `code-reviewer` covers changes in meaning: when the diff changes how
  something is done, a line it makes untrue is a REQUIRED finding with what
  the line says and what is true now.
- No new reviewer persona. Add one only if `review-noise.py` shows stale
  instructions still getting through.

**Cost.** One script run per review. The script can match a file name used
for something else in prose; such a hit is refuted at `/ship`.
