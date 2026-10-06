# checks — do the harness files agree with each other?

The harness is mostly text: agents, commands, skills and ADRs that refer to
each other. Text drifts. An ADR says a reviewer has read-only tools, and
someone later adds a write tool. A command links to a file that was renamed.
Nothing crashes, the harness just quietly does the wrong thing.

Each check reads the files and compares them with a rule. It runs no model and
costs nothing. CI runs all of them on every push. Run one yourself after you
edit what it guards.

| File | Fails when | Guards |
| --- | --- | --- |
| `validate-frontmatter.py` | A persona's tools, model, effort or hooks differ from what its ADR decided | `claude/agents/*.md`, `settings.json` |
| `validate-artifact-paths.py` | A spec, plan or todo path is spelled differently somewhere | every file that names `docs/specs/…` or `docs/tasks/…` |
| `check-references.py` | A link between harness files points at a file, `#anchor` or `§Section` that no longer exists | every harness markdown file |
| `check-writing.py` | More than 20% of an ADR's sentences are over 25 words (the "Writing for humans" rule) | ADRs from 0073 on; pass a file to check any spec or plan |
| `harness-map.py` | `docs/harness-map.html` no longer matches the files it describes | the generated map. Without `--check`, it rebuilds the page |

Run one from the repository root, for example:

```bash
python3 dotfiles/tools/checks/check-references.py
```

Each check has a test of its own in `../tests/`, so a broken check cannot
silently pass everything.
