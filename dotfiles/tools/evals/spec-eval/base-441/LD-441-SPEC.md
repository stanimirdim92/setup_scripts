# Spec: Ticker Feed — Latest / Most Relevant Sorting (Backend)

Status: Draft
Ticket: LD-441 (parent LD-440)
Change kind: Modify
Supersedes: N/A
Approved by: —
Approved at: —

## Objective

The Ticker feed API (`GET socials.ticker.index`) gets a second sort mode, `most_relevant`, beside the current behavior, which becomes the `latest` mode. Most Relevant ranks one combined set of Organic Posts, Standalone Ads and paid-ads signals by relevance inside a selected timeframe. Users can then see the most sales-relevant activity first, not just the newest.

Repository state at spec time (commit `d4f4c33`): Jira marks LD-441 and LD-440 as Done, but this checkout has no sort or relevance code. A search for `most_relevant`, `mostRelevant`, `EVENT_TYPE_SCORES` and `sort_by` found nothing in `Modules/`, `resources/js/` or `routes/`. The FE (`resources/js/hooks/useTickerFeed.ts:101-112`) sends no sort parameter. This spec therefore covers the full backend implementation. See Assumption A-1.

Out of scope:
- The FE sort and timeframe selector, and keeping filters when the mode changes (LD-442, FE).
- Ticker exports (`TickerExportController`, `TickerPostsExport`, `GenerateTickerExportLinks`, `TickerService::exportJSON`). They keep the `latest` order. See REQ-009.
- Ticker presets (`TickerPresetController`, `TickerPresetService`), and whether they save the sort mode.
- Any change to how Organic Posts or Standalone Ads get their `score`. Classifier output and `CategoriseSocialPosts`/`CategoriseAds` stay unchanged.
- Showing any score in the UI.

### Assumptions

- **A-1:** No LD-441 implementation exists on another branch that this spec should reconcile with. Confirmation: the human states where the "Done" work lives, or confirms that none exists.
- **A-2:** Organic Post and Standalone Ad `score` values are on the same 1–10 scale as the hardcoded signal scores. Evidence: the column defaults to 1 (`database/schema/mysql-schema.sql:1020`), and `CategoriseAds.php:203` treats `score >= 9` as "hot". The classifier prompt is outside this repository, so the upper bound is not verified. The ticket's own scenario (organic 10 ranks above signal 9) depends on this shared scale.

## Change Impact

- Added behavior: request parameters for sort mode and timeframe (REQ-001, REQ-003), Most Relevant selection and ranking (REQ-004–REQ-006), and stable cursor pagination in Most Relevant (REQ-007, REQ-008).
- Modified behavior: `TickerRequest` (`Modules/Socials/app/Http/Requests/TickerRequest.php:27-58`) accepts and validates the new parameters. `TickerRepository::fetchAll` (`Modules/Socials/app/Repositories/TickerRepository.php:59-273`) chooses the ordering and eligibility by mode.
- Explicitly preserved behavior:
  - REQ-002: a request with no sort parameter, or with `latest`, returns the same rows in the same order with the same cursor format as today. The order is `sfp.time_posted DESC, sfp.id DESC` (`TickerRepository.php:237-238`). `srch_interval` defaults to `1w` (line 72). Unknown interval keys fall back to `1 month` (line 527).
  - REQ-005: every existing filter and the access scoping apply unchanged in both modes.
  - REQ-006: the response shape (`TickerExportResource`) does not change. `sales_relevance` stays the stored `score`, and no computed signal score is exposed.
  - REQ-009: export ordering does not change.
- Compatibility/migration constraints:
  - No schema change is required by any requirement.
  - Signal rows already written by `PaidAdsTickerEventGenerator::buildEvent()` (`Modules/Advertisers/app/Services/PaidAdsTickerEventGenerator.php:711-757`) carry `score = 1` (column default). Most Relevant must rank them by event type without a backfill.
  - Clients that send no sort parameter (the current FE) keep today's behavior.

## Requirements

