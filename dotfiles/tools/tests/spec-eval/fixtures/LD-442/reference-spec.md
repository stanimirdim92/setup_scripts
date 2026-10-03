# Spec: Ticker Latest / Most Relevant Sorting (Frontend)

Status: Approved
Ticket: LD-442
Change kind: Modify
Supersedes: N/A
Approved by: Stanimir Dimitrov
Reapproved at: 2026-09-18 by Stanimir Dimitrov — **behavioral revision**: DEC-009 revised. The timeframe dropdown cannot be opened while `Latest` is active; the chevron there switches to Most Relevant and opens the dropdown in that mode instead. Affects REQ-002 and REQ-003, both reconciled before this line was written. DEC-010, recorded earlier the same day, is withdrawn — the fourth label keeps the design's `Last 14 Days`.
Reapproved at: 2026-09-18 by Stanimir Dimitrov — **behavioral revision**: DEC-009 added. Using the timeframe dropdown while Latest is active now switches to Most Relevant rather than being inert, closing a gap found during T002. Affects REQ-002 and REQ-003; both reconciled before this line was written.
Approved at: 2026-09-18 — approved together with two changes requested at approval time and reconciled into the draft before this header was set: (a) exports now forward `srch_sort` and follow the active ordering (REQ-010, DEC-008), reversing the draft's out-of-scope exclusion; (b) the calendar icon is supplied by Zornitsa Stoyanova rather than authored here (REQ-011).

## Objective

Add a sort-mode selector above the Ticker feed so a user can switch between the existing chronological **Latest** view and the new relevance-ranked **Most Relevant** view delivered by LD-441. When Most Relevant is active, the user picks the ranking window from a dropdown inside the tab.

This is the UI half of LD-440. The backend contract already exists on this branch (LD-441): `srch_sort=latest|most_relevant` plus the existing `srch_interval`. No new API parameter and no new response field is introduced by this change.

Out of scope — named because the request could reasonably be read wider:

- **Any backend change.** All four timeframe options map to interval keys that already exist in `TickerRepository::$srchIntervals` (`24h`, `3d`, `1w`, `2w`), and `srch_sort` is already validated in `TickerRequest`. LD-442 adds no PHP.
- **The export's own timeframe control.** The export dialog keeps its independent six-option range picker (`24h`, `3d`, `7d`, `2w`, `3w`, `1m`) and continues to strip the feed's `srch_interval`. Only the sort mode is newly forwarded — see REQ-010 and DEC-008.
- **Ticker cards, rows and overlays.** Untouched. `TickerPostRow`, `PaidAdsEventOverlay` and the preview modal are not modified.
- **Hardening `srch_interval` validation.** `TickerRequest` validates it as `nullable|string` only; an unrecognized value silently falls back to `'1 month'` (`TickerRepository.php:555`) instead of returning 422. Adding an `in:` rule would 422 existing callers that send other values — `OrganicHistoryCard.tsx` sends `3m`, and the export control sends `3w`/`2m`. That is a backend change with its own blast radius and belongs to a sibling ticket, not here.
- **Saved presets.** See DEC-004: sort mode and timeframe are deliberately not part of a saved preset.

## Change Impact

- **Added behavior:** REQ-001 (tab selector), REQ-002 (timeframe dropdown), REQ-003 (tab label states), REQ-004 (request contract), REQ-007 (URL round-trip), REQ-011 (localized copy and the calendar icon).
- **Modified behavior:** `Ticker.tsx`'s `queryFilters` memo (`:704-780`) gains the two sort keys. `useTickerUrlFilters.readFiltersFromURL` gains two keys in its parse list. `TickerResultsPane` gains a tab strip between the filter header and the results list. `TickerFilters.tsx` adds `srch_sort` to `TICKER_FEED_ALLOWED_PARAMS` and forwards it from both export URL builders, so **export ordering and row set now follow the active sort mode** (REQ-010) — previously exports were always chronological.
- **Removed behavior:** None.
- **Renamed behavior:** None.
- **Explicitly preserved behavior:**
  - REQ-005 pins that Latest keeps sending `srch_interval=1m`, exactly as `Ticker.tsx:706` does today. This is the line that stops Most Relevant's narrower window leaking into Latest.
  - REQ-006 pins that every existing filter and the search term survive a mode or timeframe change.
  - REQ-008 pins that cursor pagination and infinite scroll behave identically in both modes.
  - REQ-009 pins that the existing loading, empty and error states are reused, not replaced.
  - REQ-012 pins that no score is rendered anywhere.
- **Compatibility/migration constraints:** LD-441 is unmerged. This work builds on `worktree-LD-441`; the FE cannot be verified end-to-end against `main`. A deployment carrying LD-442 without LD-441 would send `srch_sort=most_relevant` to a backend that rejects the parameter (422), so LD-441 must ship first or together.

