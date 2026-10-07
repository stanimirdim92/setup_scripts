# The TDD skill is back in the executor

**Context.** ADR 0039 switched `test-driven-development` to explicit use
(`disable-model-invocation: true`) to save tokens. The executor got a compact
copy of its method inside `executor-development-discipline` instead: five
red/green steps and the bug-reproduction rule. Usage over 79 sessions showed
the full skill never ran. The compact copy kept only the cycle. It dropped
the rest of the skill:
- choosing a test level;
- writing good tests and avoiding test anti-patterns;
- the rationalizations that lead to skipping a test.
 The
approver states that tokens are no longer the constraint.

**Decision.**
- `test-driven-development` can be invoked automatically again, in Claude
  Code and in Codex (`allow_implicit_invocation: true`).
- The executor preloads it beside `executor-development-discipline`, and
  `/build` lists both as the baseline. Codex executors load both explicitly.
- `executor-development-discipline` drops its own red/green steps and points
  to the TDD skill. It keeps only what is specific to `/build`. That is the
  packet as the contract, the local test command and verification cadence,
  retries from evidence, commits with trailers, and the completion evidence.
- The skill advises spawning a subagent to write the reproduction test. An
  executor cannot spawn agents, so a note tells it to get the same separation
  by order: write the test before reading the suspected code.

**Cost.** About 3.9k more tokens in every executor's starting context.

Reverses ADR 0039 for `test-driven-development`. `incremental-implementation`
and `code-review-and-quality` stay explicit-only.
