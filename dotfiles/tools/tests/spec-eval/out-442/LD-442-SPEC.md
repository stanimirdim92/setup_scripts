# Spec: Ticker Sorting — Latest / Most Relevant (Frontend)

Status: Draft
Ticket: LD-442
Change kind: Modify
Supersedes: N/A
Approved by: —
Approved at: —

## Objective

Add a sorting control above the Ticker feed. It has two tabs: **Latest** (the existing chronological feed) and **Most Relevant** (the relevance-ranked feed from LD-441). Most Relevant has a timeframe dropdown with Last 24 Hours, Last 3 Days and Last 7 Days. Last 7 Days is the default.

As a sales user, I want to see the most relevant local-business activity first, within a recent window, without losing my search and filters.

The Jira ticket is **Done**, but the repository has no frontend implementation. A search of `resources/` and `lang/` for `srch_sort`, `most_relevant`, `Most Relevant` and `RANK POST` found nothing. The backend from LD-441 exists and is approved (`docs/specs/LD-441-SPEC.md`). This spec therefore covers the full frontend work.

Out of scope:
- Any backend change. The request contract is fixed by LD-441 (see Contract below).
- Any change to Ticker cards (`TickerPostRow`) or overlays (`PaidAdsOverlay/*`).
- Showing any score, rank or relevance value anywhere in the UI.
- Sort or timeframe in CSV and feed-URL exports. Exports behave as today (DEC-005).
- A new loading skeleton. The Ticker keeps its existing loading, error and empty states.

### Backend contract (from LD-441, verified in source)

- Endpoint: route `api.socials.ticker.index`, called by `useTickerFeed` (`resources/js/hooks/useTickerFeed.ts:102-113`).
- `srch_sort`: optional, `latest` or `most_relevant` (`Modules/Socials/app/Http/Requests/TickerRequest.php:55`). Absent means `latest` (`TickerRepository.php:80`).
- Timeframe: the existing `srch_interval` parameter (LD-441 DEC-006). The UI options map to `24h`, `3d` and `1w`.
- Pagination: the existing `srch_cursor` cursor. The backend orders Most Relevant by `score DESC, time_posted DESC, id DESC`.

## Change Impact

- **Added behavior:**
  - The sort tabs and the timeframe dropdown (REQ-001, REQ-002, REQ-003).
  - Most Relevant feed requests (REQ-004).
  - Sort state in the page URL (REQ-007).
  - New EN and DE translation keys (REQ-009).
- **Modified behavior:**
  - `queryFilters` in `resources/js/pages/Advertisers/Ticker.tsx:704-782` gains `srch_sort` and a mode-dependent `srch_interval` in Most Relevant mode only (REQ-004).
  - `useTickerUrlFilters` (`resources/js/hooks/useTickerUrlFilters.ts:58-104`) reads the sort state back from the URL (REQ-007).
- **Removed behavior:** none.
- **Renamed behavior:** none.
- **Explicitly preserved behavior:**
  - The Latest request stays byte-identical to today: `srch_interval=1m`, no `srch_sort` (REQ-008, DEC-003).
  - Search and every filter keep their values across mode and timeframe changes (REQ-005).
  - Cursor pagination, infinite loading, request abort and the 250 ms debounce in `useTickerFeed` (REQ-006).
  - Existing loading, error and empty states in `TickerResultsPane.tsx:220-235` (REQ-006).
  - Cards and overlays, and the absence of any score in the UI (REQ-010).
  - Presets, Clear All Filters and exports (REQ-008, DEC-004, DEC-005).
- **Compatibility/migration constraints:** old Ticker URLs have no `srch_sort`. They open in Latest, as today (REQ-007). No stored data changes.

## Requirements

### Requirement: REQ-001 — Sort tabs above the feed
Source: LD-442 Requirements and AC ("Latest and Most Relevant tabs are implemented", "UI matches the approved Figma design"); Figma `2:3891` "Latest", `1:5247` "Most relevant (closed)", tabs `2:5164`.

The results pane shows a tab bar above the feed list and below the existing search and filter header (`TickerResultsPane.tsx:183-218`). The bar has two tabs: **Latest** with a clock icon, and **Most Relevant** with a calendar icon. The active tab is underlined. The default mode is Latest.

#### Scenario: Default page load
- GIVEN a user opens `/ticker` with no `srch_sort` in the URL
- WHEN the page renders
- THEN both tabs show, Latest is underlined, and the feed is the Latest feed