Terms used below:
- **Signal row:** a `social_feed_posts` row with `type = 'paid_ads_event'`. Its event type is the second element of `category_json` (`["paid_ads", "<event_type>"]`) and the fourth `:` segment of `source_post_id` (`paid-ads:{profileId}:{date}:{event_type}`). Both are written by `PaidAdsTickerEventGenerator::buildEvent()`.
- **Organic Post:** `type = 'social_post'` (`SocialFeedPostSyncService.php:98`).
- **Standalone Ad:** `type = 'paid_ads'` (`CategoriseAds.php:170`).
- **Relevance score:** for an Organic Post or Standalone Ad, the stored `social_feed_posts.score`. For a signal row, the value from the REQ-004 table.

### Requirement: REQ-001 — Sort mode parameter
Source: LD-441 Requirements ("supports two sort modes: latest and most_relevant"; "parameter names can follow existing API conventions"); LD-441 AC-1. The parameter name is pending OPEN QUESTION Q-3.

The Ticker feed endpoint accepts an optional sort-mode parameter with the values `latest` and `most_relevant`. When the parameter is absent, the mode is `latest`.

#### Scenario: Most Relevant requested
- GIVEN an authenticated user with access to the Ticker
- WHEN they request the feed with the sort mode `most_relevant`
- THEN the response is ranked and selected by REQ-003–REQ-006

#### Scenario: Sort mode absent
- GIVEN the same user
- WHEN they request the feed without the sort-mode parameter
- THEN the response is identical to a request with sort mode `latest`

#### Scenario: Unsupported sort mode
- GIVEN the same user
- WHEN they request the feed with sort mode `oldest`
- THEN the response is HTTP 422 with a validation error on the sort-mode parameter

### Requirement: REQ-002 — Latest mode is unchanged
Source: LD-441 AC-2 and AC-15 ("existing Latest behavior does not change"; "no backend regression"); LD-441 Constraints.

In `latest` mode the endpoint returns the same rows, in the same order, with the same response shape and cursor behavior as before this change. This holds for every existing parameter combination.

#### Scenario: Characterization against current behavior
- GIVEN a fixed data set of Organic Posts, Standalone Ads and signal rows of every event type (including `paid_ads_reactivated`), with mixed `score`, `value_score` and `time_posted` values
- WHEN the feed is requested in `latest` mode, with and without filters, across several pages
- THEN the row ids, their order and the `next_cursor` progression match the output of the code before this change

#### Scenario: Latest ignores Most Relevant eligibility
- GIVEN a signal row whose event type has no score in REQ-004
- WHEN the feed is requested in `latest` mode with filters that match it
- THEN the row is returned, as it is today

### Requirement: REQ-003 — Most Relevant timeframe
Source: LD-441 Requirements and AC-3/AC-4 (Last 24 Hours, Last 3 Days, Last 7 Days; "timeframe applied before relevance sorting"); LD-440 (default Last 7 Days). The parameter name and window boundary are pending OPEN QUESTIONS Q-3 and Q-4.

In `most_relevant` mode the request selects one of three timeframes: Last 24 Hours, Last 3 Days or Last 7 Days. The default is Last 7 Days. Only rows whose `time_posted` falls inside the selected window and not after the request time are candidates. Ranking happens only among those candidates.

#### Scenario: Default timeframe
- GIVEN rows posted 2, 6 and 9 days ago that otherwise qualify
- WHEN the feed is requested in `most_relevant` mode without a timeframe
- THEN the rows posted 2 and 6 days ago are returned, and the row posted 9 days ago is not

#### Scenario: Timeframe applied before ranking
- GIVEN an Organic Post with score 10 posted 2 days ago, and a signal `paid_ads_activity_reduced` (score 6) posted 2 hours ago
- WHEN the feed is requested in `most_relevant` mode with the Last 24 Hours timeframe
- THEN only the signal is returned

#### Scenario: Each supported timeframe
- GIVEN qualifying rows on both sides of each window boundary
- WHEN the feed is requested with Last 24 Hours, Last 3 Days and Last 7 Days in turn
- THEN each response holds exactly the rows inside its window, under the boundary rule settled by Q-4

