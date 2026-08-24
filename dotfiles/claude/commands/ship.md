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
`references/reviewer-triggers.md` requires was never run, that is a `/review`
gap — return it to `/review` instead of opening a second dispatch path to the
same personas.

## 1. Require the upstream gates

Confirm, from the actual reports rather than assumption:

- `/test` reported **VERIFY PASS** for the scope being shipped;
- `/review` reported its findings for the same integrated diff;
- the shipped commits are the ones those gates examined.

If any is missing, stop and name the missing gate. Do not substitute your own
verification for a gate that never ran.

## 2. Resolve findings from the pipeline

Carry `/review`'s findings forward without re-ranking them into a single list:

- every **Critical** finding is a blocker until fixed or explicitly accepted by
  the user;
- every **Important** finding is a recommended fix — record it as fixed,
  deferred with a reason, or accepted as risk;
- **Suggestions** do not block shipping.

Resolve duplicates across reviewers, and keep the source persona attached to
each finding so the origin stays traceable.

Fixes go back through `/build`, then re-enter `/test`. `/ship` does not
implement.

## 3. Verify the uncovered axes directly

These are not owned by any persona in the pipeline. Check them here, and say
explicitly which ones do not apply to this change rather than silently
dropping them.

- **Accessibility** — keyboard navigation, focus order, screen-reader labels,
  contrast, for any user-facing surface touched.
- **Infrastructure** — required env vars present in the target environment,
  migrations ordered and backward-compatible for the deploy window, feature
  flags with a defined default and an owner, monitoring/alerting for the new
  path.
- **Documentation** — README, changelog, an ADR when the change carries an
  architectural decision (`skills/adr-recording`), and any runbook the on-call
  rotation would need.

For tagging, branching, and release mechanics, use
`skills/git-workflow-and-versioning`; do not re-derive that process here.

## 4. Rollback plan

Mandatory before any GO, including for a small change. It may be short, but it
must be concrete — "revert the commit" only counts when reverting is genuinely
sufficient and safe, which it is not once a migration, a cache format, or an
external side effect is involved.

## 5. Decision

Produce one output:

```markdown
## Ship Decision: GO | NO-GO

### Blockers (must fix before ship)
- [source persona/axis: finding + file:line]

### Recommended fixes (should fix before ship)
- [source persona/axis: finding + file:line]

### Acknowledged risks (shipping anyway)
- [risk + mitigation + who accepted it]

### Uncovered-axis checks
- Accessibility: [result, or not applicable + why]
- Infrastructure: [result, or not applicable + why]
- Documentation: [result, or not applicable + why]

### Rollback plan
- Trigger conditions: [signals that would prompt rollback]
- Rollback procedure: [exact steps]
- Recovery time objective: [target]
```

## Rules

1. `/ship` synthesizes; it does not dispatch reviewers and does not implement.
2. Any unresolved Critical finding makes the default verdict **NO-GO**. Only
   the user can accept that risk, and the acceptance is recorded above.
3. No GO without a rollback plan.
4. Evidence only. An unrun check is reported as unverified, never inferred from
   a gate that did not cover it.
5. `/ship` never bypasses `/test` or `/review` for a change that skipped them.
