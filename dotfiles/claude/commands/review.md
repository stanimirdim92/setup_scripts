---
description: Review a verified change across correctness, readability, architecture, security, performance, and triggered specialist risks
argument-hint: "[commit range, PR, diff, task, or feature]"
---

`/review` is the independent **REVIEW** gate after `/test`.

Review only work that has passed the VERIFY phase, unless the user explicitly
asks for an earlier review.

## 1. Scope the reviewed change

Resolve:

- the integrated diff to review
- a one-line goal
- the relevant acceptance criteria
- verification result/evidence from `/test`

Do not load the full spec or plan unless a specific ambiguity requires it.

## 2. Dispatch reviewers

Read `references/reviewer-triggers.md`.

Dispatch:

- `code-reviewer` always;
- each specialist whose trigger matches.

Give every reviewer:

- the integrated diff;
- the one-line goal;
- relevant acceptance criteria.

Do not give reviewers:

- the full spec unless specifically necessary;
- the full implementation plan;
- another reviewer's output.

Each reviewer should form an independent judgment.

### Reviewer concurrency

Never run more than **2 reviewers concurrently**.

If 3 or more reviewers are required:

1. dispatch up to 2;
2. wait for both;
3. dispatch the next batch.

## 3. Report findings without reranking

Report each reviewer's findings under its own heading.

Do not blend reviewers into one newly ranked list.

Preserve each specialist's own severity vocabulary. When deciding the final
verdict, interpret findings by whether they block shipping rather than forcing
all reviewers onto one severity scale.

## 4. Verdict

State one explicit verdict:

**GO** or **NO-GO**

Default policy:

- any Critical/blocking finding → **NO-GO**;
- an Important/High finding that must be fixed before release → **NO-GO**;
- non-blocking suggestions/medium-low advisory findings may remain with an
  explicit note;
- clean review across all reviewers that ran → **GO**.

A **GO** requires:

- `/test` reported **VERIFY PASS**;
- review ran against the integrated result;
- no unresolved blocking finding remains.

### NO-GO

List exactly what must change.

Implementation fixes go back through `/build`.

After the fix:

1. rerun the affected `/test` verification;
2. rerun the review required to support a new verdict.

### GO

Report:

- reviewers that ran
- blocking findings: none
- important non-blocking follow-ups, if any
- verification status: PASS
- verdict: GO

`GO` means the change cleared the engineering gates.

Actual merge/deploy/release remains the SHIP action and follows the repository's
normal workflow.
