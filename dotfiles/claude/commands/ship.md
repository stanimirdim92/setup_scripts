---
description: Final release gate — synthesize review evidence into a GO/NO-GO decision with rollback
argument-hint: "[release/change under consideration, or commit range]"
---

`/ship` is the final **SHIP** gate. It synthesizes; it does not dispatch agents
or implement fixes.

## 1. Require the REVIEW handoff

Resolve the target per `../references/target-selection.md`, and announce it ("Using: <target>") before anything else.

Require `/review`'s complete result from one of the valid sources in
`../references/target-selection.md` §Gate handoffs for the exact current
candidate.

Confirm the current branch, commits, diff, and tree still match the reviewed
candidate. Re-read the handoff artifacts and any spec/plan documents from disk
even if they appeared earlier in the conversation — the user may have edited
them since. Missing/stale review evidence or undeclared candidate changes are
**SHIP BLOCKED**.

Use `/review`'s independent-verification status:

- `NOT REQUIRED` is valid when REVIEW recorded that decision for this candidate;
- `PASS` is required when REVIEW required `/test`.

Use `/review`'s weakened-test result: **Weakened tests: none found**, or every
listed entry resolved as a finding or a stated reason. A missing result or
**Weakened tests: Not verified** is **SHIP BLOCKED** (ADR 0078).

Run the ledger check with `--ship` on the current tree
(`../references/plan-quality-gates.md` §6):

```bash
python3 "$HOME/.claude/skills/spec-driven-development/scripts/check-ledger.py" <TICKET> --ship
```

Any FAIL is **SHIP BLOCKED**: an `Open` item, a `Pending` task that is not
superseded, a spec that changed after the plan pin, or untracked deferred work.
Exit 2 is **SHIP BLOCKED** too. Warnings go into the report.

Do not independently re-run the trigger matrix or substitute new inline testing
for a missing gate.

### Paths that always need a person

Carry `/review`'s "Always a person" result forward (ADR 0096). When it lists
files, put them first in the report, under "Read these yourself", with the
reason each matched. GO stays the user's decision; the warning makes sure the
user reads those files before merging. A missing or Not verified result is
**SHIP BLOCKED**.

### Current base

Check that the candidate still passes on the current base, as a merge queue
would (ADR 0095). The candidate itself is not touched: the script merges the
base into a scratch worktree, runs the plan's integrated verification commands
there, and removes it.

```bash
"$HOME/.claude/skills/git-workflow-and-versioning/scripts/base-check.sh" \
    --base origin/<base branch> [--setup "<worktree setup command>"] -- "<integrated command>" ...
```

Take the commands from the plan's Verification Strategy (Integrated), and the
setup command from the project's `CLAUDE.md` when a fresh worktree needs one
(dependencies, environment).

- Exit 0: record the result line ("Base: current" or every check passing).
- Exit 1: a merge conflict or a failing check is **NO-GO**. The fix is a new
  candidate through `/build` and `/review`. A failure listed in the project's
  known-failures file is pre-existing; say so.
- Exit 2: **SHIP BLOCKED** with the error; the check did not run.

## 2. Resolve findings

Carry REVIEW findings forward unchanged. Their dispositions are defined once,
in `../references/component-response-contracts.md` §Dispositions.

- every **BLOCKER** must be resolved before GO: fixed, or — for a finding the
  reviewer marked low-confidence (suspected) — refuted with recorded evidence
  that addresses its specific failure scenario. Low confidence alone never
  waives a BLOCKER, and refutation evidence comes from the resolution loop
  (`/build` or the user) or from `/review`'s independent verification
  (a REFUTED verdict with `file:line` evidence), not from `/ship` itself;
