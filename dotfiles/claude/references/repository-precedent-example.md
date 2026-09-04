# Repository Precedent — Worked Example

A filled-in `repo-recon` report, for calibrating what a usable one looks like.
It stays separate because the trigger rules are hot-path guidance while this
long example is needed only when learning the report shape.

Rules this illustrates: `repository-precedent.md`. Report format and the agent's
own constraints: `../agents/repo-recon.md`.

A report for `/spec` on the area "advertiser statistics refresh" in a Laravel
modular monolith. Note what it does *not* contain: no file contents, no
recommendations, and no command it did not find defined in the repository.

```markdown
## Recon: advertiser statistics refresh (Modules/Advertiser)

### Rules and precedent
- `Modules/Advertiser/CLAUDE.md` — "every write path goes through a Service;
  controllers never touch Eloquent directly"
- `deptrac.yaml:24` — the Advertiser layer may not depend on Reporting;
  violations fail CI
- (repo-wide Pint/PHPStan config bears on this area but adds no rule the
  caller does not already follow)
- Naming: singular Eloquent models, plural tables — `Advertiser` /
  `advertisers` (`Modules/Advertiser/Models/Advertiser.php:18`)
- Architectural chain: Controller → Service → Repository → Model. Verified
  across all four services in this module, not inferred from two.
- Boundaries: Services accept Data objects, never Requests
  (`Modules/Advertiser/Data/AdvertiserData.php:12`)
- Registration/routing: routes declared per-module in
  `Modules/Advertiser/routes/api.php:31`, bound in the module provider
- `Modules/Advertiser/Services/TagAssignmentSyncService.php:44` — same
  shape: a scheduled refresh that reconciles rows against an external
  feed, with a per-advertiser lock. Closest match.
- `Modules/Billing/Services/InvoiceRefreshService.php:61` — similar
  chunked refresh, different module conventions; use for the chunking
  pattern only.

### Verification
- Framework/location/fixtures: Pest; `Modules/Advertiser/tests/Feature/`;
  factories under `Modules/Advertiser/database/factories/`
- Repository-defined commands:
  - `php artisan test --filter=Advertiser`
  - `vendor/bin/pint --dirty`
  - `vendor/bin/phpstan analyse --memory-limit=1G`
  - `vendor/bin/deptrac analyse`

### Constraints
- `advertiser_statistics` is ~40M rows; the existing refresh chunks at 1,000
  and runs on the `statistics` queue (`config/queue.php:38`)
- The admin dashboard reads this table directly, so a schema change has a
  consumer outside this module
- Pre-existing state: `TagAssignmentSyncService` has a skipped test
  (`tests/Feature/TagAssignmentSyncTest.php:88`, marked `->skip('flaky
  since #4412')`) — a plan touching that path inherits it

### Unknowns
- No precedent found for: partial-failure semantics for a refresh that fails
  midway; both existing refreshes restart from scratch. Also no soft-delete
  precedent: the table and siblings have no `deleted_at`.
- Not surveyed: the admin dashboard read path; queue worker and supervisor
  configuration.
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