#### Scenario: Unsupported timeframe in Most Relevant
- GIVEN the same user
- WHEN they request `most_relevant` with a timeframe outside the three supported values (for example `1m`)
- THEN the response is HTTP 422 with a validation error on the timeframe parameter

#### Scenario: Nothing in the timeframe
- GIVEN no qualifying rows in the selected window after filters
- WHEN the feed is requested in `most_relevant` mode
- THEN the response is HTTP 200 with an empty `data` array and no next cursor, as Latest returns for no matches today

### Requirement: REQ-004 — Most Relevant eligibility and scores
Source: LD-441 Requirements steps 3–7 and AC-5/6/7/12; LD-440 comment (Stanimir Dimitrov, 2026-09-23, `EVENT_TYPE_SCORES`). Pending OPEN QUESTIONS Q-1 (reactivated) and Q-2 (rows "without a score").

In `most_relevant` mode a candidate row is included only when it has a relevance score. Organic Posts and Standalone Ads use their stored `score`. Signal rows use this fixed table and never their stored `score`:

| Ticket name | Event type | Score |
|---|---|---|
| Ads Started | `paid_ads_started` | 9 |
| New Google Channel Started | `paid_ads_new_channel` | 9 |
| Ads Stopped | `paid_ads_stopped` | 8 |
| Google Channel Stopped | `paid_ads_channel_stopped` | 8 |
| Ads Increased | `paid_ads_activity_increase` | 7 |
| Ads Decreased | `paid_ads_activity_reduced` | 6 |
| (not in ticket) | `paid_ads_reactivated` | pending Q-1 |

A signal row whose event type is not in the table is excluded.

#### Scenario: Signal ranked by its table score, not its stored score
- GIVEN a `paid_ads_stopped` signal row with stored `score = 1`, and an Organic Post with `score = 7`, both in the window
- WHEN the feed is requested in `most_relevant` mode
- THEN the signal comes before the Organic Post

#### Scenario: Organic Post and Standalone Ad use stored score
- GIVEN an Organic Post with `score = 5` and a Standalone Ad with `score = 8`, both in the window
- WHEN the feed is requested in `most_relevant` mode
- THEN the Standalone Ad comes before the Organic Post

#### Scenario: Unsupported signal type excluded
- GIVEN a signal row with an event type not in the table, in the window and matching all filters
- WHEN the feed is requested in `most_relevant` mode
- THEN the row is not returned

#### Scenario: Each supported signal type
- GIVEN one signal row of each supported event type, all with the same `time_posted`
- WHEN the feed is requested in `most_relevant` mode
- THEN they are ordered by their table score, and rows with equal scores are ordered by `id DESC`

### Requirement: REQ-005 — Existing filters, search and access scoping apply in Most Relevant
Source: LD-441 Requirements step 2 and AC-11 ("all existing Ticker filters and search conditions are respected"); LD-441 Constraints (Categories, Source, Industry, Location, ZIP Code, CRM ID, Franchise, name search); "must not bypass or change any filter behavior".

In `most_relevant` mode every existing filter applies exactly as in `latest` mode. Most Relevant only narrows the result further (REQ-003, REQ-004). The filters are:
- `value_score` (default `high`);
- `srch_platforms`;
- `srch_category`, including signal event codes;
- `srch_business_types`;
- `srch_zip_code`, `srch_area` and `srch_city`;
- `srch_external_id`;
- `srch_franchise`;
- `srch_tags`;
- `search`, `srch_search` and `srch_q`;
- `srch_advertiser_id`.

The access scoping also applies in this mode: the user's integration ids (`Utils::getIntegrationIds`), soft-deleted advertisers and the user's hidden advertisers (`advertisers_hidden`).

#### Scenario: Result set is the Latest set narrowed, then reordered
- GIVEN a fixed data set and any one of the listed filters
- WHEN the feed is requested in both modes with that filter and the same window
- THEN every row in the `most_relevant` result also appears in the `latest` result for that window

#### Scenario: Signal category filter
- GIVEN signal rows of types `paid_ads_started` and `paid_ads_stopped`, and Organic Posts, all in the window
- WHEN the feed is requested in `most_relevant` mode with `srch_category = ["paid_ads_started"]`
- THEN only the `paid_ads_started` rows are returned

