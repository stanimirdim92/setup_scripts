---
description: Break work into small verifiable tasks with acceptance criteria and dependency ordering
argument-hint: "[ticket or feature description]"
---

Invoke the `planning-and-task-breakdown` skill.

## Require an approved spec

Read the spec from disk — including its `Status` header, not your memory of
approval earlier in the conversation. Proceed only on `Status: Approved`.
`Draft`, `Needs reapproval` or `Superseded` stops planning immediately: report
the status and return the spec to `/spec`. A spec whose requirements have no
`REQ-###` ids is also not plannable; return it for ids
(`../references/spec-quality-gates.md` §2-3).

Then pin the spec's content — `git hash-object -w docs/specs/[TICKET]-SPEC.md` —
and record it in the plan as `Spec revision: git-blob:<hash>`. `/build`
recomputes it and stops on a mismatch, which catches a spec edited without its
approval status being updated. `-w` matters: it writes the blob so the pinned
content can be diffed later.

Reconcile every planned behavior and acceptance criterion against the approved
spec. On contradiction, infeasibility, or a proposed new/stronger behavior,
stop with `SPEC CONFLICT` and return the decision to `/spec`.

## Requirement coverage

Map every spec requirement to the tasks that deliver it, and give every task at
least one `REQ-###`. Record the map in the plan's Requirement Coverage table and
report both lines explicitly:

- `Unmapped requirements: None` — a requirement with no task is a dropped
  requirement; it surfaces in production rather than at this gate.
- `Orphan tasks: None` — a task with no requirement is scope the spec never
  asked for. Remove it, or return a `SPEC CONFLICT` if the behavior is genuinely
  needed, so it gets specified and approved instead of entering through the plan.

Neither line may read anything other than `None` at handoff.

## Repository recon

Dispatch one `repo-recon` agent for the affected area before planning — the area,
`/plan` as the calling stage, and any specific questions you already have. Do not
survey the repository in this context. Reuse, pointer-following, and
**No precedent found for** / **Not surveyed** handling:
`../references/repository-precedent.md` §1. Its no-precedent entries are risks
for the plan, not settled ground.

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

Bounded single-workstream work with no schema, contract, migration or major risk
uses the template's compact plan.

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
