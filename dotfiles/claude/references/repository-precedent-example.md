# Repository Precedent — Worked Example

A filled-in `repo-recon` report, for calibrating what a usable one looks like.
Split out of `repository-precedent.md` deliberately: that file is read on every
`/spec` and `/plan` run, and an example is needed once while learning the shape,
not on every run.

Rules this illustrates: `repository-precedent.md`. Report format and the agent's
own constraints: `../agents/repo-recon.md`.

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
