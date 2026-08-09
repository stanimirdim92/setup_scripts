---
name: php
description: PHP conventions — strict types, error handling, security basics, Composer, PHP-FPM pool tuning. Use whenever writing or reviewing PHP code or PHP-FPM config, in this repo or any other project.
---

# PHP conventions

## Code

- `declare(strict_types=1);` at the top of every file — implicit type
  coercion hides bugs, especially around `0`/`""`/`null`/`false`.
- PSR-12 formatting, PSR-4 autoloading via Composer — don't hand-roll
  `require`/`include` chains in new code.
- Prepared statements (PDO or mysqli, bound params) for every query that
  includes a variable — never string-concatenate user input into SQL.
- Check `composer audit` (or `roave/security-advisories`) for known-CVE
  dependencies before adding a package, and after bumping one.
- Production error settings: `display_errors=Off`, `log_errors=On`, a
  real `error_log` path — never let a stack trace with paths/queries
  reach a response body.
- OPcache on in production (`opcache.enable=1`,
  `opcache.validate_timestamps=0` + a deploy-time cache clear) — without
  it every request recompiles every file.

## PHP-FPM pool tuning

- `pm = static` (fixed worker count) is predictable and simple to reason
  about for capacity planning; `dynamic`/`ondemand` trade that for lower
  idle memory but need real `pm.min_spare_servers`/`pm.max_spare_servers`
  values, not template defaults left in place.
- `pm.max_children` × the pool's average per-request memory should stay
  under available RAM with headroom — a 300-worker pool of a 100MB
  process needs ~30GB, not a rough guess.
- `pm.max_children` should also stay sane against the database's
  `max_connections` if every request opens a DB connection — see the
  `mysql`/`postgresql` skills.
- `pm.max_requests` (respawn a worker after N requests) is a pragmatic
  leak mitigation for third-party extensions, not a substitute for
  fixing an actual leak you've found.

## This repo's example (`php/fpm/pool.d/www.conf`)

`pm = static`, `pm.max_children = 300` — a fixed pool, sized without the
dynamic-mode spare-server tuning above being relevant. Any switch to
`dynamic`/`ondemand` here needs those values filled in deliberately, not
left at whatever the package default was.
