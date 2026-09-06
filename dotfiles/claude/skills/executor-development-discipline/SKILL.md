---
name: executor-development-discipline
description: Implements a planned task through thin behavioral slices, test-driven development, focused verification, evidence-driven retries, and atomic commits. Use only when /build explicitly selects it for an executor; do not use it for planning, independent verification, review, or release decisions.
---

# Executor Development Discipline

Apply this methodology to one bounded implementation task. The task packet owns
the outcome, acceptance criteria, scope, dependencies, and verification commands;
this skill owns how the executor changes code safely.

Load this skill once when starting a fresh executor for a workstream. When the
same executor is resumed for later tasks in that workstream, do not reload it —
the discipline already in context stays in force.

## The Task Packet Is the Contract

Implement the acceptance criteria as written. Do not reinterpret, weaken, or
extend them. If a criterion turns out to be infeasible against the actual
repository, contradicts what you find in the code, or requires a decision the
packet does not contain, stop that task and report the conflict through the
completion evidence (as a blocker) — do not pick an interpretation and build
it. `/build` routes genuine behavior conflicts back through the pipeline.

For claimed reuse, apply `../../references/repository-precedent.md` §1's
"Verify claimed reuse" check before implementing the affected slice. Read the
method/job and relevant callees, including arguments or mode flags that alter
its behavior. Reuse current evidence; report mismatches rather than copying a
similar call whose semantics do not fit this task.

## Discover the Local Test Path

Before the first edit, identify the repository-defined focused and broader
verification commands from project rules, build files, test configuration,
neighboring tests, or CI. Prefer checked-in wrappers and repository scripts.
Never guess a generic command when the project defines one.

## Implement Thin Behavioral Slices

Work on the smallest complete observable behavior that advances the current
task. Do not accumulate unrelated production code before testing it.

For each behavioral slice:

1. Write a focused test that expresses the expected behavior.
2. Run it and confirm it fails for the expected reason.
3. Write the minimum production code that makes it pass.
4. Run the focused test again and confirm it passes.
5. Refactor only while the relevant tests remain green.

For bug fixes, first reproduce the bug with a failing regression test. A test
that fails for an incidental setup or environment problem is not proof of the
bug; correct the test setup before implementing the fix.

Pure documentation, static content, and configuration-only changes with no
behavioral surface do not require a manufactured failing test. Apply the
repository's appropriate validation instead.

## Batch Independent Operations

Issue independent, read-only operations together in a single turn rather than
one per turn. Reading three files, running two greps, and inspecting git state
are independent when no one of them needs another's result first — request them
in one turn.

Serialize only when there is a real dependency: the next call's input, path, or
decision comes from the previous call's output. A test run that must follow an
edit is dependent; two unrelated file reads are not.

This is a cost constraint, not a style preference. Every turn re-reads the whole
accumulated context, so a task that issues 60 tool calls one-per-turn re-reads
context 60 times. The same 60 operations batched into 15 turns cut that roughly
fourfold, with no loss of information. Read-only inspection at the start of a
task — rules, precedents, sibling files, current git state — should be gathered
in as few turns as the operations' dependencies allow.

Mutating operations (edits, writes, migrations, commits) stay one per step and
follow the TDD loop; batching applies to reads, greps, and non-mutating
inspection, not to changes that must be verified individually.

## Verify at the Right Cadence

During a slice, run the smallest test command that can change meaningfully from
the edit. Do not repeatedly run the entire suite after each small change.

Run broader verification early when the task changes shared or risky surfaces
such as migrations, configuration, shared modules, or public contracts.

At task completion:

- run every verification command required by the task packet;
- if this is the last selected task in the workstream, also run the supplied
  workstream-level or full relevant verification;
- record exact commands and outcomes;
- report any required check that could not run and why.

Match evidence to the promised outcome. A dispatch assertion proves enqueueing,
not job execution or its effect on the intended record. When that effect is in
scope, exercise the relevant job path with repository-supported test boundaries.
For a concurrency invariant, derive conflicting cases from the actual matching
rules, including alternate identities that can match the same entity; the
presence of a lock or one identical-input case is not proof of the whole claim.
Add focused checks for already-required behavior within the task. If adequate
verification needs an unresolved decision or unavailable capability, report the
gap and its limit instead of claiming completion or expanding scope silently.

Do not repeat an unchanged successful command without an intervening change or
new condition that could affect its result.

## Retry from Evidence

Never rerun an unchanged failing command merely hoping for a different result.
Every retry must follow at least one of:

- a relevant code or configuration change;
- a changed environmental condition;
- a new hypothesis derived from the failure evidence.

If no new evidence or materially different hypothesis exists — or the same
failure has survived three evidence-driven attempts — stop and report the
blocker instead of looping.

## Commit Atomic Increments

Commit a logical increment only when its intended behavior works, its required
focused verification is green, and the tree is in a valid state. Use meaningful
messages that explain the change and follow the repository's commit convention.

Invocation through `/build` authorizes these scoped local commits for the
approved task unless the user explicitly requests an uncommitted result;
preserve and report that override. It does not authorize push, tag, deploy, release,
protected-branch mutation, history rewriting, or unrelated changes.

Apply the staged-diff and commit-content checks in `../../CLAUDE.md` §3.
Report directly required neighboring changes as scope expansion through the
executor's output contract.

## Completion Evidence

Before reporting a task complete, provide evidence for:

- behavioral slices implemented;
- tests added or changed;
- required focused and workstream verification;
- commits created;
- final working-tree state;
- checks not run, scope expansions, untouched observations, and blockers
  (including any task-packet conflict reported under The Task Packet Is the
  Contract).

Evidence is the result of an executed check, not confidence that the change
should work.