## Requirements

### Requirement: REQ-001 — A tab selector switches the feed between Latest and Most Relevant
Source: LD-442 "Latest and Most Relevant tabs are implemented"; Figma `8:2575`, `2:3891`, `1:5247`, `2:3075`

A tab strip sits directly above the results list, below the existing search and filter header, inside the results pane. It offers exactly two tabs: `Latest` (clock icon) and `Most Relevant` (calendar icon). Selecting a tab switches the feed's ordering and nothing else.

#### Scenario: Latest is the active mode on first load
- GIVEN a user opens the Ticker with no `srch_sort` in the URL
- WHEN the feed loads
- THEN the chronological feed is shown and `Latest` is rendered as the active tab

#### Scenario: Selecting Most Relevant switches the ordering
- GIVEN the user is on `Latest`
- WHEN the user clicks the `Most Relevant` tab
- THEN the feed refetches with `srch_sort=most_relevant` and the results are ordered by the backend's relevance ranking

#### Scenario: Selecting Latest returns to the chronological feed
- GIVEN the user is on `Most Relevant`
- WHEN the user clicks the `Latest` tab
- THEN the feed refetches without `srch_sort=most_relevant` and the results are ordered chronologically

### Requirement: REQ-002 — Most Relevant exposes a four-option timeframe dropdown
Source: User decision 2026-09-18; Figma `2:3075` (dropdown open)

The `Most Relevant` tab carries a chevron that opens a dropdown listing exactly four options under the section header `RANK POST FROM`: `Last 24 Hours`, `Last 3 Days`, `Last 7 Days`, `Last 14 Days`. The currently selected option is visually highlighted. `Last 7 Days` is the default.

The ticket text lists only three options; the approved design lists four. The design wins — see DEC-001.

#### Scenario: The dropdown lists four options with Last 7 Days preselected
- GIVEN the user has selected `Most Relevant` without choosing a timeframe
- WHEN the user opens the dropdown
- THEN the four options are listed under `RANK POST FROM` and `Last 7 Days` is highlighted as selected

#### Scenario: Choosing a timeframe reloads the feed
- GIVEN the user is on `Most Relevant (Last 7 Days)`
- WHEN the user selects `Last 24 Hours`
- THEN the feed refetches with `srch_interval=24h` and the tab reads `Most Relevant (Last 24 Hours)`

#### Scenario: The dropdown closes without changing the feed when dismissed
- GIVEN the dropdown is open
- WHEN the user clicks outside it or presses Escape
- THEN the dropdown closes, the timeframe is unchanged, and no refetch occurs

#### Scenario: The chevron switches modes rather than opening the dropdown on Latest
- GIVEN `Latest` is the active tab, whose `Most Relevant` label carries a chevron per DEC-006
- WHEN the user clicks that chevron
- THEN the feed switches to Most Relevant at the current timeframe — the request carries `srch_sort=most_relevant` and `srch_interval=1w` — `Most Relevant` becomes the active tab, and the dropdown opens in that mode

#### Scenario: The dropdown is never open while Latest is active
- GIVEN `Latest` is the active tab
- WHEN the user interacts with the tab strip in any way
- THEN no timeframe dropdown is shown over a Latest feed, and no timeframe can be selected without Most Relevant becoming active first

See DEC-009.

### Requirement: REQ-003 — The Most Relevant tab label reflects timeframe state
Source: Figma `8:2594` (initial) vs `2:5164` (Latest active); LD-436 comment 2026-09-14 requesting the initial state

The label is derived entirely from the URL, with `srch_sort` as the discriminator:

- **No `srch_sort` in the URL** — the user has not engaged with sorting. The tab reads `Most Relevant` with no timeframe suffix and no chevron. This is Figma `8:2594`.
- **`srch_sort=most_relevant`** — the tab reads `Most Relevant (<Timeframe>)` with a chevron, where the timeframe is read back from `srch_interval`.
- **`srch_sort=latest`** — the tab reads `Most Relevant (Last 7 Days)` with a chevron, using the default. It cannot read `srch_interval`, which REQ-005 pins to `1m` in this mode. This is Figma `2:5164`, which shows exactly the default while `Latest` is active. See DEC-006.

The active tab always carries its active styling, including on a first load where `Latest` is active by default — see DEC-005.

#### Scenario: Initial visit shows the bare Most Relevant label with Latest active
- GIVEN a user opens the Ticker with no `srch_sort` in the URL
- WHEN the tab strip renders
- THEN the second tab reads `Most Relevant` with no timeframe suffix and no chevron, and `Latest` is styled as the active tab

