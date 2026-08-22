---
description: Conduct a five-axis code review — correctness, readability, architecture, security, performance
---

Thin orchestrator, same pattern as `/build`'s review step — one rubric,
not two. Dispatch the `code-reviewer` agent instead of re-running its
five-axis framework inline via the `code-review-and-quality` skill.

## 1. Scope the diff

Work out the diff to review (staged changes, recent commits, or whatever
the user pointed at) plus a one-line goal and the acceptance criteria
that apply, if there's a spec or task to draw them from. If neither
exists and the diff's purpose genuinely isn't inferable, say so —
`code-reviewer`'s own rule 2 already expects this input and will do the
same rather than guess.

## 2. Dispatch code-reviewer

Send `code-reviewer` the diff plus the goal/acceptance criteria — not
the full spec or plan. Let it run its own five-axis rubric (correctness,
readability, architecture, security, performance); don't re-derive that
framework here in the command.

## 3. Specialists, by trigger

Check the diff against `references/reviewer-triggers.md`
(the same file `/build` uses) and dispatch any specialist whose
condition matches — `security-auditor`,
`distributed-systems-reviewer`. Give each the
same goal/acceptance-criteria/diff, not each other's output; each axis
reviews blind to the others.

## 4. Report

Report each reviewer's findings under its own heading, categorized
Critical/Important/Suggestion. Don't blend axes or reviewers into one
ranked list — a quiet-but-real finding from one axis shouldn't get
buried under a louder one from another.
