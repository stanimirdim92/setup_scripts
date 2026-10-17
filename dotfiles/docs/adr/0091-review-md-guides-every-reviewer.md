# A project REVIEW.md guides every reviewer

**Context.** The reviewers knew the harness's general bar and the project's
`CLAUDE.md` rules. They did not know what failure looks like in one
repository: which mistake leaks data, which paths are generated, how many
nits are worth a reader's time. Anthropic's Claude Code team gives that
knowledge to its reviewer through a `REVIEW.md` that code owners write
(claude.dev, "Solving code review at Anthropic", 2026-10).

**Decision.**
- `/review` reads the project's `REVIEW.md`: the one at the repository root,
  and any in a directory the diff touches.
- Every reviewer gets it, `blind-reviewer` included. It describes the area,
  not the change, so it does not break the blind review.
- Its failure definitions, skip list and finding rules apply, and reviewers
  follow its summary format (`component-response-contracts.md` §Shared
  conventions).
- `references/templates/review.md` is the starting shape: what failure looks
  like, what to always check, what to skip, the finding rules (evidence as
  `file:line`, a nit cap, `pre-existing`), and a summary that starts with a
  count.
- Without a `REVIEW.md`, `/review` says so in its report.

**Cost.** The file loads into every reviewer's context, so it must stay short.
A project-specific `REVIEW.md` lives in that project, not in this public
repository.
