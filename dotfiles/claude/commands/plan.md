---
description: Break approved requirements into ordered, verifiable implementation tasks
argument-hint: "[ticket or feature description]"
---

Invoke `planning-and-task-breakdown` before drafting; its methodology is
required.

## Preconditions

Read the spec from disk. Proceed only when:

- its header reads `Status: Approved`;
- every requirement uses a stable `REQ-###` id;
- the spec is committed with no uncommitted edits; and
- `git log -1 --format=%H -- <spec>` resolves the revision to record as
  `Spec revision: git-commit:<sha>:<spec path>`.

Any other status returns to `/spec`. Pin and later comparison rules are in
`../references/plan-quality-gates.md` §1–2.

Use the spec's pointers and any current recon report. Reuse current evidence;
otherwise choose the smallest adequate path in
`../references/repository-precedent.md` §1. Never guess or abbreviate a
repository-defined command. Treat **No precedent found for** as a risk and
**Not surveyed** as a limit.

If repository evidence contradicts the approved behavior, or planning requires
new, weaker, or stronger behavior, save the bounded `SPEC CONFLICT` from the
plan template and stop. Do not repair the spec inside `/plan`.

## Draft

Use `../references/templates/plan.md` and
`../references/templates/task.md`. Choose compact or full form per the skill.

The plan must include:

- a Technical Approach without production code or repeated requirements;
- an ordered Task Index with stable `T###` ids;
- Requirement Coverage with every `REQ-###` mapped and exactly
  `Unmapped requirements: None` and `Orphan tasks: None`;
- a Verification Strategy using repository-defined commands; and
- conditional contracts, migration, workstream, decision, checkpoint, and risk
  sections only when applicable.

Each task packet carries requirements, acceptance criteria, verification,
dependencies, workstream, and material context pointers. Keep one coherent
behavior and its proving tests in one delivery task.

For a compact plan, `plan.md` contains only its header, Technical Approach,
Task Index, Requirement Coverage, Verification Strategy, and Handoff;
`todo.md` owns the full task packets. When focused and integrated verification
are identical, record the command once as Integrated.

Before writing, inspect the target artifacts. Revise in place only for the same
work. If an incomplete plan or task target belongs to different work, stop and
ask rather than overwriting, renaming, closing, or deleting it.

Save:

- `docs/tasks/[TICKET]-plan.md`;
- `docs/tasks/[TICKET]-todo.md`, unless project rules designate an external
  tracker. In that case, record the tracker in the plan and keep its Task Index
  as ordered item ids or links, not duplicate task packets.

## Approval

Present the plan with `Status: Draft`, `Approved by: —`, `Approved at: —`, and
`Handoff: Awaiting plan approval`. Run the skill's Approval Check, but set
`Status: Approved` and `Handoff: Ready for /build` only after explicit human
approval (`../references/plan-quality-gates.md` §1).

After approval, stop. `/plan` authorizes planning only; it does not invoke
`/build`, `/test`, `/review`, or `/ship`.