#### Scenario: Switch to Most Relevant by the tab label
- GIVEN Latest is active
- WHEN the user clicks the Most Relevant tab label
- THEN Most Relevant becomes underlined, Latest loses its underline, and the feed reloads in Most Relevant mode with the current timeframe

#### Scenario: Switch back to Latest
- GIVEN Most Relevant is active
- WHEN the user clicks the Latest tab
- THEN Latest becomes underlined and the feed reloads as the Latest feed

#### Scenario: Click on the active tab
- GIVEN Latest is active
- WHEN the user clicks the Latest tab
- THEN nothing changes and no new request is sent

### Requirement: REQ-002 — Most Relevant tab shows the selected timeframe
Source: LD-442 ("Most Relevant shows the selected timeframe", "Last 7 Days is the default"); Figma `1:5247`, `2:5164`; OPEN QUESTION Q2.

The Most Relevant tab label reads "Most Relevant (<timeframe>)" followed by a chevron, for example "Most Relevant (Last 7 Days) ▾". The timeframe is Last 7 Days until the user picks another. The page remembers the picked timeframe while the user switches between tabs.

#### Scenario: Default timeframe label
- GIVEN Most Relevant is active and the user has not picked a timeframe
- WHEN the tab renders
- THEN the label reads "Most Relevant (Last 7 days)" with a chevron (EN casing per DEC-002)

#### Scenario: Timeframe survives a round trip through Latest
- GIVEN the user picked Last 3 Days in Most Relevant
- WHEN the user switches to Latest and then back to Most Relevant
- THEN the label reads "Most Relevant (Last 3 days)" and the request uses `srch_interval=3d`

#### Scenario: Inactive tab label
- GIVEN Latest is active
- WHEN the tab bar renders
- THEN the Most Relevant tab shows [pending Q2]

### Requirement: REQ-003 — Timeframe dropdown
Source: LD-442 ("Clicking the arrow opens a dropdown with Last 24 Hours, Last 3 Days and Last 7 Days"; Figma details); Figma `2:3075` "Most relevant (open)", `2:3093`; OPEN QUESTION Q1.

Clicking the chevron on the Most Relevant tab opens a dropdown. The dropdown has the header "RANK POST FROM" and the options Last 24 Hours, Last 3 Days and Last 7 Days, in that order [Last 14 Days pending Q1]. The selected option is highlighted. The chevron points up while the dropdown is open and down while it is closed.

#### Scenario: Open the dropdown
- GIVEN Most Relevant is active with Last 7 Days
- WHEN the user clicks the chevron
- THEN the dropdown opens with the header "RANK POST FROM", three options, Last 7 Days highlighted, and the chevron pointing up

#### Scenario: Pick a different timeframe
- GIVEN the dropdown is open with Last 7 Days selected
- WHEN the user clicks Last 24 Hours
- THEN the dropdown closes, the label reads "Most Relevant (Last 24 hours)", and the feed reloads with `srch_interval=24h`

#### Scenario: Pick the timeframe that is already selected
- GIVEN the dropdown is open with Last 7 Days selected
- WHEN the user clicks Last 7 Days
- THEN the dropdown closes and no new request is sent

#### Scenario: Close without picking
- GIVEN the dropdown is open
- WHEN the user clicks outside it or presses Escape
- THEN the dropdown closes, the chevron points down, and the timeframe and feed do not change

#### Scenario: Pick a timeframe while Latest is active
- GIVEN Latest is active and the dropdown is reachable from the inactive tab (pending Q2)
- WHEN the user picks Last 3 Days
- THEN Most Relevant becomes active with Last 3 Days and the feed reloads in Most Relevant mode

#### Scenario: Keyboard use
- GIVEN keyboard focus is on the tab bar
- WHEN the user tabs to a tab or the chevron and presses Enter or Space
- THEN the tab activates or the dropdown opens; the chevron button reports `aria-expanded` and `aria-haspopup`, as `ExportDropdown.tsx:60-80` does

### Requirement: REQ-004 — Feed request per mode
Source: LD-442 AC ("Latest loads the existing chronological feed", "Most Relevant loads the relevance-ranked feed", "Changing the timeframe requests the correct result set"); LD-441 REQ-001, REQ-002, DEC-006.

The feed request depends on the mode:

