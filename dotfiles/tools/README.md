# Harness tools

Grouped by what you do with them. Paths below are from the repository root. Each folder has its own README that explains it in plain terms.

| Folder | What it is | When you use it |
| --- | --- | --- |
| `setup/` | `link_dotfiles.sh` — links `dotfiles/claude` and `dotfiles/codex` into `$HOME` | Once per machine, and after adding a synced file |
| `run/` | Tools you use during ticket work | When you need them |
| `checks/` | Validators that read the harness files and fail on drift | CI runs them; run one after editing what it guards |
| `tests/` | Self-tests for the hooks, the checks, and the `run/` and `setup/` scripts | CI runs them; run the one for what you changed |
| `evals/` | Scores real tickets against what shipped | After a ticket ships, or after a harness change |

## `run/`

| File | Does | Run |
| --- | --- | --- |
| `batch-spec.sh` | `/spec` for many tickets at once, one worktree each | `dotfiles/tools/run/batch-spec.sh --help` |
| `spec-batch.example.txt` | The ticket-list format; copy it to `spec-batch.txt` (gitignored), which `batch-spec.sh` reads by default | — |
| `run-metrics.sh` | Tokens, batching, large reads and failure signals from a transcript; `--row` prints an observation-log row | `dotfiles/tools/run/run-metrics.sh --help` |

## `checks/`

| File | Fails when |
| --- | --- |
| `validate-frontmatter.py` | A persona's tools, model, effort or hooks, or a `settings.json` pin, drifts from its ADR |
| `validate-artifact-paths.py` | A spec, plan or todo path is spelled differently anywhere |
| `check-references.py` | A cross-reference between harness files no longer resolves, including a `#anchor` or `§Section` it names |
| `check-writing.py` | More than 20% of the sentences in an ADR from 0073 on run over 25 words. Pass files to check a spec or plan |
| `harness-map.py` | `dotfiles/docs/harness-map.html` is out of date. Without `--check` it regenerates the page |

## `tests/`

| File | Covers |
| --- | --- |
| `test-hooks.sh` | The PreToolUse hooks: destructive commands, force push, agent push |
| `test-handoff-hook.sh` | The handoff report gate on writer personas |
| `test-worktree-hooks.sh` | The stale-base warning and the writer-worktree guard |
| `test-isolated-test-runner.sh` | The isolated test-runner guard |
| `validate-frontmatter-test.py`, `validate-artifact-paths-test.py`, `check-references-test.py`, `check-writing-test.py` | The checks above |
| `test-install-skills.py`, `test-codex-harness.py`, `test-codex-worktree.py` | The Codex installer, roles, hook adapter and worktree launcher |
| `test-link-dotfiles.sh` | `setup/link_dotfiles.sh` |
| `test-batch-spec.sh`, `test-run-metrics.sh` | The two `run/` scripts |
| `test-weakened-tests.py` | `/review`'s weakened-test guard, shipped in the `code-review-and-quality` skill |

Run everything CI runs:

```bash
grep -E '^\s+(run: )?(bash|python3) dotfiles' .github/workflows/ci.yml \
  | sed -E 's/^\s+(run: )?//' | while read -r c; do $c >/dev/null 2>&1 && echo "ok   $c" || echo "FAIL $c"; done
```

## `evals/`

| Folder | Measures | Costs |
| --- | --- | --- |
| `plan-recall/` | How many of the files a ticket changed its plan named | Free |
| `spec-eval/` | How close a fresh `/spec` gets to a deployed spec | One real `/spec` run per ticket |
| `workflow/` | The pipeline end to end in a throwaway project | Real model runs |

Each folder's README has the commands. Their own logic tests (`test_*.py`) run in CI.