#### Scenario: The chevron and default timeframe appear after switching back to Latest
- GIVEN the user selected `Most Relevant` and `Last 3 Days`
- WHEN the user clicks the `Latest` tab
- THEN `Latest` becomes the active tab and the second tab reads `Most Relevant (Last 7 Days)` with its chevron

#### Scenario: Returning to Most Relevant starts from the default timeframe
- GIVEN the user picked `Last 3 Days`, then switched to `Latest`
- WHEN the user clicks `Most Relevant` again
- THEN the feed is requested with `srch_interval=1w` and the tab reads `Most Relevant (Last 7 Days)`

#### Scenario: A reload of a Most Relevant feed keeps its timeframe
- GIVEN the URL carries `srch_sort=most_relevant` and `srch_interval=3d`
- WHEN the page is reloaded
- THEN the tab reads `Most Relevant (Last 3 Days)` and the feed is ranked over that window

### Requirement: REQ-004 — The feed request carries the sort mode and the mapped interval
Source: LD-441 backend contract (`TickerRequest.php:55`, `TickerRepository.php:80`); user decision 2026-09-18

In Most Relevant mode the feed request sends `srch_sort=most_relevant` and `srch_interval` set from the selected timeframe using this mapping, all four keys of which already exist in `TickerRepository::$srchIntervals`:

| UI option | `srch_interval` |
| --- | --- |
| Last 24 Hours | `24h` |
| Last 3 Days | `3d` |
| Last 7 Days | `1w` |
| Last 14 Days | `2w` |

The frontend sends `srch_interval` explicitly and never relies on the backend's `1w` default, because `Ticker.tsx` already sets this parameter on every request.

`srch_sort` is sent **unconditionally**, including the literal `srch_sort=latest`. It is not omitted in Latest mode. This is load-bearing rather than cosmetic: `useTickerFeed` mirrors the query string into the URL, and REQ-003's three-state label discriminates a first visit (no `srch_sort`) from a deliberate return to Latest (`srch_sort=latest`). Omitting it would make the two indistinguishable and collapse the tab back to its bare label on every switch to Latest.

#### Scenario: Each timeframe maps to its interval key
- GIVEN the user is on `Most Relevant`
- WHEN the user selects `Last 14 Days`
- THEN the request carries `srch_sort=most_relevant` and `srch_interval=2w`

#### Scenario: Latest sends the sort parameter explicitly
- GIVEN the user clicks the `Latest` tab
- WHEN the feed is requested
- THEN the request carries `srch_sort=latest` and `srch_interval=1m`, and the backend's `latest` branch applies

#### Scenario: A first visit sends no sort parameter at all
- GIVEN a user opens the Ticker without interacting with the tab strip
- WHEN the first feed request is issued
- THEN it carries no `srch_sort` key, preserving REQ-005's byte-identical query string

### Requirement: REQ-005 — Latest keeps its existing one-month window
Source: LD-440 "No changes should be introduced to the current Latest feed behavior"; `Ticker.tsx:706`

`Ticker.tsx` hardcodes `srch_interval = "1m"` on every Ticker request today. In Latest mode that value is unchanged by this work. The timeframe dropdown governs Most Relevant only.

This produces a deliberate asymmetry: Most Relevant at `Last 14 Days` considers a two-week pool, and switching back to Latest widens the feed to a month. That follows from "Latest is unchanged" and is accepted — see DEC-002.

#### Scenario: Switching to Latest restores the one-month window
- GIVEN the user is on `Most Relevant (Last 24 Hours)`
- WHEN the user clicks `Latest`
- THEN the request carries `srch_interval=1m` and items older than 24 hours reappear

#### Scenario: A first load in Latest is byte-identical to today's request
- GIVEN a user opens the Ticker with no sort parameters
- WHEN the first feed request is issued
- THEN its query string is identical to the one the current implementation sends

### Requirement: REQ-006 — Filters and search survive every mode and timeframe change
Source: LD-442 "Active Ticker filters/search remain selected when switching…"

Switching Latest→Most Relevant, Most Relevant→Latest, or between timeframes changes only `srch_sort` and `srch_interval`. Every other query parameter, and the corresponding UI control state, is carried over untouched.

#### Scenario: A full filter set survives a mode switch
- GIVEN the user has a search term, selected categories, a platform, a locality and a franchise filter applied
- WHEN the user switches from `Latest` to `Most Relevant`
- THEN every one of those controls remains selected and the new request carries the same parameters plus `srch_sort` and the mapped `srch_interval`

#### Scenario: Filters survive a timeframe change
- GIVEN the user is on `Most Relevant (Last 7 Days)` with filters applied
- WHEN the user selects `Last 3 Days`
- THEN the filters remain applied and only `srch_interval` changes

