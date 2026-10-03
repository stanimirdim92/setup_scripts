# Spec: Ticker Latest / Most Relevant Sorting (Backend)

Status: Approved
Ticket: LD-441
Change kind: Modify
Supersedes: N/A
Approved by: Stanimir Dimitrov (this session)
Approved at: 2026-09-17 (editorial revision same day: Commands and Data Lifecycle corrected — `./bin/schema-refresh.sh` is a post-deployment step, not a development one, per `bin/worktree-test.sh:33-46`. No requirement, scenario or decision changed; approval retained.)
Reapproved at: 2026-09-18 by Stanimir Dimitrov — **behavioral revision** from review/verification findings. (a) An unmapped event type now throws instead of scoring 1 (REQ-004). (b) `BackfillSocialFeedPostsCommand` now copies the source `score` into `social_feed_posts`, so backfilled organic posts rank on their real relevance instead of the default 1 (bears on REQ-003, REQ-005). Both reconciled into REQ-004's text before reapproval.
Reapproved at: 2026-09-17 by Stanimir Dimitrov — **behavioral revision**. DEC-005 reversed: `paid_ads_reactivated` is assigned score 9 and participates in Most Relevant. Affected REQ-003, REQ-004, REQ-008 and DEC-005; all four reconciled before reapproval.

## Objective

Extend the Ticker backend so the feed can be returned in two orderings: the existing chronological **Latest**, and a new **Most Relevant** that ranks organic posts, standalone ads and supported paid-ads signals together by relevance score within a selected timeframe.

Relevance for organic posts and standalone ads is the score the AI categorisation pipeline already writes. Relevance for signals is a fixed per-event-type value, which this change starts persisting to the database at event-generation time so that a single `ORDER BY` can rank all three item classes without a query-time `CASE` expression.

Out of scope:
- The Latest/Most Relevant tabs, the timeframe dropdown and filter-state preservation in the UI — LD-442 owns those.
- Any change to how organic-post or standalone-ad relevance scores are calculated (LD-441: *"No change to the current Standalone Ad scoring logic is required."*).
- Backfilling `score` on paid-ads event rows that already exist — see DEC-002.
- Displaying any score in the UI (LD-440, LD-442 both forbid it).

## Change Impact

- **Added behavior:** a `srch_sort` request parameter selecting the ordering mode (REQ-001); a relevance ordering with a deterministic tie-break (REQ-005); a signal-type exclusion applied only in Most Relevant mode (REQ-003). `srch_sort` is the only new request parameter — the candidate window reuses the existing `srch_interval` filter unchanged (REQ-002, DEC-006).
- **Modified behavior:**
  - `PaidAdsTickerEventGenerator` now sets `social_feed_posts.score` on the event rows it inserts, where today it sets only `value_score => 'high'` and lets `score` fall to the column default `1` (REQ-004). `Modules/Advertisers/app/Services/PaidAdsTickerEventGenerator.php:735-756`.
  - As a consequence, the `sales_relevance` field of the Ticker API payload and the `score` column of the CSV export take values 6–9 rather than `1` for **newly generated** paid-ads event rows (REQ-009). `Modules/Socials/app/Http/Resources/TickerExportResource.php:40`, `TickerExportOldResource.php:60`, `Modules/Socials/app/Jobs/TickerPostsExport.php:223`.
- **Removed behavior:** none.
- **Renamed behavior:** none.
- **Explicitly preserved behavior** (pinned by REQ-008):
  - Latest ordering stays `sfp.time_posted DESC, sfp.id DESC` (`TickerRepository.php:237-238`).
  - Latest item inclusion is unchanged — no signal-type exclusion is applied when `srch_sort` is absent or `latest`.
  - The default-on `value_score = 'high'` gate (`TickerRepository.php:79, 222-224`) stays in force in both modes.
  - The `srch_interval` filter keeps its current meaning, default (`1w`) and full key set in both modes; it is not repurposed as the relevance timeframe (see DEC-006).
  - `cursorPaginate(cursorName: 'srch_cursor')` remains the pagination mechanism (`TickerRepository.php:252-257`), per `.ai/rules/repositories.md:9`.
  - The export paths (`skip_pagination`, `query_only`) are unaffected.
- **Compatibility/migration constraints:** paid-ads event rows written before this change retain `score = 1` and are not backfilled (DEC-002). Because the widest Most Relevant timeframe is 7 days, such rows leave the Most Relevant candidate pool within 7 days of deployment. During that window they rank below every scored item. `persistEvents` uses `insertOrIgnore` (`PaidAdsTickerEventGenerator.php:986`), so regeneration does not update them.

## Requirements

### Requirement: REQ-001 — `srch_sort` selects the feed ordering mode
Source: LD-441 §Sorting Modes (`latest`, `most_relevant`, *"The exact parameter naming can follow the existing API conventions"*); parameter name follows the endpoint's existing `srch_*` convention (`TickerRequest.php:27-58`).

The Ticker index endpoint accepts an optional `srch_sort` parameter with the values `latest` and `most_relevant`. Absent or `latest` produces today's chronological feed; `most_relevant` produces the relevance-ranked feed.

