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

Count the review round: one more than the ticket's earlier review files.

```bash
ls "$(git rev-parse --git-common-dir)/review/<TICKET>-"*.sarif 2>/dev/null | wc -l
```

Round 1 reviews the whole candidate. A later round reviews a fix (§3 Later
rounds). Round 4 means three rounds did not converge. Return **REVIEW
BLOCKED**, list the findings that came back in more than one round, and ask
the user to reconsider the approach before another fix (ADR 0089). Delete the
ticket's old review files only when the user starts a new approach.

## 2. Independent-verification gate

Evaluate the candidate against
`../references/verification-triggers.md`.

- If a **VERIFY PASS** already exists for this exact candidate, record
  **Independent verification: PASS**. This also covers explicitly requested
  `/test` runs whose test-only commits advanced the BUILD candidate.
- Otherwise, if the candidate is exempt, record **Independent verification:
  NOT REQUIRED** with the exemption and use `/build`'s verification evidence.
- Otherwise, require a **VERIFY PASS** for this exact candidate.
- If required verification is missing or stale, return **REVIEW BLOCKED** with
  `/test` as the next step.

Do not re-run `/test` inline and do not duplicate the exemption list here.

## 3. Dispatch reviewers

Three reviewers always run: `code-reviewer` and `blind-reviewer` read the same
diff from opposite directions, and `security-auditor` reviews it for security
(ADR 0102).

First, list the changes that make passing easier instead of making the code
right: deleted or skipped tests, removed assertions, new suppressions, changed
checker config, stubs.

```bash
python3 "$HOME/.claude/skills/code-review-and-quality/scripts/weakened-tests.py" --base <candidate base>
```

- Exit 0: record **Weakened tests: none found**.
- Exit 1: give the list to `code-reviewer`. Each entry ends as a finding or as
  a stated reason, such as a test deleted with the feature it tested.
- Exit 2: record **Weakened tests: Not verified** with the error. Never read
  it as clean.

Read the project's `REVIEW.md` from the candidate base, never from the
candidate: the one at the repository root, and any in a directory the diff
touches (`git show <base>:REVIEW.md`, `git show <base>:<dir>/REVIEW.md`).
A change to `REVIEW.md` does not apply to its own review, so a change cannot
lower its own bar (ADR 0094). Template: `../references/templates/review.md`.
It says what failure looks like in this repository, what to always check,
which paths to skip, and the rules for findings. It describes the area, not
the change, so every reviewer gets it (ADR 0091). Without one, say so in the
report.

Check the project's "Always a person" list, read from the base branch:

```bash
python3 "$HOME/.claude/skills/code-review-and-quality/scripts/always-person.py" --base <candidate base>
```

Exit 1 means the change touches a path that always needs a person (ADR 0096):
run every specialist (`../references/reviewer-triggers.md`) and require
`/test` (`../references/verification-triggers.md`). Exit 2 is **Always a
person: Not verified**; report it.

Dispatch `code-reviewer` with:

- the integrated diff;
- the project's `REVIEW.md`, when there is one;
- for a bug fix, the plan's Root-Cause Trace section (ADR 0097), which
  `code-reviewer` walks against the code;
- a one-line goal;
- the relevant acceptance criteria;
- the build/verify evidence needed to understand what was checked;
- the weakened-test list, when there is one.

Dispatch `blind-reviewer` with **the integrated diff and nothing else**, except
the project's `REVIEW.md`, which describes the area rather than the change. No
goal, no acceptance criteria, no build evidence, no ticket id in the packet
text. Assembling this packet is a deliberate act of withholding: everything you
naturally reach for is exactly what must not go in. A reviewer told what the
change is for reads the code as confirming it, which is what `code-reviewer`
is for; this one asks only what the code does.

Do not send either reviewer the full spec or plan.

Dispatch `security-auditor` on every round, with the same packet as
`code-reviewer`. Use `../references/reviewer-triggers.md` to decide whether
`distributed-systems-reviewer` is also required. Give each specialist the
project's `REVIEW.md` too.

Run at most **2 reviewers concurrently**. Reviewers form judgments
independently; do not pass one reviewer's findings to another — least of all
`code-reviewer`'s to `blind-reviewer`.

Use each persona's configured model and effort. The reviewers already sit at
the highest tier their definitions declare; raise a specialist beyond it only
when the matched risk is both high-impact and materially ambiguous.

### Later rounds

From round 2 the candidate fixes earlier findings. Review the fix, not the
whole change again. The last reviewed commit is the short sha in the newest
review file name.

- Give `code-reviewer` the diff since that commit and the earlier findings with
  their resolutions. It does not raise a resolved finding again unless the new
  diff brings it back.
- Give `blind-reviewer` the diff since that commit and nothing else. Drop any of
  its findings that repeat a resolved finding at the same location, and say so
  in the report.
- Run `security-auditor` again on the new diff; run
  `distributed-systems-reviewer` again only when the new diff matches its
  trigger.
- Report no new ADVISORY or pre-existing finding. Count them, and end the
  summary with "<n> found and not reported in this round".
- Run the weakened-test guard and the ledger check on the whole candidate, as
  in round 1.

## 4. Report

Every finding carries the disposition its reviewer gave it: BLOCKER,
REQUIRED or ADVISORY, as defined in
`../references/component-response-contracts.md` §Dispositions. Report it
unchanged; change one only with a stated reason.