#### Scenario: Default value_score filter kept
- GIVEN an Organic Post with `value_score = 'low'` and `score = 10` in the window
- WHEN the feed is requested in `most_relevant` mode without `value_score`
- THEN the row is not returned, as in `latest` mode

#### Scenario: Hidden advertiser
- GIVEN a high-score row whose only linked advertiser the user has hidden
- WHEN the user requests the feed in `most_relevant` mode
- THEN the row is not returned

#### Scenario: Selective and broad query paths
- GIVEN one request with an advertiser-side filter (for example `srch_zip_code`) and one request without it
- WHEN both are sent in `most_relevant` mode
- THEN both results follow the REQ-006 order and the REQ-004 eligibility

### Requirement: REQ-006 — Most Relevant ordering and response
Source: LD-441 Requirements steps 8–9 and AC-8/9/10/16; LD-440 comment (Petya Zhelyazkova, 2026-09-18) scenarios; LD-440 "no score shown in the UI".

In `most_relevant` mode the eligible rows form one result set, ordered by relevance score DESC, then `time_posted` DESC, then `id` DESC. Each row's response shape is the same as in `latest` mode. No field exposes the REQ-004 signal score. `sales_relevance` stays the stored `score`.

#### Scenario: Higher score wins over recency
- GIVEN an Organic Post with `score = 10` posted 5 days ago, and a `paid_ads_started` signal posted 1 hour ago
- WHEN the feed is requested in `most_relevant` mode with Last 7 Days
- THEN the Organic Post comes first

#### Scenario: Equal score, newer first
- GIVEN two rows with relevance score 8, posted 1 hour ago and 3 hours ago
- WHEN the feed is requested in `most_relevant` mode
- THEN the row posted 1 hour ago comes first

#### Scenario: Equal score and time, higher id first, repeatable
- GIVEN two rows with relevance score 8 and the same `time_posted`, with ids 100 and 101
- WHEN the feed is requested in `most_relevant` mode twice
- THEN both responses list id 101 before id 100

#### Scenario: Signal score not exposed
- GIVEN a `paid_ads_started` signal row with stored `score = 1`
- WHEN it is returned in `most_relevant` mode
- THEN its `sales_relevance` is 1, the same as in `latest` mode, and the response has no other score field

### Requirement: REQ-007 — Stable cursor pagination in Most Relevant
Source: LD-441 Requirements step 10 and AC-13/14 ("existing pagination works"; "no duplicate or missing results"); LD-441 ("existing unique item ID can be used" as tie-breaker). The stability scope is pending OPEN QUESTIONS Q-4 and Q-5.

`most_relevant` uses the existing cursor pagination: the `srch_cursor` parameter, `meta.next_cursor` and the current page size. When all pages are walked, they hold every eligible row exactly once, in REQ-006 order.

#### Scenario: Walk all pages
- GIVEN more eligible rows than one page, with repeated scores and repeated `time_posted` values across the page boundary
- WHEN a client follows `next_cursor` until it is null
- THEN the concatenated pages equal the single ordered result, with no duplicate and no missing id

#### Scenario: New row inserted between pages
- GIVEN a client has fetched page 1
- WHEN a new eligible row is inserted that sorts before the cursor position, and the client fetches page 2
- THEN page 2 holds no row from page 1, and no row that sorted after the cursor is skipped

### Requirement: REQ-008 — Cursor from another sort mode is rejected
Source: derived from REQ-007. A cursor holds the sort-key values of its mode, so a cursor from the other mode cannot be positioned. This failure case is proposed here for approval.

When `srch_cursor` was issued under the other sort mode, or does not hold the keys of the requested mode, the endpoint responds with HTTP 422 and a validation error on `srch_cursor`. It never responds with a server error.

#### Scenario: Latest cursor sent with Most Relevant
- GIVEN a `next_cursor` from a `latest` response
- WHEN it is sent with sort mode `most_relevant`
- THEN the response is HTTP 422 with an error on `srch_cursor`