### Requirement: REQ-007 — Sort mode and timeframe round-trip through the URL
Source: `useTickerFeed.ts:180` (`replaceState`), `useTickerUrlFilters.ts` (`popstate`, `pageshow` rehydration)

`useTickerFeed` already mirrors the full query string into the URL via `replaceState`, so the new parameters appear there automatically. `readFiltersFromURL` parses an explicit key list that currently includes neither `srch_sort` nor `srch_interval`; both must be added so a rehydration restores the mode and timeframe instead of silently reverting to Latest.

#### Scenario: A shared URL restores the mode and timeframe
- GIVEN a URL containing `srch_sort=most_relevant` and `srch_interval=3d`
- WHEN the page is opened
- THEN `Most Relevant (Last 3 Days)` is the active tab and the feed is relevance-ranked

#### Scenario: Back navigation restores the previous mode
- GIVEN the user switched from `Latest` to `Most Relevant`
- WHEN a `popstate` fires
- THEN the tab state and the feed both follow the URL rather than diverging from it

#### Scenario: A bfcache restore does not desynchronize the tabs from the feed
- GIVEN the user navigated away from a `Most Relevant` feed and returns via the back button
- WHEN `pageshow` fires
- THEN the tab strip and the feed agree on the mode and timeframe in the URL

#### Scenario: History entries win over the forward-path default
- GIVEN the user went `Latest` → `Most Relevant (Last 3 Days)` → `Latest`, which per DEC-006 reset the forward timeframe to the default
- WHEN the user presses Back into the `Most Relevant (Last 3 Days)` history entry
- THEN `srch_interval=3d` is restored from that entry and the tab reads `Most Relevant (Last 3 Days)` — history traversal is authoritative and DEC-006's reset does not override it

### Requirement: REQ-008 — Pagination and infinite scroll work identically in both modes
Source: LD-442 "Existing pagination/infinite loading behavior works correctly with both sorting modes"

Cursor pagination is unchanged. `useTickerFeed` resets the feed and scroll position whenever the query signature changes, which already covers a mode or timeframe change; no additional reset logic is introduced.

#### Scenario: Scrolling a relevance-ranked feed appends the next page
- GIVEN the user is on `Most Relevant` with more results than one page
- WHEN the user scrolls to the prefetch threshold
- THEN the next cursor page is appended with no duplicated and no skipped rows

#### Scenario: Changing mode resets scroll and cursor
- GIVEN the user has scrolled several pages into `Latest`
- WHEN the user switches to `Most Relevant`
- THEN the list is reset to the top and pagination restarts from the first page

### Requirement: REQ-009 — Existing loading, empty and error states are reused
Source: LD-442 "Standard loading behavior… Standard empty state…"; `TickerResultsPane.tsx:220-235`

The three existing states render unchanged in both modes: the loading line `filters.loading_results_please_wait`, the error line, and the empty block `filters.no_posts_match_filters` + `ticker.try_changing_or_clearing_filters`. No mode-specific state, copy or illustration is added.

#### Scenario: An empty relevance result shows the standard empty state
- GIVEN filters and a timeframe that match no items
- WHEN the `Most Relevant` feed returns zero rows
- THEN the existing empty block is shown, with its existing copy

#### Scenario: The tab strip stays visible and usable in the empty state
- GIVEN the empty state is displayed
- WHEN the user looks at the pane
- THEN the tab strip is still rendered, so the user can change mode or timeframe to recover

### Requirement: REQ-010 — Exports follow the active sort mode
Source: User decision 2026-09-18 ("add `srch_sort` in export path"); `TickerFilters.tsx:80-93, 149-160, 203-222`

`srch_sort` is added to `TICKER_FEED_ALLOWED_PARAMS` and forwarded by both export URL builders, so an export taken while Most Relevant is active is relevance-ranked rather than chronological. No backend change is needed: `TickerExportRequest extends TickerRequest`, so `srch_sort` is already validated, and `$request->safe()` carries it into `TickerService` and on to the same `TickerRepository::fetchAll` branch the feed uses.

The export's own range picker is unchanged and still governs the window, so the exported set is "what this ordering would return over the range I chose". Because the backend's `most_relevant` branch also excludes `paid_ads_event` rows of unsupported types, a Most Relevant export returns a **different row set**, not merely a different order — see DEC-008.

#### Scenario: A Most Relevant export is relevance-ranked
- GIVEN the user is on `Most Relevant`
- WHEN the user runs a Ticker export
- THEN the export request carries `srch_sort=most_relevant` and the exported rows are ordered by score, then recency

#### Scenario: A Latest export stays chronological
- GIVEN the user is on `Latest`
- WHEN the user runs a Ticker export
- THEN the export request carries `srch_sort=latest` and the exported rows are ordered chronologically, identically to today

