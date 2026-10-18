# Repeated findings are fixed at the source

**Context.** Anthropic fixes a finding the reviewer keeps raising "at the
source: the skill, a lint rule, `CLAUDE.md` or `REVIEW.md`" (claude.dev,
"Solving code review at Anthropic", 2026-10, layer 1). In the harness, the
same mistake could be found on ticket after ticket, fixed each time, and
never prevented. `review-noise.py` (ADR 0093) counted findings per reviewer
but could not tell that two findings were the same kind of defect.

An example: three tickets in a row each get a finding that a new query skips
the tenant scope, and each is fixed. A fourth ticket
will get it too, unless a rule stops it at the source.

**Decision.**
- Every review finding carries a `class` in the SARIF file: a short slug for
  the kind of defect, such as `missing-tenant-scope`. `/review` lists the
  names already used (`review-noise.py --classes`) and reuses one when it
  fits.
- `review-noise.py --repeats` lists classes found in 3 or more tickets. Many
  findings on one ticket count once. Each class gets an action. Mostly fixed
  means fix at the source. Mostly refuted means stop reporting it. Still open
  means wait.
- `/ship` runs it. For each repeated class this ticket also raised, it
  proposes one change with exact text under "Fix at the source". It picks the
  first that fits: a rule in the project's own linter, a REVIEW.md "Always
  check" line, a CLAUDE.md line, or a REVIEW.md "Do not report" line.
- The owner accepts or declines. `/ship` never edits those files, and a
  proposal never blocks GO.
- `review-noise.py` moves to `skills/code-review-and-quality/scripts/` so
  `/review` and `/ship` can run it from `~/.claude`.

**Cost.** One short script run in `/review` and in `/ship`, and one property
per finding. The proposals start after three tickets share a class.
