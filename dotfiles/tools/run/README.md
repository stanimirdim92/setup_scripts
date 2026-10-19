# run — tools you use during ticket work

These help while you work on tickets. They are optional: the pipeline
(intake → `/spec` → `/plan` → `/build` → `/review` → `/ship`) works without them.

| File | What it does | Run |
| --- | --- | --- |
| `batch-fix.py` | Overnight: for every ticket whose last review left BLOCKER or REQUIRED findings open, runs `/build <TICKET> review fixes` in the worktree at the reviewed commit, and stops. Skips at the round cap, when the candidate moved, or when the checkout is not one ticket's alone (ambiguous, shared, dirty, detached or on main). Locks each checkout for the whole job. A job counts as built only on a BUILD COMPLETE line and a new commit; it saves that message to `<TICKET>-BUILD-COMPLETE.md` for you to paste into `/test`, then `/review`. BUILD BLOCKED or a CLI error fails it and the exit is non-zero. Never reviews, pushes or ships. | `dotfiles/tools/run/batch-fix.py --dry-run` |
| `pipeline.py` | Runs `/build`, `/test` and `/review` for one ticket, each in a fresh `claude -p` session, and passes each stage the previous messages verbatim. Review findings start a fix round, up to three reviews. Moves on only on BUILD COMPLETE, VERIFY PASS and a review count line with its review file; anything else stops it. Saves every message under `<git-common-dir>/handoff/`. Stops before `/ship`; never pushes (ADR 0114). The project's settings must allow the test commands, because `-p` sessions cannot ask. | `dotfiles/tools/run/pipeline.py <TICKET> --dry-run` |
| `run-metrics.sh` | Reads a finished session's transcript and reports what it cost: tokens, how well tool calls were batched, large file reads, and signs of trouble. `--row` prints a line for the observation log. | `dotfiles/tools/run/run-metrics.sh --help` |
