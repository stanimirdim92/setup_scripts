# Notes — "The life of a change" (claude.dev, Solving code review at Anthropic, 2026-10-15)

Path: before the PR → on every PR (CI, AI review, security review, risk-based
approval) → merging (merge queue) → after the merge (flag, gradual release,
watch and roll back). FIG B: "Each layer catches some problems and misses
others. Few get through all of them, and rollback handles the rest."

How to use: under each gap at the end, write your note (keep / change /
drop, and why). Each noted gap becomes one change with its own ADR.

Legend: ✅ the harness has it · ◐ partly · ❌ missing · — out of scope (project or team level)
MY_NOTE - Is a note left from the engineer for the sentence above MY_NOTE!

---

## 1. The work is verified before anyone else looks

What they do:
- Give Claude something it can run (tests, build, a screenshot against the
  design) and make it show the output instead of saying it's done.
- A subagent reviews the diff in a fresh context.
- Before a PR: skills that hunt bugs, simplify the diff, check behavior end to
  end. UI checked against design guidelines.
- Boris Cherny: verification is "probably the most important thing"; makes
  results "two to three times better".
- A finding the reviewer keeps repeating is fixed at the source: the skill, a
  lint rule, `CLAUDE.md` or `REVIEW.md`.
- `CLAUDE.md` is short and points to other docs. The reviewer flags code that
  breaks a convention in it, AND changes that make a line in it out of date.
- `REVIEW.md` by code owners; "we check separately whether the reviewer
  actually follows it"; summary starts with a count and says plainly when
  there's nothing to fix.

