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

- `/plan` never sets `Approved` on its own judgment, and a passing closure check
  is not approval. Record `Approved by` as the human identified themselves and
  `Approved at` as the date; never invent a name.
- A material plan change sets `Needs replan` in the same edit: a task added,
  removed or rescoped, a dependency or workstream reassignment, a changed
  decision, a changed contract, or a changed verification command. Fixing a typo
  or clarifying wording does not.
- `/build` refuses to dispatch against anything other than `Approved`.

## 2. Spec revision pinning

A plan is only valid against the spec it was planned from. `Status: Approved` on
the spec proves a human approved *something*; it does not prove the spec still
says what the plan assumed — a spec can be edited without its status being
updated correctly, which is exactly the case this pin catches.

**When planning starts**, after confirming the spec reads `Status: Approved`,
pin its content:

```bash
git hash-object -w docs/specs/[TICKET]-SPEC.md
```

Record the result as `Spec revision: git-blob:<hash>`. Use `-w` so the blob is
written to the object database — without it the hash is recorded but the pinned
content cannot be recovered later, which makes the mismatch unresolvable.

**When `/build` starts**, recompute:

```bash
git hash-object docs/specs/[TICKET]-SPEC.md
```

A match means the plan is current; dispatch proceeds.

A **mismatch is not automatically a stale plan** — an editorial correction
changes the hash without changing behavior, and refusing on that alone would
make the gate something people learn to bypass. Resolve it by looking:

```bash
git cat-file blob <pinned-hash> > /tmp/spec-pinned.md
diff /tmp/spec-pinned.md docs/specs/[TICKET]-SPEC.md
```

- **Editorial only** (typos, formatting, wording that changes no behavior):
  re-pin the new hash in the plan, note it, and proceed. This is the cheap path
  and it is the common one.
- **Behavioral** (a requirement, scenario, contract, invariant, boundary or
  Change Impact entry differs): stop. The plan is stale — set the plan to
  `Needs replan`, and the spec to `Needs reapproval` if its status does not
  already say so. Do not dispatch against a plan built on requirements that have
  since changed.

Report which path was taken. "The hashes differed and I proceeded" without the
diff is the failure this gate exists to prevent.

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

## 4. Closure checks before presenting a plan

- Every `REQ-###` maps to at least one task, or to explicit verification-only
  evidence when the requirement is already satisfied by existing behavior that
  the change must preserve. `Unmapped requirements: None`.
- Every task maps to a `REQ-###`, a `TD-###`, or a named delivery concern
  (migration, rollout, contract stabilization). `Orphan tasks: None`. A task
  that maps to none of those is scope the spec never asked for.
- **Every risk mitigation names the task or checkpoint that performs it.** A
  mitigation with no owner is a hope, and a plan whose risk table is entirely
  hopes has not mitigated anything. This fails closure.
- Every verification command comes from repository evidence — the recon report,
  package manifests, CI config — never guessed.
- Open Questions reads `None`. Anything about feature behavior is a
  `SPEC CONFLICT`, not an open question.

## 5. Bounded technical spikes

Some HOW questions cannot be answered read-only: whether an index supports a
query at real cardinality, whether a library behaves as documented under the
repository's configuration, which of two migration strategies holds a lock.
Leaving these as Open Questions blocks the plan; guessing hides the risk inside
an implementation task, which the skill's guardrails forbid.

Sanctioned instead: a spike task in the plan, executed by `/build` like any
other task.

```markdown
- [ ] T000 (S, ws-research, deps: —) [TD-002]: Prove whether the proposed
      index supports the target query
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
