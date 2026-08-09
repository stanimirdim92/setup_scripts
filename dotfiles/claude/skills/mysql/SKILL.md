---
name: mysql
description: MySQL conventions — schema design, indexing, transactions, durability tradeoffs, my.cnf tuning. Use whenever writing queries/migrations or changing MySQL config, in this repo or any other project.
---

# MySQL conventions

General good practice, plus (marked explicitly) this repo's actual
`database/my.cnf` as a worked example.

## General

- Index for the queries you actually run: composite indexes match the
  `WHERE`/`ORDER BY` column order, not one index per column. Check with
  `EXPLAIN`/`EXPLAIN ANALYZE` before assuming an index helped.
- Never `SELECT *` in application code that could survive a schema change
  — list columns, so an added column doesn't silently change response
  shape or bloat network transfer.
- Wrap multi-statement writes in an explicit transaction; don't rely on
  autocommit for anything that must be all-or-nothing.
- `utf8mb4` (not `utf8`, which is a 3-byte MySQL-specific alias) for any
  column that might hold emoji or full Unicode.
- Migrations: additive and backward-compatible in one deploy (add column
  nullable/defaulted), drop/rename in a later deploy once code no longer
  references the old shape — avoids downtime on rolling deploys.
- Durability vs. throughput is a config-level decision
  (`sync_binlog`, `innodb_flush_log_at_trx_commit`) — know which one your
  environment has chosen before assuming a write is durable the instant
  it returns.

## This repo's conventions (worked example, `database/my.cnf`)

- `innodb_buffer_pool_size=5G` is commented as "~80% of total RAM" — any
  resize should keep that comment and the ratio, not just change the
  number.
- Durability is deliberately mixed: `sync_binlog=1` (safe) but
  `innodb_flush_log_at_trx_commit=0` (fast, small data-loss window on
  crash). This is a specific, already-made tradeoff — don't "fix" one
  side without discussing the other.
- `max_connections=2000` must stay sane against PHP-FPM's
  `pm.max_children` (`php/fpm/pool.d/www.conf`, currently 300 static) —
  connections-per-worker × max_children should not blow past
  `max_connections`.
- `sql_mode` is strict (`STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,...`) — don't
  loosen it to work around an app bug; fix the app.
- `disabled_storage_engines` excludes MyISAM/BLACKHOLE/FEDERATED/ARCHIVE/MEMORY
  on purpose — a migration that needs one of these needs that line
  changed explicitly, not worked around.
