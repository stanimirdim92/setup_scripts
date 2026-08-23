# Agent execution: bounded context, evidence, and measurement

**Decision.** Keep the existing workstream-oriented `/build` architecture and
make the execution contract more explicit:

1. Executors receive bounded task packets: outcome, acceptance criteria,
   dependencies/workstream, scope, verification, and only the rule/precedent/
   contract pointers that materially constrain the task.
2. Related tasks reuse the same executor within a workstream; unrelated work
   gets a fresh context.
3. Writer concurrency remains one active executor in a shared checkout, per
   [0003](0003-executor-concurrency-sequential-only.md). Future parallel writers
   require isolated worktrees/branches; integration remains sequential.
4. Executors do not broaden permissions or seek credentials to escape their tool
   boundary. Missing privileged capabilities are surfaced to the orchestrator.
5. Retries must be evidence-driven. Repeating an unchanged failed operation with
   no new hypothesis is not progress.
6. Completion reports contain exact verification evidence and explicit unverified
   gaps, not confidence language.
7. `/build` reports lightweight actual run metrics so task sizing, workstream
   shape, context reuse, and model tiering can be tuned after a meaningful sample
   of runs. Runtime token/cost/time is recorded only when exposed, never guessed.
8. Old backup command/agent/skill files are removed from live discoverable
   directories; Git history is the backup.

These refine rather than replace
[0002](0002-model-split-sonnet-orchestrator-tiered-subagents.md),
[0003](0003-executor-concurrency-sequential-only.md), and
[0020](0020-build-test-review-pipeline-split.md).

**Rejected — full spec/plan in every executor prompt.** It repeats context that
the executor rarely needs, dilutes task-local constraints, and repays token cost
on every dispatch. Authoritative pointers are cheaper and less likely to drift.

**Rejected — fresh executor for every task.** Tasks in one workstream share
implementation context; throwing that context away increases discovery cost
without increasing independence.

**Rejected — mandatory per-project metrics files.** Global config is used across
different projects. Metrics are emitted in run output by default and persisted
only where a project/user explicitly chooses a storage location.

**Rejected — broadening global permissions to make agents more autonomous.**
Bounded capabilities make unsafe or privileged actions visible at the
orchestration boundary instead of silently expanding the blast radius.
