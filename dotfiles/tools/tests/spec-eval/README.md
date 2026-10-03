# Spec reproducibility eval

Re-run `/spec` against a ticket whose right answer is known, and check it still
finds it.

Every other check in this repo tests the harness's *shape* — a persona declares
its tools, a path is spelled one way, a hook denies a push. None can tell you
whether a change made specs better or worse. That question only has an answer
where the correct output is known independently, and it is known in one place:
a ticket that shipped, whose spec a human has read against the implementation.

## Quick start: a deployed ticket

You need the Jira ticket, its deployed spec, and the project checkout.

```bash
cd /var/www/html/personal/setup_scripts/dotfiles/tools/tests/spec-eval

# Once per ticket: freeze the Jira intake, store the deployed spec as the
# reference, and find the commit before the spec was written.
python3 run.py --new LD-441 --repo /var/www/html/leadbuster \
    --reference docs/specs/LD-441-SPEC.md

# After any harness change: write a fresh spec on the old code, compare.
python3 run.py --fixture LD-441 --repo /var/www/html/leadbuster --output ./out-441
```

`--new` runs the `jira-ticket` skill once (Jira MCP must work in a plain
`claude` session) and saves its output as `intake.md`. Pass `--intake FILE`
to use a saved intake instead, or `--at <commit>` when the spec file was not
added in its own commit. The base commit is the parent of the commit that
first added the spec, so the run sees the code as `/spec` first saw it.

A run reports **reference terms named**: of the concrete terms the deployed
spec names in backticks (parameters, columns, classes, routes), how many the
fresh spec also names, and which it missed. It is a recall figure, like plan
recall. It says whether a harness change made specs better or worse at naming
the right things; it cannot say whether a spec is good. Read `out-441/` next
to the reference.

To make a finding permanent, edit `fixtures/LD-441/expectations.json`: change
its `severity` from `should` to `must`, or delete a term that does not matter.

## Running it

```bash
python3 run.py --fixture LD-380                      # produce, then judge (~$1.40)
python3 run.py --fixture LD-380 --spec path/to.md    # judge an existing spec (free)
python3 run.py --fixture LD-380 --output ./out       # keep the spec and run metadata
python3 run.py --fixture LD-441 --repo ~/code/leadbuster   # repo-backed: the project at the fixture's commit
```

A fixture with a `"repo": {"at": "<commit>"}` block runs against the project
as it was at that commit. `--repo` names the checkout; `--at` overrides the
commit. The files are exported with `git archive`: no `.git`, no history, so
the run can see neither the shipped implementation nor the final spec.
Gitignored files are absent, which `/spec` does not need. The project keeps its
own `.claude/` and `CLAUDE.md`; the harness is added beside them.
`test_produce.py` covers the layout and runs in CI.

Never in CI. It drives the real model and spends tokens; run it when the
harness changes in a way that could move spec quality — a model, a template, a
quality gate, `spec-driven-development`.

## Two kinds of fixture, and why it matters

A fixture fixes the *evidence available*, and that changes what the right answer
is. LD-380 exists twice:

- **`LD-380-no-repo`** — empty project. Measures how `/spec` behaves when
  repository evidence is absent: does it record absence honestly, escalate what
  it cannot settle, and decline to decide what belongs to the approver.
- **`LD-380`** — requires the application repository. Measures what only
  repository evidence can establish, and its expectations are in places the
  *inverse* of the other fixture's.

That inversion is the lesson, not an inconsistency. With no repository, the
contradiction between a spike promising an email and a story forbidding one is
a question to raise. With the repository, it is answerable — the email belongs
to a different, pre-existing endpoint — and raising it instead of resolving it
is the weaker spec. Likewise: absent evidence must be recorded as absent, and
present evidence must be read.

The sharpest single expectation is `duplicate-signals-match-the-code`. The
ticket lists four duplicate signals; the code being reused implements two. A
spec written without reading that code specifies all four faithfully and sends
an executor to build a path nobody asked for. Only a repository-backed run can
catch that, and no amount of care in a repo-less one substitutes.

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

## Building a fixture from a shipped ticket

A ticket that went through the pipeline already holds its answer key: every
commit that revised the spec after its first draft is a correction a human
made. A fresh `/spec` that makes those corrections on its own has improved;
one that misses them has not.

1. **Pick the commit.** The parent of the ticket's first spec commit, so the
   project is as `/spec` first saw it:
   `git log --reverse --format=%h --grep LD-441 -- docs/specs | head -1`, then
   add `^`.
2. **Freeze the intake.** Run `jira-ticket LD-441` and save its output as
   `fixtures/LD-441/intake.md`. Do not edit it.
3. **List the corrections.** `git log --format='%h %s' --grep LD-441 -- docs/specs`
   shows every spec revision. `git show <sha> -- docs/specs` shows what changed.
4. **Write one expectation per correction you still agree with**, with the
   reason in `why`. Prefer `near` or `regex`; use `kind: semantic` when no
   pattern can stand in for the judgment.
5. **Check the expectations against the shipped spec**, free:
   `run.py --fixture LD-441 --spec <final spec>`. Every `must` passes, or the
   expectation is wrong. Then run them against the first draft
   (`git show <first-spec-sha>:docs/specs/LD-441-SPEC.md`): the corrections
   should fail there, or they test nothing.

## Adding a fixture

Only from a ticket that has shipped **and** whose spec someone has read against
the implementation. Without that reading you are freezing an opinion, not an
answer. Write each expectation from something the reviewer actually confirmed,
and put their reasoning in `why` — a year from now, an expectation without a
rationale gets deleted the first time it fails.