#### Scenario: Parameter absent yields the existing feed
- GIVEN a request to the Ticker index endpoint with no `srch_sort` parameter
- WHEN the feed is fetched
- THEN the result is ordered by `time_posted DESC, id DESC` and contains exactly the items it contains today

#### Scenario: Explicit latest is equivalent to absent
- GIVEN two otherwise identical requests, one with no `srch_sort` and one with `srch_sort=latest`
- WHEN both feeds are fetched
- THEN both return the same items in the same order

#### Scenario: Unsupported value is rejected
- GIVEN a request with `srch_sort=popular`
- WHEN the request is validated
- THEN the response is HTTP 422 and names `srch_sort`

### Requirement: REQ-002 — The existing `srch_interval` filter bounds the Most Relevant candidate pool
Source: LD-441 §Most Relevant Timeframes (Last 24 Hours / Last 3 Days / Last 7 Days, *"must restrict the candidate items before relevance sorting is applied"*); LD-440 AC (*"Last 7 Days is the default Most Relevant timeframe"*); user decision 2026-09-17 to reuse `srch_interval` rather than add a parameter (DEC-006) and to retain its `startOfDay` semantics (DEC-007).

Most Relevant introduces no timeframe parameter of its own. The candidate window is the existing `srch_interval` filter, unchanged in meaning, default and key set. The frontend's three timeframe options map onto existing keys: Last 24 Hours → `24h`, Last 3 Days → `3d`, Last 7 Days → `1w`. `srch_interval` already defaults to `1w` (`TickerRepository.php:72`), which is the required Most Relevant default, and the window is already applied before ordering (`TickerRepository.php:226-227`), satisfying "restrict the candidate items before relevance sorting is applied".

The window continues to be computed as `now - interval` truncated by `->startOfDay()` (`TickerRepository.php:91-96`). Per DEC-007 this is deliberate: `24h` therefore means "since 00:00 yesterday", between 24 and 48 hours of data depending on the time of day, not a rolling 24 hours. The same rule already governs the Latest feed.

#### Scenario: Default window is 7 days
- GIVEN a request with `srch_sort=most_relevant` and no `srch_interval`
- WHEN the feed is fetched
- THEN the candidate pool is bounded by the `1w` window, the existing default

#### Scenario: Narrower window excludes older items
- GIVEN an eligible organic post with `time_posted` 4 days ago and score 10
- WHEN the feed is fetched with `srch_sort=most_relevant&srch_interval=24h`
- THEN that post does not appear in the result

#### Scenario: Window boundary is start-of-day, not rolling
- GIVEN the current time is 18:00 and an eligible item was posted at 09:00 the previous day, 33 hours earlier
- WHEN the feed is fetched with `srch_sort=most_relevant&srch_interval=24h`
- THEN the item is included, because the window begins at 00:00 of the previous day

#### Scenario: Interval keys behave identically in both modes
- GIVEN the same `srch_interval` value
- WHEN the feed is fetched once in `latest` mode and once in `most_relevant` mode
- THEN both requests consider the same set of candidate items, differing only in ordering and in the signal-type exclusion of REQ-003

#### Scenario: Interval keys outside the three UI options remain valid
- GIVEN a request with `srch_sort=most_relevant&srch_interval=1m`
- WHEN the request is validated and the feed fetched
- THEN the request is accepted and ranked over a one-month window; the three timeframes named in LD-441 are the options the UI offers, not a restriction the API enforces

### Requirement: REQ-003 — Only eligible item types participate in Most Relevant
Source: LD-441 §Most Relevant Logic step 3 and step 7 (*"Exclude items that do not have a relevance score and are not one of the supported Signal types listed above"*); DEC-003; DEC-005.

In `most_relevant` mode the eligibility rule is expressed as an **exclusion of unsupported signals**, not as an inclusion list of organic/ad types: a row participates unless it is a `paid_ads_event` whose event type is outside the supported list. Since DEC-005's reversal that list covers all seven event types the generator emits, so the rule excludes nothing in today's data. It is retained as the guard that keeps a future event type out of Most Relevant until it is scored and added deliberately.

The rule must be written this way because `social_feed_posts.type` is nullable and organic posts do **not** all carry `'social_post'`. Three write paths set it (`SocialFeedPostSyncService.php:98` → `'social_post'`, `CategoriseAds.php:170` → `'paid_ads'`, `PaidAdsTickerEventGenerator.php:753` → `'paid_ads_event'`), but a fourth, `BackfillSocialFeedPostsCommand.php:198-217`, inserts organic posts via `insertOrIgnoreUsing` with `type` absent from its column list entirely, leaving those rows at the column default `NULL` (`type varchar(45) DEFAULT NULL`). An inclusion whitelist of `type IN ('social_post','paid_ads')` would therefore silently drop every backfilled organic post from Most Relevant.

#### Scenario: Supported signal participates
- GIVEN a `paid_ads_event` row whose event type is `paid_ads_started`, inside the selected window
- WHEN the feed is fetched in `most_relevant` mode
- THEN the row appears in the result