- every **REQUIRED** finding must be fixed, refuted with recorded evidence that
  addresses its specific claim, explicitly accepted as risk, or deferred with a
  concrete reason. Refutation is the resolution for a false positive; do not
  record one as an accepted risk, which attributes to the release a risk it
  does not carry. Unlike a BLOCKER, a REQUIRED finding may be refuted at any
  confidence, but the evidence — not the reviewer's own uncertainty — is what
  resolves it, and it comes from the resolution loop, not from `/ship` itself;
- **ADVISORY** findings do not block shipping.
- A finding marked **pre-existing** does not block at any disposition. List it
  under follow-ups with where it is tracked: a ticket, or an observation-log
  row. A pre-existing BLOCKER with no tracked follow-up is NO-GO.

Write each finding's resolution into the review SARIF file
(`properties.resolution`): `fixed`, `refuted`, `accepted`, `deferred`,
`follow-up` for a tracked pre-existing finding, or `open`. ADVISORY findings
the author declined are `declined`. `review-noise.py` counts these to show
which reviewers raise findings that end as fixes and which raise noise
(ADR 0093).

A production fix returns to `/build`, then the new candidate goes through
`/review` again; REVIEW will decide whether `/test` is required.

## 3. Requirement evidence

Carry `/review`'s per-requirement evidence forward. For every `REQ-###` in the
approved spec, confirm both an implementing change and verification evidence.

A requirement missing either is **NO-GO**, not an advisory note: the spec said
the release must do this and nothing shows that it does. Two resolutions only —
the evidence is produced (back to `/build` or `/test`), or the requirement is
withdrawn from the spec through `/spec` with re-approval. Do not accept a
missing requirement as risk; risk acceptance is for a known finding, not for an
unproven requirement.

Evidence covers each MUST and MUST NOT clause, and each SHOULD or SHOULD NOT
clause or the exception the spec names for it. A MAY clause grants latitude and
needs no evidence of its own. A requirement the spec marks withdrawn needs no
evidence. Explicitly preserved
behavior from Change Impact is a requirement like any other — its evidence is
that its tests still pass.

## 4. Release-readiness attestations

Record `PASS`, `FAIL`, or `BLOCKED` with evidence for:

- **Infrastructure** — required env/config present; migrations/deploy ordering
  safe; flags have defaults/owners; monitoring exists for meaningful new risk.
- **Documentation** — README/changelog/ADR/runbook updated when the change
  actually requires them.

Use `PASS — not applicable: <reason>` when an axis genuinely does not apply.

## 5. Rollback

A concrete rollback plan is mandatory before GO. "Revert the commit" is enough
only when that is genuinely sufficient and safe.

## 6. Decision

GO requires:

- unchanged reviewed candidate;
- the current-base check passing, or the base unchanged;
- independent verification satisfied exactly as REVIEW required;
- no unresolved BLOCKER, except a pre-existing one tracked as a follow-up;
- `check-ledger.py --ship` passing;
- every spec requirement carrying both implementation and verification evidence;
- every REQUIRED finding resolved (fixed or refuted), explicitly risk-accepted,
  or deferred with a concrete reason;
- release-readiness attestations passed;
- concrete rollback plan;
- explained working-tree state.

Return:

```markdown
## Ship Decision: GO | NO-GO | SHIP BLOCKED

### Read these yourself
- [file] — matches `[glob]` in REVIEW.md "Always a person" (or: none)

### Blockers
- ...

### Required findings / refutations / accepted risks
- ...

### Pre-existing findings (follow-ups)
- [id] [disposition] — tracked in [ticket or observation-log row]

### Requirement evidence
- REQ-001: [implementing change] / [verification evidence]

### Release-readiness
- Infrastructure: ...
- Documentation: ...

### Rollback plan
- Trigger conditions: ...
- Procedure: ...
- Recovery target: ...

### Candidate
- Base check: [Base: current | merged clean, checks pass]
- Branch:
- Commits:
- Diff/status:
```

GO is a readiness verdict only. It does not authorize push, tag, deploy,
release, protected-branch mutation, or history rewriting.
