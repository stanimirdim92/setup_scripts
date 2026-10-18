# Unattended pipeline with batched decisions (proposed)

**Status.** Proposed. Nothing here is built yet; the owner decides the open
points below.

**Context.** The owner wants Jira → `/spec` → `/plan` → `/build` automated,
and named the blocker: decisions. Today each stage stops when it hits one.
`batch-spec.sh` already writes Draft specs unattended, but each Draft then
waits on questions asked one at a time, in separate sessions, whenever the
owner happens to look. Overnight fixes (ADR 0108) cover the end of the
pipeline. The middle still waits on a person for every question.

**Proposal.**

1. *Night 1, `/spec` for a batch.* Each job writes its Draft spec. Every open
   question goes into the spec's `## Open Questions`, numbered, each with
   options and a recommended default. The runner gathers them into one
   morning message across all tickets (made-up example):

   ```text
   AB-10 Export advertisers
     1. Soft-deleted advertisers in the export?  A) never (recommended)  B) behind a filter
     2. Format?  A) CSV (recommended)  B) XLSX  C) both
   AB-11 Retry enrichment
     3. Retries before "failed"?  A) 3 (recommended)  B) 5
   Reply e.g. "1A 2C 3A, approve AB-10 AB-11", or "defaults".
   ```

2. *One reply.* The owner answers every question at once. The runner writes
   each answer as a `DEC-###` with "decided by <owner>, <date>". It approves
   only the specs the reply names; approval stays the owner's
   (`spec-quality-gates.md` §2, unchanged).
3. *Night 2, `/plan` → `/build` → `/review` → overnight fixes* for each
   approved spec, in its own worktree. A plan that passes `check-plan.py` and
   raises no new question goes straight to `/build`. A plan that raises one
   joins the next morning's batch instead of blocking.
4. *Morning 2.* Each ticket stops before `/ship` with its review, VERIFY and
   Risk lines. The owner reads and ships. No push, no PR, unless turned on.

**Open points for the owner.**
- Can the owner's spec approval also approve a clean plan (step 3)? The
  alternative is a second short reply on the plans.
- Is "defaults" an allowed answer for every question? Or must questions on a
  High-risk path (`risk-tiers.md`) be answered one by one?
- Where does the morning message arrive: the terminal, a file, or a push
  notification?
- Should a draft PR be opened at the end? The harness opens none today.

**Cost.** Night 1 costs what `batch-spec.sh` costs today. Night 2 costs one
`/plan`, `/build`, `/review`, and `/test` run per ticket, plus at most two
fix rounds, each capped by `--max-budget-usd`. The saving is the owner's
time: one reply a day instead of a stop at every question.
