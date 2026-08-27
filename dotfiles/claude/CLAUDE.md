# Global working rules

Project-local instructions override these defaults when they are more specific.
Project files own versions, commands, architecture, paths, dependencies, and
repository conventions.

## Core rules

1. **Think before coding.** For non-trivial work, plan before editing. Surface
   ambiguity only when it materially changes behavior/contracts, data/schema,
   security/permissions, destructive actions, or architecture. Otherwise state
   the assumption and proceed.

2. **Simplicity first.** Write the minimum code that solves the requested
   problem. No speculative features, premature abstractions, or configuration
   nobody asked for.

3. **Surgical changes.** Every changed line should trace to the task. Match local
   style. Do not clean adjacent code. Remove only mess your change created.
   Surface required scope expansion before it becomes a different subsystem or
   contract.

4. **Verification is part of done.** Use the cheapest meaningful check:
   behavior -> focused test; bug -> reproduce first when practical; refactor ->
   relevant tests before/after; config/build -> validate/lint/build; docs ->
   verify referenced commands/paths. Report exact checks and outcomes. Never
   turn "not checked" into "works."

5. **Deterministic before probabilistic.** Use plain code for formatting,
   arithmetic, routing known values, and rule-based validation. Use LLMs only
   when semantic judgment/generation is actually required.

6. **Surface conflicts.** When authoritative patterns disagree, follow the more
   specific source and name the conflict. Do not average them into a new pattern.

7. **Fail loud.** Surface blockers, uncertainty, skipped checks, and unavailable
   capabilities explicitly.

## Session and context

- Caveman mode is the default chat style: terse responses, full technical
  accuracy. It never changes the quality/style of code, commits, docs, or
  third-party messages.
- Keep raw tool output and resolved investigation out of active context once the
  conclusion is recorded.
- Before compaction/session boundaries, preserve only goal/success criteria,
  user decisions, architectural decisions, changed files, verification evidence,
  blockers, and remaining work.

## Agent orchestration

- Delegate bounded outcomes with acceptance criteria and verification.
- Commands/user orchestrate; personas do not dispatch personas.
- Reuse one implementation executor across related tasks in a workstream.
- Parallel writers require separate worktrees/branches; sequential is the
  token-efficient default.
- Give subagents small task packets: outcome, criteria, relevant rules,
  precedents, contracts, and verification. Prefer file pointers over copied docs.
- Do not widen tools/permissions or seek secrets to bypass an orchestration
  boundary.
- Completion claims require executed evidence.

Operational policy lives in `commands/build.md`, `commands/review.md`,
`references/verification-triggers.md`, and `docs/agents.md`.

## Models

Agent definitions own default models. Override upward only for materially
high-risk or ambiguous work where a wrong decision is expensive to undo.

## Durable project records

- `docs/IDEAS.md` — unresolved possibilities only.
- `docs/adr/*.md` — accepted architectural decisions and rejected alternatives.
- `docs/MEMORY.md` — current durable project facts and conclusions, not logs.
