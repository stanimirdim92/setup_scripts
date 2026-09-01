# Repository Precedent

How to use a `repo-recon` report, and how to decide when the repository gives no
guidance. Single-sourced because `/spec` and `/plan` had near-identical copies of
the dispatch rules and `spec-driven-development` a third, while the precedent
hierarchy existed only in the spec skill even though planning and implementation
both depend on it.

## 1. Using a recon report

Before naming files, classes, tables, architectural layers, test helpers, or
implementation patterns, you need the project's applicable rules, the owning
module's conventions and architectural chain, its test setup, and the closest
sibling implementations.

Do not gather that by reading the repository yourself. The calling stage
dispatches one `repo-recon` agent for the affected area and works from its
report — that survey is the largest avoidable cost of the command, and the
agent's reads stay in its own context. `repo-recon` owns the discovery method,
including which instruction sources to look for; do not restate that list.

- **Reuse** a report already in this conversation when it covers the same area
  and nothing has changed since. Dispatch again only for a different area, after
  the repository has changed, or when the report's **Not surveyed** section
  excludes something you now need.
- **Findings are pointers.** Open a file the report names only when a specific
  unresolved question turns on that file's detail — one or two files, not the
  survey again.
- **No precedent found for** is load-bearing: those are the aspects being
  decided without repository guidance.
- **Not surveyed** bounds what the report can support. If it excludes something
  the work depends on, ask for a follow-up recon rather than assuming.

Per-stage handling of **No precedent found for**:

| Stage | Obligation |
|---|---|
| `/spec` | The spec must justify each one explicitly, not present it as the obvious choice. |
| `/plan` | Carry them into the plan as risks, not as settled ground. |

## 2. Evidence order

1. Explicit user requirements and approved feature-specific decisions.
2. Applicable project-local rules.
3. Existing patterns in the owning module or closest sibling feature.
4. Existing repository-wide conventions.
5. Framework conventions only when the repository provides no applicable
   precedent.

Repository precedent is a strong default, not a prohibition against deliberate
change.

## 3. When no precedent exists

- If an explicit user requirement or approved feature-specific decision requires
  a new layer, file, pattern, or abstraction, include it and label it clearly as
  a **new feature-specific decision**.
- If no requirement or decision justifies it, do not invent it merely because it
  is common framework practice.
- If the evidence is mixed, or the choice would change an acceptance criterion,
  schema, public contract, or lifecycle behavior, raise an `OPEN QUESTION` block
  instead of silently deciding.

Examples:

- A Factory may be introduced when comparable tests use factories, the feature
  needs reusable test/seed data, or it is an explicit feature decision.
- A DTO/Data layer may be introduced when project rules require it, repository
  precedent supports it, or an explicit feature decision accepts the additional
  boundary/complexity for a concrete benefit.
- Do not derive class/table names solely from ticket wording when sibling
  resources establish a different ownership/naming convention.

Do not confuse **no precedent** with **forbidden**. New patterns are acceptable
when they are intentional, justified, and identified as new rather than
misrepresented as existing repository convention.

## 4. Worked example

A report for `/spec` on the area "advertiser statistics refresh" in a Laravel
modular monolith. Note what it does *not* contain: no file contents, no
recommendations, and no command it did not find defined in the repository.

```markdown
## Recon: advertiser statistics refresh (Modules/Advertiser)

### Applicable rules
- `Modules/Advertiser/CLAUDE.md` — "every write path goes through a Service;
  controllers never touch Eloquent directly"
- `deptrac.yaml:24` — the Advertiser layer may not depend on Reporting;
  violations fail CI
- (repo-wide Pint/PHPStan config bears on this area but adds no rule the
  caller does not already follow)

### Conventions
- Naming: singular Eloquent models, plural tables — `Advertiser` /
  `advertisers` (`Modules/Advertiser/Models/Advertiser.php:18`)
- Architectural chain: Controller → Service → Repository → Model. Verified
  across all four services in this module, not inferred from two.
- Boundaries: Services accept Data objects, never Requests
  (`Modules/Advertiser/Data/AdvertiserData.php:12`)
- Registration/routing: routes declared per-module in
  `Modules/Advertiser/routes/api.php:31`, bound in the module provider

### Tests
- Framework/location/fixtures: Pest; `Modules/Advertiser/tests/Feature/`;
  factories under `Modules/Advertiser/database/factories/`
- Repository-defined commands:
  - `php artisan test --filter=Advertiser`
  - `vendor/bin/pint --dirty`
  - `vendor/bin/phpstan analyse --memory-limit=1G`
  - `vendor/bin/deptrac analyse`

### Closest precedents
- `Modules/Advertiser/Services/TagAssignmentSyncService.php:44` — same
  shape: a scheduled refresh that reconciles rows against an external
  feed, with a per-advertiser lock. Closest match.
- `Modules/Billing/Services/InvoiceRefreshService.php:61` — similar
  chunked refresh, different module conventions; use for the chunking
  pattern only.

### Constraints and dependencies
- `advertiser_statistics` is ~40M rows; the existing refresh chunks at 1,000
  and runs on the `statistics` queue (`config/queue.php:38`)
- The admin dashboard reads this table directly, so a schema change has a
  consumer outside this module
- Pre-existing state: `TagAssignmentSyncService` has a skipped test
  (`tests/Feature/TagAssignmentSyncTest.php:88`, marked `->skip('flaky
  since #4412')`) — a plan touching that path inherits it

### No precedent found for
- Partial-failure semantics for a refresh that fails midway. No existing
  service in this module records progress or resumes; both existing
  refreshes restart from scratch. The spec must justify whichever it picks
  rather than presenting it as the module's convention.
- Soft-delete behavior on statistics rows. The table has no
  `deleted_at`, and no sibling table carries one.

### Not surveyed
- The admin dashboard's read path (outside this module; flagged above as a
  consumer only)
- Queue worker configuration and supervisor setup
```

What makes this report usable rather than a survey dump:

- **Pointers, not contents** — every claim carries a `path:line` the caller can
  open if a specific question turns on it.
- **Verified is distinguished from inferred** — "verified across all four
  services, not inferred from two" is the difference between a convention and a
  coincidence.
- **Absence is reported as a finding.** The two `No precedent found for` entries
  are the ones that change the spec's obligations: partial-failure semantics now
  needs an explicit justification, and the missing soft-delete precedent means
  §5's lifecycle gate has nothing to inherit.
- **Commands are quoted, never guessed** — including the flags
  (`--memory-limit=1G`, `--dirty`) that a generic guess would omit.
- **Pre-existing broken state is surfaced** — the skipped flaky test is exactly
  what a plan must account for and what a survey would silently omit.

