# Agent orchestration

Personas own a role; skills own reusable methodology/policy; commands own routing
and gates. Personas never dispatch other personas.

## Personas

| Persona | Role | Default use |
|---|---|---|
| `executor` | implementation | `/build`, one resumable instance per workstream |
| `test-engineer` | independent verification | `/test` when risk/request warrants it |
| `code-reviewer` | general code review | every `/review` |
| `security-auditor` | security trust-boundary review | triggered `/review` only |
| `distributed-systems-reviewer` | distributed failure-semantics review | triggered `/review` only |

## Pipeline

```text
/spec -> /plan -> /build -> /review -> /ship
                         \
                          -> /test -> /review
                             when required
```

### `/build`

- one executor per workstream;
- resume it for later tasks in that workstream;
- executor implements, tests, verifies, and makes scoped local commits;
- sequential execution is the token-efficient default;
- concurrent writers require isolated worktrees and genuinely independent,
  dependency-ready workstreams;
- `/build` reports `BUILD COMPLETE` and verification evidence.

Source: `../commands/build.md`.

### `/test`

Independent VERIFY is **risk-triggered, not mandatory**.

`/review` evaluates `../references/verification-triggers.md`. If a trigger
matches, the exact candidate must have `VERIFY PASS` before review proceeds.

`/test` dispatches one `test-engineer`, which may add test-only changes but never
production fixes.

Source: `../commands/test.md`.

### `/review`

`/review` requires the current `BUILD COMPLETE` candidate, decides whether
independent verification is required, then dispatches:

- `code-reviewer` always;
- specialists only when `../references/reviewer-triggers.md` matches.

At most two reviewers run concurrently. Reviewer findings remain separate and
are mapped to canonical `BLOCKER` / `REQUIRED` / `ADVISORY` dispositions.

A valid `VERIFY PASS` may advance the BUILD candidate only through declared,
passing test-only commits. `/review` verifies that narrow delta; any production
or undeclared post-BUILD change blocks the gate.

Source: `../commands/review.md`.

### `/ship`

No fan-out. `/ship` synthesizes the current REVIEW handoff, its verification
status, release-readiness evidence, unresolved findings, and rollback plan into
GO / NO-GO / SHIP BLOCKED.

Source: `../commands/ship.md`.

## Context discipline

A subagent receives a task packet, not the parent conversation.

Implementation packets normally contain outcome, acceptance criteria,
dependencies/workstream, expected scope, verification, relevant rule/precedent
pointers, and shared contracts/invariants.

Review packets are smaller: integrated diff, one-line goal, relevant acceptance
criteria, and build/verify evidence.

Prefer authoritative pointers over copied spec/plan text.

## Models and cost

Use persona defaults for routine work. Escalate upward only when a specific
high-impact risk is materially ambiguous.

Fresh agents pay fresh context/discovery cost. Reuse the executor inside a
workstream and avoid parallelism unless wall-clock benefit is worth that cost.

## Direct invocation

Use a persona directly only when the user explicitly wants that perspective
outside the pipeline, e.g. security review, distributed-systems review, code
review, or test design. `executor` remains `/build`-only.