`blind-reviewer` also returns two things no other reviewer produces, and both
are yours to resolve because you are the only participant holding the diff
*and* the intent:

- **"What this change appears to do"** — its reading of the diff without the
  goal. Compare it against the actual goal. A material mismatch is a finding in
  its own right at the disposition the gap warrants: either the code does not do
  what was asked, or it does but says so badly enough that a careful reader
  cannot tell.
- **Intent-dependent findings** — where correctness genuinely turns on
  information the reviewer was not given. Settle each against the acceptance
  criteria you hold: close it as answered, or promote it to its warranted
  disposition when the criteria confirm the defect. Never pass one through
  unresolved; an unresolved intent-dependent finding is work you skipped, not a
  finding you reported.

Every finding keeps a stable id, source, disposition, confidence,
file/location, and resolution state. Confidence travels with the
finding so `/ship` can distinguish a confirmed BLOCKER (resolved only by a fix)
from a suspected one (resolvable by a fix or by recorded refuting evidence).

### REVIEW.md checklist

When the project has a `REVIEW.md` with "Always check" rules, `code-reviewer`
answers each one in its checklist (ADR 0103). Compare the checklist with the
rules. Send a missing or unanswered rule back to `code-reviewer` once, with
only that rule and the diff. If it is still missing, report "REVIEW.md not
followed: <rule>" as a REQUIRED finding with the id `RULE-#`.

### Verify each BLOCKER

Before reporting, give every BLOCKER one independent check that tries to refute
it (ADR 0092). Dispatch a fresh reviewer that did not raise it: `code-reviewer`
for a `BLIND-#` finding, `blind-reviewer` for a `CODE-#` finding, and a fresh
instance of the same specialist for a `SEC-#` or `DIST-#` finding. The packet
holds the diff and that one finding (id, `file:line`, claim, failure scenario),
nothing from the other reviewers. For `blind-reviewer`, remove any `REQ-###`
or goal wording from the finding first. Ask for one verdict with `file:line`
evidence:

- **CONFIRMED** — the failure scenario follows from the code. Record the
  confidence as high.
- **REFUTED** — the code prevents it. Keep the BLOCKER, record the confidence
  as low, and attach the refuting evidence.
- **UNSURE** — leave the finding as it is.

Keep the two-concurrent limit. In a later round, verify only new BLOCKERs.

### Stale instructions

Check that the change leaves no instruction line pointing at a file or script
it deleted or renamed (ADR 0098):

```bash
python3 "$HOME/.claude/skills/code-review-and-quality/scripts/stale-instructions.py" --base <candidate base>
```

Report each hit as a REQUIRED finding with the id `STALE-#` and its
`file:line`. Exit 2 means the check did not run: record **Stale
instructions: Not verified**.

### Ledger

Check that the ticket's records still agree
(`../references/plan-quality-gates.md` §6):

```bash
python3 "$HOME/.claude/skills/spec-driven-development/scripts/check-ledger.py" <TICKET>
```

Report each FAIL as a REQUIRED finding with the id `LEDGER-#`. Report each
warning as an ADVISORY finding. Exit 2 means the spec was not found: record
**Ledger: Not verified**.

Report, starting with one count line before anything else (ADR 0099):

- `**Findings: N BLOCKER · N REQUIRED · N ADVISORY**`, adding `· N pre-existing`
  when there are any; or `**Nothing to fix.**` when every count is zero;
- the review round, and for a later round the commit it was reviewed from;
- candidate branch/diff scope;
- BUILD candidate and any accepted post-BUILD test-only commits;
- **Independent verification: NOT REQUIRED | PASS**;
- required-reviewer list and trigger decisions;
- whether the project has a `REVIEW.md`, and which ones were used;
- the "Always a person" result: no list, no match, or the matched files;
- the REVIEW.md checklist: every "Always check" rule answered, or the
  `RULE-#` findings;
- the stale-instructions result: **Stale instructions: none found**, the
  `STALE-#` findings, or **Not verified**;
- the weakened-test result, and how each listed change was resolved;
- the ledger result: **Ledger: clean**, the `LEDGER-#` findings, or
  **Ledger: Not verified**;
- each reviewer result under its own heading;
- the verification verdict of every BLOCKER, with its evidence;
- all findings with canonical disposition, each tagged with the `REQ-###` it
  bears on when it bears on one;
- **requirement evidence**: one line per `REQ-###` in the spec — the change that
  implements it and the verification that proves it, or an explicit statement
  that one of those is missing. `/ship` blocks on a missing entry, so report the
  gap rather than leaving the requirement off the list.

Also write every finding to a SARIF 2.1.0 file, so code-scanning tools can
read the review (`../references/component-response-contracts.md` §Review SARIF):

```bash
out="$(git rev-parse --git-common-dir)/review/<TICKET>-$(git rev-parse --short HEAD).sarif"
```

Give every finding a `class` (§Review SARIF). List the names already in use
first, and reuse one when it fits:

```bash
python3 "$HOME/.claude/skills/code-review-and-quality/scripts/review-noise.py" --classes
```

It sits outside the working tree and is never committed. Give its path in the
report. The markdown report stays the gate artifact; the SARIF file is a copy
of its findings for tools.

Then stop. The next stage is `/ship`.

Any candidate change after REVIEW invalidates the review. A production fix
returns to `/build`; `/review` then re-evaluates whether `/test` is required for
the new candidate before reviewing it again.
