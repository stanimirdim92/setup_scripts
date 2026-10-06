# Plan-localization recall

Scores a plan against the change that actually shipped: of the files the merged
change touched, how many did the plan's tasks name under `Files/areas likely
touched`?

This is the measure LoLBench (arXiv 2609.37143) found decisive. On large
systems, agents' edits land in the right files 65–80% of the time, but they
reach only 37–65% of the files the real change needed, and handing them a file
list raised solve rates by 16–22 points. In this harness the plan is where that
list is made (`references/plan-quality-gates.md` §4, change surface), so plan
recall is the number that says whether the list is complete.

## Running it

From the project checkout, once the ticket has shipped. Score each ticket
against its own plan:

```bash
python3 ~/path/to/setup_scripts/dotfiles/tools/evals/plan-recall/recall.py --repo ./ \
    --ticket LD-380 --subject-only --show-commits \
    --plan docs/tasks/LD-380-plan.md --plan docs/tasks/LD-380-todo.md \
    --range <commit before the ticket>..<last commit of the ticket>
```

Read the `scored commits` list first. It must hold the ticket's own pipeline
commits (`(LD-380 T001)` and the like) and nothing else. If a commit of the
ticket names it only in its body, drop `--subject-only`; if another ticket's
commits got in, add `--not-ticket <id>`. Then record the figures in the Plan
recall table of `dotfiles/docs/observation-log.md`.

- `--ticket LD-380` scores only the commits in the range whose message names
  the ticket (case-insensitive substring, merges skipped). Repeat it to score
  several tickets together against all their plans; a commit naming any of
  them counts. Use it whenever the
  range also carries other tickets' work; without it, their files read as
  misses. A file added and then removed inside the ticket is dropped. Each
  missed file shows the first ticket commit that touched it, so a planning
  miss can be told apart from a review fix or a scope expansion.
- `--subject-only` matches tickets in the commit subject only. Pipeline commits
  name their ticket there (`(LD-442 T002)`); a squash or summary commit that
  only mentions a ticket in its body ("builds on LD-441") is then left out.
- `--trailer-only` matches a ticket only when it equals a `Refs:` trailer value
  (ADR 0073), never the subject or body text. Use it for history written after
  the trailer convention; `--subject-only` is for older history.
- `--baseline before.json` compares this plan with an earlier one (a `--json`
  output) on the same range, file by file: which changed files each plan
  found that the other missed. It exits 1 when this plan loses more files than
  it gains. Use it to compare a new plan with the original.
- `--show-commits` lists the commits that were scored. Check it whenever a
  number looks wrong.
- `--not-ticket LD-442` (with `--ticket`, repeatable) drops commits whose
  message also names another ticket. Use it when two tickets were built on one
  branch and some commits name both.
- Pipeline artifacts and agent configuration are excluded by default
  (`docs/specs/*`, `docs/tasks/*`, `CLAUDE.md`, `AGENTS.md`, `.claude/*`,
  `.codex/*`, `.ai/*`, `.worktreeinclude`): no task plans them.
  `--no-default-excludes` scores them too.
- `--exclude 'docs/*'` drops changed files the plan is not expected to list
  (repeatable).
- `--min-recall 0.8` exits 1 below that recall over pre-existing files.
- `--json` for the raw figures.

It reports recall over every changed file and over pre-existing files (the
paper's measure: a new file has no location to find), precision over the
planned edits, the changed files nobody planned, and the planned files the
change never touched. An entry marked `unchanged — reason` counts as found but
is not expected in the diff.

Costs nothing and drives no model. Run it after a ticket ships, and record the
existing-file recall in `dotfiles/docs/observation-log.md`. A missed file is worth a
failure row when it was a consumer or registration of a surface the task
changed — that is the case the change-surface gate exists to catch.

## What a number means

High recall means the plan named the places. It does not mean the changes made
there were correct; `/review` and the tests judge that. Low precision is
usually fine — a planned test directory or an `unchanged` check costs little —
but a plan that lists half the repository has stopped saying anything.

`test_recall.py` covers the parsing and scoring and runs in CI.
