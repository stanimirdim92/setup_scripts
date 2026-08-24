---
description: Conduct a five-axis code review — correctness, readability, architecture, security, performance
argument-hint: "[commit range, PR, diff, task, or feature]"
---

`/review` is the independent **REVIEW** gate after `/test`.

Invoke `skills/code-review-and-quality`. It owns the review methodology at
command level: the five-axis rubric (correctness, readability, architecture,
security, performance), the Critical/Important/Suggestion categorization, the
"verify the verification" step, and the output template. `code-reviewer`
applies that same rubric to the diff and reports; `/review` does not re-derive
a second rubric of its own.

`/review` reports findings. It does not issue the ship verdict — that belongs
to `/ship`.

## 1. Scope the diff

Work out the diff to review (staged changes, recent commits, or whatever
the user pointed at) plus a one-line goal and the acceptance criteria
that apply, if there's a spec or task to draw them from. If neither
exists and the diff's purpose genuinely isn't inferable, say so —
`code-reviewer`'s own rule 2 already expects this input and will do the
same rather than guess.

## 2. Dispatch code-reviewer

Send `code-reviewer` agent the diff plus the goal/acceptance criteria — not
the full spec or plan.

`code-reviewer` has no `Skill` tool (see `tools:` in its definition), so it
cannot invoke `code-review-and-quality` itself. It already carries the same
five-axis rubric inline; that is deliberate. Do not instruct it to invoke the
skill, and do not paste the skill into its packet.

## 3. Specialists, by trigger

Check the diff against `../references/reviewer-triggers.md`
(the same file `/build` uses) and dispatch any specialist whose
condition matches — `security-auditor`,
`distributed-systems-reviewer`. Give each the
same goal/acceptance-criteria/diff, not each other's output; each axis
reviews blind to the others.

## 4. Report

Report each reviewer's findings under its own heading, categorized
Critical/Important/Suggestion, using the skill's Review Checklist shape for
`code-reviewer`'s section. Don't blend axes or reviewers into one
ranked list — a quiet-but-real finding from one axis shouldn't get
buried under a louder one from another.

Stop there. No GO/NO-GO here.

The next workflow stage is `/ship`.
