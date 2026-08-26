---
description: Conduct a five-axis code review — correctness, readability, architecture, security, performance
argument-hint: "[commit range, PR, diff, task, or feature]"
---

`/review` is the independent **REVIEW** gate after `/test`.

Invoke `../skills/code-review-and-quality`. It owns the review methodology at
command level: the five-axis rubric (correctness, readability, architecture,
security, performance), its native finding categorization, the "verify the
verification" step, and the output template. `code-reviewer` applies the same
five-axis rubric with its own native severity vocabulary; `/review` preserves
each source vocabulary and adds the canonical release disposition instead of
re-deriving a second rubric.

`/review` reports findings. It does not issue the ship verdict — that belongs
to `/ship`.

## 1. Scope the diff

Require `/test`'s **VERIFY PASS** handoff from the current conversation. Inspect
the current branch, local commits, and diff. If candidate code changed after
that PASS, the scope is ambiguous, or the tree contains undeclared changes,
return **REVIEW BLOCKED** and send the candidate back through `/test`.
Standalone review may still be performed when directly requested, but it is not
the pipeline REVIEW gate. No separate evidence record or SHA checkpoint is
created.

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

Check the diff against `../references/reviewer-triggers.md` and dispatch any
specialist whose condition matches — `security-auditor`,
`distributed-systems-reviewer`. Give each the
same goal/acceptance-criteria/diff, not each other's output; each axis
reviews blind to the others.

Run no more than **2 reviewers concurrently**, with no exception for high-risk
diffs. This is read-only fan-out; `test-engineer` is not part of REVIEW.

## 4. Report

Report each reviewer under its own heading and preserve its native severity.
Then add one canonical release disposition:

| Source | Native severity | Disposition |
|---|---|---|
| `code-review-and-quality` | Critical | BLOCKER |
|  | Required | REQUIRED |
|  | Optional, Consider, Nit, FYI | ADVISORY |
| `code-reviewer` | Critical | BLOCKER |
|  | Important | REQUIRED |
|  | Suggestion | ADVISORY |
| `security-auditor` | Critical, High | BLOCKER |
|  | Medium | REQUIRED |
|  | Low, Info | ADVISORY |
| `distributed-systems-reviewer` | Critical | BLOCKER |
|  | Important | REQUIRED |
|  | Suggestion | ADVISORY |

Every finding carries a stable id, source reviewer, native severity, canonical
disposition, file/location, and resolution state. Report the required-reviewer
list, explicit matched/not-matched decisions for both specialists, all reviewer
results, and the current branch/diff scope reviewed. Don't blend axes or
reviewers into one ranked list.

Stop there. No GO/NO-GO here.

The next workflow stage is `/ship`.

Any candidate change after REVIEW invalidates that result. A fix must repeat
`/build -> /test -> /review -> /ship`; re-testing without re-review is not enough.