#### Scenario: The export range comes from the dialog, not the feed
- GIVEN the user is on `Most Relevant (Last 7 Days)`
- WHEN the user opens the export dialog and selects `Last 1 month`
- THEN the export covers a one-month window ranked by relevance, and the feed's `srch_interval` is not forwarded

#### Scenario: The export dialog preselects the feed's current window
- GIVEN the user is on `Most Relevant (Last 7 Days)`
- WHEN the user opens the export dialog
- THEN its range control preselects `7d`, whose `interval` is `1w` (`exportTypes.ts`), matching the feed

### Requirement: REQ-011 — New copy is localized and the calendar icon is added
Source: `lang/en/ticker.php`, `lang/de/ticker.php`; `resources/js/components/icons/` (no calendar asset exists)

Every new string is a translation key present in both locales: the two tab labels, the four timeframe option labels, and the `RANK POST FROM` section header. English wording comes from the design verbatim.

Four timeframe keys already exist for the export dropdown — `ticker.last_24_hours` ("Last 24 hours"), `last_3_days`, `last_7_days`, `last_2_weeks` ("Last 2 weeks"). They are **not** reused: their sentence case and the "2 weeks" wording differ from the design's "Last 24 Hours" / "Last 14 Days". See DEC-007.

The design's calendar icon has no asset in `resources/js/components/icons/` — `clock.svg` and `chevron-down.svg` exist, a calendar does not. **Zornitsa Stoyanova supplies the calendar SVG** (user decision, 2026-09-18); it is not authored as part of this work. It is dropped into `resources/js/components/icons/` and imported in the same `?react` form as its siblings. Until it arrives, the Most Relevant tab is built against the existing `clock.svg` as a placeholder — an inbound dependency `/plan` should sequence, not a blocker for the rest of the work.

#### Scenario: No hardcoded user-facing string ships
- GIVEN the tab strip and dropdown are rendered
- WHEN their text is inspected
- THEN every label resolves through `trans(...)` and has an entry in both `lang/en/ticker.php` and `lang/de/ticker.php`

#### Scenario: The dropdown labels match the design verbatim
- GIVEN the timeframe dropdown is open in English
- WHEN its options are read
- THEN they read `Last 24 Hours`, `Last 3 Days`, `Last 7 Days`, `Last 14 Days` — title case, and "14 Days" rather than "2 weeks"

### Requirement: REQ-012 — No relevance score is rendered anywhere
Source: LD-440 and LD-442, "should not be displayed anywhere in the UI"

The backend returns the score through the existing `sales_relevance` field. This change adds no display of it — not on rows, overlays, tooltips, badges, labels, or in the tab strip.

#### Scenario: A relevance-ranked row renders exactly like a chronological one
- GIVEN the same post appears in both modes
- WHEN its row is rendered in `Most Relevant`
- THEN its visible content is identical to its `Latest` rendering, with no score and no ranking indicator

## Material Decisions

### DEC-001 — Four timeframe options, not the ticket's three
- Decision: the dropdown offers `Last 24 Hours`, `Last 3 Days`, `Last 7 Days`, `Last 14 Days`.
- Alternatives: implement the three options named in LD-440/LD-441/LD-442 and treat the fourth as a design error.
- Reason: the approved Figma (`2:3075`) shows four, and LD-442's first acceptance criterion is "UI matches the approved Figma design". The user resolved the conflict in favour of the design and confirmed `Last 14 Days` = two weeks with the existing `startOfDay` truncation. No backend change results, because `2w` already exists in `TickerRepository::$srchIntervals`.
- Source: user decision, 2026-09-18.
- Affects: REQ-002, REQ-004.

### DEC-002 — Latest keeps `srch_interval=1m`; the dropdown governs Most Relevant only
- Decision: the timeframe selection is not applied to the Latest feed, which continues to request a one-month window.
- Alternatives: apply the selected timeframe to both modes, giving one consistent window.
- Reason: `Ticker.tsx:706` hardcodes `1m` today, and LD-440 requires "No changes should be introduced to the current Latest feed behavior". Applying a ≤2-week window to Latest would narrow the existing feed — a regression the acceptance criteria forbid. The consequence is an accepted asymmetry: leaving `Most Relevant (Last 14 Days)` for `Latest` widens the pool to a month.
- Source: LD-440 acceptance criteria; repository evidence `Ticker.tsx:706`.
- Affects: REQ-004, REQ-005.

