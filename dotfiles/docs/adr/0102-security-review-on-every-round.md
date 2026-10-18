# Security review runs on every round

**Context.** `security-auditor` ran only when the reviewer triggers matched a
security boundary, and on "Always a person" paths (ADR 0096). `code-reviewer`
checked security as one of its five areas on every review. A change that
crossed a boundary without looking like it could get only that lighter check.
Anthropic runs a separate security review on every pull request (claude.dev,
"Solving code review at Anthropic", 2026-10, layer 3). The owner chose the
same: "run on every pass".

**Decision.**
- `security-auditor` runs on every `/review` round, beside `code-reviewer` and
  `blind-reviewer`, with the same packet as `code-reviewer`.
- It goes deepest where the diff changes a security boundary. On a diff that
  touches none, it says so in one line and stops.
- In a later round (ADR 0089) it reviews the new diff.
- `distributed-systems-reviewer` stays triggered, and also runs on "Always a
  person" paths.

**Cost.** One more Opus run at high effort per review round, including docs
and copy changes. A no-boundary diff keeps that run short.

Amends ADR 0096 (the forced-specialist rule now adds only
`distributed-systems-reviewer`).