#### Scenario: Reactivation signal participates
- GIVEN a `paid_ads_event` row whose event type is `paid_ads_reactivated`, inside the selected window
- WHEN the feed is fetched in `most_relevant` mode
- THEN the row appears in the result, ranked on score 9

#### Scenario: A signal type outside the supported list is excluded from Most Relevant
- GIVEN a `paid_ads_event` row whose event type is not in the supported list, inside the selected window
- WHEN the feed is fetched in `most_relevant` mode
- THEN the row does not appear in the result

#### Scenario: A signal type outside the supported list still appears in Latest
- GIVEN that same row
- WHEN the feed is fetched in `latest` mode
- THEN the row appears exactly as it does today

#### Scenario: Organic posts and standalone ads participate on their stored score
- GIVEN an organic post with score 10 and a standalone ad with score 9, both inside the window
- WHEN the feed is fetched in `most_relevant` mode
- THEN both appear, the post ranked above the ad

#### Scenario: Organic post with a NULL type still participates
- GIVEN an organic post row whose `type` is `NULL`, as written by `BackfillSocialFeedPostsCommand`, inside the window and passing the `value_score` gate
- WHEN the feed is fetched in `most_relevant` mode
- THEN the row appears in the result, ranked by its stored `score`

### Requirement: REQ-004 — Paid-ads signal relevance scores are persisted at generation time
Source: user decision, 2026-09-17 (*"fix all events scoring when saving in DB with the scores from the table"*); score values from LD-441 §Relevance Scores and §Signal Ranking, confirmed by the user in conversation.

`PaidAdsTickerEventGenerator` sets `score` on every paid-ads event row it inserts, using a fixed per-event-type mapping that covers all seven event types. A type added later without a mapped value raises `UnexpectedValueException` rather than falling back to the column default, matching the behaviour of the sibling `eventTypePriority()` for the same keyspace: a type present in `EVENT_TYPE_PRIORITIES` but absent from `EVENT_TYPE_SCORES` is a programming error, and silently persisting it at `1` would both mis-rank it and hide the mistake.

| Event type (code) | Signal (ticket) | Score |
| --- | --- | --- |
| `paid_ads_started` | Ads Started | 9 |
| `paid_ads_new_channel` | New Google Channel Started | 9 |
| `paid_ads_stopped` | Ads Stopped | 8 |
| `paid_ads_channel_stopped` | Google Channel Stopped | 8 |
| `paid_ads_activity_increase` | Ads Increased | 7 |
| `paid_ads_activity_reduced` | Ads Decreased | 6 |
| `paid_ads_reactivated` | — (not in ticket; scored by human decision) | 9 |

Event-type codes verified against `PaidAdsTickerEventGenerator::EVENT_TYPE_PRIORITIES` (`Modules/Advertisers/app/Services/PaidAdsTickerEventGenerator.php:59-67`).

#### Scenario: Generated signal carries its mapped score
- GIVEN the generator produces a `paid_ads_activity_increase` event
- WHEN the event row is persisted to `social_feed_posts`
- THEN its `score` column is `7`

#### Scenario: Each supported type maps to its table value
- GIVEN the generator produces one event of each supported type
- WHEN the rows are persisted
- THEN their scores are 9, 9, 9, 8, 8, 7 and 6 respectively, per the table above

#### Scenario: Reactivation carries the same score as a start
- GIVEN the generator produces a `paid_ads_reactivated` event
- WHEN the event row is persisted
- THEN its `score` column is `9`

#### Scenario: Existing rows are not rewritten
- GIVEN a `paid_ads_started` row already present with `score = 1`
- WHEN the generator runs again and the row's unique key already exists
- THEN `insertOrIgnore` leaves the existing row untouched, including its `score`

### Requirement: REQ-005 — Most Relevant ordering with a deterministic tie-break
Source: LD-441 §Most Relevant Logic step 9 (`score DESC`, `timestamp DESC`) and §Pagination (*"If an additional deterministic tie-breaker is technically required... the existing unique item identifier can be used"*).

In `most_relevant` mode, eligible items are ordered by `score DESC`, then `time_posted DESC`, then `id DESC`. All three item classes are ranked against each other in a single result set.

#### Scenario: Higher score ranks first regardless of type
- GIVEN an organic post with score 10 posted 5 days ago and a `paid_ads_started` signal with score 9 detected 1 hour ago, both in the window
- WHEN the feed is fetched in `most_relevant` mode
- THEN the organic post is returned before the signal

#### Scenario: Equal scores fall back to recency
- GIVEN two items both with score 9 and different `time_posted`
- WHEN the feed is fetched in `most_relevant` mode
- THEN the newer item is returned first

#### Scenario: Equal score and timestamp fall back to identifier
- GIVEN two items with identical `score` and identical `time_posted`
- WHEN the feed is fetched in `most_relevant` mode
- THEN they are returned in descending `id` order, and that order is identical on every repeated request

### Requirement: REQ-006 — Cursor pagination is stable under relevance ordering
Source: LD-441 §Pagination (no duplicates, no missing items, no unexpected order changes) and BE AC (*"Pagination remains stable and does not produce duplicated or missing results"*); `.ai/rules/repositories.md:9`.

