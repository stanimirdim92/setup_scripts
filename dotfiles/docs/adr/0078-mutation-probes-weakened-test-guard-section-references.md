# Mutation probes, a weakened-test guard, and checked section references

**Context.** Three ideas from the last two weeks of addyosmani/agent-skills
(MIT), checked against this harness on 2026-10-04:
- its code review answers "would the tests catch a regression?" by
  experiment (commit `28f435e`);
- its floor guard lists diff changes that make passing easier (the
  `constraint-driven-development` reference, fixed in `aa68c3e`);
- its link validator checks `#anchor` fragments (commit `a831506`).

The harness had none of them. Our code review asks the regression question
and answers it by reading. No reviewer rule or check looks for a weakened
test. `check-references.py` dropped the anchor, and about 60 `§Section`
references were never checked.

**Decision — `test-engineer` probes the tests by mutation.** For each
condition the candidate adds on an in-scope requirement's path:
1. Copy the file.
2. Invert one condition.
3. Run the focused tests.
4. Restore the file and confirm that `git diff` is clean.

A mutant that stays green has survived. The agent writes the missing test,
then shows that the new test kills the mutant. This is the only production
edit `test-engineer` may make. It lasts one test run and is never committed.
`/test` checks that every file was restored and every survivor has a test or
a reason. Reviewers stay read-only, so the probe belongs in `/test`, not in
`/review`.

**Decision — `/review` runs a weakened-test guard.**
`skills/code-review-and-quality/scripts/weakened-tests.py` reads the diff
from the candidate's base. It lists six moves:
- a deleted test file;
- a skip, todo or focus marker;
- a test that stayed but lost assertions;
- a new suppression comment;
- a changed checker config line;
- a stub or an empty catch in code.

A rename is not a deletion. A file moved and edited in one change is not a
deletion either. Documentation files are skipped. Exit 0 means none found, 1
means some found, and 2 means it could not run. A 2 is recorded as Not
verified, never as clean. `/review` gives the list to `code-reviewer`. Each
entry ends as a finding or a stated reason. The script lives in the skill, so
it is linked into `~/.claude` on every machine. Its fixtures run in CI. On
this repository's last 30 commits it listed four entries, all real empty
catches.

**Decision — section references are checked.** `check-references.py` now
fails when a `#anchor` matches no GitHub heading slug. It also fails when a
`§Section` after a path, or after a backticked skill, persona or command name,
matches no heading. A numbered section (`§3`) must match a heading numbered 3.
It checks 64 section references today, and all resolve.

**Rejected.**
- *Vendor the floor guard.* It is Node and tied to a `CONSTRAINTS.md` file
  this harness does not use. The contract transfers; the code does not.
- *Mutation testing tools (Infection, Stryker, mutmut).* A full run costs
  minutes to hours and needs per-project setup. One hand-made probe per risky
  condition answers the review question.
- *Let `code-reviewer` run mutations.* It is read-only by design (ADR 0055).
