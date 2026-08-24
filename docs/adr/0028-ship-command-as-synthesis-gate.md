# `/ship` added as a synthesis gate, reversing 0027's "no `/ship` command"

**Decision.** Added `/ship` as the final gate after `/review`, reversing
[0027](0027-vendored-shipping-and-launch-skill-no-ship-command.md)'s decision
not to have one. `/ship` dispatches no personas: it requires `/test`'s VERIFY
PASS and `/review`'s findings for the same integrated diff, resolves those
findings into blockers/recommended/accepted-risk, verifies the three axes no
persona in the pipeline owns (accessibility, infrastructure, documentation),
and issues the GO/NO-GO verdict with a mandatory rollback plan. Release
mechanics defer to `skills/git-workflow-and-versioning`.

This keeps 0027's actual objection intact. 0027 rejected upstream's `/ship`
because it fans out `code-reviewer`/`security-auditor`/`test-engineer` in
parallel — a second orchestration path to the personas `/test` and `/review`
already own, which is the problem
[0006](0006-review-thin-wrapper-over-code-reviewer.md) closed. The shape
adopted here has no dispatch at all, so that path is never opened. A required
reviewer that never ran is treated as a `/review` gap and returned there.

It also resolves a live contradiction. Commit `fbb3e64` stripped the verdict
out of `commands/review.md`, but `commands/plan.md` and `docs/agents.md` still
attributed GO/NO-GO to `/review`, so nothing owned it. Verdict ownership now
sits in exactly one place: `/review` reports findings, `/ship` decides.

**Rejected — restoring the `shipping-and-launch` skill deleted in `fbb3e64`.**
Upstream's `/ship` is a thin prompt over that 310-line skill. Re-vendoring it
an hour after deleting it would reverse a deliberate choice nobody asked to
reverse, and `commands/ship.md` needs three checklist axes and a rollback
template, not staged-rollout thresholds and feature-flag lifecycle guidance
this repo has no use case for (`CLAUDE.md` rule 2). The command is
self-contained instead. Revisit if staged rollout becomes real work here.

**Rejected — folding the ship verdict back into `/review`.** That is where it
used to live, and `fbb3e64` removed it on purpose: the review gate judges a
diff, while the ship decision needs infrastructure readiness, docs, and a
rollback plan that have nothing to do with reading code. Merging them puts two
jobs in one gate and gives `code-reviewer`'s scope authority over deploy
concerns it cannot see.
