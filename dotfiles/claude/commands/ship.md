---
description: Final release gate — synthesize review evidence into a GO/NO-GO decision with rollback
argument-hint: "[release/change under consideration, or commit range]"
---

`/ship` is the final **SHIP** gate. It synthesizes; it does not dispatch agents
or implement fixes.

## 1. Require the REVIEW handoff

Resolve the target per `../references/target-selection.md`, and announce it ("Using: <target>") before anything else.

Require `/review`'s result for the exact current candidate.

Confirm the current branch, commits, diff, and tree still match the reviewed
candidate. Re-read the handoff artifacts and any spec/plan documents from disk
even if they appeared earlier in the conversation — the user may have edited
them since. Missing/stale review evidence or undeclared candidate changes are
**SHIP BLOCKED**.

Use `/review`'s independent-verification status:

- `NOT REQUIRED` is valid when REVIEW recorded that decision for this candidate;
- `PASS` is required when REVIEW required `/test`.

Do not independently re-run the trigger matrix or substitute new inline testing
for a missing gate.

## 2. Resolve findings

Carry REVIEW findings forward unchanged.

- every **BLOCKER** must be resolved before GO: fixed, or — for a finding the
  reviewer marked low-confidence (suspected) — refuted with recorded evidence
  that addresses its specific failure scenario. Low confidence alone never
  waives a BLOCKER, and refutation evidence comes from the resolution loop
  (`/build` or the user), not from `/ship` itself;
- every **REQUIRED** finding must be fixed, refuted with recorded evidence that
  addresses its specific claim, explicitly accepted as risk, or deferred with a
  concrete reason. Refutation is the resolution for a false positive; do not
  record one as an accepted risk, which attributes to the release a risk it
  does not carry. Unlike a BLOCKER, a REQUIRED finding may be refuted at any
  confidence, but the evidence — not the reviewer's own uncertainty — is what
  resolves it, and it comes from the resolution loop, not from `/ship` itself;
- **ADVISORY** findings do not block shipping.

A production fix returns to `/build`, then the new candidate goes through
`/review` again; REVIEW will decide whether `/test` is required.

## 3. Release-readiness attestations

Record `PASS`, `FAIL`, or `BLOCKED` with evidence for:

- **Infrastructure** — required env/config present; migrations/deploy ordering
  safe; flags have defaults/owners; monitoring exists for meaningful new risk.
- **Documentation** — README/changelog/ADR/runbook updated when the change
  actually requires them.

Use `PASS — not applicable: <reason>` when an axis genuinely does not apply.

## 4. Rollback

A concrete rollback plan is mandatory before GO. "Revert the commit" is enough
only when that is genuinely sufficient and safe.

## 5. Decision

GO requires:

- unchanged reviewed candidate;
- independent verification satisfied exactly as REVIEW required;
- no unresolved BLOCKER;
- every REQUIRED finding resolved (fixed or refuted), explicitly risk-accepted,
  or deferred with a concrete reason;
- release-readiness attestations passed;
- concrete rollback plan;
- explained working-tree state.

Return:

```markdown
## Ship Decision: GO | NO-GO | SHIP BLOCKED

### Blockers
- ...

### Required findings / refutations / accepted risks
- ...

### Release-readiness
- Infrastructure: ...
- Documentation: ...

### Rollback plan
- Trigger conditions: ...
- Procedure: ...
- Recovery target: ...

### Candidate
- Branch:
- Commits:
- Diff/status:
```

GO is a readiness verdict only. It does not authorize push, tag, deploy,
release, protected-branch mutation, or history rewriting.
