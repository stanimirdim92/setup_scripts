# Spec reproducibility eval

Re-run `/spec` against a ticket whose right answer is known, and check it still
finds it.

Every other check in this repo tests the harness's *shape* — a persona declares
its tools, a path is spelled one way, a hook denies a push. None can tell you
whether a change made specs better or worse. That question only has an answer
where the correct output is known independently, and it is known in one place:
a ticket that shipped, whose spec a human has read against the implementation.

## Running it

```bash
python3 run.py --fixture LD-380                      # produce, then judge (~$1.40)
python3 run.py --fixture LD-380 --spec path/to.md    # judge an existing spec (free)
python3 run.py --fixture LD-380 --output ./out       # keep the spec and run metadata
```

Never in CI. It drives the real model and spends tokens; run it when the
harness changes in a way that could move spec quality — a model, a template, a
quality gate, `spec-driven-development`.

## Fixtures

A fixture is a directory under `fixtures/`:

```
fixtures/<TICKET>/
  intake.md            the jira-ticket intake output, frozen
  expectations.json    what the spec must still find, and why
```

`fixtures/` is gitignored except `example/`. Real fixtures carry ticket
content — colleagues' names, design links, comment threads — and this
repository is public. `fixtures/example/` shows the format with invented
tickets; copy its shape.

Intake is frozen rather than re-fetched on purpose. Re-running `jira-ticket`
each time moves two variables at once and makes a regression impossible to
attribute. Refresh the intake deliberately, when the tickets change.

## Expectations

Each carries an `id`, a `why` in plain language, and one predicate:

| Predicate | Meaning |
|---|---|
| `near: [terms]`, `within_lines: N` | every term inside some N-line window |
| `regex: "..."` | matches somewhere (multiline, case-insensitive) |
| `absent_regex: "..."` | must **not** match |
| `kind: "semantic"` | not machine-checkable; printed for human review |

`severity: "should"` reports a miss without failing the run.

`near` exists because presence is not noticing. A spec that says "email"
somewhere has not seen that one ticket promises a notification and another
forbids it; a spec that says both within a few lines has. Every deterministic
predicate is a proxy for a judgment, and a determined spec could satisfy one
without doing the work — which is why `why` is mandatory and the semantic
expectations are not optional to read.

## What a pass means

The findings a human confirmed are still there. It does **not** mean the spec
is good. Nothing here checks whether new requirements are sound, whether the
open questions are warranted, or whether the thing is readable. Read the spec.

## Adding a fixture

Only from a ticket that has shipped **and** whose spec someone has read against
the implementation. Without that reading you are freezing an opinion, not an
answer. Write each expectation from something the reviewer actually confirmed,
and put their reasoning in `why` — a year from now, an expectation without a
rationale gets deleted the first time it fails.
