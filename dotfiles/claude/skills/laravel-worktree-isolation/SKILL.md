---
name: laravel-worktree-isolation
description: "Set up a Laravel repository so its test suite runs isolated per git worktree — separate database and Redis keyspace — enabling parallel ticket work. Use when tests in one worktree corrupt another's, when adding worktree-based parallel work to a Laravel project, or when a project's test database is built from a schema dump rather than migrations."
---

# Laravel Worktree Isolation

A git worktree isolates git and the filesystem. It does not isolate a database,
a Redis keyspace, or a fixed port. Two worktrees running the same Laravel suite
share all three, and concurrent runs drop and re-migrate each other's schema
with no lock error — one suite simply fails for reasons unrelated to its own
diff. This skill sets up the missing isolation.

Produce the scripts inside the repository, not in dotfiles. `composer.json`
references them by relative path, teammates and CI do not have your dotfiles,
and a worktree checks out tracked files only — so in-repo scripts arrive in
every worktree automatically.

## 1. Establish the project's facts first

Do not assume; read them:

- **Migrations or a schema snapshot?** Count migration files. A project whose
  schema came from an imported dump has few or none, so `RefreshDatabase` can
  never rebuild a test database and §4 applies.
- **Which test env file is loaded.** `phpunit.xml` usually pins
  `APP_ENV=testing`, which makes Laravel load `.env.testing`; the database named
  there is the one every worktree would otherwise share.
- **The package manager**, `npm` or `yarn`, from the lockfile actually present.
- **Whether the local database is treated as production.** If it is, nothing in
  this setup may write to it — the schema snapshot is read-only.

## 2. Carry the ignored env files into worktrees

Add `.worktreeinclude` at the project root, gitignore syntax. Claude Code and
Codex both copy matching files into every managed worktree, but only files that
are **both** matched and gitignored — a tracked file silently copies nothing.
Verify with `git check-ignore -v <file>` before relying on it. Add
`.claude/worktrees/` to `.gitignore` while here.

This solves file presence, not isolation: every worktree now holds an identical
env file naming the same database. §3 is what separates them.

## 3. Derive the database and Redis keyspace from the worktree

Laravel's environment repository is immutable (`Env::getRepository()` builds
with `->immutable()`), so a real process environment variable beats the copied
env file. A wrapper script is therefore enough — no per-worktree file editing:

- Derive a slug from the worktree directory name, stripping anything outside
  `[A-Za-z0-9]` so the result is a legal unquoted SQL identifier.
- Set `DB_DATABASE=<project>_test_<slug>`.
- Separate Redis with `REDIS_PREFIX`, not `REDIS_DB`: database indexes are a
  fixed pool (16 by default), prefixes are unbounded.
- Guard the resolved name against the project's test namespace and refuse
  anything outside it, so a mangled worktree name can never resolve to the
  production database.
- Point `composer.json`'s `test` script at the wrapper; composer forwards extra
  arguments, so `composer test -- --filter=X` keeps working.

**The trap:** Laravel connects to `DB_DATABASE` *first* in order to issue
`CREATE DATABASE <base>_test_<token>`
(`Illuminate\Testing\Concerns\TestDatabases`). The base database must already
exist or the connection fails before anything is created. The wrapper creates
it — connect to `information_schema` and issue
`CREATE DATABASE IF NOT EXISTS`.

With `--parallel`, Laravel appends its own per-process token on top of the base
name, so worktree isolation and in-worktree concurrency compose.

## 4. When the schema comes from a dump, not migrations

`php artisan schema:dump` snapshots the live schema to
`database/schema/<connection>-schema.sql`, which `migrate` loads before applying
any remaining migrations. It shells out to `mysqldump`, so it reads the source
database and never writes to it — safe against a database treated as
production. Do not pass `--prune`; that deletes migration files the project
still needs.

Inspect the dump before trusting it: it should contain the expected table count,
no data rows beyond the `migrations` table, no `DEFINER` clauses, and no
hard-coded database name.

**A snapshot goes stale silently.** Once the source schema changes, test
databases are built from the old shape and the suite passes against a schema
that no longer exists — nothing errors. Record a fingerprint beside the dump
(hash the table, column, type, nullability and default rows from
`information_schema`) and have the test wrapper compare the live schema against
it, refusing to run and naming the refresh command on mismatch. State the
limitation: a column-level fingerprint does not catch index-only changes.

## 5. Scope the destructive-command guards to testing

`DB::prohibitDestructiveCommands()` called with no argument blocks
`migrate:fresh` in **every** environment, including `testing`. `RefreshDatabase`
then cannot rebuild anything and every test database comes up empty — the
failure surfaces as "table doesn't exist", not as a permission error, which
makes it expensive to diagnose. Scope it:

```php
DB::prohibitDestructiveCommands(! app()->environment('testing'));
```

Check for a second guard before concluding: projects often also disable migrate
commands in `routes/console.php`. Any such guard must key on the same condition,
or the two disagree and only one is visible.

Prefer `! app()->environment('testing')` over `app()->isProduction()` when the
local database is treated as production — the latter also unblocks destructive
commands against it in local development.

## 6. Provisioning

A worktree checks out tracked files only, so dependencies are absent and every
build, lint, and test command fails until installed. Provide an idempotent
setup script that installs them, skips what exists, and warns when an expected
env file did not arrive.

## Verification

Claims here are cheap to test, so test them rather than reporting them:

- The suite passes through the wrapper, and the created databases carry the
  expected per-worktree and per-process names.
- The staleness guard actually trips: corrupt the recorded fingerprint, confirm
  the run refuses, then restore it.
- The name guard refuses a database outside the test namespace.
- The production database is untouched afterwards — compare its table count.
- A destructive command is still blocked outside `testing`.

Compare any failure against the untouched baseline before attributing it to this
setup; a suite that already failed will keep failing for its own reasons.