Most Relevant paginates through the same `cursorPaginate(cursorName: 'srch_cursor')` mechanism as Latest, with the cursor derived from the full ordering triple so that no row can be duplicated across pages or skipped between them.

#### Scenario: Full traversal yields every item exactly once
- GIVEN a Most Relevant result set of 250 eligible items and a page size of 200
- WHEN every page is fetched by following `next_cursor` to exhaustion
- THEN each of the 250 items appears exactly once across the pages, in non-increasing `(score, time_posted, id)` order

#### Scenario: Page boundary within a score tie is not duplicated
- GIVEN more items sharing a single score value than fit on one page, so a page boundary falls inside that tie group
- WHEN the next page is fetched using the returned cursor
- THEN no item from the previous page reappears and no item between the two pages is skipped

### Requirement: REQ-007 — Existing filters and search apply unchanged in Most Relevant
Source: LD-441 §Filters (*"It must not bypass or alter existing filter behavior"*); LD-440 §Filters & Search. The `value_score` gate below is specified as behavior to preserve today, not as behavior expected to last — see DEC-008.

Every filter and search condition the Ticker supports today is applied identically in `most_relevant` mode. The sorting mode changes ordering and item-type eligibility only.

#### Scenario: Advertiser-scoped filters still constrain the relevance pool
- GIVEN a Most Relevant request carrying `srch_zip_code`, `srch_business_types` or `srch_franchise`
- WHEN the feed is fetched
- THEN only items whose advertiser satisfies those conditions are returned

#### Scenario: Search term still constrains the relevance pool
- GIVEN a Most Relevant request carrying `srch_search`
- WHEN the feed is fetched
- THEN only items whose advertiser matches the search term are returned

#### Scenario: Default value_score gate remains in force
- GIVEN an item with `value_score` other than `high`, inside the window and otherwise eligible
- WHEN the feed is fetched in `most_relevant` mode with no `value_score` parameter
- THEN the item is not returned, matching the Latest feed's default gate

#### Scenario: Category filter still constrains the relevance pool
- GIVEN a Most Relevant request carrying `srch_category`
- WHEN the feed is fetched
- THEN only items whose `category_json` overlaps the requested categories are returned

#### Scenario: Advertiser eligibility and per-user scoping are not bypassed
- GIVEN a user whose integrations grant access to a subset of advertisers, and an advertiser that user has hidden (`advertisers_hidden`)
- WHEN the feed is fetched in `most_relevant` mode
- THEN only items belonging to advertisers that user may see are returned, hidden and soft-deleted advertisers are excluded, and the result is scoped identically to the Latest feed for the same user

### Requirement: REQ-008 — The Latest feed is preserved
Source: LD-441 §Latest Logic (*"The implementation of Most Relevant must not modify the existing Latest ranking or item inclusion logic"*) and BE AC (*"No backend regression is introduced to the current Latest feed"*).

Latest keeps its ordering, its item inclusion, its filter defaults and its pagination behavior exactly as they are today. The item-type eligibility filter of REQ-003 and the ordering of REQ-005 apply only when `srch_sort=most_relevant`.

#### Scenario: Latest ordering is unchanged
- GIVEN any set of feed items
- WHEN the feed is fetched in `latest` mode
- THEN items are ordered by `time_posted DESC, id DESC`

#### Scenario: Latest inclusion is unchanged
- GIVEN feed rows of every type, including `paid_ads_event` rows of every event type and items with `score = 1`
- WHEN the feed is fetched in `latest` mode
- THEN every row that is returned today is still returned

#### Scenario: Export paths are unaffected
- GIVEN an export request using `skip_pagination` or `query_only`
- WHEN the export runs
- THEN its result set and ordering are unchanged by this feature

### Requirement: REQ-009 — Signal scores surface only through the existing score field
Source: LD-441 BE AC (*"Signal scores do not need to be returned as UI-facing values unless technically required"*); LD-442 (no score displayed anywhere in the UI); DEC-004.

No new score field is added to the API payload or the CSV export. Because the hardcoded values are stored in the existing `score` column, newly generated paid-ads event rows report those values through the existing `sales_relevance` field and export column instead of `1`.

#### Scenario: No new payload field
- GIVEN a Most Relevant response
- WHEN its item payload is inspected
- THEN it contains the same keys as a Latest response, with no additional relevance or ranking field

#### Scenario: Newly generated signals report their stored score
- GIVEN a `paid_ads_stopped` row generated after this change
- WHEN it is serialized by `TickerExportResource`
- THEN its `sales_relevance` is `8`

### Requirement: REQ-010 — Most Relevant ordering is index-supported
Source: LD-441 BE AC (*"No backend regression is introduced to the current Latest feed"*) plus schema inspection — see the note below; no ticket text covers query performance, so this requirement exists because the repository evidence shows the new ordering has no index behind it.

Every index on `social_feed_posts` that serves the feed today terminates in `time_posted DESC, id DESC`, matching the current `ORDER BY` exactly: `idx_sfp_value_posted (value_score, time_posted DESC, id DESC, platform, source_profile_id)`, `idx_sfp_profile_value_posted`, `idx_sfp_profile_value_category_posted` (`database/schema/mysql-schema.sql`). **No index contains `score`.** Ordering by `score DESC, time_posted DESC, id DESC` therefore cannot be served by an existing index and will sort the whole candidate set.