| Mode | Timeframe | `srch_sort` | `srch_interval` |
|---|---|---|---|
| Latest | — | absent | `1m` (unchanged) |
| Most Relevant | Last 24 Hours | `most_relevant` | `24h` |
| Most Relevant | Last 3 Days | `most_relevant` | `3d` |
| Most Relevant | Last 7 Days | `most_relevant` | `1w` |

All other request parameters are the same in both modes.

#### Scenario: Latest request is unchanged
- GIVEN Latest is active with any search and filters
- WHEN the feed request is sent
- THEN its parameters are exactly what the page sends today for the same search and filters, with `srch_interval=1m` and no `srch_sort`

#### Scenario: Most Relevant default request
- GIVEN the user switches to Most Relevant without picking a timeframe
- WHEN the feed request is sent
- THEN it has `srch_sort=most_relevant` and `srch_interval=1w`

#### Scenario: Timeframe change refetches from the first page
- GIVEN Most Relevant is active and the user has scrolled to page 3
- WHEN the user picks Last 3 Days
- THEN the list clears, scroll resets to the top, and a first-page request is sent with `srch_interval=3d` and no `srch_cursor`

#### Scenario: Rapid switching shows only the last choice
- GIVEN a Most Relevant request is in flight
- WHEN the user switches to Latest before it returns
- THEN the list shows only Latest results; the earlier response is discarded by the existing abort and signature check in `useTickerFeed.ts:177-218`

### Requirement: REQ-005 — Search and filters stay active across mode and timeframe changes
Source: LD-442 ("Keep all active search and filter state when the user switches Latest ↔ Most Relevant or changes the timeframe"); LD-442 AC ("Filters and search stay active").

Switching mode or timeframe changes only `srch_sort` and `srch_interval`. Search, Categories, Source, Integrations, Districts, ZIP Codes, Industry, Tags, CRM ID, Franchise and any active preset keep their values and stay in the request.

#### Scenario: Filters survive a mode switch
- GIVEN Latest is active with the search "bäckerei", Source Instagram, Industry "Restaurants" and CRM ID "Without"
- WHEN the user switches to Most Relevant
- THEN the filter controls show the same values, and the request carries the same `srch_search`, `srch_platforms`, `srch_business_types` and `srch_external_id` values plus `srch_sort=most_relevant&srch_interval=1w`

#### Scenario: Filters survive a timeframe change
- GIVEN Most Relevant is active with Categories and Franchise filters set
- WHEN the user picks Last 24 Hours
- THEN the same `srch_category` and `srch_franchise` values are sent with `srch_interval=24h`

#### Scenario: Filter change keeps the mode
- GIVEN Most Relevant is active with Last 3 Days
- WHEN the user changes a filter or the search text
- THEN Most Relevant and Last 3 Days stay selected and the new request carries both the new filter and `srch_sort=most_relevant&srch_interval=3d`

#### Scenario: Active preset stays active
- GIVEN a preset is active and unchanged
- WHEN the user switches mode or timeframe
- THEN the preset stays active, because sort and timeframe are not part of a preset (DEC-004, pending Q4)

### Requirement: REQ-006 — Loading, empty, error and pagination states reuse the existing mechanisms
Source: LD-442 ("Reuse the existing loading patterns", "standard Ticker empty state", "Existing pagination and infinite loading must work in both modes"); LD-442 AC.

Both modes use `useTickerFeed` unchanged, including `srch_cursor` pagination, scroll-triggered loading and the existing states in `TickerResultsPane.tsx:220-235` and `:283-287`.

#### Scenario: Loading state
- GIVEN the user switches mode or timeframe
- WHEN the first page is loading
- THEN the pane shows the existing loading text (`filters.loading_results_please_wait`) and the tab bar stays visible and usable

#### Scenario: Empty state
- GIVEN no item matches Most Relevant with Last 24 Hours and the active filters
- WHEN the response returns no items
- THEN the pane shows the existing empty state (`filters.no_posts_match_filters` and `ticker.try_changing_or_clearing_filters`) and the tab bar stays visible

#### Scenario: Error state
- GIVEN the feed request fails in Most Relevant mode
- WHEN the error is handled
- THEN the pane shows the existing error text (`errors.failed_to_load_data`), and switching mode or timeframe retries

