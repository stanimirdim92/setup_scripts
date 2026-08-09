---
name: postgresql
description: PostgreSQL conventions — indexing, EXPLAIN ANALYZE, migrations, connection pooling, JSONB, isolation levels. Use whenever writing queries/migrations or changing Postgres config, in any project (this repo doesn't run Postgres itself).
---

# PostgreSQL conventions

This repo doesn't run Postgres — this skill is a general reference for
other projects, kept here alongside the MySQL/Redis skills so the same
"index for the query you run, not one per column" discipline applies
consistently across whichever database a given project uses.

## General

- `EXPLAIN (ANALYZE, BUFFERS)` before trusting a query plan guess —
  Postgres's planner is cost-based and genuinely surprises people;
  don't add an index speculatively without checking it's used.
- Composite indexes match query column order; a `WHERE a = ? AND b = ?`
  query wants an `(a, b)` index, not two separate single-column ones
  (Postgres can bitmap-AND them, but a composite index is usually
  cheaper).
- Connection pooling (PgBouncer, or the app framework's own pool) is not
  optional under real concurrency — Postgres connections are
  process-backed and expensive; don't open one per request with no pool.
- `JSONB` for semi-structured data you'll query into; plain `JSON` only
  if you need to preserve exact input formatting and never query fields.
- Migrations: additive/backward-compatible first (nullable/defaulted
  column), drop/rename later once code no longer references the old
  shape — same rolling-deploy discipline as MySQL.
- Know your isolation level: default `READ COMMITTED` allows some
  anomalies that `REPEATABLE READ`/`SERIALIZABLE` don't — pick
  deliberately for anything doing read-then-write logic under
  concurrency, and handle serialization failures with retry if you use
  `SERIALIZABLE`.
- `VACUUM`/autovacuum isn't optional maintenance — a table with heavy
  updates/deletes and disabled or lagging autovacuum bloats and slows
  down over time. Check `pg_stat_user_tables` if a table "used to be
  fast."
- Use `RETURNING` to get inserted/updated rows back instead of a
  separate `SELECT` after the write.