### DEC-003 — Mode and timeframe live in the URL, like every other Ticker filter
- Decision: `srch_sort` and `srch_interval` are URL-carried state, parsed by `readFiltersFromURL` alongside the existing `srch_*` keys.
- Alternatives: hold them in component state only, or persist them to `localStorage`.
- Reason: `useTickerFeed` already mirrors the whole query string into the URL and rehydrates on `popstate`/`pageshow`. Component-only state would desynchronize the tabs from the feed on back navigation and bfcache restore, and would make a Most Relevant view unshareable. No other Ticker filter uses `localStorage`.
- Source: repository precedent — `useTickerFeed.ts:180`, `useTickerUrlFilters.ts`.
- Affects: REQ-003, REQ-007.

### DEC-004 — Sort mode and timeframe are not part of a saved preset
- Decision: Ticker presets continue to store filters and search only. Applying a preset leaves the current sort mode and timeframe untouched.
- Alternatives: include sort mode in presets, so a saved view restores its ordering.
- Reason: neither LD-440 nor LD-442 mentions presets, and presets are a filter concept — LD-440 scopes the sort mode to "ranking and eligible data selection only". Widening the preset payload would change stored data shape for an unrequested benefit.
- Source: LD-440 scope statement; absence from both tickets' acceptance criteria.
- Affects: REQ-006.

### DEC-005 — The bare tab label is URL-derived, and the active tab is always styled
- Decision: the `Most Relevant` tab shows no timeframe and no chevron only while the URL carries neither `srch_sort` nor `srch_interval`. The active tab always receives its active styling, including `Latest` on a first load.
- Alternatives: (B) reproduce Figma `8:2594` literally, leaving neither tab styled active until the user clicks one; (C) track "has the user opened Most Relevant yet" as session state independent of the URL, so a reload of a Latest feed returns to the bare label.
- Reason: B would load the Ticker with a chronological feed and no tab highlighted, misrepresenting the active mode — the un-underlined `Latest` in the Initial frame is read as a design artifact, not intent. C would need state outside the URL, which no other Ticker filter uses, and would desynchronize the label from a shared link. A is the only option consistent with DEC-003.
- Source: user decision, 2026-09-18, resolving the Figma `8:2594` vs `2:5164` conflict.
- Affects: REQ-003.

### DEC-006 — The timeframe resets to the default on a round-trip through Latest
- Decision: while `srch_sort=latest`, the `Most Relevant` tab shows the default `Last 7 Days`, and returning to Most Relevant requests `srch_interval=1w`. A non-default timeframe is retained only while Most Relevant stays active.
- Alternatives: carry the last-used relevance window in a dedicated UI-only URL key (e.g. `srch_relevance_interval`) so the label and the next Most Relevant request restore the user's previous choice.
- Reason: REQ-005 pins `srch_interval=1m` while Latest is active, so `srch_interval` cannot carry the relevance window in that mode — the two cannot both be true of one parameter. The design does not require retention: Figma `2:5164` shows `Most Relevant (Last 7 Days)`, the default, while `Latest` is active, and no frame shows a non-default timeframe alongside an active `Latest`. The alternative adds a second window parameter to satisfy a behavior neither ticket asks for.
- Scope: this describes the **forward interaction** only — clicking `Latest` and then `Most Relevant` again. It does not govern history traversal: a Back navigation into a `Most Relevant` history entry restores that entry's `srch_interval`, per REQ-007's history scenario. The URL remains the single state of record in both directions.
- Source: internal contradiction found while drafting, 2026-09-18; resolved against Figma `2:5164` and REQ-005. Flagged to the user for override.
- Affects: REQ-003, REQ-004, REQ-007.

### DEC-007 — New translation keys for the sort dropdown rather than reusing the export's
- Decision: add dedicated keys whose English matches the design verbatim (`Last 24 Hours`, `Last 3 Days`, `Last 7 Days`, `Last 14 Days`).
- Alternatives: reuse the existing `ticker.last_24_hours` / `last_3_days` / `last_7_days` / `last_2_weeks`, which the export dropdown already uses.
- Reason: LD-442's first acceptance criterion is "UI matches the approved Figma design", and the existing values differ in case ("Last 24 hours") and in wording for the fourth option ("Last 2 weeks" vs "Last 14 Days"). Reusing them would fail that criterion.
- Consequence, stated because it is a real cost: the same two-week window is labelled "Last 14 Days" in the sort dropdown and "Last 2 weeks" in the export dialog. A single shared key set would be more consistent but would not match the approved design. Cheap to reverse if the product owner prefers consistency.
- Source: design `2:3075` vs `lang/en/ticker.php:17-20`, read 2026-09-18.
- Affects: REQ-002, REQ-011.

