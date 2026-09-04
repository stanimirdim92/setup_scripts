---
name: planning-and-task-breakdown
description: Breaks an approved spec into ordered tasks. Use when implementation needs dependency ordering, workstreams, technical decisions, checkpoints, or durable scope for later sessions.
---

# Planning and Task Breakdown

## Overview

Turn an approved behavioral specification into a small, ordered implementation
plan. Each task should produce a coherent outcome that one focused executor can
implement and verify.

## When to Use

- The approved spec needs more than one implementation step
- Dependencies or implementation order are not obvious
- Work may span distinct implementation contexts or sessions
- Technical decisions, checkpoints, or durable task packets are needed

**When NOT to use:** bounded low-risk work with one obvious implementation step
does not need a formal plan merely because production code and focused tests are
in different files. An explicit `/plan` request still produces the durable plan
required by the `/build` pipeline.

## Preconditions

1. Read the spec from disk and require `Status: Approved` with stable
   `REQ-###` ids. Any other state returns to `/spec`.
2. Require the spec committed with no uncommitted edits. Record the commit that
   last touched it as `Spec revision: git-commit:<sha>:<spec path>` according to
   `../../references/plan-quality-gates.md` §2.
3. Start from the spec's repository pointers and any current recon report. Use
   the smallest adequate evidence path in
   `../../references/repository-precedent.md`; never guess a command or repeat
   an unchanged survey.
4. Reconcile the plan against the approved behavior. If repository evidence
   makes a requirement contradictory, infeasible, or incomplete, write the
   bounded `SPEC CONFLICT` described by the plan template and stop.

Planning is read-only with respect to production code. It produces plan and task
artifacts, not implementation.

## Draft the Plan

Use `../../references/templates/plan.md` for the plan and
`../../references/templates/task.md` for task packets.

Choose the smallest valid form:

- **Compact:** bounded single-workstream work with no schema change, public
  contract, migration, or major risk. The plan contains only its header,
  Technical Approach, Task Index, Requirement Coverage, Verification Strategy,
  and Handoff. The todo contains the full task packets.
- **Full:** use the template's conditional sections when contracts, stored data,
  multiple workstreams, migrations, major risks, decisions, or checkpoints
  require them. Omit inapplicable sections rather than filling them with `N/A`.

Give each fact one home: the spec owns behavior, the plan owns implementation
approach and ordering, and the todo owns executable task detail.

### Technical Approach and Decisions

Describe the current-to-proposed implementation flow, affected areas, and
component responsibilities without production code or repeated requirements.
Record a `TD-###` only when two or more plausible implementations existed and
the choice needs to survive review; cite its spec, project-rule, precedent, or
new technical-decision source. Id rules live in
`../../references/plan-quality-gates.md` §3.

### Behavioral Tasks and Dependencies

- Slice by independently verifiable behavior, not architectural layer or file
  count. Production implementation and its proving tests normally share one
  delivery task.
- Apply one boundary test: can this task produce behavior that is meaningfully
  verified on its own? Prefer `Contacts persist with the uniqueness invariant`
  to `Create ContactRepository, ContactFactory, and DTO`.
- A separate foundation task must be independently verifiable and consumed by
  at least two downstream tasks. A separate test task needs value before the
  production change, such as characterization evidence.
- Every task uses stable `T###` ids and carries its requirements, acceptance
  criteria, verification, dependencies, workstream, material context pointers,
  likely areas, and estimated scope.
- Carry each invariant transition into every task that can establish, transfer,
  violate, or release it, including the enforcing layer from the spec.
- Order real prerequisites before dependent behavior. A call relationship or
  architectural adjacency alone does not create a task dependency.

Keep a task as one coherent slice when it fits a focused implementation session.
Split work that spans independent behavior or more than one such session; file
count is context, not the gate.

### Workstreams, Checkpoints, and Spikes

Default to one workstream. Split only when implementation context is materially
different and work is independent, or when a stable contract plus an explicit
dependency checkpoint separates upstream and downstream work. `/build`, not the
plan, owns actual concurrency and isolation.

Independent workstreams share no files or mutable state and have no unfinished
dependency. Contract-separated workstreams retain their dependency and cannot
start downstream work until the named checkpoint passes.

Add a `CP-###` only after a risky schema/external-contract decision, before
dependent work consumes a new contract, or after multiple workstreams integrate.
Put high-risk work early enough to fail fast, and order every task so its
completion leaves the system in a working state.

Technical uncertainty that cannot be resolved read-only becomes a bounded spike
task whose acceptance criteria name the evidence and decision threshold. It
resolves a `TD-###`, names the `REQ-###` ids it unblocks, changes no production
behavior, and is checkpointed before dependents. Anything that could change
required behavior is a `SPEC CONFLICT`, not a spike. Full rules:
`../../references/plan-quality-gates.md` §5.

### Coverage and Verification Strategy

- Map every `REQ-###` to one or more tasks or explicit verification-only
  evidence for already-preserved behavior.
- Every delivery task names at least one `REQ-###`; every spike names its
  `TD-###` and the requirements it unblocks.
- Report exactly `Unmapped requirements: None` and `Orphan tasks: None` before
  handoff. A withdrawn requirement remains visible as withdrawn.
- Use exact repository-defined verification commands. Task checks prove the
  slice; workstream checks prove integrations within a stream; Integrated checks
  prove the selected plan as a whole. Record a focused command only when it
  differs from Integrated.
- Every risk mitigation names the task or checkpoint that performs it.

## Approval Check

Before presenting the plan for human review, confirm:

- the approved committed spec and its revision pin are current;
- the plan neither drops nor adds behavior;
- every task is behavioral, ordered, dispatchable, and covered by requirements;
- workstreams and checkpoints follow actual dependencies and risk;
- verification commands come from repository evidence; and
- the applicable checks in `../../references/plan-quality-gates.md` §4 pass.

Fix plan-level failures and rerun the check. Return behavioral conflicts to
`/spec`. Passing this check does not grant approval.

## Output and Handoff

Save:

- plan: `docs/tasks/[TICKET]-plan.md`;
- task packets: `docs/tasks/[TICKET]-todo.md`, unless project rules designate an
  external tracker.

Inspect the target before writing. Revise existing artifacts in place only when
they describe the same work. If an incomplete plan or task target belongs to
different work, stop and ask where the new plan should live or whether the old
one should be superseded; never overwrite, rename, bulk-close, or delete it on
your own.

The plan indexes tasks; the todo or tracker owns their full packets. Never copy
the same task packet into both. Start with `Status: Draft` and
`Handoff: Awaiting plan approval`. After explicit human approval, record
`Status: Approved`, `Approved by`, `Approved at`, and
`Handoff: Ready for /build`, then stop. `/plan` does not implement or invoke
`/build`.

## Changes and Reapproval

A material edit to an approved plan—task scope, dependency, workstream,
decision, contract, or verification command—sets `Needs replan` in the same
edit and requires the Approval Check plus renewed human approval. Editorial
corrections do not. If the pinned spec changes behaviorally, the spec returns to
`/spec` and the plan becomes `Needs replan`. See
`../../references/plan-quality-gates.md` §1–2.

## Verification

Verification is a human gate. The agent runs the Approval Check before
presenting the draft but cannot self-certify approval:

- [ ] The human reviewed and explicitly approved this exact plan
- [ ] The header records `Status: Approved`, `Approved by`, and `Approved at`
- [ ] The handoff reads `Ready for /build`

The plan is not ready for `/build` until all items pass. Project-wide completion
standards remain in `../../references/definition-of-done.md`.
