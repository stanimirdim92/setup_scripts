# REVIEW.md

<!-- What matters when this repository is reviewed. Code owners write it.
/review passes it to every reviewer (ADR 0091), read from the base branch,
never from the change under review (ADR 0094). Claude Code Review reads the
same file, so the headings follow its documented example. Keep it short:
every review loads it. Put one at the repository root; a directory may hold
its own REVIEW.md for rules that apply only under it. General project context
belongs in CLAUDE.md, not here. -->

## What Important means here

<!-- The defects that block in this repository, concretely. Examples: "a query
that drops the tenant scope shows one customer another's data"; "docs that
lie"; "config that misroutes". In the harness, Important is BLOCKER or
REQUIRED; a nit is ADVISORY. -->

- ...

## Cap the nits

Report at most 5 nits per review. Keep the ones that matter most.

## Do not report

<!-- Paths and issue classes not worth comments: generated files, vendored
code, lockfiles, checks CI already enforces. -->

- `path/to/generated/**`

## Always a person

<!-- Paths so costly to get wrong that a person reads every change to them,
one glob per bullet in backticks. A change touching one runs every specialist
reviewer and /test, and /ship lists the files under "Read these yourself"
(ADR 0096). In a directory's own REVIEW.md, globs are relative to it. -->

- `.github/workflows/**`
- `database/migrations/**`

## Review depth

<!-- Optional. The lowest depth any change here gets: Quick, Standard or Deep.
The change's own risk tier can raise it, never lower it (ADR 0106). Delete
this section to let the tier decide. -->

Standard

## Always check

<!-- What a reviewer must look at on every change in this area, and the
evidence rule. -->

- Behavior claims need a `file:line` citation, never a guess from a name.
- Mark a defect the change did not introduce as pre-existing.
- ...
