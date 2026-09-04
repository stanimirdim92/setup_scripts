# Spec Quality Gates

The single source for three things `spec-driven-development` and the gate
commands all need and would otherwise each restate: what makes a requirement
approvable, how approval is recorded, and how a requirement id is traced from
spec to release.

Single-sourced here for the same reason as `reviewer-triggers.md` — five
consumers (`/spec`, `/plan`, `/test`, `/review`, `/ship`) enforcing
copy-pasted versions of one rule set is how the copies start disagreeing.

## 1. Requirements quality — approval-check assertions

`spec-driven-development`'s Approval Check runs these against the spec before it
is presented for approval. The check is the unit test for the English; these are
its assertions.

- **Measurable.** No requirement leans on "fast", "secure", "robust",
  "reliable" or "scalable" without a threshold and a way to measure it. A
  performance criterion names metric, threshold, workload, environment, and
  measurement method.
- **Scenario coverage.** Each requirement covers the cases that apply to it —
  primary, alternate, failure, recovery, boundary — not the happy path alone.
- **Operational concerns are requirements or explicit exclusions**, never
  silence, wherever they apply:
  - authorization and privacy;
  - performance and scale;
  - timeout, retry, idempotency, partial failure;
  - logging, metrics, auditability;
  - migration, mixed-version compatibility, rollback;
  - accessibility and localization.
- **Assumptions validated.** Every assumption surfaced in Phase 1 has been
  confirmed, contradicted, or recorded as a constraint — not left standing
  because nobody objected.
- **No duplicate or conflicting requirements.** Two requirements describing the
  same behavior are one requirement; two requiring different behavior are a
  contradiction to resolve, not to ship.

Judge applicability honestly and include only the concerns this change actually
touches. A column of `N/A` lines is not coverage, it is the appearance of it,
and it buries the entries that matter.

This is a pass over the existing document, not a new artifact. Do not emit a
separate checklist file.

## 2. Approval state

`Status` in the spec's header is the durable record of approval, because a later
session, a compaction boundary, or a downstream stage cannot see what was said
in the conversation where approval happened.

| Status | Meaning | Set by |
|---|---|---|
| `Draft` | Being written, or an `OPEN QUESTION` remains | `/spec`, on creation |
| `Approved` | The human approved this exact content | `/spec`, only after explicit human approval |
| `Needs reapproval` | Approved once, then edited in a way that changes behavior | whichever stage made or discovered the edit |
| `Superseded` | Replaced by a later spec, which names it in `Supersedes` | the superseding spec's `/spec` run |

- `/spec` never sets `Approved` on its own judgment. Explicit human approval is
  the only thing that moves `Draft` → `Approved`. A passing approval check is not
  approval; neither is silence, nor an instruction to continue, nor the absence
  of objections.
- Record `Approved by` as the human identified themselves and `Approved at` as
  the date approval was given. Never invent a name — when none was given, write
  `human (this session)`.
- Any behavioral edit to an approved spec — requirement, scenario, schema,
  contract, invariant, boundary, or Change Impact entry — sets
  `Needs reapproval` in the same edit that makes the change, not at the end of
  the session. Editorial edits (typos, formatting, wording that changes no
  behavior) leave the status alone.
- `/plan` refuses to proceed on any status other than `Approved`, and returns
  the spec to `/spec`. This is a document check, not a memory check: read the
  header from disk rather than trusting that approval was seen earlier in the
  conversation.

## 3. Requirement traceability

Every requirement in a spec that will enter `/plan` carries a stable
`REQ-###` id inside the `### Requirement:` heading form, plus a `Source:` line.
Ids are sequential, assigned once, and **never renumbered after approval** —
every downstream artifact references them, so renumbering silently invalidates
the whole trace. A withdrawn requirement keeps its id and is marked withdrawn
rather than reused. The full id-ownership table — which document owns `REQ`,
`DEC`, `TD`, `T` and `CP` — is in `plan-quality-gates.md` §3.

The chain each id carries:

| Stage | Obligation |
|---|---|
| `/spec` | Assigns the id and its `Source:`. No id, no `/plan`. |
| `/plan` | Maps every requirement to one or more tasks; every task names at least one requirement. Reports `Unmapped requirements: None` and `Orphan tasks: None`. |
| `/build` | Carries the ids in each task packet, so an executor knows which requirement its work answers. |
| `/test` | Reports verification evidence per requirement id, not per file. |
| `/review` | Records findings and evidence against requirement ids. |
| `/ship` | Blocks GO while any requirement lacks both implementation and verification evidence. |

Two failure modes this catches, which prose-reading does not:

- **A dropped requirement.** It was specified, approved, and then no task
  delivered it. Without a coverage map this surfaces in production, not at
  `/plan`.
- **An orphan task.** Work with no requirement behind it is scope the spec
  never asked for. Remove it, or — if the behavior is genuinely needed — return
  a `SPEC CONFLICT` so it gets specified and approved rather than smuggled in
  through the plan.

Neither is resolved by adding a traceability matrix as a separate document. The
coverage table in the plan and the requirement ids in the task packets *are* the
matrix; a third artifact would be a copy that drifts.

## 4. Invariant mechanism proof

Naming a transaction, lock, constraint, retry, or "last write wins" policy is not
proof that an invariant holds. For every cross-row, cross-resource, or concurrent
invariant, explain why the chosen mechanism covers every transition and writer.

The proof must identify:

- the precise invariant, including zero/empty-state semantics;
- every operation that can establish, transfer, violate, or release it;
- the common serialization point or persistence constraint;
- how the mechanism works when no child/entity row exists yet;
- what the application guarantees and what infrastructure guarantees;
- the verification evidence, including a lower-level constraint test when
  infrastructure participates in correctness.

If the mechanism cannot be shown to serialize or reject all conflicting writes,
the invariant design is unresolved. A transaction alone does not imply a common
lock or uniqueness guarantee.

Deriving the transitions to test from an invariant — creation from empty,
creation with related state, updates that establish or transfer it, deletion of
the satisfying entity, deletion of the last one, concurrent writes across rows
or processes — is part of the spec's Testing Strategy, and each transition's
enforcing layer is named there (a persistence constraint may guarantee **at most
one** while application behavior still owes **at least one when applicable**).

## 5. Data lifecycle semantics

When the schema or existing model contains a deletion marker, soft-delete
timestamp, tombstone, archival flag, status, or equivalent lifecycle field, the
spec must define what "delete" means. State whether deletion is hard, soft,
archival, or another transition, and define how deleted records affect reads,
uniqueness, relationships, restoration, invariant calculations, retention, and
tests. Do not propose a deletion marker while leaving deletion behavior as an
implementation detail.
