---
name: fastapi
description: FastAPI conventions — Pydantic models, dependency injection, async endpoint correctness, routing, testing. Use whenever writing or reviewing FastAPI code, in any project.
---

# FastAPI conventions

Builds on the general `python` skill — this covers what's specific to
FastAPI.

## Models & validation

- Pydantic v2 `BaseModel` for every request/response shape — don't
  accept/return raw `dict`; you lose validation and the generated
  OpenAPI schema.
- Separate models for input vs. output when they differ (e.g. a
  `UserCreate` with a password field vs. a `UserOut` without one) —
  don't reuse one model and hope nobody serializes the wrong fields.
- `BaseSettings` (pydantic-settings) for config from environment
  variables, not scattered `os.environ.get()` calls — one place to see
  every config value and its default.

## Routing & dependency injection

- Group routes into `APIRouter`s per domain/resource, included in the
  app with a prefix — not one giant file of `@app.get(...)`.
- Use `Depends()` for anything shared across endpoints (DB session,
  current-user auth, pagination params) — don't repeat the same setup
  logic in every handler.
- Raise `HTTPException` (or a custom exception + registered
  `exception_handler`) for expected error cases — don't let a bare
  `ValueError`/`KeyError` turn into an unhandled 500 with no context.

## Async correctness

- An `async def` endpoint must not call blocking code directly (sync
  DB drivers, `requests`, CPU-bound work) — it stalls the whole event
  loop for every concurrent request, not just the slow one. Use an
  async driver (`asyncpg`, `motor`, async SQLAlchemy) or wrap the
  blocking call with `run_in_threadpool`.
- If an endpoint's handler is entirely synchronous work, define it as
  `def`, not `async def` — FastAPI runs sync endpoints in a threadpool
  automatically, which is often simpler than making everything async
  for no benefit.
- Long-running work that shouldn't block the response goes through
  `BackgroundTasks` for fire-and-forget, or a real task queue (Celery,
  arq) for anything that needs retries/monitoring — not an
  un-awaited `asyncio.create_task` with no supervision.

## Testing

- `TestClient` (sync) or `httpx.AsyncClient` (async) against the actual
  FastAPI app — test through the HTTP layer, not by calling route
  functions directly, so routing/validation/dependency wiring are
  covered too.
- Override dependencies with `app.dependency_overrides` for test
  doubles (fake DB session, fake auth user) instead of monkeypatching
  internals.
