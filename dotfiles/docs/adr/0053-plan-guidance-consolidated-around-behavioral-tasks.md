# Plan guidance consolidated around behavioral tasks

**Decision.** Keep the planning Overview and durable `/plan` contracts while
removing repeated examples, guardrails, rationalizations, red flags, sizing
tables, parallelization prose, and the duplicated agent checklist.

The consolidated skill now has one flow:

1. require and commit-pin the Approved spec;
2. gather only the repository evidence the implementation needs;
3. choose compact or full form;
4. describe the technical approach and any material `TD-###` decisions;
5. create behavioral `T###` task packets with dependencies and workstreams;
6. add risk-based `CP-###` checkpoints or bounded spikes only when needed;
7. prove requirement coverage and integrated verification; and
8. run an Approval Check before human review.

File count alone does not require a formal plan. An explicit `/plan` invocation
still produces the durable artifacts required by `/build`. Production changes
and their proving tests normally remain one task; acceptance criteria stay in
the task packet because they are the executor contract, not a duplicate plan
section.

Verification is a human gate. Draft artifacts use
`Handoff: Awaiting plan approval`; only explicit approval changes the plan to
`Status: Approved` and the handoff to `Ready for /build`. The plan continues to
index tasks while the todo or external tracker owns their full packets.

The full template's sizing exception is now conditional instead of a mandatory
`None` section. Approval-check terminology replaces the former closure wording,
and stale numbered-step references were removed from the templates.

One behavioral-slice example remains because it makes the task-boundary rule
concrete. The skill also retains the original working-state invariant and the
conditions that distinguish independent from contract-separated workstreams.

**Validation.** The plan skill fell from 481 to 185 lines and `/plan` from 107
to 75 lines. Plugin validation passed, all 65 hook tests passed, relevant
reference paths resolved, and `git diff --check` passed. A fresh `/plan` canary
under the configured permission mode produced a 45-line compact Draft plan and
a 28-line task packet: one behavioral `T001`, an exact committed-spec pin, all
three requirements mapped, `Unmapped requirements: None`,
`Orphan tasks: None`, the exact repository-defined test command, no empty full
sections, no recon agent, no permission denials, and no implementation.

**Rejected — remove task acceptance criteria as duplicated behavior.** The plan
document does not repeat them, but the task packet must carry the executor's
bounded observable contract without requiring the full spec in its prompt.

**Rejected — merge plan and todo artifacts.** The existing pipeline consumes
the plan for approach, ordering, coverage, and integrated verification, while
`/build` consumes todo packets for execution. Enforcing that separation removes
duplication without changing the interface.

**Rejected — let the Approval Check set `Status: Approved`.** Internal
consistency is not human authorization.

**Revisit if** full plans lose conditional contract/migration/risk detail, or
compact plans duplicate task packets, split implementation from its proving
tests, or omit the exact spec pin and coverage lines.
