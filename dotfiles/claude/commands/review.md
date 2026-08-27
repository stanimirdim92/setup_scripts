---
description: Conduct independent review and decide whether a separate VERIFY gate is required
argument-hint: "[commit range, PR, diff, task, or feature]"
---

`/review` is the independent **REVIEW** gate after `/build`.

It owns two orchestration decisions:

1. whether `/test` is required for this candidate;
2. which review personas run.

It reports findings. `/ship` owns the release verdict.

## 1. Establish the candidate

Require `/build`'s **BUILD COMPLETE** handoff from the current conversation.
Inspect the current branch, commits, diff, and tree state.

If the candidate changed after that handoff, the intended scope is ambiguous, or
the tree contains undeclared changes, return **REVIEW BLOCKED**.

Standalone review may still be performed when directly requested, but it is not
the pipeline REVIEW gate.

## 2. Independent-verification gate

Evaluate the candidate against
`../references/verification-triggers.md`.

- If no trigger matches, record **Independent verification: NOT REQUIRED** and
  use `/build`'s verification evidence.
- If a trigger matches, require a **VERIFY PASS** for this exact candidate.
- If required verification is missing or stale, return **REVIEW BLOCKED** with
  `/test` as the next step.

Do not re-run `/test` inline and do not duplicate the trigger matrix here.

## 3. Dispatch reviewers

Always dispatch `code-reviewer` with:

- the integrated diff;
- a one-line goal;
- the relevant acceptance criteria;
- the build/verify evidence needed to understand what was checked.

Do not send the full spec or plan.

Use `../references/reviewer-triggers.md` to decide whether
`security-auditor` and/or `distributed-systems-reviewer` are also required.

Run at most **2 reviewers concurrently**. Reviewers form judgments
independently; do not pass one reviewer's findings to another.

Use each persona's configured model by default. Escalate a specialist to a
higher reasoning tier only when the matched risk is both high-impact and
materially ambiguous; ordinary triggered reviews stay on the default model.

## 4. Report

Preserve every reviewer's native severity and add the canonical disposition:

| Source | Native severity | Disposition |
|---|---|---|
| `code-reviewer` | Critical | BLOCKER |
|  | Important | REQUIRED |
|  | Suggestion | ADVISORY |
| `security-auditor` | Critical, High | BLOCKER |
|  | Medium | REQUIRED |
|  | Low, Info | ADVISORY |
| `distributed-systems-reviewer` | Critical | BLOCKER |
|  | Important | REQUIRED |
|  | Suggestion | ADVISORY |

Every finding keeps a stable id, source, native severity, disposition,
file/location, and resolution state.

Report:

- candidate branch/diff scope;
- **Independent verification: NOT REQUIRED | PASS**;
- required-reviewer list and trigger decisions;
- each reviewer result under its own heading;
- all findings with canonical disposition.

Then stop. The next stage is `/ship`.

Any candidate change after REVIEW invalidates the review. A production fix
returns to `/build`; `/review` then re-evaluates whether `/test` is required for
the new candidate before reviewing it again.
