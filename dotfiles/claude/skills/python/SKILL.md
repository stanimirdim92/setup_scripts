---
name: python
description: Python conventions — project layout, typing, dependency management, testing, linting. Use whenever writing or reviewing Python code, in any project.
---

# Python conventions

## Project structure

- `src/<package>/` layout over a flat top-level package — avoids
  accidentally importing the uninstalled working copy instead of the
  installed package during tests.
- One tool for dependency + environment management (`uv` or `poetry`) —
  don't mix a `requirements.txt` maintained by hand with a
  `pyproject.toml` maintained by a tool; pick one source of truth.
- Pin direct dependencies with a lockfile committed to the repo; pin
  transitive ranges loosely enough that security patches aren't blocked.

## Code

- Type hints on public function signatures at minimum; run `mypy` or
  `pyright` in CI, not just as an editor nicety nobody enforces.
- Never use a mutable default argument (`def f(x=[])`) — it's shared
  across calls. Default to `None` and assign inside the function.
- `logging` module, not `print`, for anything that runs outside a
  throwaway script — `print` output can't be leveled, filtered, or
  routed.
- Context managers (`with`) for anything with cleanup (files, locks,
  DB connections/transactions) — don't rely on `__del__` or manual
  `close()` calls on every exit path.
- `pathlib.Path`, not string concatenation, for filesystem paths.
- Format/lint with `ruff` (format + check) as a single fast tool rather
  than separately running `black`+`isort`+`flake8`.

## Testing

- `pytest`, fixtures over `setUp`/`tearDown` boilerplate.
- Test the public behavior, not the private implementation — a test
  that breaks on every internal refactor without a behavior change is
  testing the wrong thing.
- Mark slow/integration tests explicitly (`@pytest.mark.slow`, a
  separate marker) so the fast unit-test loop stays fast.

## Async

- Don't mix blocking calls (sync DB drivers, `requests`, disk I/O
  without a thread) into an `async def` function — it blocks the whole
  event loop, not just that request. Use the async-native client or
  `asyncio.to_thread`/`run_in_executor`.