#### Scenario: Infinite loading in Most Relevant
- GIVEN Most Relevant returns a `next_cursor` on the first page
- WHEN the user scrolls near the end of the list
- THEN the next page is requested with the same `srch_sort` and `srch_interval` plus `srch_cursor`, appended below, with the existing "loading more" text while it loads

#### Scenario: End of results
- GIVEN the last Most Relevant page returns no `next_cursor`
- WHEN the user scrolls to the end
- THEN no further request is sent

### Requirement: REQ-007 — Sort state in the URL
Source: OPEN QUESTION Q3; repository behavior: `useTickerFeed.ts:188-192` writes every `queryFilters` key to the address bar, and `currentParams` flows into details-page links (`Ticker.tsx:1049-1050`, `TickerPostRow`).

[Pending Q3. The recommended behavior follows.] On page load, `popstate` and `pageshow`, the page reads `srch_sort` and `srch_interval` from the URL and restores the mode and timeframe.

#### Scenario: Reload keeps Most Relevant
- GIVEN the URL contains `srch_sort=most_relevant&srch_interval=3d`
- WHEN the page loads
- THEN Most Relevant is active with Last 3 Days and the first request uses those values

#### Scenario: Back from an advertiser page
- GIVEN the user opened an advertiser from the Ticker while in Most Relevant with Last 24 Hours
- WHEN the user navigates back
- THEN Most Relevant with Last 24 Hours is restored

#### Scenario: Old or Latest URL
- GIVEN the URL has no `srch_sort`, or has `srch_sort=latest`, and has `srch_interval=1m`
- WHEN the page loads
- THEN Latest is active and the stored timeframe is the default Last 7 Days

#### Scenario: Unsupported values fall back
- GIVEN the URL contains `srch_sort=most_relevant&srch_interval=1m`, or `srch_sort=popular`
- WHEN the page loads
- THEN an unsupported timeframe falls back to Last 7 Days, and an unsupported mode falls back to Latest

### Requirement: REQ-008 — The Latest feed has no regression
Source: LD-442 AC ("The existing Latest Ticker has no visual or functional regression"); LD-442 Constraints ("Latest feed behavior must not change").

In Latest mode, the request, the result list, pagination, presets, Clear All Filters, hidden companies and exports behave exactly as before this change. The only visible addition is the tab bar.

#### Scenario: Latest request parity
- GIVEN the same search and filters before and after this change
- WHEN the Latest feed loads
- THEN the request parameters are identical

#### Scenario: Clear All Filters keeps the mode
- GIVEN Most Relevant is active with Last 3 Days and filters set
- WHEN the user clicks Clear All Filters
- THEN the filters reset as today, and Most Relevant with Last 3 Days stays selected (DEC-004, pending Q4)

#### Scenario: Exports ignore the sort mode
- GIVEN Most Relevant is active
- WHEN the user opens Export Ticker Data and exports CSV or creates a feed URL
- THEN no `srch_sort` is added to the export; the export timeframe default still comes from the URL's `srch_interval` through the existing `getInitialTickerExportTimeframe` (`TickerFilters.tsx:210-226`) (DEC-005)

### Requirement: REQ-009 — Translations for the new labels
Source: CLAUDE.md and repository convention (`lang/{en,de}/ticker.php`, `useTranslations().trans`); LD-442 Figma copy.

All new copy goes through `trans()` with keys in `lang/en/ticker.php` and `lang/de/ticker.php`. The timeframe options reuse the existing keys `ticker.last_24_hours`, `ticker.last_3_days` and `ticker.last_7_days` (DEC-002). New keys are added for "Latest", "Most Relevant" and "Rank post from".

#### Scenario: English labels
- GIVEN the locale is `en`
- WHEN the tab bar and dropdown render
- THEN they show "Latest", "Most Relevant (Last 7 days)", the header "RANK POST FROM" and the three existing timeframe labels

#### Scenario: German labels
- GIVEN the locale is `de`
- WHEN the tab bar and dropdown render
- THEN every label shows German text from `lang/de/ticker.php`, for example "Letzte 7 Tage"; no English string or raw key shows

### Requirement: REQ-010 — No score in the UI, cards and overlays unchanged
Source: LD-442 ("Do not show any score anywhere", "Do not change the content or structure of existing Ticker cards or overlays"); LD-442 AC; LD-441 REQ-009.

No score, rank or relevance value shows in the tab bar, dropdown, cards, overlays, tooltips, badges or labels in either mode. `TickerPostRow` and `PaidAdsOverlay/*` are not changed. The `TickerPost` type (`resources/js/types/types.ts:223-241`) does not gain a score field.

