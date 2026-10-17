# REVIEW.md

<!-- What matters when this repository is reviewed. Code owners write it;
/review passes it to every reviewer (ADR 0091). Keep it short: every review
loads it. Put one at the repository root. A directory may hold its own
REVIEW.md for rules that apply only there. -->

## What failure looks like here

<!-- Name the ways a change goes wrong in this repository, concretely.
Examples: "a query that drops the tenant scope shows one customer another's
data"; "docs that lie"; "config that misroutes". -->

- ...

## Always check

<!-- The few things a reviewer must look at on every change in this area. -->

- ...

## Skip

<!-- Paths not worth review comments: generated files, vendored code,
lockfiles, snapshots. -->

- `path/to/generated/**`

## Rules for findings

- Evidence is a `file:line` in the diff or the code it reaches, never a guess
  from a name.
- At most [N] ADVISORY findings per review; keep the ones that matter most.
- Mark a defect the change did not introduce as `pre-existing`.

## Summary

Start the summary with the count of findings by disposition. When there is
nothing to fix, say so in one line.