#### Scenario: Most Relevant cursor sent with Latest
- GIVEN a `next_cursor` from a `most_relevant` response
- WHEN it is sent without a sort mode
- THEN the response is HTTP 422 with an error on `srch_cursor`

### Requirement: REQ-009 — Exports keep Latest ordering
Source: scope decision in this spec. The ticket covers the feed only. Exports share `TickerRepository::fetchAll` through `TickerService::exportJSON` (`Modules/Socials/app/Services/TickerService.php:37-50`).

Ticker exports (JSON, CSV and generated export links) return the same rows in the same order as before this change, even when a sort-mode parameter is present in the export request.

#### Scenario: Export with sort parameter
- GIVEN an export request that carries sort mode `most_relevant`
- WHEN the export runs
- THEN its rows and order equal the export without that parameter

### Requirement: REQ-010 — Most Relevant response time
Source: operational requirement (spec-quality-gates §1, performance). `social_feed_posts` has no index that includes `score` (`database/schema/mysql-schema.sql:1026-1033`). Ranking by score cannot reuse the `time_posted DESC, id DESC` indexes that serve `latest`. The threshold is pending OPEN QUESTION Q-6.

The first page of a `most_relevant` request stays within the agreed latency threshold for the Q-6 workload.

#### Scenario: Broad feed, Last 7 Days
- GIVEN production-sized `social_feed_posts` data in the Q-6 environment
- WHEN an admin user (no integration restriction) requests the first page in `most_relevant` mode with Last 7 Days and no other filter
- THEN the measured p95 server time meets the Q-6 threshold

## Material Decisions

None yet. Each resolved OPEN QUESTION below becomes a `DEC-###` here.

## Tech Stack

- PHP 8.4, Laravel (`composer show --direct` gives exact versions; not run for this spec), nwidart-style `Modules/` layout.
- MySQL. Query building with `DB::query()` / `Illuminate\Database\Query\Builder`. Cursor pagination with `cursorPaginate`.
- Pest for tests.

## Commands

Found in source. None of them was executed for this spec.
- Test suite (per CLAUDE.md, multi-worktree): `composer test -- --filter=Ticker`. `composer.json:101-104` maps `test` to `bin/worktree-test.sh`. **That script, the `bin/` directory and `.env.testing` are missing in this checkout**, so this command cannot run here as is. /plan must resolve this.
- Single worktree (CLAUDE.md): `php artisan test --compact --filter=Ticker`.
- Format: `vendor/bin/pint --dirty --format agent`.
- Static analysis (module-architecture skill): `vendor/bin/phpstan analyse` and `vendor/bin/deptrac analyse --config-file=deptrac.yaml`.

## Project Structure

- `Modules/Socials/routes/api.php:79`: route `socials.ticker.index`, FE name `api.socials.ticker.index`.
- `Modules/Socials/app/Http/Controllers/Api/TickerController.php:32-37`: thin controller.
- `Modules/Socials/app/Http/Requests/TickerRequest.php`: validation.
- `Modules/Socials/app/Services/TickerService.php`: forces `per_page = 200` for the feed. `exportJSON` serves exports.
- `Modules/Socials/app/Repositories/TickerRepository.php`: query, filters, ordering and `cursorPaginate`. It deviates from the module-architecture chain (pagination in the repository, no Builder class). These deviations already exist and are out of scope.
- `Modules/Socials/app/Http/Resources/TickerExportResource.php`: response shape.
- `Modules/Advertisers/app/Services/PaidAdsTickerEventGenerator.php`: signal row writer (read-only for this spec).

## Code Style

Follow `.ai/rules/app.md`, `controllers.md`, `controllers-api.md`, `routes.md`, `http.md` and `services-repositories.md`, plus `.ai/rules/repositories.md`. That last rule requires `cursorPaginate()` for the ticker feed and overrides the generic `paginate()` rule for this file. The existing ticker request-to-repository flow passes a `ValidatedInput` or array, which `.ai/rules/app.md` allows for this existing code. Keep that flow rather than adding a DTO for two parameters. The module-architecture skill is at `.ai/skills/module-architecture/SKILL.md`.

