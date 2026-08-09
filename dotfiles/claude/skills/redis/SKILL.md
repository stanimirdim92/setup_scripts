---
name: redis
description: Redis conventions — data structure choice, persistence/eviction tradeoffs, safe production commands, redis.conf tuning. Use whenever adding a Redis-backed feature or changing Redis config, in this repo or any other project.
---

# Redis conventions

General good practice, plus (marked explicitly) this repo's actual
`redis/redis.conf` as a worked example.

## General

- Decide **cache vs. store** explicitly before writing to Redis: a
  cache-only instance (no persistence, LRU eviction) can lose data at
  any time by design — never point session state, queues, or anything
  that must survive a restart at one without first checking its
  `save`/`appendonly`/`maxmemory-policy` settings.
- Never run `KEYS *` against a production instance — it blocks the
  single-threaded event loop. Use `SCAN` with a cursor instead.
- Pick the data structure for the access pattern: hashes for objects you
  partially update, sorted sets for anything ranked/time-ordered, sets
  for membership checks — not everything needs to be a JSON blob in a
  string key.
- Pipeline or use `MULTI`/`EXEC` for batches of related commands instead
  of N round trips.
- For HA, Sentinel or Cluster — a single unmonitored instance is a single
  point of failure for anything that isn't purely disposable cache data.

## This repo's conventions (worked example, `redis/redis.conf`)

- This instance is **cache-only**: `save ""` (no RDB snapshots),
  `appendonly no` (no AOF), `maxmemory-policy allkeys-lru` (silently
  evicts under memory pressure). Anything stored here can vanish on
  restart or eviction — never point session/queue/durable data at this
  instance without changing persistence settings first.
- `bind redis_docker 127.0.0.1` with `protected-mode` commented out is
  safe *only* because it's Docker-internal-only — loosening the bind
  address without also turning protected-mode/auth back on is a real
  security regression (see the `security-reviewer` agent).
- `maxmemory 1gb` is a hard ceiling with LRU eviction, not OOM protection
  — raising it should be a deliberate capacity decision, not a
  workaround for eviction churn (check what's actually being evicted
  first, with `INFO stats` / `evicted_keys`).
