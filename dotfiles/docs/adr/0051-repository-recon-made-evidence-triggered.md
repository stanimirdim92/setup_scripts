# Repository recon made evidence-triggered

**Decision.** Keep the read-only `repo-recon` agent and its isolated context,
but stop dispatching it automatically from every `/spec` and `/plan`.

Each stage now chooses the smallest adequate evidence path:

1. reuse a current report for the same unchanged area;
2. perform a bounded check of applicable instructions and named source, test,
   manifest, or CI files for a familiar low-risk change; or
3. dispatch `repo-recon` when the area is unfamiliar or broad, crosses modules,
   changes schema/contract/lifecycle/concurrency behavior, lacks verified
   commands or precedent, or needs something a previous report did not survey.

`/plan` starts from the approved spec's pointers and any current report. It does
not repeat `/spec`'s evidence gathering unless the affected area changed or a
material gap remains.

The dispatched report is also shortened to four sections: Rules and precedent,
Verification, Constraints, and Unknowns. Unknowns preserves the two distinct
safety signals from [0041](0041-recon-delegated-to-repo-recon-subagent.md):
**No precedent found for** means the area was checked and gave no guidance;
**Not surveyed** means no conclusion is supported.

**Why this reverses part of 0041.** Its rejection of risk-triggered recon
assumed that a change small enough to skip recon was too small for `/spec`.
Compact specs now deliberately cover bounded low-risk multi-file work, so that
premise no longer holds. In the compact harness canary, both `/spec` and
`/plan` completed without a recon subagent; the standalone plan explicitly
declined dispatch for two known files despite mandatory wording. The model's
reasonable behavior and the written contract disagreed. Making the policy
proportional resolves that disagreement without removing evidence requirements.

No durable recon artifact is added. Decisions, commands, and useful pointers
already belong in the spec, plan, and task packet; another document would
duplicate them.

**Validation.** A fresh bounded canary ran both `/spec` and `/plan` with zero
recon subagents. The spec retained its complete approval header, requirement
trace, and exact repository-defined test command; the plan reused that evidence
and mapped all requirements into one task.

**Rejected — remove `repo-recon`.** Broad or unfamiliar areas still create
unbounded reads in the main context. The isolated pointer report remains useful
there.

**Rejected — keep mandatory dispatch and strengthen the wording.** The canary
already showed that prose enforcement fights proportional behavior. A hook or
validator for subagent dispatch would add machinery without improving the
evidence itself.

**Rejected — use a fixed file-count threshold.** Two files can contain a public
contract or concurrency invariant, while ten generated files may be routine.
The trigger follows uncertainty and risk, not file count.

**Revisit if** bounded checks expand into broad inline surveys, or dispatched
reports regularly omit rules that change the resulting spec or plan. That would
show the trigger boundary is too permissive.
