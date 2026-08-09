---
name: mysql-redis-tuning
description: House-style conventions for this repo's MySQL (database/my.cnf) and Redis (redis/redis.conf) config — durability tradeoffs, memory sizing, and the cache-only Redis contract. Use when changing my.cnf or redis.conf, or when adding a new database/cache dependency.
---

# MySQL (`database/my.cnf`)

- `innodb_buffer_pool_size=5G` is commented as "~80% of total RAM" — any
  resize should keep that comment and the ratio, not just change the number.
- Durability is deliberately mixed: `sync_binlog=1` (safe) but
  `innodb_flush_log_at_trx_commit=0` (fast, small data-loss window on crash).
  This is a specific, already-made tradeoff — don't "fix" one without
  discussing the other.
- `max_connections=2000` must stay sane against PHP-FPM's
  `pm.max_children` (`php/fpm/pool.d/www.conf`, currently 300 static) —
  connections-per-worker × max_children should not blow past max_connections.
- `sql_mode` is strict (`STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,...`) —
  don't loosen it to work around an app bug; fix the app.
- `disabled_storage_engines` excludes MyISAM/BLACKHOLE/FEDERATED/ARCHIVE/MEMORY
  on purpose — a migration that needs one of these needs that line changed
  explicitly, not worked around.

# Redis (`redis/redis.conf`)

- This instance is **cache-only**: `save ""` (no RDB snapshots),
  `appendonly no` (no AOF), `maxmemory-policy allkeys-lru` (silently evicts
  under pressure). Anything stored here can vanish on restart or under
  memory pressure — never point session/queue/durable data at this instance
  without changing persistence settings first.
- `bind redis_docker 127.0.0.1` + protected-mode commented out only because
  it's Docker-internal-only — see the `security-reviewer` agent before
  loosening this.
- `maxmemory 1gb` is a hard ceiling with LRU eviction, not OOM — raising
  it should be a deliberate capacity decision, not a fix for eviction
  churn (check what's being evicted first).
