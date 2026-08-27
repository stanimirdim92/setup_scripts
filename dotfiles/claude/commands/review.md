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

Require `/build`'s **BUILD COMPLETE** handoff from the current conversation and
record that handoff's candidate identity. Inspect the current branch, commits,
diff, and tree state.

The current candidate may differ from BUILD only by passing test-only commits
that `/test` declared in a **VERIFY PASS** for this exact current candidate.
Confirm those commits contain only tests, fixtures, or test configuration.

Any production change after BUILD, undeclared post-BUILD commit/change, stale
VERIFY result, ambiguous scope, or undeclared working-tree change is **REVIEW
BLOCKED**.

Standalone review may still be performed when directly requested, but it is not
the pipeline REVIEW gate.

## 2. Independent-verification gate

Evaluate the candidate against
`../references/verification-triggers.md`.

- If a **VERIFY PASS** already exists for this exact candidate, record
  **Independent verification: PASS**. This also covers explicitly requested
  `/test` runs whose test-only commits advanced the BUILD candidate.
- Otherwise, if no trigger matches, record **Independent verification: NOT
  REQUIRED** and use `/build`'s verification evidence.
- Otherwise, require a **VERIFY PASS** for this exact candidate.
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
- BUILD candidate and any accepted post-BUILD test-only commits;
- **Independent verification: NOT REQUIRED | PASS**;
- required-reviewer list and trigger decisions;
- each reviewer result under its own heading;
- all findings with canonical disposition.

Then stop. The next stage is `/ship`.

Any candidate change after REVIEW invalidates the review. A production fix
returns to `/build`; `/review` then re-evaluates whether `/test` is required for
the new candidate before reviewing it again.
