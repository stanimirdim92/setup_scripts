# tests — does the harness's own code work?

The harness has real code: hooks that block a dangerous command, scripts that
link files or fetch skills, and the checks in `../checks/`. These are the
tests for that code.

Each test builds a small fake situation, such as a throwaway repository or a
made-up command, and checks that the code reacts correctly. No model runs, and
nothing outside a temporary folder is touched. CI runs all of them on every
push.

| Test | Covers |
| --- | --- |
| `test-hooks.sh` | The hooks that block destructive commands, force pushes, and pushes by agents |
| `test-commit-trailers.sh` | The hook that refuses a writer's commit without a `Refs:` trailer |
| `test-handoff-hook.sh` | The hook that stops a writer agent from finishing without its handoff report |
| `test-worktree-hooks.sh` | The stale-base warning and the rule that writers work in a worktree |
| `test-isolated-test-runner.sh` | The rule that a project's tests run in isolation |
| `validate-frontmatter-test.py`, `validate-artifact-paths-test.py`, `check-references-test.py`, `check-writing-test.py` | The checks in `../checks/` |
| `test-link-dotfiles.sh`, `test-fetch-figma-skill.sh` | The scripts in `../setup/` |
| `test-batch-spec.sh`, `test-run-metrics.sh` | The scripts in `../run/` |
| `test-install-skills.py`, `test-codex-harness.py`, `test-codex-worktree.py` | The Codex side: skill install, roles and hook adapters, and the worktree launcher |
| `test-weakened-tests.py` | The guard `/review` runs for deleted or weakened tests (the script lives in the code-review skill) |
| `test-check-spec.py`, `test-check-plan.py` | The checks `/spec` and `/plan` run on their own output (the scripts live in those skills) |

Run the one for what you changed, from the repository root:

```bash
bash dotfiles/tools/tests/test-hooks.sh
python3 dotfiles/tools/tests/check-references-test.py
```

To run everything CI runs, see `../README.md`.

The evals in `../evals/` keep their own tests next to their code.
