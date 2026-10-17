# Notes — "The life of a change" (claude.dev, Solving code review at Anthropic, 2026-10-15)

Path: before the PR → on every PR (CI, AI review, security review, risk-based
approval) → merging (merge queue) → after the merge (flag, gradual release,
watch and roll back). FIG B: "Each layer catches some problems and misses
others. Few get through all of them, and rollback handles the rest."

How to use: under each gap at the end, write your note (keep / change /
drop, and why). Each noted gap becomes one change with its own ADR.

Legend: ✅ the harness has it · ◐ partly · ❌ missing · — out of scope (project or team level)

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
- ✅ `blind-reviewer` is the fresh-context reviewer (no spec, no goal).
- ✅ `/test` covers behavior end to end in a browser; Figma frames for UI.
- ◐ Fix at the source: observation log → ADR is manual. `review-noise.py`
  (ADR 0093) now shows which reviewer repeats noise; nothing turns a repeated
  finding into a rule automatically.
- ❌ No reviewer checks that a change makes a `CLAUDE.md` / `AGENTS.md` /
  `.ai/rules` line out of date.
- ❌ No check that reviewers follow `REVIEW.md` (could be a review-eval case:
  a REVIEW.md rule plus a diff that breaks it).
- ❌ The "summary starts with a count; say plainly when nothing to fix" rule
  was dropped from the template in ADR 0094. It belongs in `/review`'s report.

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
- ◐ Depth: no Quick/Standard/Deep knob. Reviewer triggers choose specialists;
  effort is fixed per persona.
- ◐ Style filtering: ADVISORY findings are kept; only `REVIEW.md`'s nit cap
  limits them.
- — Overnight agent fixes: part of the batched-pipeline proposal, not built.

## 3. Security review that can block

What they do:
- A separate automated security review on every PR. Open findings from it or
  from the bug review block the merge.
- A later commit that fixes the issue clears the finding on its own.
- Public equivalents: the security-review GitHub Action, `/security-review`.

Harness:
- ◐ `security-auditor` runs only when `reviewer-triggers.md` matches. They run
  a security pass on every PR.
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
- ❌ No "always needs a person" path list. Candidates: CI workflow files,
  migrations, auth/permission code, `.env*`, the harness's own config. These
  should force `/test` and every specialist, and tell the user plainly to read
  the diff.

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

---

## Gaps worth closing, in order

Add your note under each bullet as `> Note: ...`.

1. **Re-run on current main before GO** (layer 6): `/ship` merges the latest
   base into a scratch copy of the candidate and re-runs the task commands.
2. **Paths that always need a person** (layer 5): a list in `REVIEW.md`
   ("Always a person"), honoured by `/review` (force `/test` + all specialists)
   and `/ship` (say it plainly).
3. **Root cause on bug fixes** (layer 2): `code-reviewer` checks a bugfix
   against the spec's root cause, not just the symptom.
4. **Stale instruction lines** (layer 1): reviewers flag a change that makes a
   `CLAUDE.md` / `AGENTS.md` / `.ai/rules` line untrue.
5. **Report starts with a count** (layer 1): `/review` summary line
   "N BLOCKER · N REQUIRED · N ADVISORY", or "Nothing to fix."
6. **Security pass on every candidate** (layer 3): a light always-on check,
   `security-auditor` still by trigger.
7. **Shipped-bug rows** (layer 7): an observation-log row type for a bug found
   after merge, naming the layer that should have caught it — and each one
   becomes a review-eval case.
8. **Flag question at `/ship`** (layer 6) for risky new behavior.
