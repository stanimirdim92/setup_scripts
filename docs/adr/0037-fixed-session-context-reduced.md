# Fixed session context reduced: compact prompts and settings

**Decision.** Compressed the always-loaded and per-dispatch prompt baseline:
`CLAUDE.md` (~7.6KB to ~3.4KB), `commands/build.md`, `commands/test.md`,
`commands/review.md`, `commands/ship.md`, `agents/executor.md`,
`agents/distributed-systems-reviewer.md`, `docs/agents.md`. Commands route and
gate; personas and skills own execution methodology, and duplicated
testing/review methodology was removed from the command prompts that had
restated it.

Settings changes: `CLAUDE_CODE_AUTO_COMPACT_WINDOW` 400000 to 200000;
`autoMemoryEnabled` false; the experimental Agent Teams env flag removed.

**Why each.** `CLAUDE.md` is loaded unconditionally on every session, and
`build.md`/`executor.md` are paid on every implementation dispatch, so they are
the highest-leverage files in the repo per token. All seven numbered rules, the
caveman session default, the compaction-preservation list, and the orchestration
invariants survive the compression — what was cut is prose, the per-rule
"*Catches:*" one-liners, and the Project Structure listing, not policy.

`autoMemoryEnabled` off because this harness already keeps durable facts in
versioned `docs/MEMORY.md`; two memory systems with no defined precedence is the
conflict rule 6 forbids, and only one of them is reviewable in a diff. The Agent
Teams flag is removed because `docs/agents.md` states no command depends on that
capability, so it was an experimental surface enabled for nothing.

**Honest note on two items.** The bundle described "enable tool search
explicitly" as a saving; it is not one. MCP tool schemas are already deferred by
default and `ENABLE_TOOL_SEARCH` only matters when set to `false`. Setting it
`true` documents intent and guards against a future default change — it does not
reduce current usage. And halving the auto-compact window makes compaction happen
sooner and more often: it lowers per-request context in long sessions but spends
more summarization passes and loses more fidelity per session. It is a trade, not
a free win.

**Rejected — measure the saving from prompt size.** Prompt bytes are a proxy, not
a measurement, and the largest real saving in this pass came from not spawning a
subagent at all ([0035](0035-independent-verify-made-risk-triggered.md)), which
prompt size cannot show. Judge this from
`references/agent-run-metrics.md` over 5-10 representative tasks.

**Rejected — compress the skills too.** Skills load only on invocation, so their
cost is already conditional, and two are near the 5,000-token per-skill
post-compaction re-attachment cap where truncation would be silent. Compressing
the unconditional baseline first is the better ratio.

**Rejected — remove plugins in the same pass.** Untested here and independent of
prompt size; bundling it would confound the before/after metrics this ADR asks
for.