The Most Relevant ordering must be backed by an index covering the leading filter and ordering columns, so that the feature does not degrade the shared `social_feed_posts` table for the Latest feed that queries it concurrently.

The index must not depend on `value_score` as a leading column. Every existing feed index leads with `value_score`, but that column is scheduled for removal (DEC-008); an index designed around it would have to be dropped and rebuilt, taking Most Relevant's ordering support with it. The exact column list is a technical decision for `/plan` to settle against `EXPLAIN` output — this requirement fixes the outcome and the forward constraint, not the DDL.

#### Scenario: Ordering does not fall back to a full sort of the candidate set
- GIVEN a Most Relevant query at the default 7-day window with no additional filters
- WHEN its execution plan is inspected with `EXPLAIN`
- THEN the plan shows an index serving the ordering, with no full-table scan of `social_feed_posts`

#### Scenario: Index survives the removal of `value_score`
- GIVEN the index added for the ordering above
- WHEN `value_score` is dropped from `social_feed_posts` at a later date
- THEN the index remains valid and continues to serve the Most Relevant ordering without being rebuilt

#### Scenario: Latest keeps its existing plan
- GIVEN any index added for the ordering above
- WHEN a Latest query's execution plan is inspected
- THEN it still uses the `time_posted DESC, id DESC` index it uses today, unchanged

A timed comparison against the Latest feed on production-like data would be stronger evidence than `EXPLAIN` alone, but no such environment has been established in this work. `/plan` should add a measured first-page latency check if staging with representative volume is available, and record it as unavailable if not — rather than this spec pinning an absolute threshold to an environment nobody has confirmed exists. The local `leadbuster` database has zero rows in `social_feed_posts`, so it cannot serve that purpose.

## Material Decisions

### DEC-001 — Signal scores are stored in the database rather than applied at query time
- Decision: `PaidAdsTickerEventGenerator` writes the fixed per-type score into `social_feed_posts.score` when it inserts an event row. The Most Relevant query then sorts on the stored column with no `CASE` expression.
- Alternatives: apply the mapping as a query-time `CASE WHEN` in `TickerRepository`, leaving `score = 1` in the database.
- Reason: explicit user instruction. It also keeps the ordering expression a plain column sort, which matters for the cursor-stability argument in REQ-006, since `cursorPaginate` derives its cursor from the `ORDER BY` columns.
- Source: user decision in conversation, 2026-09-17.
- Affects: REQ-004, REQ-005, REQ-009.

### DEC-002 — Existing paid-ads event rows are not backfilled
- Decision: event rows already in `social_feed_posts` keep `score = 1`. No backfill migration or one-off command is included.
- Alternatives: a backfill migration, or an Artisan command to rescore historical event rows.
- Reason: explicit user decision (*"existing records are ok like that"*). The exposure is time-bounded: the widest Most Relevant window is 7 days, so unscored historical events leave the candidate pool within 7 days of deployment. `persistEvents` uses `insertOrIgnore` (`PaidAdsTickerEventGenerator.php:986`), so they will not be corrected by regeneration either.
- Source: user decision in conversation, 2026-09-17.
- Affects: REQ-004, REQ-006.

### DEC-003 — "No relevance score" is an item-type condition, not a score-value condition
- Decision: the exclusion rule is implemented against item/event type — specifically as an exclusion of unsupported `paid_ads_event` rows (see REQ-003 for why an inclusion whitelist is unsafe). No row is excluded on the basis of its numeric score.
- Alternatives: treat `score = 1` as "unscored" and filter those rows out of Most Relevant.
- Reason: `social_feed_posts.score` is `smallint unsigned NOT NULL DEFAULT '1'` (`database/schema/mysql-schema.sql:1020`), so no row can lack a value and a not-yet-scored row is indistinguishable from a genuinely-scored-1 row. The ticket's own wording is conjunctive — *"items that do not have a relevance score **and are not one of the supported Signal types**"* — which the type-based exclusion satisfies. Filtering on `score > 1` would silently drop genuinely low-relevance posts.
- Source: LD-441 §Most Relevant Logic step 7; schema inspection.
- Affects: REQ-003.