### DEC-008 — Exports carry the sort mode but keep their own range picker
- Decision: forward `srch_sort` to both export builders; continue stripping the feed's `srch_interval` and letting the export dialog's six-option range picker set the window.
- Alternatives: (a) leave exports chronological, as the original draft had it; (b) forward both `srch_sort` and the feed's `srch_interval`, making the export mirror the feed exactly and retiring the export range picker.
- Reason: the user asked for the sort mode in the export path. Option (b) would silently discard a deliberate, existing user control and would cap exports at two weeks, since the sort dropdown has no `3w` or `1m` option — a regression for anyone exporting a month. Forwarding only the ordering keeps both controls meaningful.
- Consequence, stated because it is more than cosmetic: a Most Relevant export returns a different **set** of rows, not just a different order, because the backend's `most_relevant` branch excludes `paid_ads_event` rows whose type is outside the supported list. A user comparing a Latest export with a Most Relevant export over the same range may find fewer rows in the latter.
- Source: user decision, 2026-09-18; `TickerExportRequest extends TickerRequest` confirms no backend change is required.
- Affects: REQ-010.

### DEC-009 — The timeframe dropdown is unreachable while Latest is active; its chevron switches modes
- Decision: the dropdown cannot be opened while `Latest` is the active tab. The chevron stays visible there, per Figma `2:5164`, and clicking it — or anywhere on the `Most Relevant` tab — switches the feed to Most Relevant and opens the dropdown in that mode. A timeframe is therefore only ever selected while Most Relevant is already active.
- Alternatives: (a) selecting a timeframe from the Latest tab applies it and switches mode in one action; (b) draw the chevron inert, so it ignores clicks while Latest is active; (c) hide the chevron entirely on Latest.
- Reason: user decision. It keeps the design's chevron visible without leaving a dead control — every visible affordance does something — while preserving the rule that the timeframe belongs to Most Relevant. Option (a) was recorded first and reversed by the user the same day; (b) leaves a visible control that ignores clicks; (c) departs from the design.
- Consequence: switching via the chevron costs one extra click before a timeframe can be picked, and the feed reloads at the current timeframe on that first click.
- Source: user decision, 2026-09-18, revising the same day's earlier reading.
- Affects: REQ-002, REQ-003.

### DEC-010 — WITHDRAWN (proposed label change to "Last 2 Weeks")
- Status: **withdrawn 2026-09-18, same day it was recorded.** It arose from a misread instruction, not a product decision; the user confirmed the fourth option keeps the design's `Last 14 Days`.
- The id is retained rather than reused, so the reversal stays visible instead of vanishing from the record.
- Affects: nothing. REQ-002 and REQ-011 read as they did before it.

## Tech Stack

- PHP 8.4, Laravel 12, Inertia v3, React 19, TypeScript, Tailwind CSS 4, Vite.
- Testing: Vitest 4 with `@testing-library/react`; Pest 4 for backend.
- Icons are SVGs imported as React components (`@/components/icons/<name>.svg?react`).
- Package manager: Yarn.

## Commands

