# Multi-agent rules enforced by the harness; parallel-when-safe replaces sequential-by-default

**Decision.** Five changes to the multi-agent layer, made together because they
share one motive: every rule that governed how agents run was instruction-only,
and the one lever that buys speed was pointed the wrong way.

1. **Nesting is structurally impossible.** `settings.json` sets
   `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=1`. "Personas never dispatch personas"
   was true only because all six persona files list `tools:` explicitly and
   none grants `Agent`; a persona that omitted `tools:`, or a built-in agent,
   inherited three levels of nesting by default.
2. **`/build` dispatches in parallel whenever every condition holds**, and
   queues a workstream the moment any condition is unmet *or unproven*. The
   conditions are unchanged from [0054](0054-executor-concurrency-condition-gated-not-capped.md);
   only the default flips. This partially supersedes 0054's "sequential is the
   token-efficient default" and [0031](0031-parallel-executors-via-worktree-isolation.md)'s
   economics framing, which still hold as facts (parallelism costs tokens) but
   no longer decide the default.
3. **Writers may commit and tag locally; they can never push.** `executor` and
   `test-engineer` carry an agent-scoped `PreToolUse` hook,
   `hooks/block-agent-push.sh`, that hard-denies every spelling of `git push`
   (aliases, typos, global options) and the `gh` commands that push or publish
   (`pr create`, `pr merge`, `release create`, `repo sync`). Local tags
   (release/commit tagging) are newly allowed; "tag" is removed from the
   not-authorized lists in `executor.md`, `test-engineer.md`,
   `executor-development-discipline`, and `/test`. This amends
   [0033](0033-canonical-disposition-and-scoped-commit-authority.md)'s list.
4. **A handoff is gated, not trusted.** The same two personas carry a `Stop`
   hook (`SubagentStop` at runtime), `hooks/require-handoff-report.sh`, that
   blocks the agent from finishing — once — unless its final report carries
   verification commands with outcomes, a commit id or an explicit no-commit
   reason, and the working-tree state.
5. **Read-only personas have a turn cap.** `repo-recon` `maxTurns: 40`; the
   three reviewers `maxTurns: 60`. Each persona states that a capped run is
   reported as partial under its existing "Not surveyed" / "Not verified"
   section, never as complete or clean.

## Why parallel-when-safe is not "sacrifice quality for speed"

The request behind this ADR was: use more agents to finish faster, but never at
the cost of quality. The first instinct — raise the nesting depth — would have
done the opposite. Depth lets an executor spawn sub-executors that receive no
task packet from `/build`, whose diffs and evidence never reach the
orchestrator's report, and whose code `/review` sees without anyone having
scoped it. Depth buys no speed either: elapsed time falls with *width* (how many
executors run at once), and width was already uncapped.

So the lever is the default, not the limit. 0054 established that the five
conditions, not a number, are what make concurrent execution correct. If that is
true, then a workstream satisfying all five is exactly as safe run concurrently
as sequentially — the sequential default was buying token savings, not
correctness. Flipping it trades tokens for wall-clock on precisely the work
where the trade is free of risk, and leaves everything else where it was: a
condition in doubt is a condition unmet, and that workstream queues.

The fixture cases `build_shared_db` and `build_independent` in
`tools/tests/workflow/run.py` pin both halves: a shared test database must not
fan out; genuinely isolated workstreams must.

## Why enforcement moved from instruction to hook

[0044](0044-config-security-hardening-pass.md) and
[0049](0049-durable-spec-pin-and-hook-bypasses.md) established the principle
for the main session: a guarantee the config states should be one the harness
enforces. The subagent layer had not caught up. "Never push" was a sentence in
two persona files while the global `warn-force-push.sh` lets a plain push
through on the web surface without asking. "Completion claims require executed
evidence" was a sentence in `CLAUDE.md` while `/build` accepted whatever the
executor's last message said.

Agent-scoped hooks exist for exactly this — a `PreToolUse` or `Stop` hook that
runs only while that persona runs — and they were unused. Both new hooks follow
0049's rule that a guardrail nothing tests is a guardrail nobody has checked:
`tools/test-hooks.sh` covers every push spelling plus the allow cases that
matter as much (commit, tag, fetch, `gh pr view`), and
`tools/test-handoff-hook.sh` covers complete, partial, claim-only, second
attempt, unknown agent, and unreadable transcript.

## Rejected alternatives

**Rejected — nesting depth 3.** See above: no speed, and it defeats the
review chain. Depth 1 also protects against a future persona that forgets its
`tools:` line.

**Rejected — executors do not commit.** Considered when the push block was
requested. Local commits are the unit `/review` identifies the candidate by,
the unit `/ship` verifies as unchanged, and the only way parallel worktrees
integrate. Removing them would have made change 2 impossible and would not have
added review coverage: nothing reaches the remote until a human pushes.

**Rejected — a "clean working tree" check in the handoff hook.** Simpler than
parsing the report, but `test-engineer` is explicitly told to preserve
unrelated pre-existing working-tree changes, so a clean-tree gate would block
correct behavior. The hook checks the report's shape — the sections the persona
already promises — and says so in its header: it catches a skipped section, not
a lie.

**Rejected — hook denies `git tag`.** The user wants release/commit tagging from
the executor. A local tag is as reviewable and reversible as a local commit;
pushing it is a push and is denied.

## Consequences

- Wide fan-out is now the expected behavior for a plan whose workstreams the
  repository evidence shows to be independent and runtime-isolated. Most
  projects will still see small effective fan-out for the reason 0054 gave:
  shared databases and queues fail condition 4. The completion report keeps
  saying which condition each queued workstream failed.
- Token spend per build rises where fan-out rises. 0031's economics are
  unchanged; the trade is now made deliberately.
- An executor that pushes now gets a hook denial with the reason in its
  context, and an executor that returns "Done." gets one block asking for the
  report sections. Both are visible in the subagent transcript.
- `maxTurns` values are first guesses. `tools/run-metrics.sh` reports turn
  counts from transcripts; tune the caps from a few real runs rather than
  from intuition.
- The workflow runner grows two stages (`build`, `review`) and two output
  fields (`dispatch`, `reviewers`). Its cases assert the orchestration
  *decision*, not dispatch itself — the runner grants no `Agent` tool.
