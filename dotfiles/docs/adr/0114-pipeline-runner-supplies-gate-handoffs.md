# The pipeline runner supplies gate handoffs

**Context.** The owner wants the pipeline to run without a stop between
stages. Each stage should also start with a clean context, as after `/clear`.
A command cannot run `/clear`; only the user can. A new `claude -p` session
starts clean, but §Gate handoffs in `target-selection.md` let `/test`,
`/review` and `/ship` accept the previous stage's message only from the same
conversation or from the user. So `batch-fix.py` had to stop after `/build`
(review finding R4), and every stage gap needed the owner.

**Decision.**
- `tools/run/pipeline.py <TICKET>` runs, in the ticket's worktree and one
  fresh `claude -p` session per stage: `/build`, `/test`, `/review`. When the
  review leaves BLOCKER or REQUIRED findings, it runs `/build <TICKET> review
  fixes`, `/test` and `/review` again, up to the review round cap (ADR 0089).
- The runner gives each stage the previous stages' complete messages,
  verbatim, in its prompt. §Gate handoffs accepts that as a third source,
  next to the conversation and the user. The receiving stage still
  reconciles every identity field against git; a mismatch blocks as before.
- The runner reads each result with fixed rules: `BUILD COMPLETE`,
  `VERIFY PASS`, the review count line and the review SARIF file for HEAD.
  Any other result stops the run. It saves every message to
  `<git-common-dir>/handoff/` for the owner to read.
- It starts after an approved, committed plan and stops before `/ship`.
  Spec approval, plan approval and GO stay the owner's. It never pushes.

**Rejected — stages read handoff files themselves.** A stage would then
trust a file it found on disk, which the rule forbids for a reason: the file
can be stale or written by anything. The runner passes exactly the message
the previous session returned, and the stage checks it against git.

**Rejected — a stage starts the next one.** Personas do not dispatch
personas, and a stage that starts the next would keep its own context.

**Cost.** Three headless runs per round, each capped by `--max-budget-usd`.
A ticket that needs every fix round costs up to nine runs.