Harness:
- ✅ Executor runs the project's tests/lint per task; the handoff hook refuses
  a report without verification outcomes (show, don't claim).
  MY_NOTE: install browser mcp alongside Figma if missing and use it for all FE review tasks. 
   Assuming something is correct by code is wrong. Always verify like a real engineer would do.
- ✅ `blind-reviewer` is the fresh-context reviewer (no spec, no goal).
- ✅ `/test` covers behavior end to end in a browser; Figma frames for UI.
- ◐ Fix at the source: observation log → ADR is manual. `review-noise.py`
  (ADR 0093) now shows which reviewer repeats noise; nothing turns a repeated
  finding into a rule automatically.
  MY_NOTE: apply practices from the article.
- ❌ No reviewer checks that a change makes a `CLAUDE.md` / `AGENTS.md` /
  `.ai/rules` line out of date.
  MY_NOTE: do we need that? Usually engineer will do it or ask you to do it. Propose fixes.
- ❌ No check that reviewers follow `REVIEW.md` (could be a review-eval case:
  a REVIEW.md rule plus a diff that breaks it).
  MY_NOTE: FIX IT!
- ❌ The "summary starts with a count; say plainly when nothing to fix" rule
  was dropped from the template in ADR 0094. It belongs in `/review`'s report.
  MY_NOTE: FIX IT!

## 2. AI review on every pull request

What they do:
- Reads the diff against the whole repo and the PR's stated intent: does it
  solve its problem, fit the system, break something else?
- On a bug fix, looks for the root cause.
- Quick / Standard / Deep per repo. Deep where a missed bug costs more than
  the review time. 16% → 54% of PRs got substantive comments.
- Several agents find; a separate group votes on each finding; posted only if
  enough agree. Style/diagnostics/cleanup findings dropped (A/B tested).
- Labels Important / Nit / Pre-existing.
- Every finding answered: fixed, or thread resolved with a reason. Often an
  agent fixes overnight.

Harness:
- ✅ `/review` on every candidate; `code-reviewer` with intent, `blind-reviewer`
  without; specialists by trigger.
- ✅ BLOCKER check (ADR 0092, one verifier, not a vote); Pre-existing (0090);
  every finding resolved at `/ship`.
- ❌ No explicit "on a bug fix, check the root cause, not the symptom" rule for
  reviewers. The bugfix spec template has a root-cause section; review does
  not use it.
 MY_NOTE: ADD THIS!
- ◐ Depth: no Quick/Standard/Deep knob. Reviewer triggers choose specialists;
  effort is fixed per persona.
  MY_NOTE: I need suggestions and examples to understand this.
- ◐ Style filtering: ADVISORY findings are kept; only `REVIEW.md`'s nit cap
  limits them.
  MY_NOTE: I need suggestions and examples to understand this.
- — Overnight agent fixes: part of the batched-pipeline proposal, not built.
  MY_NOTE: I need suggestions and examples to understand this.

## 3. Security review that can block

What they do:
- A separate automated security review on every PR. Open findings from it or
  from the bug review block the merge.
- A later commit that fixes the issue clears the finding on its own.
- Public equivalents: the security-review GitHub Action, `/security-review`.

Harness:
- ◐ `security-auditor` runs only when `reviewer-triggers.md` matches. They run
  a security pass on every PR.
  MY_NOTE: We will do the same. run on every pass.
- ✅ Open BLOCKER/REQUIRED findings block `/ship`.
- ✅ Later rounds re-check earlier findings against the fix (ADR 0089).
- Note: a cheap always-on pass (e.g. the built-in `/security-review` on every
  candidate) with `security-auditor` kept for triggered depth.

## 4. Automated checks that block

What they do:
- Lint, types, tests on every platform, build. Dozens of checks per CLI PR.
- PR template asks how it was tested and how to undo it. Claude can fill it
  in; the person who asked for the change signs off.

Harness:
- ✅ The project's commands run per task and per workstream (`/build`).
- ✅ `/ship` requires requirement evidence and a concrete rollback plan (the
  "how tested / how to undo").
- ✅ Only a person approves; `/ship` GO is a recommendation.
- — Leadbuster's own CI is the project's, not the harness's.
  MY_NOTE:  We dont have a CI for Leadbuster. for now.

## 5. Human approval, scaled by risk

What they do:
- Low (docs, copy, flag-gated additive): no person once automated + security
  are green. Medium (ordinary product, caching, auto-updater, system prompts):
  one. High (highest-risk + some paths): two.
- The change sets the tier, not the author. A second classifier can demand a
  person anyway. Some paths always need a person: owner-listed sensitive
  paths and every CI workflow file.
- Only trusted authors get lighter paths. An agent's approval never counts as
  a person's.
- Whoever prompted the agent is a required reviewer.
- An approval covers one commit; new commits need it again.

Harness:
- ✅ Approval binds to the candidate: `/ship` requires the reviewed candidate
  unchanged; any change returns to `/build` → `/review`.
- ✅ Agents never approve; the user is the one who prompted and decides.
- ◐ Risk shapes the pipeline (verification and reviewer triggers) but there
  is no written risk tier.
  MY_NOTE: I need suggestions and examples before implementing this.
- ❌ No "always needs a person" path list. Candidates: CI workflow files,
  migrations, auth/permission code, `.env*`, the harness's own config. These
  should force `/test` and every specialist, and tell the user plainly to read
  the diff.
  MY_NOTE: For all of the above. I need suggestions and examples. I think we can automate jira/spec/plan/build. 
 The only problem I know is all the open questions and decisions that must be taken and in 99% of the cases it needs a person.
 I am looking forward to automate this, but do not know how.

## 6. Merge queue, flags and a gradual release

What they do:
- The merge queue re-runs every check on main with the change applied, so two
  PRs that pass alone can't combine into a broken main.
- New behavior behind a flag, employees first. `latest` before `stable`.

Harness:
- ◐ `warn-stale-base.sh` warns when a worktree's base is old; nothing re-runs
  the checks on the current main with the change applied before GO.
- ❌ `/ship` does not ask whether risky new behavior ships behind a flag.
- — Release channels are the project's deployment, not the harness's.
  MY_NOTE: For all 3, I need suggestions and examples.

## 7. Fast detection, fast rollback

What they do:
- Flags turn off without a deploy. Weekly on-call. Incident reviews ask which
  layer should have caught the issue.
- No circuit breakers yet that tighten approval when revert/incident numbers
  move; they want them before more zero-human merges.
- "We'd rather get faster at noticing and fixing problems" than slow down.

Harness:
- ✅ `/ship` requires a rollback plan with trigger, procedure, recovery target.
- ◐ Observation-log failure rows end "Fixed — <check>", which is the "which
  layer should have caught it" question, but they cover harness failures, not
  shipped bugs. A bug found after merge has no row type.
- — Circuit breakers: they don't have them either. With review-noise and the
  review eval, a later step could tighten `/review` depth when shipped-bug
  rows rise.
  MY_NOTE: For all of the above. I need suggestions and examples to understand this.

---

## Gaps worth closing, in order

Add your note under each bullet as `> Note: ...`.

1. **Re-run on current main before GO** (layer 6): `/ship` merges the latest
   base into a scratch copy of the candidate and re-runs the task commands.

   > Note: yes! worktree or a scratch copy or a scratchpad is fine.

2. **Paths that always need a person** (layer 5): a list in `REVIEW.md`
   ("Always a person"), honoured by `/review` (force `/test` + all specialists)
   and `/ship` (say it plainly).

   > Note: Not sure. I do not understand.

3. **Root cause on bug fixes** (layer 2): `code-reviewer` checks a bugfix
   against the spec's root cause, not just the symptom.

   > Note: yes. I need a real validation. files, paths, lines, logical trace of the bug.

4. **Stale instruction lines** (layer 1): reviewers flag a change that makes a
   `CLAUDE.md` / `AGENTS.md` / `.ai/rules` line untrue.

   > Note: what should we do?

5. **Report starts with a count** (layer 1): `/review` summary line
   "N BLOCKER · N REQUIRED · N ADVISORY", or "Nothing to fix."

   > Note: yes.

6. **Security pass on every candidate** (layer 3): a light always-on check,
   `security-auditor` still by trigger.
7. **Shipped-bug rows** (layer 7): an observation-log row type for a bug found
   after merge, naming the layer that should have caught it — and each one
   becomes a review-eval case.
8. **Flag question at `/ship`** (layer 6) for risky new behavior.

---

## "How you can adopt this process" — their checklist against the harness

Their intro: "Most of the pieces to do this with your team exist today."

### Before the pull request

| Their item | Harness | Gap |
|---|---|---|
| Checks the agent can run, listed in a short `CLAUDE.md` | ✅ Task packets carry the project's test/lint commands; `CLAUDE.md` holds them | — |
| Hooks that run formatters and linters | ❌ No PostToolUse hook. Formatting is an instruction (`pint --dirty`), not enforced | 9 |
| `/code-review`, `/security-review` locally, or a fresh-context subagent review | ✅ `/review` with `blind-reviewer`; ◐ `/security-review` not run on every candidate | 6 |
| A `REVIEW.md`, and move repeated review comments into it | ✅ `REVIEW.md` (ADRs 0091, 0094); ◐ nothing proposes the move | 10 |

### On every pull request

| Their item | Harness | Gap |
|---|---|---|
| Require CI; PR template with "Testing", "Risk", "How to revert" | ✅ Requirement evidence and rollback plan at `/ship`; ◐ no "Risk" line | 2 |
| An AI reviewer on one repo, tune `REVIEW.md` for a few weeks, then widen | ✅ `/review`; the managed Code Review is optional | — |
| Automated security review; every thread resolved before merge | ◐ Security by trigger; ✅ every finding resolved at `/ship` | 6 |
| Effort matched to risk: Quick / Standard / Deep | ◐ Reviewer triggers only; no depth by risk | 2 |
| Cap review rounds; after the first few, review only the new diff | ✅ ADR 0089 | — |

### Approval

| Their item | Harness | Gap |
|---|---|---|
| Written risk tiers, set from the change; start strict, loosen with evidence | ❌ No written tiers | 2 |
| Lighter paths only for trusted authors | — One developer | — |
| CODEOWNERS and branch protection: auth, billing, CI and release workflows, installers always need a person | ❌ No such path list in the harness; CODEOWNERS is the project's | 2 |
| A bot's approval never replaces a human's; dismiss approvals on new commits | ✅ Agents never approve; `/ship` binds to the reviewed candidate | — |

### Merge and after

| Their item | Harness | Gap |
|---|---|---|
| Merge queue, flags, internal use first, staged releases, one-step rollback | ◐ Rollback plan ✅; no re-run on current main; no flag question | 1, 8 |
| Incidents and reverts as an eval set; rescore when the reviewer's prompts, tools or model change | ◐ `review-eval` exists (ADR 0093); nothing requires a rescore when a reviewer changes | 7, 11 |
| Measure human time, with revert and incident rates as the guardrail | ❌ Run metrics measure tokens and cost, not your time or shipped bugs | 12 |

### New gaps from the checklist

9. **Formatter and linter hooks** — a PostToolUse hook that runs the project's
   formatter on edited files when the project declares one (e.g. `pint` for
   PHP, `prettier`/`eslint --fix` for TS), so formatting is enforced, not asked.

   > Note: Yes, but only if project has it. I have python and rust projects. Therefore it must be project agnostic.

10. **Repeated findings into `REVIEW.md`** — when `review-noise.py` or `/ship`
    sees the same class of finding across tickets, propose a `REVIEW.md` line
    for the owner to accept.

   > Note: what?

11. **Rescore on reviewer change** — a change to a reviewer persona, to
    `/review`, or to a reviewer's model must come with a review-eval run
    against the baseline; the commit or ADR names the result.

   > Note: Ok. what it will cost

12. **Human time and shipped bugs** — record per ticket how many times you
    were asked to decide (questions, approvals, review rounds) and any bug
    found after merge, so automation can be loosened only while the
    shipped-bug rate holds.

   > Note: yes.

Gap 2 grows: written risk tiers (low / medium / high, set by the change),
review depth matched to the tier, a "Risk" line in the `/ship` report, and
the paths that always need a person (auth, billing, CI and release workflows,
installers, migrations).