## Testing Strategy

No ticker test exists today. `tests/` is absent, and `Modules/Socials/tests/` holds only `.gitkeep`. Tests go in `tests/Feature/Socials/` (`phpunit.xml` suite `./tests/Feature`, module-architecture skill). They hit the HTTP endpoint as an authenticated user.

- **New feature-specific decision:** add a `SocialFeedPost` factory in `Modules/Socials/database/factories/`. No precedent was found for it. Every requirement needs controlled rows, and no factory exists. It needs states for `social_post`, `paid_ads` and a signal row of a given event type. Note: `type` is not in `SocialFeedPost::$fillable`.
- **REQ-002 first:** write the Latest characterization test before any production change. Run it green against the current code and keep it unchanged after the change. Without this test, nothing proves "no regression".
- REQ-001, REQ-003, REQ-004, REQ-006, REQ-008: one feature test per scenario. Assert ids and order.
- REQ-005: one test per listed filter or scoping rule, run in both modes. Assert the narrowing relation and the named scenarios. Cover the selective and broad query paths.
- REQ-007: a small page size through the repository (the service forces 200), or ≥ 201 rows through the endpoint. Walk all pages and compare with the unpaged order. The insert-between-pages scenario inserts a row between requests.
- REQ-009: export-path test comparing output with and without the sort parameter.
- REQ-010: measured outside the test suite, under the Q-6 method. Evidence is recorded for /review, not as a Pest test.

## Invariants and Mechanism Proof

Invariant (REQ-007): for a fixed `most_relevant` request, the pages together list each eligible row exactly once, in the total order `(relevance score DESC, time_posted DESC, id DESC)`.

- **Total order:** `id` is the primary key, so the three-key order has no ties. Keyset (cursor) pagination over a total order returns each row at most once and skips none, provided each row's key values and eligibility do not change between page requests.
- **Writers that can break the proviso:**
  1. `SocialFeedPostSyncService` upserts can rewrite `score`, `time_posted`, `value_score`, `category_json` and `type` of an existing row (`SocialFeedPostSyncService.php:116-134`). A row that moves across the cursor position between pages can appear twice or not at all. `latest` mode has the same exposure today through `time_posted`.
  2. The timeframe lower bound. If it moves with the request time, a row can drop out of the window between page 1 and page 2. Today the bound is `startOfDay(now − interval)` (`TickerRepository.php:91-96`), so it moves only at midnight.
  3. New inserts. These are safe: a new row either sorts before the cursor (never shown to this walk) or after it (shown once).
- **Status:** the guarantee holds for writer 3. Writers 1 and 2 depend on Q-4 and Q-5. Until they are resolved, the invariant is unresolved, and this spec cannot be approved.
- **Evidence:** the REQ-007 tests, plus a test for whatever Q-4/Q-5 settles (window anchoring, key mutation).

## Data Lifecycle

N/A. This change reads `social_feed_posts` only and adds no lifecycle field. Soft-deleted advertisers are already excluded by the existing scoping, which REQ-005 preserves.

## Boundaries

- Always: keep `latest` byte-for-byte compatible (REQ-002). Apply filters before ranking. Keep signal scores out of responses.
- Ask first: any schema change (a new column or index on `social_feed_posts`, which needs `./bin/schema-refresh.sh`). Any write to `social_feed_posts.score` for signal rows. Any change to `PaidAdsTickerEventGenerator`.
- Never: migrate, truncate or seed the `leadbuster` database. Change Organic Post or Standalone Ad scoring. Expose signal scores in the API.

### Documentation affected (for /plan)

- `docs/USER-GUIDE.md:261,622,688` (Ticker feed, "Sales relevance") describes the feed. Update it after implementation lands.
- `.ai/rules/ticker-page.md:9` says "rows with no type are single ads". `CategoriseAds.php:170` writes `type = 'paid_ads'`. Reconcile this through Q-2.

## Open Questions

