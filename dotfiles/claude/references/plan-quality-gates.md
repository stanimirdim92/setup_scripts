# Plan Quality Gates

The plan-side counterpart to `spec-quality-gates.md`: what makes a plan
approvable, how its approval and its spec pin are recorded, and the id rules
that let `/build`, `/review` and `/ship` address the same units of work.

Requirement-id rules and the `REQ-###` chain live in `spec-quality-gates.md` §3
and are not repeated here.

## 1. Plan approval state

The plan carries its own status, for the same reason the spec does: the handoff
line records approval as prose at the bottom of one document, and prose is not
readable by a later session or a downstream gate.

| Status | Meaning | Set by |
|---|---|---|
| `Draft` | Being written, or an Open Question remains | `/plan`, on creation |
| `Approved` | The human approved this exact plan | `/plan`, only after explicit human approval |
| `Needs replan` | Approved once, then materially changed — or its spec pin went stale behaviorally | whichever stage made or discovered the change |
| `Superseded` | Replaced by a later plan for the same work | the superseding plan's `/plan` run |

- `/plan` never sets `Approved` on its own judgment, and a passing approval check
  is not approval. Record `Approved by` as the human identified themselves and
  `Approved at` as the date; never invent a name.
- A material plan change sets `Needs replan` in the same edit: a task added,
  removed or rescoped, a dependency or workstream reassignment, a changed
  decision, a changed contract, or a changed verification command. Fixing a typo
  or clarifying wording does not.
- `/build` refuses to dispatch against anything other than `Approved`.

## 2. Spec revision pinning

A plan is only valid against the spec it was planned from. `Status: Approved`
on the spec proves a human approved *something*; it does not prove the spec
still says what the plan assumed — a spec can be edited without its status
being updated correctly, which is exactly the case this pin catches.

**The pin must be a commit, not a loose blob.** An earlier version of this rule
used `git hash-object -w`, which writes an object no ref points at: `git prune`
deletes it, and it is never transferred by push or clone. The plan was
unverifiable on a second machine and could become unverifiable on the first
(see `../../../docs/adr/0049-durable-spec-pin-and-hook-bypasses.md`).

**When planning starts**, after confirming `Status: Approved`, require the spec
to be committed with no uncommitted edits, then pin the commit that last
touched it:

```bash
git diff --quiet HEAD -- docs/specs/[TICKET]-SPEC.md \
  || echo "spec has uncommitted edits — commit it before planning"
git log -1 --format=%H -- docs/specs/[TICKET]-SPEC.md
```

Record it as `Spec revision: git-commit:<sha>:docs/specs/[TICKET]-SPEC.md`.
Requiring the commit is not extra ceremony: `spec-driven-development`'s
"Keeping the Spec Alive" already says the spec belongs in version control.

**When `/build` starts**, retrieve the pinned content and compare:

```bash
git show <sha>:docs/specs/[TICKET]-SPEC.md > /tmp/spec-pinned.md
diff /tmp/spec-pinned.md docs/specs/[TICKET]-SPEC.md
```

Identical means the plan is current; dispatch proceeds.

A **difference is not automatically a stale plan** — an editorial correction
changes the file without changing behavior, and refusing on that alone would
make the gate something people learn to bypass. Resolve it by reading the diff:

- **Editorial only** (typos, formatting, wording that changes no behavior):
  re-pin the new commit, note it, and proceed. The cheap and common path.
- **Behavioral** (a requirement, scenario, contract, invariant, boundary or
  Change Impact entry differs): stop. Set the plan `Needs replan`, and the spec
  `Needs reapproval` if its status does not already say so.
- **A `Status` line change is never editorial.** `Approved` →
  `Needs reapproval` or `Superseded` is the spec telling you the plan's
  foundation moved. Treat it as behavioral, whatever the rest of the diff says.

Report which path was taken. "The revisions differed and I proceeded" without
the diff is the failure this gate exists to prevent.

**If the sha no longer resolves** — the spec commit was rebased, squashed or
amended away — the pin cannot be checked. Do not guess: treat the plan as
`Needs replan` and re-pin against the current committed spec after confirming
with the human that the requirements did not change in the rewrite.

## 3. Id stability

Three id spaces, one owner each, none reused:

| Id | Lives in | Owner | Meaning |
|---|---|---|---|
| `REQ-###` | spec | `/spec` | A behavior the system must provide |
| `DEC-###` | spec | `/spec` | A material product/domain/contract/lifecycle decision |
| `TD-###` | plan | `/plan` | A technical decision between plausible implementations |
| `T###` | plan | `/plan` | A task |
| `CP-###` | plan | `/plan` | A checkpoint |

`TD-###` rather than `DEC-###` in the plan deliberately: the spec already owns
`DEC-###`, and one id space split across two documents makes "see DEC-002"
ambiguous exactly when someone is trying to trace a decision.

Ids are **stable after approval and never renumbered.** `/build`, `/review` and
`/ship` all address work by these ids, so renumbering silently invalidates every
report that referenced the old numbers. A task that is dropped or replaced keeps
its id and is marked superseded (`~~T003~~ superseded by T007`); the next task
takes the next unused number.

## 4. Approval checks before presenting a plan

- Every `REQ-###` maps to at least one task, or to explicit verification-only
  evidence when the requirement is already satisfied by existing behavior that
  the change must preserve. `Unmapped requirements: None`.
- **A withdrawn requirement stays in the coverage table**, marked withdrawn,
  rather than being deleted from it. Deleting the row makes a dropped
  requirement indistinguishable from one that was never specified.
- Every task carries requirement ids, under one of exactly two shapes:
  - a **delivery task** names at least one `REQ-###` — the behavior it
    delivers;
  - a **spike** names the `TD-###` it resolves *and* the `REQ-###` ids it
    unblocks, because a spike with no downstream requirement is investigation
    for its own sake.
  A task fitting neither is scope the spec never asked for.
  `Orphan tasks: None`.
- **Every risk mitigation names the task or checkpoint that performs it.** A
  mitigation with no owner is a hope, and a plan whose risk table is entirely
  hopes has not mitigated anything. This fails the approval check.
- Every verification command comes from repository evidence — the recon report,
  package manifests, CI config — never guessed.
- In a full plan, Open Questions reads `None`; a compact plan omits the section
  when none exist. Anything about feature behavior is a `SPEC CONFLICT`, not an
  open question.

## 5. Bounded technical spikes

Some HOW questions cannot be answered read-only: whether an index supports a
query at real cardinality, whether a library behaves as documented under the
repository's configuration, which of two migration strategies holds a lock.
Leaving these as Open Questions blocks the plan; guessing hides the risk inside
an implementation task, which the planning boundary forbids.

Sanctioned instead: a spike task in the plan, executed by `/build` like any
other task.

```markdown
- [ ] T000 (S, ws-research, deps: —) [TD-002, unblocks REQ-004]: Prove whether
      the proposed index supports the target query
```

Its acceptance criteria state the evidence to produce, the comparison to run,
and the threshold that decides — not "investigate and report back". A spike:

- produces evidence and resolves a named `TD-###`; it does not change production
  behavior, and it is not a licence to start implementing;
- is gated by a checkpoint before any dependent task runs, so the decision is
  made before work is built on it;
- happens during `/build`, not during `/plan`. Planning does not investigate.

**A spike is only for technical uncertainty.** If the outcome could change what
the system must do — an acceptance criterion, a contract, a lifecycle rule —
that is a `SPEC CONFLICT` and goes back to `/spec`, however technical the
question looks. The test: could a reasonable answer to this question change a
`REQ-###`? Then it is not a spike.