- Frontend tests: `yarn test` (resolves to `vitest run`)
- Lint: `yarn lint` — fix with `yarn lint:fix`
- Format check: `yarn format` — write with `yarn format:write`
- Build: `yarn run build` (`tsc && vite build`)
- Dev server: `yarn dev`
- Backend regression (LD-441's suite): `composer test -- --compact --filter=Ticker`
- Assets for browser verification in this checkout: `bin/worktree-setup.sh --build`

`composer test` in this checkout exits 1 even when every test passes — read the `Tests:` summary line, not the exit code. Verified 2026-09-18 across eight filters; evidence in this session's scratchpad.

## Project Structure

- `resources/js/pages/Advertisers/Ticker.tsx` — page container; owns filter state and the `queryFilters` memo (`:704-780`)
- `resources/js/components/partials/TickerPage/TickerResultsPane.tsx` — results pane; the tab strip belongs between the filter header (`:184-218`) and the state branch (`:220`)
- `resources/js/components/partials/TickerPage/` — Ticker-specific components; `TickerPresetsDropdown.tsx` is the closest dropdown precedent
- `resources/js/hooks/useTickerFeed.ts` — fetching, cursor pagination, URL mirroring
- `resources/js/hooks/useTickerUrlFilters.ts` — URL parsing and rehydration
- `resources/js/utils/ticker/` — helpers and constants
- `resources/js/components/icons/` — SVG assets
- `lang/{en,de}/ticker.php` — translation keys

No new base directory is introduced.

## Code Style

Follow `TickerPresetsDropdown.tsx` for the dropdown idiom — local `open` state, a `ref` for outside-click dismissal, `useTranslations`, icons imported as components:

```tsx
import IconChevronDown from '@/components/icons/chevron-down.svg?react';
import { useTranslations } from '@/hooks/use-translations';

export default function TickerSortTabs({ sort, interval, onChange }: Props) {
    const { trans } = useTranslations();
    const [open, setOpen] = useState(false);
    // …
}
```

Per `.ai/rules/js.md`: access API fields directly, type payloads honestly, and add no defensive coercion wrappers or response-shape guesses. Per `.ai/rules/ticker-page.md`: do not add per-component copies of shared constants — the timeframe option list is a single exported constant.

## Testing Strategy

Component and unit coverage with Vitest, alongside the existing `TickerFilters.test.tsx` and `TickerPostRow.test.tsx` precedents in the same directory.

| Requirement | Evidence |
| --- | --- |
| REQ-001 | Component test: tab strip renders both tabs; clicking each one invokes the change handler with the expected mode |
| REQ-002 | Component test: dropdown lists the four options under the section header, marks the selected one, closes on outside click and Escape |
| REQ-003 | Component test over the three URL states: no `srch_sort` renders the bare label; `srch_sort=most_relevant&srch_interval=3d` renders `Most Relevant (Last 3 Days)`; `srch_sort=latest` renders `Most Relevant (Last 7 Days)` with a chevron and `Latest` styled active |
| REQ-004 | Unit test on the query-building helper: each of the four options produces its interval key, and Most Relevant adds `srch_sort` |
| REQ-005 | Unit test: the Latest-mode query string equals the current implementation's for the same filter state, including `srch_interval=1m` |
| REQ-006 | Unit test: a populated filter set is preserved across a mode change and a timeframe change, with only the two keys differing |
| REQ-007 | Component test with a seeded `window.location.search`: mode and timeframe hydrate from the URL; `popstate` and `pageshow` re-hydrate them |
| REQ-008 | **Manual verification only.** No automated test covers it. `useTickerFeed`'s reset already keys off the query signature and is unchanged by this work, and cursor correctness is LD-441's proven backend invariant — but "no duplicated and no skipped rows" across a real multi-page relevance traversal is checked by hand, not asserted |
| REQ-009 | Component test: the pane renders the existing loading, error and empty branches in Most Relevant mode with the existing translation keys |
| REQ-010 | Unit test on `normalizeTickerFeedExportParams` and `buildTickerFeedExportRequestUrl`: both carry `srch_sort` through, neither carries the feed's `srch_interval`, and the range picker's own interval wins. Plus a manual export in each mode during end-to-end verification |
| REQ-011 | Unit test asserting every new key resolves in both locale files; lint and `tsc` cover the icon import |
| REQ-012 | Component test: a row's rendered output is identical between modes, asserting no score text is present |

Backend regression for the mode itself is already covered by LD-441's suite: `composer test -- --compact --filter=Ticker` (77 tests, 524 assertions at the time of writing).

REQ-008 is the one requirement with no automated evidence; the manual pass below is its only verification, and `/review` should treat it as such rather than assuming the table covers it.

End-to-end verification is manual in this checkout: `bin/worktree-setup.sh --build`, then exercise the four timeframes, both mode switches, a filter set, back navigation and an export. The project has **no** `tests/Browser` directory; Pest 4 supports browser tests, but adding that directory is a new base folder and needs approval under the project's structure rule, so it is not assumed here.

## Invariants and Mechanism Proof

The one invariant this change must not break is **feed-query equivalence for Latest**: for any filter state, the query string produced in Latest mode is identical to the one the current implementation produces.

- Writers: the `queryFilters` memo in `Ticker.tsx` is the single place that assembles feed parameters. There is no second assembly path — `useTickerFeed` forwards `queryFiltersRef.current` verbatim and appends only `srch_cursor`.
- Enforcement: the two new keys are added conditionally, and in Latest mode `srch_interval` retains its literal `1m`.
- Coverage: because assembly is single-sourced, a unit test over that memo's output covers every transition into and out of Latest, including the empty filter state.
- Evidence: REQ-005's scenarios, tested at the helper level.

Cursor stability is a backend invariant, established and proven under LD-441 (`sfp.id` is unique across all three item classes). This change introduces no client-side reordering, merging or deduplication, so it cannot affect it.

## Data Lifecycle

N/A — this change persists nothing. Sort mode and timeframe are request parameters mirrored into the URL (DEC-003); they are not written to the database, to a preset (DEC-004), or to browser storage. Nothing is created, soft-deleted, archived or restored.

## Boundaries

- **Always:** keep `srch_interval=1m` for Latest; route every new string through `trans(...)` in both locales; keep the timeframe option list a single shared constant; reuse the existing loading, empty and error branches.
- **Ask first:** any change under `Modules/` (this ticket is frontend-only); adding a `tests/Browser` directory; widening the preset payload; hardening `srch_interval` validation.
- **Never:** render a relevance score; modify Ticker rows or overlays; duplicate the feed-query assembly; add a client-side sort, merge or dedupe over the returned pages.

## Open Questions

None. The initial tab-state question was resolved on 2026-09-18 and recorded as DEC-005.
