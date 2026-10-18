# /ship checks the candidate on the current base

**Context.** `/ship` judged the candidate as it was built. The base branch can
move during the ticket. Two changes that each pass alone can then break the
base together: one removes what the other uses, or both edit the same code. A
merge queue catches this by re-running the checks on the latest base with the
change applied. Anthropic's Claude Code team runs one for that reason
(claude.dev, "Solving code review at Anthropic", 2026-10, layer 6).
`warn-stale-base.sh` only warns when a worktree's base is old.

**Decision.**
- `/ship` runs `skills/git-workflow-and-versioning/scripts/base-check.sh`
  before GO.
- When the base has not moved past the candidate's merge base, it reports
  "Base: current" and stops.
- Otherwise it merges the base into a scratch worktree of the candidate, runs
  the project's setup command, then the plan's integrated verification
  commands, and removes the worktree. The candidate is never touched.
- A merge conflict or a failing check is NO-GO; the fix is a new candidate
  through `/build` and `/review`. A failure the project already lists as known
  is pre-existing. A check that cannot run is SHIP BLOCKED.
- The script is project-agnostic: the plan names the commands, the project's
  `CLAUDE.md` names the setup.

**Cost.** One run of the integrated checks at `/ship` when the base moved,
plus the setup time of a fresh worktree.
