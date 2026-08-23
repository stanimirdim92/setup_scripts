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

## Downstream quality signals

Across the full pipeline, useful signals are:

- VERIFY failures that found a production defect missed during BUILD
- REVIEW NO-GO findings after VERIFY PASS
- number/type of blocking findings
- rework loop count: BUILD → TEST and BUILD → TEST → REVIEW
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

## Persistence

The default is to include the compact metrics in command output.

Do not create a new metrics directory/file inside every project by default.
Persist run metrics only when the project already designates a telemetry/log
location or the user explicitly asks for durable tracking.
