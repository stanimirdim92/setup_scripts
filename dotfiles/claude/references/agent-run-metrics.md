# Agent Run Metrics

Use lightweight actual measurements to tune the coding harness from real runs
instead of intuition.

## BUILD signals

Record when available:

- selected tasks
- workstreams
- fresh executor dispatches
- executor resumes
- model-tier overrides
- implementation verification failures that caused rework
- human redirects/decisions during BUILD
- directly required scope expansions
- actual token/cost/duration reported by the runtime

Never estimate token usage, cost, or elapsed time when the runtime does not
expose it.

## Where the exposed numbers actually come from

- `/cost` — session cost and duration.
- The statusline payload — `cost.total_cost_usd`, `cost.total_duration_ms`,
  `context_window.used_percentage`. Read before BUILD and at BUILD COMPLETE;
  the delta is that run.
- The session transcript — `~/.claude/projects/<slug>/<session-id>.jsonl`, the
  only source for per-request tool batching and cache-token totals. Each
  assistant turn carries `message.usage` with `input_tokens`, `output_tokens`,
  `cache_read_input_tokens`, and `cache_creation_input_tokens`.

`tools/run-metrics.sh` in this repo reports batching, tokens, and the
main-session/subagent split from a transcript, with `--since`/`--until` to scope
one BUILD.

**Counting tool batching correctly.** Parallel tool calls are written as
separate assistant records that share one `requestId`. Counting calls per record
reports a mean of 1.0 and zero batching no matter what actually happened — group
by `requestId` instead. A measurement claiming "zero batched" is usually this
mistake rather than a finding.

## Downstream quality signals

Across the full pipeline, useful signals are:

- VERIFY failures that found a production defect missed during BUILD
- REVIEW NO-GO findings after VERIFY PASS
- number/type of blocking findings
- triggered-gate loop count: REVIEW → TEST → REVIEW
- defect rework loop count: TEST/REVIEW → BUILD → REVIEW, with another TEST
  when the new candidate still matches a verification trigger
- repeated task splitting or workstream regrouping caused by a bad plan

These are signals, not targets. Do not game them by suppressing tests, findings,
or necessary human decisions.

## What to learn after multiple runs

After roughly 10–20 comparable tickets, look for:

- fresh-agent vs resumed-agent cost/quality differences
- task sizes that most often cause rework or scope expansion
- workstream boundaries that preserve useful context vs become too large
- model overrides that materially improved outcomes
- defects that repeatedly escape BUILD into VERIFY
- reviewer findings that repeatedly should have been caught earlier

Use the evidence to change task sizing, workstream rules, model defaults, or
verification gates. Do not change global policy from one unusual run.

## Runtime catalog audits

When reviewing plugin/skill context cost, record:

- Claude Code version;
- enabled versus merely installed plugins;
- `claude plugin details` projected always-on and on-invoke costs;
- lifetime `pluginUsage` / `skillUsage` counters;
- explicit skill, agent, and MCP calls in a stated recent transcript window.

Projected token cost is a comparison proxy, not billed usage. Hook counters can
show automatic activity rather than deliberate capability use, and deferred MCP
schemas may project zero always-on cost even when the server is useful.

## Persistence

The default is to include the compact metrics in command output.

Do not create a new metrics directory/file inside every project by default.
Persist run metrics only when the project already designates a telemetry/log
location or the user explicitly asks for durable tracking.