```
OPEN QUESTION Q-1: Is `paid_ads_reactivated` eligible in Most Relevant?
- Option A: exclude it. The ticket's signal list omits it; REQ-004 excludes unlisted types.
- Option B: include it with score 9, as in the LD-440 implementation comment (`EVENT_TYPE_SCORES`).
  The generator writes it in the same branch as `paid_ads_started` (PaidAdsTickerEventGenerator.php:572),
  so it is a "started again" event.
→ Recommendation: B. Product (LD-440 owner) must confirm. Affects REQ-004.
```

```
OPEN QUESTION Q-2: What does "no relevance score" mean, given `score` is NOT NULL DEFAULT 1?
Repository fact: every row has a score; signal rows carry the default 1. No row has a NULL score.
- Option A: every non-signal row is eligible with its stored score. Only signal rows with an
  unsupported event type are excluded. Rows with NULL or legacy `type` count as non-signal.
- Option B: only `type IN ('social_post','paid_ads')` and supported signals are eligible.
  Rows with NULL/other `type` are excluded.
- Option C: also treat `score = 1` (the default) as "no score" and exclude those rows.
  Risk: drops genuinely low-scored posts and ads.
→ Recommendation: A. It keeps Most Relevant a pure narrowing of Latest. Affects REQ-004, REQ-005.
  Do NULL-`type` rows still exist in production? (Not checked: Boost DB tool is down.)
```

```
OPEN QUESTION Q-3: Request parameter names and values (public contract shared with LD-442 FE)
- Option A: `srch_sort` = `latest` | `most_relevant` (default `latest`). Timeframe reuses `srch_interval`.
  In `most_relevant`, `srch_interval` may only be `24h` | `3d` | `7d`, with `7d` as a new key equal to
  `1w`. The default is `7d`. Matches the existing `srch_*` convention and the existing `24h`/`3d` keys.
- Option B: `srch_sort` plus a new `srch_timeframe` = `24h` | `3d` | `7d`. `srch_interval` is ignored
  in `most_relevant`. This keeps the two meanings apart, but the FE must send a second time parameter.
→ Recommendation: A. If LD-442 FE code exists elsewhere, its names win. Affects REQ-001, REQ-003, REQ-008.
```

```
OPEN QUESTION Q-4: Timeframe window boundary
Today `srch_interval` starts at startOfDay(now − interval). So "24h" at 15:00 covers from 00:00 yesterday (~39h).
- Option A: reuse that boundary. Consistent with Latest, and the bound moves only at midnight,
  which keeps pages stable during the day. "Last 24 Hours" then means "since yesterday 00:00".
- Option B: rolling window, exactly now − 24h / 72h / 168h. Matches the labels.
  The bound moves on every request, so rows can drop out between pages, unless the window start
  is fixed on page 1 and carried with the cursor (extra contract surface).
→ Recommendation: A, for stability and consistency. Product must accept the label mismatch.
  Affects REQ-003, REQ-007 and the invariant.
```

```
OPEN QUESTION Q-5: Pagination stability scope when a row's score or time changes mid-walk
`SocialFeedPostSyncService` upserts can rewrite `score` and `time_posted` of existing rows. Latest has the same exposure today.
- Option A: guarantee stability only for rows whose sort keys and eligibility do not change between
  page requests, the same guarantee Latest gives today. Explicit narrowing of AC-14.
- Option B: full snapshot stability (for example, freeze the candidate set on page 1).
  Needs new state or storage. This is a much larger change.
→ Recommendation: A. Needs explicit human acceptance because it narrows "no duplicate or missing results". Affects REQ-007.
```

```
OPEN QUESTION Q-6: Performance threshold for REQ-010
No index covers `score`, so ranking a 7-day broad window needs a sort of every candidate row.
- Proposed: first-page p95 server time ≤ 2× the `latest` p95 for the same filters and window.
  Workload: broad feed (admin, no filters), Last 7 Days, 200 rows per page. Environment: staging with
  production-sized `social_feed_posts`. Method: 20 warm requests per mode, timed server-side.
- Alternative: give an absolute budget (for example ≤ 1.5 s), or exclude performance from this ticket.
→ Decision needed: threshold, environment, and whether an index (schema change, Ask-first) is in bounds.
```
