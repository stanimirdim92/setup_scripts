# Opus 5.5: medium session effort, and bounded continuations for early stops

Anthropic's "Prompting Claude Opus 5.5" guide (read 2026-10-01) drives four
changes. Each records what the guide says and what this harness did with it.

**Decision — session effort `medium`; reviewers `high`.** Opus 5.5 defaults to
`medium`, and at `medium` it matches or beats Opus 5 at `high` on coding; at
the same level name it thinks more per turn than Opus 5, so the carried-over
`high` was buying longer, costlier turns. `settings.json` `effortLevel` is now
`medium`. The four reviewers declare `effort: high` in their frontmatter — the
review is where depth pays and it runs once per candidate. Sonnet personas
keep their `modelSettings` override (0063) and the Fable advisor its own.
`dotfiles/tools/validate-frontmatter.py` pins both values. This reverses 0056's "no
persona declares `effort:`", deliberately: two levels, set where they apply.
Revisit from `dotfiles/docs/observation-log.md` cost and quality per stage.

**Decision — the handoff hook allows two continuations, and catches announced
next steps.** The guide: an unattended agent often ends a turn with a progress
report and no tool call; treat that as a report, nudge with the open items, and
stop after two or three automatic continuations. `require-handoff-report.sh`
(and the Codex adapter) now blocks at most twice per agent run, tracked by a
counter keyed by `agent_id`, and also blocks a first-person announced next step
("Next, I'll …") that names no blocker. A third stop always goes through.

**Decision — `batch-spec.sh` resumes a job that ends without its spec.** The
headless `/spec` jobs are the harness's one fully unattended run. A job that
exits 0 without a spec for its tickets is resumed in the same session with a
nudge, at most twice, then reported NO SPEC as before. `--budget` is now per
CLI call.

**Decision — the progress-update rule in `AGENTS.md` is trimmed.** Opus 5.5
writes progress updates between tool calls by default, and Claude Code sends
its own "hasn't heard from you" reminder — the mechanism the guide measured.
The "roughly every 60 seconds" cadence and its elaboration are removed; phase
announcements, prompt failure reports and no invented progress stay.

**Rejected — the guide's long "don't end your turn to report" system-prompt
paragraph.** It is written for fully unattended agents with no human; this
harness is human-in-the-loop by design, and the guide says to leave it out
there. The handoff hook and the batch continuation cover the unattended paths.

**Rejected — time budgets for parallel `/build`.** Claude Code offers no clean
way to append elapsed time to each turn; revisit once parallel builds have run
metrics.