### DEC-004 — The `sales_relevance` change on event rows is accepted, not a Latest regression
- Decision: newly generated paid-ads event rows will report `sales_relevance` 6–9 instead of `1` in the API payload and CSV export. This is accepted as an intended consequence of DEC-001.
- Alternatives: apply scores at query time only (DEC-001's alternative), keeping the stored value and therefore the payload at `1`.
- Reason: DEC-001 makes the stored score the single source of ranking truth, and `score` is already exposed as `sales_relevance`. Latest's *ordering* and *inclusion* are untouched, which is what LD-441's no-regression criterion protects; the payload value is a deliberate data correction, since `1` was never a meaningful relevance value for a signal.
- Source: user decision in conversation (DEC-001), traced to `TickerExportResource.php:40`, `TickerExportOldResource.php:60`, `TickerPostsExport.php:223`.
- Affects: REQ-008, REQ-009.

### DEC-005 — `paid_ads_reactivated` scores 9 and participates in Most Relevant
- Decision: the seventh event type defined by the generator is assigned score 9 — the same value as `paid_ads_started` — and ranks in Most Relevant alongside the other six. All seven event types are therefore supported.
- Alternatives: leave it unscored and excluded, as this decision originally read; or give it a value of its own between 9 and 6.
- Reason: explicit human decision, 2026-09-17. `paid_ads_reactivated` is the delayed form of `paid_ads_started` — the generator treats the two as mutually exclusive branches of the same transition (`PaidAdsTickerEventGenerator.php:588`) — so ranking a return to advertising below a first start had no product justification. The original exclusion recorded the absence of a product decision, not a decision to exclude; this supplies it.
- Consequence: the eligibility clause in `TickerRepository` now excludes nothing in current data. It is retained deliberately as the guard for a future unscored event type, not removed.
- Consequence: per DEC-002 there is no backfill, so `paid_ads_reactivated` rows written before this change keep `score = 1` and rank low until they age out of the seven-day window.
- Source: human decision in conversation, 2026-09-17, reversing the original entry; `PaidAdsTickerEventGenerator.php:59-67` for the type's existence.
- Affects: REQ-003, REQ-004, REQ-008.

### DEC-006 — The relevance timeframe reuses `srch_interval` instead of adding a parameter
- Decision: Most Relevant has no timeframe parameter of its own. The existing `srch_interval` filter is opened up as the timeframe control; the UI's three options map to the existing `24h`, `3d` and `1w` keys.
- Alternatives: add a separate `srch_relevance_interval` applying alongside `srch_interval`, so that the two intersect.
- Reason: explicit user decision. It keeps one time window rather than two, so there is no intersection rule to reason about, no way for a label to disagree with the pool, and no new validation surface. `srch_interval`'s existing default (`1w`, `TickerRepository.php:72`) already matches LD-440's required Most Relevant default, and its lookup already contains all three keys (`TickerRepository.php:20-34`), so no date logic is added.
- Accepted tradeoff: `srch_interval` is a user-facing filter with its own control (`resources/js/components/partials/TickerPage/TickerFilters.tsx:87,160,217`). Because it now doubles as the timeframe selector, switching into Most Relevant can change an already-active interval filter, which sits awkwardly against LD-440's *"Switching between Latest and Most Relevant must not reset the currently active filters or search"*. The user accepted this; how the single control is presented across the two modes is LD-442's to resolve.
- Source: user decision in conversation, 2026-09-17; LD-440 §Filters & Search; repository inspection.
- Affects: REQ-002, REQ-007, REQ-008.
- Note for product: LD-436's Figma shows a fourth option, Last 14 Days, that no ticket lists. Under this decision it would cost nothing — `'2w' => '2 week'` already exists in the same lookup — so it is a product choice, not an implementation constraint.

### DEC-007 — The window keeps `startOfDay` truncation rather than becoming a rolling window
- Decision: Most Relevant reuses the existing window computation unchanged — `now - interval` then `->startOfDay()` (`TickerRepository.php:91-96`). `24h` means "since 00:00 yesterday", which spans 24 to 48 hours of data depending on the time of day.
- Alternatives: compute the relevance window as a literal rolling window (`now - 24 hours`, `now - 3 days`, `now - 7 days`), matching LD-441's "Last 24 Hours" wording and the UI label.
- Reason: explicit user decision. It keeps one interval semantic across both sorting modes — under DEC-006 they are the same parameter, so a divergent rule would have made one key mean two different things. The cost is that the literal ticket and UI wording "Last 24 Hours" is approximate.
- Source: user decision in conversation, 2026-09-17, resolving the spec's open question.
- Affects: REQ-002.

### DEC-008 — `value_score` is scheduled for removal, so nothing new may depend on it
- Decision: the index required by REQ-010 must not use `value_score` as a leading column, and this change entrenches no further dependency on it. Removing the column itself is out of scope here.
- Alternatives: design the index the way every existing feed index is designed — leading with `value_score`, e.g. `(value_score, score DESC, time_posted DESC, id DESC)` — which is the locally optimal shape today.
- Reason: the user stated that `value_score` will be removed at some future point. This is roadmap knowledge the repository does not record: today the column looks permanent, carries a default-on `= 'high'` gate (`TickerRepository.php:79, 222-224`), and leads `idx_sfp_value_posted`, `idx_sfp_profile_value_posted`, `idx_sfp_profile_value_category_posted` and `idx_sfp_value_category_json`. An index built on that assumption would be dropped along with the column, silently returning Most Relevant to the unindexed sort that REQ-010 exists to prevent.
- Source: user decision in conversation, 2026-09-17.
- Affects: REQ-010; contextual for REQ-007, whose default `value_score = 'high'` gate is specified as current behavior to preserve, not as behavior intended to last.

## Tech Stack

- PHP 8.4.25, Laravel `^13`, `nwidart/laravel-modules` `^13` (modules: `Advertisers`, `Core`, `Socials`).
- Inertia `^3` with React on the frontend (not modified here).
- Pest `^4` for tests.
- MySQL; test schema loaded from `database/schema/mysql-schema.sql`.

## Commands

- Tests: `composer test` (resolves to `bin/worktree-test.sh`, per `composer.json`). Filtered: `composer test -- --filter=<name>`.
- Never run bare `php artisan test` while more than one worktree is active — see CLAUDE.md §Parallel Builds & Worktree Isolation.
- Formatting: `vendor/bin/pint --dirty --format agent` after touching PHP.
- Schema fingerprint: `./bin/schema-refresh.sh` is **not** needed to develop or test this change. `bin/worktree-test.sh:33-46` compares the live `leadbuster` database against the recorded fingerprint, and adding a migration file does not alter `leadbuster` — test databases pick the REQ-010 index up by applying the migration on top of the loaded schema dump. CLAUDE.md further records that the fingerprint covers tables, columns, types, nullability and defaults, not index-only changes. Run `schema-refresh.sh` only once the index has been deployed to `leadbuster` itself.

## Project Structure

Files this change is expected to touch:

- `Modules/Socials/app/Http/Requests/TickerRequest.php` — one added rule for `srch_sort`. `srch_interval`'s existing rule is untouched.
- `Modules/Socials/app/Repositories/TickerRepository.php` — mode branch on ordering, relevance window, signal-type exclusion. The ordering and pagination tail is shared by both query shapes (selective at `:180-186`, broad at `:210-211`), so the branch has one home at `:237-238`.
- `Modules/Advertisers/app/Services/PaidAdsTickerEventGenerator.php` — the event-row array at `:735-756` gains `score`.
- `Modules/Socials/app/Services/TickerService.php` — parameter pass-through if the service filters keys.
- A new migration under `Modules/Socials/database/migrations/` — the index required by REQ-010. Index-only, no data change. Governed by `.ai/rules/migrations.md`.

Layering note: `Modules/Socials/app/Contracts/TickerRepositoryInterface.php` declares no methods; it is a marker interface only. Adding parameters to `fetchAll` therefore changes no declared contract, but also gains no type safety from one. `TickerRequest` has no `toDto()`, and `TickerController` passes `$request->safe()->toArray()` — the grandfathered array path described in `.ai/rules/app.md:19`. This change follows the existing array shape rather than introducing a DTO.

## Code Style

Follows `.ai/rules/*` for the paths in scope. The relevant constraints:

- `.ai/rules/repositories.md:9` — `cursorPaginate()` for the ticker feed. This rule is path-scoped to `TickerRepository.php` and therefore governs over the more general `.ai/rules/services-repositories.md:9` (`paginate()` for index listings), which would otherwise appear to conflict.
- `.ai/rules/controllers-api.md` — API controllers wrap responses in a JsonResource; `TickerExportResource` already does.
- `.ai/rules/feature.md:9` — Mockery is for external boundaries only; feature tests exercise the real repository and service.
- PHP: curly braces always, constructor property promotion, explicit return types and parameter type hints, PHPDoc over inline comments (CLAUDE.md §php rules).

The score mapping should sit beside the existing `EVENT_TYPE_PRIORITIES` constant as a sibling `private const array`, matching how the generator already expresses per-event-type data.

## Testing Strategy

There is **no existing test coverage** for `TickerController`, `TickerService` or `TickerRepository` — the only ticker-adjacent test is `tests/Unit/PaidAdsTickerEventGeneratorTest.php`, which covers event-type selection and not the feed. This feature therefore builds its coverage from nothing rather than extending a suite, and `/plan` should budget for that.

| Requirement | Evidence | Level |
| --- | --- | --- |
| REQ-001 | Feed request with absent / `latest` / `most_relevant` / invalid `srch_sort` | Feature |
| REQ-002 | `1w` default; narrower interval excludes older items; start-of-day boundary case (item 33h old still inside `24h`); same candidate set as Latest for the same interval; non-UI keys still accepted | Feature |
| REQ-003 | Supported signal included; `paid_ads_reactivated` included and ranked on score 9; a signal type outside the supported list excluded from Most Relevant but present in Latest; **organic row with `type = NULL` still included** | Feature |
| REQ-004 | Generator writes each mapped score; unmapped type raises `UnexpectedValueException`; `insertOrIgnore` leaves existing rows alone, proven against the real table | Unit, extending `PaidAdsTickerEventGeneratorTest` |
| REQ-005 | Ordering across all three item classes; score tie → recency; score+timestamp tie → id, repeatable | Feature |
| REQ-006 | Full cursor traversal of a set larger than one page; boundary inside a score tie | Feature |
| REQ-007 | Each filter family and search still constrains the pool; default `value_score` gate holds | Feature |
| REQ-008 | Latest ordering, inclusion and export paths unchanged | Feature (regression) |
| REQ-009 | No new payload key; `sales_relevance` reports the stored score for a new event row | Feature |
| REQ-010 | `EXPLAIN` output for the Most Relevant query and for an unchanged Latest query; index column list inspected to confirm no leading `value_score` (DEC-008) | Manual, recorded in the plan's verification evidence — not a Pest assertion. Timed comparison only if staging with representative volume is confirmed available |

Feature tests belong in `tests/Feature/Socials/`, per `.ai/rules/feature.md`'s glob. Seeding needs organic posts, standalone ads and event rows in `social_feed_posts` with controlled `score` and `time_posted`, plus the `advertisers` / `social_profile_advertisers` rows the eligibility join requires — the feed query returns nothing without them. `/plan` should confirm whether factories exist for these or whether the tests seed via `DB::table()` as `tests/Feature/Socials/SocialPostUnicodeIngestionTest.php` does.

Pagination evidence for REQ-006 must traverse real pages through `srch_cursor` rather than asserting on the `ORDER BY` string — an ordering assertion cannot detect a duplicate across a page boundary.

## Invariants and Mechanism Proof

**Invariant.** For a fixed Most Relevant query, following `next_cursor` from the first page to exhaustion returns every eligible row exactly once, in non-increasing `(score, time_posted, id)` order. Empty state: an empty candidate pool returns one empty page with a null `next_cursor`.

**Why the ordering triple is sufficient.** `cursorPaginate` builds its keyset predicate from the query's `ORDER BY` columns. Correctness requires the ordering tuple to be unique per row: if two rows compare equal on every ordering column, the keyset boundary cannot separate them and one may be repeated or skipped. Here the third column is `sfp.id`, the table's `bigint unsigned AUTO_INCREMENT` primary key (`database/schema/mysql-schema.sql:1004`), which is unique across all three item types because organic posts, standalone ads and signals are rows in the same table. The tuple is therefore unique by construction, and the two leading columns cannot weaken that. This is the same argument the existing Latest feed relies on, which already pairs `time_posted DESC` with `id DESC` (`TickerRepository.php:237-238`) — the change extends a proven pattern by one leading column rather than introducing a new mechanism.

**Writers and transitions.** `score` is written once per row at insert: by `CategoriseSocialPosts` / `SocialFeedPostSyncService` for organic posts, by `CategoriseAds` for standalone ads, and now by `PaidAdsTickerEventGenerator` for signals (REQ-004). No path updates `score` in place, so a row's ordering key does not change while a client is paging. `removeObsoleteEvents` (`PaidAdsTickerEventGenerator.php:1012-1034`) can delete event rows between page fetches; a deletion mid-traversal removes that row from later pages but cannot duplicate or reorder others, because the keyset predicate is evaluated against column values rather than offsets. This is strictly better than the `OFFSET` behavior the feed would have under `paginate()`, and is the same exposure Latest has today.

**Application vs infrastructure.** Uniqueness of `id` is an infrastructure guarantee (primary key). Ordering determinism is an application guarantee (the `ORDER BY` clause). Cursor encoding is framework behavior. The risk worth testing is therefore not that `id` collides but that the `ORDER BY` and the cursor disagree — which is why REQ-006's evidence traverses real pages rather than asserting the SQL.

**Concurrency.** No cross-row or cross-process invariant is introduced. Ranking is a read-side ordering over independently written rows; there is no aggregate to keep consistent and no write contention this change creates.

## Data Lifecycle

`social_feed_posts` carries no soft-delete or archival column for feed rows — paid-ads event rows are hard-deleted by `removeObsoleteEvents` when a snapshot no longer supports them, and that behavior is unchanged here. `score` is `NOT NULL DEFAULT 1`, so it has no null state and no "unscored" marker; DEC-003 records the consequence for the exclusion rule, and DEC-002 records that historical event rows keep the default value rather than being rewritten.

This change adds no new lifecycle state and no column. The only expected schema change is the index required by REQ-010, which is additive and carries no data migration. It does not require a test-fingerprint refresh during development — see Commands for why.

## Boundaries

- **Always:** apply the relevance ordering and the signal-type exclusion only under `srch_sort=most_relevant`; express that exclusion as "not an unsupported `paid_ads_event`" rather than as an inclusion list over `type`, which is nullable; keep both query shapes (selective and broad) on the same ordering branch; run `vendor/bin/pint --dirty --format agent` after touching PHP; run the suite with `composer test`.
- **Ask first:** changing `paid_ads_reactivated`'s score of 9 (DEC-005); changing organic-post or standalone-ad scoring; any migration that changes data or columns rather than only adding the REQ-010 index; altering the default `value_score = 'high'` gate; changing `srch_interval`'s meaning or key set.
- **Never:** switch the ticker feed away from `cursorPaginate()`; modify Latest's ordering or item inclusion; expose a new score field to the frontend; lead the new index with `value_score` (DEC-008); run `migrate` / `migrate:fresh` against the `leadbuster` database.

## Open Questions

None. The one open question this spec carried — whether "Last 24 Hours" means a rolling window or the existing `startOfDay` truncation — was resolved by the user on 2026-09-17 and is recorded as DEC-007.

Two items are deliberately deferred rather than open:
- Whether to offer Last 14 Days, which appears in LD-436's Figma but in no ticket. Free to add under DEC-006 (`2w` already exists in the interval lookup); a product choice, not a blocker for this spec.
- A measured latency comparison for REQ-010, which depends on a staging environment with representative volume that has not been established. `/plan` records it as performed or unavailable.
