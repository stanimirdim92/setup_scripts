# run — tools you use during ticket work

These help while you work on tickets. They are optional: the pipeline
(`/spec` → `/plan` → `/build` → `/review` → `/ship`) works without them.

| File | What it does | Run |
| --- | --- | --- |
| `batch-spec.sh` | Writes specs for many tickets at once. Each ticket gets its own worktree, and each run stops when the spec is ready for your approval. | `dotfiles/tools/run/batch-spec.sh --help` |
| `spec-batch.txt` | The list of tickets `batch-spec.sh` reads when you give it no list. | — |
| `run-metrics.sh` | Reads a finished session's transcript and reports what it cost: tokens, how well tool calls were batched, large file reads, and signs of trouble. `--row` prints a line for the observation log. | `dotfiles/tools/run/run-metrics.sh --help` |
