---
description: Break work into small verifiable tasks with acceptance criteria and dependency ordering
argument-hint: "[ticket or feature description]"
---

Invoke the `planning-and-task-breakdown` skill before planning; its methodology
is required, not optional background.

## Require an approved spec

Read the spec from disk — including its `Status` header, not your memory of
approval earlier in the conversation. Proceed only on `Status: Approved`.
`Draft`, `Needs reapproval` or `Superseded` stops planning immediately: report
the status and return the spec to `/spec`. A spec whose requirements have no
`REQ-###` ids is also not plannable; return it for ids
(`../references/spec-quality-gates.md` §2-3).

Then pin the spec by commit. Require it committed with no uncommitted edits
(`git diff --quiet HEAD -- <spec>`), take the commit that last touched it
(`git log -1 --format=%H -- <spec>`), and record
`Spec revision: git-commit:<sha>:<spec path>`. `/build` retrieves that content
with `git show` and diffs it, which catches a spec edited without its approval
status being updated. Pin a commit, never a loose `hash-object` blob: an
unreferenced blob is pruned by `git gc` and never leaves the machine
(`../references/plan-quality-gates.md` §2).

Reconcile every planned behavior and acceptance criterion against the approved
spec. On contradiction, infeasibility, or a proposed new/stronger behavior,
stop with `SPEC CONFLICT` and return the decision to `/spec`.

## Requirement coverage

Map every spec requirement to the tasks that deliver it. A delivery task names
at least one `REQ-###`; a spike names the `TD-###` it resolves plus the
requirements it unblocks. A withdrawn requirement stays in the table marked
withdrawn rather than disappearing from it. Record the map in the plan's
Requirement Coverage table and report both lines explicitly:

- `Unmapped requirements: None` — a requirement with no task is a dropped
  requirement; it surfaces in production rather than at this gate.
- `Orphan tasks: None` — a task that names neither a requirement nor a
  `TD-###`-plus-unblocked-requirements is scope the spec never asked for.
  Remove it, or return a `SPEC CONFLICT` if the behavior is genuinely needed,
  so it gets specified and approved instead of entering through the plan.

Neither line may read anything other than `None` at handoff.

## Repository recon

Reuse the `/spec` repo-recon report first when it still covers the affected
implementation and test area. Committing or editing the spec alone does not
make that report stale. Dispatch one `repo-recon` agent only when there is no
usable report, the affected area differs or changed, or **Not surveyed** omits
needed evidence. Pass the area, `/plan` as the calling stage, and the specific
questions; do not survey the repository in this context. Compact-plan
eligibility does not waive this rule. Full reuse,
pointer-following, and **No precedent found for** handling:
`../references/repository-precedent.md` §1. No-precedent entries are plan risks,
not settled ground.

Let the skill own planning methodology: dependency graph, behavioral slicing,
workstreams, task sizing, context pointers, verification, and risk-based
checkpoints. Project-rule discovery and repository precedent come from the
recon report above, not from the skill re-deriving them.

## Plan contents

Beyond the task breakdown the skill owns, the plan records:

- a **Technical Approach** — current flow, proposed flow, components and
  responsibilities, affected areas. This is the HOW a task list does not carry;
  no production code, and no restating requirements;
- a **Verification Strategy** with task-focused, workstream, integrated, and
  where applicable data/migration and manual lines, every command from
  repository evidence. `/build` uses the integrated line for final verification;
- **Contracts and Data Changes** and **Migration and Rollout** when the change
  has APIs, schemas, events, shared DTOs, more than one workstream, or alters
  stored data or deployment shape — omitted entirely otherwise, not filled with
  N/A;
- risks whose every mitigation names the task or checkpoint that performs it.

Choose the smallest valid plan shape. Bounded single-workstream work with no
schema, contract, migration or major risk uses the template's compact plan;
do not add empty or duplicative sections to it.

For that compact plan, enforce the separation directly:

- `plan.md` has the template header, Technical Approach, Task Index,
  Requirement Coverage, Verification Strategy, and Handoff — no `Tasks`,
  empty Risks, Boundaries, or other sections;
- `todo.md` has the full task packets; do not copy those packets into the plan;
- use stable `T001` task ids, and keep one coherent behavior plus its proving
  tests in one task; and
- when focused and integrated verification are the same command, record it once
  as Integrated.

Save:

- `docs/tasks/[TICKET]-plan.md`;
- `docs/tasks/[TICKET]-todo.md`.

Present the result for human review with `Status: Draft`, and set
`Status: Approved` (plus `Approved by`/`Approved at`) only on explicit human
approval — `../references/plan-quality-gates.md` §1.

After approval, stop. The request that invoked `/plan` authorizes planning
only, even when it says to build or fix something — that instruction does not
carry forward past this command; wait for a new user request before `/build`.
Implementation goes through `/build`. Independent verification is
risk-triggered through `/test`; `/review` decides whether it is required for
the built candidate. Final release readiness goes through `/ship`.