#### Scenario: Most Relevant cards look like Latest cards
- GIVEN the same organic post, standalone ad and paid-ads signal appear in both modes
- WHEN each is rendered
- THEN its card and overlay are identical in both modes, and none shows a number derived from `sales_relevance` or `score`

#### Scenario: Signal scores never show
- GIVEN a Most Relevant feed that contains a `paid_ads_started` signal with stored score 9
- WHEN the row and its overlay render
- THEN no "9", score label or relevance badge shows

## Material Decisions

### DEC-001 — Implement the full frontend, although the ticket is Done
- Decision: treat LD-442 as unimplemented and specify the complete frontend.
- Alternatives: specify only gaps against an existing implementation.
- Reason: the repository has no frontend code, keys or tests for the feature (recon, 2026-10-03). The backend exists.
- Source: repository evidence.
- Affects: all requirements.

### DEC-002 — Timeframe labels reuse the existing translation keys
- Decision: reuse `ticker.last_24_hours`, `ticker.last_3_days` and `ticker.last_7_days` (`lang/en/ticker.php:17-19`, `lang/de/ticker.php:17-19`). EN therefore shows "Last 7 days", not the ticket's "Last 7 Days".
- Alternatives: add title-case keys for the sort control only.
- Reason: the export timeframe list already uses these keys for the same periods (`resources/js/components/partials/Export/exportTypes.ts:9-40`). Two keys for one label drift apart. The casing difference is the only visible effect.
- Source: repository precedent. Reject this decision at review if the Figma casing is required.
- Affects: REQ-002, REQ-003, REQ-009.

### DEC-003 — Latest keeps `srch_interval=1m` and sends no `srch_sort`
- Decision: the Latest request stays exactly as today. Only Most Relevant sends `srch_sort` and a timeframe interval.
- Alternatives: send `srch_sort=latest` in Latest, or send the backend default `1w` in Latest.
- Reason: LD-442 forbids any Latest change. The page hardcodes `srch_interval=1m` today (`Ticker.tsx:706`), so Latest shows a one-month window while Most Relevant shows at most seven days. Absent and `latest` are equivalent on the backend (LD-441 REQ-001).
- Source: LD-442 Constraints; repository evidence.
- Affects: REQ-004, REQ-008.

### DEC-004 — Sort and timeframe are view state, not filters (proposed, pending Q4)
- Decision: presets do not save the sort mode or timeframe. Applying a preset, saving a preset and Clear All Filters do not change them. They do not count toward `hasAnyFiltersApplied`.
- Alternatives: store sort and timeframe in `TickerPresetFilters` and reset them in Clear All Filters.
- Reason: LD-442 limits the new UI to the tabs and dropdown and says only the dataset and order change. The preset shape (`resources/js/utils/ticker/presets.ts`) is a saved backend payload, so extending it widens the scope.
- Source: proposal for human decision.
- Affects: REQ-005, REQ-008.

### DEC-005 — Exports stay as they are
- Decision: CSV and feed-URL exports do not carry `srch_sort`. `TICKER_FEED_ALLOWED_PARAMS` (`TickerFilters.tsx:80-93`) is not changed.
- Alternatives: make exports follow the active sort mode.
- Reason: no ticket asks for sorted exports. The export modals already choose their own timeframe. The existing default reads `srch_interval` from the URL, so in Most Relevant the modal preselects the Most Relevant timeframe; this is existing mechanism, not new logic.
- Source: LD-442 scope ("The only new UI is the tab navigation, the timeframe dropdown…").
- Affects: REQ-008.

## Tech Stack

- Inertia `^3` with React and TypeScript. Page `resources/js/pages/Advertisers/Ticker.tsx`, rendered as `Ticker` by `Modules/Socials/app/Http/Controllers/Web/TickerController.php:27-31`.
- Feed requests use axios in `useTickerFeed`, not `useHttp`. Keep it.
- Tailwind CSS. Icons are local SVGs in `resources/js/components/icons`, imported with `?react`.
- Translations: Laravel lang files shared as Inertia props, read with `useTranslations().trans` (`resources/js/hooks/use-translations.ts:23-47`).
- Vitest 4 with jsdom and Testing Library (`vitest.config.ts`, `resources/js/test/setup.ts`). Package manager `yarn@4.18.0`.

