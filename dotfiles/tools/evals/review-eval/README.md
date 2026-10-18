# Review eval

Does `/review` catch bugs that really shipped, without crying wolf on changes
that were fine?

## How it works

A bugfix commit holds its own answer key. The lines it changed were wrong.
`git blame` on those lines finds the commit that wrote them. The eval runs a
standalone `/review` on that commit, on the code as it was just before it, and
checks whether a BLOCKER or REQUIRED finding points within 3 lines of them.

A **clean case** is a commit nobody had to fix. There every BLOCKER or REQUIRED
finding is noise.

## Running it

```bash
cd dotfiles/tools/evals/review-eval
P=/path/to/project

# Build cases once (free). Pick fixes whose bug a reviewer could see in one diff.
python3 run.py --new feed-order --repo $P --fix <bugfix sha>
python3 run.py --new quiet-1    --repo $P --clean <sha of a commit that needed no fix>

# Baseline, then after a harness change (each case is one paid /review run)
python3 run.py --fixture feed-order --fixture quiet-1 --repo $P --output ./before
python3 run.py --fixture feed-order --fixture quiet-1 --repo $P --output ./after --baseline ./before/results.json

# Judge a SARIF file you already have (free)
python3 run.py --fixture feed-order --findings path/to/review.sarif
```

A review that did not finish is not scored. An error result, REVIEW BLOCKED,
empty output, or a findings count the report does not back up marks the case
`ERRORED (not scored)`, and the run exits 1. A quiet review counts only when
the SARIF exists or the report says `Nothing to fix`.

`--bug <sha>` overrides the blame guess when the fix touched lines from more
than one commit. The run ends with BETTER, SAME, NOT BETTER or WORSE, as in
spec-eval. Run each side twice before you trust a small difference.

## When to run it, and what it costs

A change to a reviewer persona, `/review`, the reviewer triggers, the risk
tiers, or a reviewer's model needs a rescore (ADR 0111). CI checks that the
commit says how it went, in a trailer:

```text
Review-eval: bugs 5/8 -> 6/8, clean 3/3 -> 3/3 (BETTER); ./after/results.json
Review-eval: not run - wording only, no change to what is reported
```

Each case is one full headless `/review`: the three always-on reviewers, any
specialist the case triggers, and the BLOCKER check. `--budget` caps each run
(default $10), and the run prints the measured `Cost:` at the end. A rescore
reuses the stored baseline, so it costs one run per case, two if you repeat
it to trust a small difference. With 8 cases that is 8 to 16 runs, at most
$80 to $160 at the default cap. Write down the first measured `Cost:` line
and use it, not the cap, to decide when a change is worth a run.

## Where cases come from

Every row in the "Shipped bugs" table of `dotfiles/docs/observation-log.md`
becomes a case (ADR 0100). Add the case when you add the row.

## Good cases

- A revert, or a fix whose message names the defect.
- A bug visible in the diff that introduced it. A bug that needs production
  data or another service to show is not a fair case.
- A few clean cases for every few bug cases, so a reviewer that flags
  everything does not score well.

Cases and output are gitignored: they name a private project's commits and
files. `test_review_eval.py` covers case building and judging, and runs in CI.
