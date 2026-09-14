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

Resolve the target per `../references/target-selection.md`, and announce it ("Using: <target>") before anything else.

Require `/build`'s **BUILD COMPLETE** message from one of the valid sources in
`../references/target-selection.md` §Gate handoffs and record its candidate
identity. Inspect the current branch, commits, diff, and tree state. Re-read
spec/plan/task artifacts from disk even if they appeared earlier in the
conversation — the user may have edited them since.

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

Two reviewers always run, on the same diff, from opposite directions.

Dispatch `code-reviewer` with:

- the integrated diff;
- a one-line goal;
- the relevant acceptance criteria;
- the build/verify evidence needed to understand what was checked.

Dispatch `blind-reviewer` with **the integrated diff and nothing else**. No
goal, no acceptance criteria, no build evidence, no ticket id in the packet
text. Assembling this packet is a deliberate act of withholding: everything you
naturally reach for is exactly what must not go in. A reviewer told what the
change is for reads the code as confirming it, which is what `code-reviewer`
is for; this one asks only what the code does.

Do not send either reviewer the full spec or plan.

Use `../references/reviewer-triggers.md` to decide whether
`security-auditor` and/or `distributed-systems-reviewer` are also required.

Run at most **2 reviewers concurrently**. Reviewers form judgments
independently; do not pass one reviewer's findings to another — least of all
`code-reviewer`'s to `blind-reviewer`.

Use each persona's configured model and effort. The reviewers already sit at
the highest tier their definitions declare; raise a specialist beyond it only
when the matched risk is both high-impact and materially ambiguous.

## 4. Report

Preserve every reviewer's native severity and add the canonical disposition:

| Source | Native severity | Disposition |
|---|---|---|
| `code-reviewer` | Critical | BLOCKER |
|  | Important | REQUIRED |
|  | Suggestion | ADVISORY |
| `blind-reviewer` | Critical | BLOCKER |
|  | Important | REQUIRED |
|  | Suggestion | ADVISORY |
|  | Intent-dependent | resolve here — see below |
| `security-auditor` | Critical, High | BLOCKER |
|  | Medium | REQUIRED |
|  | Low, Info | ADVISORY |
| `distributed-systems-reviewer` | Critical | BLOCKER |
|  | Important | REQUIRED |
|  | Suggestion | ADVISORY |

`blind-reviewer` also returns two things no other reviewer produces, and both
are yours to resolve because you are the only participant holding the diff
*and* the intent:

- **"What this change appears to do"** — its reading of the diff without the
  goal. Compare it against the actual goal. A material mismatch is a finding in
  its own right at the severity the gap warrants: either the code does not do
  what was asked, or it does but says so badly enough that a careful reader
  cannot tell.
- **Intent-dependent findings** — where correctness genuinely turns on
  information the reviewer was not given. Settle each against the acceptance
  criteria you hold: close it as answered, or promote it to its warranted
  severity when the criteria confirm the defect. Never pass one through
  unresolved; an unresolved intent-dependent finding is work you skipped, not a
  finding you reported.

Every finding keeps a stable id, source, native severity, confidence,
disposition, file/location, and resolution state. Confidence travels with the
finding so `/ship` can distinguish a confirmed BLOCKER (resolved only by a fix)
from a suspected one (resolvable by a fix or by recorded refuting evidence).

Report:

- candidate branch/diff scope;
- BUILD candidate and any accepted post-BUILD test-only commits;
- **Independent verification: NOT REQUIRED | PASS**;
- required-reviewer list and trigger decisions;
- each reviewer result under its own heading;
- all findings with canonical disposition, each tagged with the `REQ-###` it
  bears on when it bears on one;
- **requirement evidence**: one line per `REQ-###` in the spec — the change that
  implements it and the verification that proves it, or an explicit statement
  that one of those is missing. `/ship` blocks on a missing entry, so report the
  gap rather than leaving the requirement off the list.

Then stop. The next stage is `/ship`.

Any candidate change after REVIEW invalidates the review. A production fix
returns to `/build`; `/review` then re-evaluates whether `/test` is required for
the new candidate before reviewing it again.