## Commands

From `package.json`. Found in source; not executed for this spec.

- Frontend tests: `yarn test` (runs `vitest run`). One file: `yarn test resources/js/components/partials/TickerPage/<File>.test.tsx`.
- Lint: `yarn lint`.
- Formatting check: `yarn format`.
- Type check and build: `yarn build` (runs `tsc && vite build`). There is no separate type-check script.
- Browser verification assets: `bin/worktree-setup.sh --build`, then `bin/worktree-doctor.sh --frontend` (CLAUDE.md §Per-Ticket Git Worktrees).
- Backend: no PHP change is expected. If one is made, run `composer test -- --compact --filter=<name>` and `vendor/bin/pint --dirty --format agent`.

## Project Structure

Expected touch points:

- `resources/js/pages/Advertisers/Ticker.tsx` — sort and timeframe state; `queryFilters` (`:704-782`) and its dependency array (`:769-782`); props to `TickerResultsPane`.
- `resources/js/hooks/useTickerUrlFilters.ts` — read `srch_sort` and `srch_interval` (pending Q3).
- `resources/js/components/partials/TickerPage/TickerResultsPane.tsx` — render the tab bar between the header (`:183-218`) and the list (`:220`).
- A new component in `resources/js/components/partials/TickerPage/` for the tab bar and dropdown, with a sibling `.test.tsx`.
- `resources/js/components/icons/` — a new calendar SVG and an up-pointing chevron (or a rotated `IconChevronDown`). No calendar icon exists today.
- `lang/en/ticker.php`, `lang/de/ticker.php` — new keys.
- `docs/USER-GUIDE.md` §6 (line 330 calls the Ticker "a chronological feed") — update after implementation lands.

Not touched: `useTickerFeed.ts`, `TickerPostRow.tsx`, `PaidAdsOverlay/*`, `presets.ts`, export components, any backend file.

## Code Style

- `.ai/rules/js.md`: trust API data; no defensive coercion wrappers. Do not copy the legacy idiom in `post-preview.tsx`.
- `.ai/rules/ticker-page.md` and `.ai/rules/ticker.md` apply to the touched paths; neither covers sorting.
- Dropdown precedent: the hand-rolled dropdowns in `TickerFilters.tsx:591-632` and `:382-399` (local open state, `mousedown` click-outside, absolute panel). Panel and item classes at `TickerFilters.tsx:1034-1065`.
- The timeframe-to-interval mapping must not duplicate `EXPORT_TIMEFRAMES` labels. Reuse its `labelKey` and `interval` values for `24h`, `3d` and `7d`, as `TickerFilters.tsx:8` already imports from that module.
- **No precedent found for** a tab bar with underline in the Ticker, or `@radix-ui/react-dropdown-menu` usage in `resources/js`. A hand-rolled control matching `TickerFilters` is the closest local precedent. `/plan` decides between that and the installed Radix primitive.

## Testing Strategy

There is no test for `Ticker.tsx`, `useTickerFeed` or `TickerResultsPane` today. Vitest component tests follow `TickerFilters.test.tsx` (mocked `usePage` with `translations: {}`, `TooltipProvider` wrapper, `fireEvent`) and `TickerPostRow.test.tsx` (`vi.hoisted` translations, `vi.stubGlobal('route', …)`).

| Requirement | Evidence | Level |
|---|---|---|
| REQ-001 | Tabs render; Latest default; switching calls the handler; active-tab click is a no-op | Vitest component |
| REQ-002 | Label shows the timeframe; default Last 7 days; timeframe kept across a round trip | Vitest component |
| REQ-003 | Open, pick, re-pick, outside click, Escape; highlighted option; chevron direction; `aria-expanded` | Vitest component |
| REQ-004 | Request parameters per mode and timeframe, including Latest parity. `queryFilters` is inline in `Ticker.tsx`; `/plan` decides how to make it testable (for example a pure builder function) | Vitest unit |
| REQ-005 | Filter values unchanged in the request after a mode or timeframe change; filter change keeps the mode | Vitest unit on the request builder |
| REQ-006 | Pane shows existing loading, empty and error states with the tab bar visible; Most Relevant pagination in the browser | Vitest component + manual browser check |
| REQ-007 | URL read: valid, absent, unsupported values | Vitest unit on `useTickerUrlFilters` |
| REQ-008 | Latest request parity; Clear All Filters keeps the mode; export allowlist unchanged | Vitest unit + manual browser check |
| REQ-009 | Every new key exists in both `lang/en/ticker.php` and `lang/de/ticker.php` | Manual check in review; no lang parity test was found |
| REQ-010 | No diff in `TickerPostRow.tsx`, `PaidAdsOverlay/*` and `types.ts`; no score text in the new component | Diff review + Vitest assertion |

