---
description: Final release gate — synthesize /test and /review evidence into a GO/NO-GO decision with a rollback plan
argument-hint: "[release/change under consideration, or the commit range being shipped]"
---

`/ship` is the final **SHIP** gate after `/review`.

It is a synthesis gate, not a fan-out. `/build` implemented, `/test` verified,
`/review` judged the diff with `code-reviewer` and any triggered specialists.
`/ship` decides whether that body of evidence is enough to go live, covers the
axes no persona in the pipeline owns, and produces the rollback plan.

Do not re-dispatch `code-reviewer`, `security-auditor`,
`distributed-systems-reviewer`, or `test-engineer` here. If a reviewer that
`../references/reviewer-triggers.md` requires was never run, that is a `/review`
gap — return it to `/review` instead of opening a second dispatch path to the
same personas.

## 1. Require the upstream gates

Confirm, from the actual reports rather than assumption:

- `/test` reported **VERIFY PASS** for the scope being shipped;
- `/review` reported its findings for the same integrated diff;
- the shipped commits are the ones those gates examined.

If any is missing, stop and name the missing gate. Do not substitute your own
verification for a gate that never ran.

Require `/test` and `/review` handoffs from the current conversation. Inspect
the current branch, local commits, diff, and working-tree status and confirm the
candidate has not changed since those gates. Missing outcomes, an undetermined
or changed candidate, undeclared dirty state, or a missing required reviewer is
**SHIP BLOCKED**; never replace a missing gate with new inline verification.
There is no hidden gate store: in a fresh conversation, supply the prior gate
outputs or rerun the gates.

## 2. Resolve findings from the pipeline

Carry `/review`'s findings forward without re-ranking them into a single list:

- every canonical **BLOCKER** must be fixed before GO;
- every **REQUIRED** finding is fixed, deferred with a reason, or explicitly
  accepted as risk;
- **ADVISORY** findings do not block shipping.

Keep every finding's source reviewer, native severity, canonical disposition,
stable id, location, and resolution. Do not reclassify during synthesis.

Preserve the exact REVIEW finding set. If two findings describe the same issue,
cross-reference them without deleting, merging, renumbering, or changing either
source persona; deduplication after REVIEW would make the evidence incomplete.

Fixes go back through `/build`, then repeat `/test`, `/review`, and `/ship`.
`/ship` does not implement, and a prior REVIEW never covers a changed candidate.

## 3. Record release-readiness attestations

These are not owned by any persona in the pipeline. Record each as a
release-readiness attestation with `PASS`, `FAIL`, or `BLOCKED` plus concrete
evidence. When an axis does not apply, use PASS only with an explicit
not-applicable reason. These attestations do not substitute for TEST or REVIEW.

- **Infrastructure** — required env vars present in the target environment,
  migrations ordered and backward-compatible for the deploy window, feature
  flags with a defined default and an owner, monitoring/alerting for the new
  path.
- **Documentation** — README, changelog, an ADR when the change carries an
  architectural decision (`../skills/adr-recording`), and any runbook the on-call
  rotation would need.

For tagging, branching, and release mechanics, use
`../skills/git-workflow-and-versioning`; do not re-derive that process here.

## 4. Rollback plan

Mandatory before any GO, including for a small change. It may be short, but it
must be concrete — "revert the commit" only counts when reverting is genuinely
sufficient and safe, which it is not once a migration, a cache format, or an
external side effect is involved.

## 5. Decision

GO requires an unchanged candidate since TEST and REVIEW, an explained clean
tree, all three PASS attestations, a complete rollback plan, completed required
reviewers, and no unresolved BLOCKER. Missing gate results and a missing rollback
plan are non-waivable blockers.

Include the current branch, local commits, and diff/status scope in every GO,
NO-GO, or SHIP BLOCKED result.

Produce one output:

```markdown
## Ship Decision: GO | NO-GO

### Blockers (must fix before ship)
- [source persona/axis: finding + file:line]

### Recommended fixes (should fix before ship)
- [source persona/axis: finding + file:line]

### Acknowledged risks (shipping anyway)
- [risk + mitigation + who accepted it]

### Release-readiness attestations
- Infrastructure: [result, or not applicable + why]
- Documentation: [result, or not applicable + why]

### Rollback plan
- Trigger conditions: [signals that would prompt rollback]
- Rollback procedure: [exact steps]
- Recovery time objective: [target]
```

## Rules

1. `/ship` synthesizes; it does not dispatch reviewers and does not implement.
2. Any unresolved canonical BLOCKER makes the verdict **NO-GO**.
3. No GO without a rollback plan.
4. Evidence only. An unrun check is reported as unverified, never inferred from
   a gate that did not cover it.
5. `/ship` never bypasses `/test` or `/review` for a change that skipped them.
6. GO is a release-readiness verdict only. It does not authorize tagging,
   pushing, deployment, release, protected-branch mutation, or history rewriting.
7. Missing gate results, an undetermined or changed candidate, missing required
   reviewers, undeclared dirty state, and a missing rollback plan cannot be
   waived.
