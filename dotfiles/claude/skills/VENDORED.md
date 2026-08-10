# Vendored skills

Everything in this directory except `qdrant-multitenancy/`,
`postgres-database-migration/`, and the six SDLC-workflow skills below is
first-party (written for this repo). The rest is **third-party, copied
verbatim**, following the vendoring discipline used in
`stanimirdim92/llms/portfolio/.claude/skills/` (source URL + pinned commit +
license file, narrow leaf skills only, never a hub topic that would argue
back at a project's own decisions).

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

## SDLC-workflow skills, agent, and shared references (from `addyosmani/agent-skills`)

| | |
|---|---|
| Source | https://github.com/addyosmani/agent-skills |
| Commit | `7676817c12a1317454ae3898a0c5c1eacf5dd3d5` |
| License | MIT — `ADDYOSMANI_AGENT_SKILLS_LICENSE` |
| Taken | 6 of 24 skills, 1 of 4 agents, 3 of 7 shared `references/`, plus 4 matching commands (adapted, see below) |

Skills: `spec-driven-development`, `planning-and-task-breakdown`,
`test-driven-development`, `code-review-and-quality`,
`debugging-and-error-recovery`, `git-workflow-and-versioning`.
Agent: `agents/code-reviewer.md`. References (sibling of `skills/`, since
upstream skills point at them with `../../references/...`):
`references/definition-of-done.md`, `references/security-checklist.md`,
`references/performance-checklist.md`.

Refresh:

    git clone --depth 1 https://github.com/addyosmani/agent-skills /tmp/agent-skills
    for s in spec-driven-development planning-and-task-breakdown test-driven-development \
             code-review-and-quality debugging-and-error-recovery git-workflow-and-versioning; do
      cp /tmp/agent-skills/skills/$s/SKILL.md dotfiles/claude/skills/$s/SKILL.md
    done
    cp /tmp/agent-skills/agents/code-reviewer.md dotfiles/claude/agents/code-reviewer.md
    cp /tmp/agent-skills/references/{definition-of-done,security-checklist,performance-checklist}.md \
       dotfiles/claude/references/
    cp /tmp/agent-skills/LICENSE dotfiles/claude/skills/ADDYOSMANI_AGENT_SKILLS_LICENSE
    # then re-apply the two adaptations below (refresh overwrites them) and update the commit hash

**Two things adapted, not copied verbatim** — noted because a naive refresh
would silently undo them:
1. `test-driven-development/SKILL.md`'s "See Also" section pointed at
   `../../references/testing-patterns.md` (JS/TS-specific: Jest, RTL,
   Supertest, Playwright), which isn't vendored — this dotfiles repo has no
   JS/TS skill. The dead link is replaced with a note explaining why, rather
   than left dangling (rule 7: fail loud).
2. `agents/code-reviewer.md`'s Composition section referenced `/ship`
   (fan-out with `security-auditor`/`test-engineer`, neither vendored) and
   linked `docs/agents.md` (not vendored). Replaced with a reference to this
   repo's own `infra-reviewer`/`security-reviewer` agents, which already
   run independently and report separately — the same shape, just under
   different names.

Everything else — prose mentions of skills like `security-and-hardening` or
`browser-testing-with-devtools` that aren't vendored — is left as-is. A
missing skill by name just means Claude can't act on that specific
cross-reference; it's a soft miss, not a broken link, and is the same
partial-adoption gap upstream's own README names (issue #361).

**Taken, not the other 18** (`interview-me`, `security-and-hardening`,
`ci-cd-and-automation`, etc.) — these six are the ones that fill an actual
gap in this dotfiles repo (nothing for spec/plan/TDD/review/debug/git
discipline at all), are fully stack-agnostic, and were explicitly requested.
The rest are either narrower to Addy Osmani's own web/frontend focus
(`frontend-ui-engineering`, `browser-testing-with-devtools`,
`performance-optimization`'s Core Web Vitals framing) or redundant with
what's already here (`security-and-hardening` overlaps this repo's
`security-reviewer` agent). Revisit individually against actual need, same
as the Qdrant set above — not as a block import.

**Commands** (`dotfiles/claude/commands/spec.md`, `plan.md`, `test.md`,
`review.md`) are adapted, not vendored verbatim: upstream's versions invoke
skills through an `agent-skills:` plugin-namespace prefix (`agent-skills:spec-driven-development`)
that only resolves inside their own Claude Code plugin install. Stripped to
plain skill names, since these skills are vendored directly into
`~/.claude/skills/` here rather than installed as a plugin. `test.md` also
drops a line invoking `browser-testing-with-devtools` (not vendored), and
`review.md`'s security/performance axis notes point at this repo's
`security-reviewer` agent instead of upstream's unvendored
`security-and-hardening`/`performance-optimization` skills.

## Why vendor into personal dotfiles at all

The `nginx`/`mysql`/`redis`/`php` skills in this repo are written from scratch
because they're this author's own conventions. Qdrant and Postgres aren't run
anywhere in *this* repo, so there's no house style to write — the value here
is purely "don't re-derive lock-level/multitenancy facts from scratch," which
is exactly what a pinned, licensed copy of someone else's correct reference
material is for.

The SDLC-workflow set is a third case: not a house style (that's the
per-technology skills), not a reference for a technology this repo doesn't
run (that's Qdrant/Postgres) — it's *process* discipline (spec, planning,
TDD, review, debugging, git hygiene) that's genuinely stack-agnostic and
was missing entirely. Vendored rather than written from scratch because
upstream's versions are already well-tested at scale (24 skills, a real
eval harness with adversarial pressure-test cases) — no reason to
re-derive "Red-Green-Refactor" or "vertical task slicing" from first
principles when a correct, maintained version already exists under a
compatible license.