Visual match with Figma (REQ-001–REQ-003) needs a manual browser check after `bin/worktree-setup.sh --build`. Exact Figma tokens and spacing were not read (see Assumptions).

Run `yarn test`, `yarn lint` and `yarn build` before review.

## Invariants and Mechanism Proof

N/A. The change is client-side view state. It adds no cross-row, cross-resource or concurrent invariant. Ordering and pagination stability belong to the backend (LD-441 REQ-005, REQ-006). Stale responses are already discarded by `useTickerFeed`'s abort and signature check, which REQ-004 reuses unchanged.

## Data Lifecycle

N/A. No stored data, schema or lifecycle field changes. Sort state lives in React state and the page URL only.

## Assumptions

- **Figma tokens unread.** `get_design_context` was not called on frames `8:2575`, `2:3891`, `1:5247` or `2:3075`, so exact colors, spacing, font sizes and the calendar icon asset are unknown. Confirm by reading the design context during `/plan` or `/build`. Until then, use the existing Ticker dropdown classes (`TickerFilters.tsx:1034-1065`).
- **Figma "Initial" frame `8:2575`** shows "Most Relevant" without timeframe or chevron and no active tab. This spec reads it as a design draft, not a required state. Q2 resolves it.
- **Most Relevant timeframes are start-of-day windows** (LD-441 DEC-007). "Last 24 hours" returns data since 00:00 yesterday. The UI label stays as designed.

## Boundaries

- **Always:** keep the Latest request identical to today; send all search and filter parameters in both modes; use `trans()` for all new copy with EN and DE keys; reuse `useTickerFeed`; run `yarn test`, `yarn lint` and `yarn build`.
- **Ask first:** changing presets, exports or Clear All Filters; adding a timeframe beyond those approved; adding a skeleton or new loading UI; any backend change.
- **Never:** show a score, rank or relevance value; change `TickerPostRow` or overlays; add a score field to `TickerPost`; hardcode backend enum copies (`.ai/rules/js.md`).

## Open Questions

OPEN QUESTION: Q1 — Is "Last 14 Days" in scope?
- Option A: three options only (24 hours, 3 days, 7 days). LD-440 and LD-442 both list three, and the AC names three.
- Option B: four options, as Figma `2:3075`/`2:3093` shows. The backend already accepts `2w` (`ticker.last_2_weeks` exists in EN and DE).
→ Recommendation: A, because the AC is explicit. Decision needed before this spec can be approved.

OPEN QUESTION: Q2 — What does the Most Relevant tab show while Latest is active?
- Option A: "Most Relevant (Last 7 Days) ▾", with the remembered timeframe and a working chevron, as Figma `2:5164` shows. Picking a timeframe from it also switches to Most Relevant.
- Option B: "Most Relevant (Last 7 Days)" with no chevron. The dropdown is available only when Most Relevant is active.
- Option C: plain "Most Relevant", as the Figma "Initial" frame `8:2575` shows.
→ Recommendation: A, because it matches the "Latest" frame and the ticket's control text. Decision needed before this spec can be approved.

OPEN QUESTION: Q3 — Does the URL restore the sort mode on reload and back navigation?
- Option A: yes. `useTickerUrlFilters` reads `srch_sort` and `srch_interval` (REQ-007 as drafted). The URL already shows these keys, because `useTickerFeed` writes every request key to it.
- Option B: no. Every page load starts in Latest, but the URL still shows the last mode until the next request.
→ Recommendation: A. Option B leaves the URL and the screen in disagreement after a reload. Decision needed before this spec can be approved.

OPEN QUESTION: Q4 — Are sort and timeframe outside presets and Clear All Filters?
- Option A: yes (DEC-004 as drafted). Presets keep their current shape. Clear All Filters does not reset the mode.
- Option B: presets save sort and timeframe, and Clear All Filters resets to Latest.
→ Recommendation: A, because the ticket treats sorting as separate from filters. Decision needed before this spec can be approved.
