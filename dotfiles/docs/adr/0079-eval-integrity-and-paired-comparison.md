# Eval integrity and paired comparison

**Context.** Comparing a fresh LD-441 spec with the deployed one showed that
the spec eval measured its own defects as much as the harness:
- The reference was the spec as it stands today. Its 2026-09-18 reapproval
  added two findings from review, made after the build. A spec written at
  the base commit cannot know them, so they counted as misses.
- The intake was fetched weeks after the work shipped. It held a comment
  from 2026-09-23 that gave the fresh run a decision the original run had to
  ask for.
- The term extractor counted `file:line` references, commands and sentence
  fragments such as `(REQ-004).` as terms.

Both evals also compared harness changes by eye, as two percentages. An
average can rise while items the old harness got right are lost. SAGE (arXiv
2609.36043) shows how often that happens when a gate accepts any average
gain.

**Decision — the fixture holds only what the original run could know.**
- `run.py --new` reads the reference from git history: the first version
  whose status is Approved. `--reference-version latest` keeps the old
  behavior.
- The intake has an as-of date: the day the spec was first committed, or
  `--as-of`. The `jira-ticket` skill is told to stop at that date. `--new`
  then lists every intake line that names a later date, because a prompt is
  not a guarantee.
- The term extractor skips fence lines before pairing backticks. It drops
  spans that read as prose: a leading closing bracket, trailing sentence
  punctuation, markdown emphasis, or three lowercase words in a row.

**Decision — harness changes are compared item by item.**
- `run.py --output` writes `results.json`. `--baseline` compares a run with
  it and lists every item gained and lost. The verdict is WORSE when a `must`
  item is lost, BETTER when more items are gained than lost, SAME when
  nothing changed, and NOT BETTER otherwise. Only BETTER and SAME exit 0.
- `recall.py --baseline` does the same per changed file. It exits 1 when a
  plan loses more files than it gains.

**Rejected.**
- *SAGE's statistical test.* Two fixtures and one run per side are too few
  items and too few runs for a significance test to mean anything. The list
  of lost items is the useful part, and the README tells the reader to run
  each side twice before trusting a close verdict.
- *Filtering the intake by date in code.* The intake is prose written by the
  skill; a date in it does not always mark a whole comment. Flagging the
  lines and letting a person delete them is more reliable.
