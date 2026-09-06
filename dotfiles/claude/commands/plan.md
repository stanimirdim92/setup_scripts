---
description: Break approved requirements into ordered, verifiable implementation tasks
argument-hint: "[ticket, module, spec path, or feature description]"
---

Invoke `planning-and-task-breakdown` before drafting; its methodology is
required.

## Resolve the target

Use the explicit ticket, module, or spec path, then the conversation when no
argument identifies it. Honor project-defined artifact locations and use the
capability map to select a module spec when applicable. If exactly one matching
spec exists, select it; otherwise ask which candidate to use. Announce the
selected spec path before drafting; never guess among multiple specs.

## Preconditions and evidence

Read the selected spec from disk. Apply the skill's Preconditions: approved
status, stable requirement ids, and a committed spec with no uncommitted edits.
Record its commit pin under `../references/plan-quality-gates.md` §2.

Reuse the spec's pointers and current recon evidence. Follow
`../references/repository-precedent.md` §1 for missing or stale evidence.

If the spec contradicts itself, repository evidence contradicts its behavior,
or planning requires new, weaker, or stronger behavior, save the bounded
`SPEC CONFLICT` from the plan template and stop. Do not choose an interpretation
or repair the spec inside `/plan`.

## Draft or revise

Follow the skill's form selection, task boundaries, coverage, and verification
rules. The plan and task templates own document structure. Inspect existing
targets before writing; revise only the same work and preserve stable ids.
Honor project-defined output locations and the skill's external-tracker rules.

New plans start as Draft. For existing plans, apply
`../references/plan-quality-gates.md` §1: editorial changes preserve approval;
material changes set Needs replan immediately and require renewed approval.

Run the skill's Approval Check before presenting the result. Save the plan and
task packets, including decisions and context pointers needed by a fresh
`/build` session; do not depend on chat-only conclusions. Report their locations,
plan status, remaining blockers, and handoff state.

Only explicit human approval permits Approved and Ready for /build. After
approval, stop. `/plan` authorizes planning only; it does not implement or invoke
`/build`, `/test`, `/review`, or `/ship`.
