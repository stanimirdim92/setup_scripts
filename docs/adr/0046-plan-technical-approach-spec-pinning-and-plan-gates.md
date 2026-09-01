# Plan gains a technical approach, a spec pin, and its own approval state

**Decision.** Applied the same treatment to PLAN that
[0045](0045-spec-approval-state-change-impact-and-requirement-traceability.md)
gave DEFINE. The diagnosis behind it: the plan template held decisions and
tasks but not the actual HOW — no technical flow, no contracts, no migration
approach, no integrated verification — so a task list was standing in for a
design. Eight changes, nothing vendored.

1. **Plan approval state and spec-revision pinning.** The plan gains
   `Status` (`Draft` / `Approved` / `Needs replan` / `Superseded`),
   `Approved by`, `Approved at`, and `Spec revision: git-blob:<hash>` from
   `git hash-object -w` on the spec. `/build` recomputes the hash and stops on a
   mismatch. Approval previously lived only in the handoff line at the bottom of
   the document, as prose.

2. **A Technical Approach section** — current flow, proposed flow, components
   and responsibilities, affected areas. No production code and no restated
   requirements; the spec owns what and why.

3. **`TD-###` technical decisions** in expanded form (choice, alternatives,
   reason, source, affects) where two or more plausible implementations existed.
   Simple decisions stay one-liners.

4. **Executable traceability.** Task ids become zero-padded `T001`, stable after
   approval and never renumbered; a dropped task keeps its id and is struck
   through as superseded. Requirement Coverage becomes
   `REQ → tasks → evidence`.

5. **Conditional Contracts and Data Changes, and Migration and Rollout**
   sections — contract owner, consumers, authoritative definition, compatibility
   class, stabilization checkpoint; deployment order, mixed-version behavior,
   backfill, locking, rollback, post-deployment evidence. Included only when the
   change has APIs, schemas, events, shared DTOs, multiple workstreams, or
   alters stored data; omitted entirely otherwise.

6. **A plan-level Verification Strategy** — task-focused, workstream,
   integrated, data/migration, manual — every command from repository evidence.
   `/build` runs the integrated line after all integrations, because task- and
   workstream-focused checks passing is not evidence that integrated behavior
   works. For a bugfix plan, the three proofs: the pre-fix implementation
   reproduces the defect, the fixed one produces the expected behavior, and the
   explicitly preserved behavior is unchanged.

7. **Risks became actionable.** The table gains Trigger/evidence and
   Task/checkpoint columns, and **a mitigation with no owning task or checkpoint
   fails closure.** A risk table of unowned mitigations documents hope.

8. **Bounded spike tasks** for technical uncertainty that cannot be resolved
   read-only, with acceptance criteria naming the evidence and the deciding
   threshold, gated by a checkpoint before dependent work. Runs during `/build`,
   changes no production behavior. Only for technical questions: if the answer
   could change a `REQ-###` it stays a `SPEC CONFLICT`. This closes the gap
   between the existing guardrail "do not hide unresolved technical risks inside
   implementation tasks" and having nowhere else to put them.

Rules for 1, 4, 7 and 8 live in one new `references/plan-quality-gates.md`,
pointed at by the skill, `/plan` and `/build` — the `reviewer-triggers.md`
pattern, as with `spec-quality-gates.md`.

**Corrected from the proposal — `TD-###`, not `DEC-###`, in the plan.** 0045 had
already given the *spec* `DEC-###` for material product/domain/contract/lifecycle
decisions. Using the same prefix for the plan's technical decisions would make
"see DEC-002" ambiguous between two documents for the same ticket, precisely
when someone is trying to trace a decision. `plan-quality-gates.md` §3 now
records one id-ownership table for all five spaces: `REQ`/`DEC` owned by the
spec, `TD`/`T`/`CP` by the plan.

**Corrected from the proposal — a hash mismatch is not an automatic refusal.**
"`/build` recomputes it and refuses a stale plan" would refuse on an editorial
typo fix, which by 0045's own rule does not reopen approval. A gate that fires
on non-events is a gate people learn to wave through. So a mismatch requires
looking: `git cat-file blob <pinned-hash>` diffed against the current spec,
then either re-pin (editorial, the common case) or `Needs replan` (behavioral).
`-w` on the original `hash-object` is load-bearing for this — without it the
hash is recorded but the pinned content was never written to the object database
and the diff is impossible. Verified both ends before adopting.

**Kept the shipped wording — "Orphan tasks", not "Unmapped tasks".** 0045 already
shipped `Orphan tasks: None` through the template, `/plan` and the planning
skill. The proposal's synonym is marginally more parallel with "Unmapped
requirements"; one term used consistently across four files beats the better
term used in two of them.

**Honest note on cost.** `planning-and-task-breakdown/SKILL.md` was ~4,600
tokens, just under the ~5,000-token per-skill re-attachment cap
[0037](0037-fixed-session-context-reduced.md) flagged. The first pass took it to
~5,039 — over. Trimming the additions to pointers brought it to ~4,956, which is
under but with almost no headroom left. The bulk went where it belongs:
`plan-quality-gates.md` (~1,720 tokens) and the template (~1,580, up from ~760),
both loaded on demand. The next addition to this skill needs an extraction
first, not more prose.

Measuring the whole catalogue while here: **four skills now exceed the cap** —
`spec-driven-development` ~7,240, `code-review-and-quality` ~6,430,
`api-and-interface-design` ~5,900, `security-and-hardening` ~5,760 — and only
the first was touched by 0045 or this entry. 0037 described this as "two are
near the cap"; it is now four over it, so the condition has drifted since that
entry was written and is no longer confined to the SDLC skills this pass edited.
These are byte/4 estimates rather than tokenizer counts, so treat the ordering as
reliable and the absolute numbers as approximate. Not fixed here: extracting
reference material out of four vendored skills is its own decision, and doing it
inside a pass about planning would bury it.

**Rejected — Spec Kit's mandatory `research.md`, `data-model.md`, `contracts/`
and `quickstart.md` artifacts.** Four documents to keep in sync for work that
one plan section covers. The conditional Contracts and Migration sections carry
the content that actually gets used, inside the document that already gets read
at the gate. Their existence as separate mandatory files is what makes them go
stale.

**Rejected — cc-sdd's rigid time-based sizing and a fresh executor per task.**
Same rejection as [0045](0045-spec-approval-state-change-impact-and-requirement-traceability.md),
for the same reasons: sizing here is XS-XL with recorded exceptions, and
[0031](0031-parallel-executors-via-worktree-isolation.md) resumes one executor
across a workstream specifically to avoid per-task discovery cost.

**Rejected — a `/build`-side or `/review`-side copy of the id rules.** They read
ids; they do not define them. Both point at the reference.

**Revisit if** the spec pin proves noisy in practice — if most mismatches turn
out editorial and the diff step becomes a formality people skip, the pin is
costing more attention than it saves and should narrow to a hash over the
requirement sections alone rather than the whole file.
