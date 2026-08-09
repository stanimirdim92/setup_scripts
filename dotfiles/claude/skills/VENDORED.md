# Vendored skills

Everything in this directory except `qdrant-multitenancy/` and
`postgres-database-migration/` is first-party (written for this repo). Those
two are **third-party, copied verbatim**, following the vendoring discipline
used in `stanimirdim92/llms/portfolio/.claude/skills/` (source URL + pinned
commit + license file, narrow leaf skills only, never a hub topic that would
argue back at a project's own decisions).

## `qdrant-multitenancy/`

| | |
|---|---|
| Source | https://github.com/qdrant/skills |
| Commit | `aa2355fcf06b805110fb8cecbd1aa4d64c15eb73` |
| License | Apache 2.0 — `QDRANT_LICENSE` |
| Taken | `qdrant-multitenancy/SKILL.md` only, out of 10 top-level skills upstream |

Refresh:

    git clone --depth 1 https://github.com/qdrant/skills.git /tmp/qdrant-skills
    cp /tmp/qdrant-skills/skills/qdrant-multitenancy/SKILL.md dotfiles/claude/skills/qdrant-multitenancy/
    cp /tmp/qdrant-skills/LICENSE dotfiles/claude/skills/QDRANT_LICENSE
    # then update the commit hash above

Taken alone, not the other 9 (scaling/monitoring/performance/search-quality/etc.),
because this is a **general** dotfiles skill with no specific project behind
it yet — multitenancy (payload partitioning vs. shard/collection isolation)
is the one decision that has to be made correctly on day one of any Qdrant
project; the rest (scaling, monitoring, performance tuning) are things to
reach for once a real deployment exists to tune. Add more of the set later
if a real Qdrant project needs them — see `stanimirdim92/llms/portfolio` for
a worked example of vendoring the deeper ones deliberately, one at a time,
against actual need.

## `postgres-database-migration/`

| | |
|---|---|
| Source | https://github.com/timescale/pg-aiguide |
| Commit | `b4f11a45907af3abda0f79e784aff9a6d5eef468` |
| License | Apache 2.0 — `PG_AIGUIDE_LICENSE`, **plus `PG_AIGUIDE_NOTICE`** |
| Taken | `postgres-database-migration/` (`SKILL.md` + 3 `references/`) only, out of 10 skills upstream |

Refresh:

    git clone --depth 1 https://github.com/timescale/pg-aiguide /tmp/pg-aiguide
    rm -rf dotfiles/claude/skills/postgres-database-migration
    cp -r /tmp/pg-aiguide/skills/postgres-database-migration dotfiles/claude/skills/
    cp /tmp/pg-aiguide/LICENSE dotfiles/claude/skills/PG_AIGUIDE_LICENSE
    cp /tmp/pg-aiguide/NOTICE   dotfiles/claude/skills/PG_AIGUIDE_NOTICE
    # then update the commit hash above

**Two license files, not one** — this upstream ships a `NOTICE` file
alongside its Apache 2.0 `LICENSE`, and Apache 2.0 §4(d) requires a
redistribution to carry the attribution notices from it. Checked, not
assumed: `qdrant/skills` has no `NOTICE`, so that one stays a single file.

Taken alone, not the hub skill `postgres` (which routes to
`pgvector-semantic-search` and would push Postgres-as-vector-store advice
into any project that already chose something else) or the TimescaleDB/PostGIS
skills (extensions this dotfiles repo has no opinion on). Lock-level-aware
migration safety is the one piece that's true regardless of what a given
Postgres project is otherwise doing.

## Why vendor into personal dotfiles at all

The `nginx`/`mysql`/`redis`/`php` skills in this repo are written from scratch
because they're this author's own conventions. Qdrant and Postgres aren't run
anywhere in *this* repo, so there's no house style to write — the value here
is purely "don't re-derive lock-level/multitenancy facts from scratch," which
is exactly what a pinned, licensed copy of someone else's correct reference
material is for.
