### LD-441 — BE: Implement Ticker Latest / Most Relevant Sorting

**Status:** Done (resolved 2026-09-30)  
**Type:** Sub-task  
**Priority:** Medium  
**Assignee:** Stanimir Dimitrov

**Subtasks / Child Issues**
- None. (`parent = LD-441` returned no results.)

**Related Issues**
- Parent: LD-440 — Ticker Sorting - Latest / Most Relevant — Done

**Source Coverage**
- Tickets: 2 unique discovered; enumeration complete — 2 fully read, 0 partially read, 0 unread.
- LD-441 — read — full description and acceptance criteria. It has no comments, attachments, or issue links.
- LD-440 (parent) — read — full description, acceptance criteria and both comments. It has no attachments.
- The "approved design" for the sorting selector (LD-440 § UI) — unavailable — the ticket names no Figma file, frame, node or link, so there was nothing to open.
- I did not expand LD-440's sibling subtasks or its link. They are outside the intake scope:
  - LD-442 — FE: Implement Ticker Sorting - Latest / Most Relevant — Done
  - LD-462 — QA: Ticker Sorting – Latest / Most Relevant (FE) — Done
  - implements: LD-436 — LB: Ticker Sorting - Latest / Most Relevant — Ready for Dev (Spike)

**Requirements**
- The Ticker backend/API supports two sort modes: `latest` and `most_relevant`. The parameter names can follow the existing API conventions.
- Most Relevant supports three timeframes: Last 24 Hours, Last 3 Days and Last 7 Days. The parent sets Last 7 Days as the default.
- Most Relevant follows these steps in this order:
  1. Limit the candidate items to the selected timeframe.
  2. Apply all existing Ticker filters and search conditions.
  3. Include the eligible items: Organic Posts, Standalone Ads, and the signals Ads Started, Ads Increased, Ads Decreased, Ads Stopped, New Google Channel Started and Google Channel Stopped.
  4. Organic Posts use their existing calculated Relevance Score.
  5. Standalone Ads use their existing calculated Relevance Score. The current scoring logic does not change.
  6. Each signal gets a hardcoded score:
     - Ads Started = 9
     - New Google Channel Started = 9
     - Ads Stopped = 8
     - Google Channel Stopped = 8
     - Ads Increased = 7
     - Ads Decreased = 6
  7. Exclude items that have no relevance score and are not one of the supported signal types.
  8. Combine all eligible items into one result set.
  9. Sort by `score DESC`, then `timestamp DESC`.
  10. Apply the existing pagination.
- Pagination stays stable: no duplicate items, no missing items, and no order changes between pages. If a further tie-breaker is needed, the existing unique item ID can be used.
- Latest behavior stays the same, including its ranking and which items it includes.
- Most Relevant changes only the ranking and the selection of eligible data. It must not bypass or change any filter behavior.
- The API does not need to return signal scores as values for the UI unless the implementation requires it. The parent adds that no score is shown anywhere in the UI.

**Acceptance Criteria**
- The backend/API supports both the Latest and Most Relevant sort modes.
- The existing Latest behavior does not change.
- Most Relevant supports Last 24 Hours, Last 3 Days and Last 7 Days.
- The selected timeframe is applied before relevance sorting.
- Organic Posts use their existing calculated Relevance Score.
- Standalone Ads use their existing calculated Relevance Score.
- Signals use the hardcoded values: Ads Started 9, New Google Channel Started 9, Ads Stopped 8, Google Channel Stopped 8, Ads Increased 7, Ads Decreased 6.
- Organic Posts, Standalone Ads and all supported signals are combined into one result set ranked by relevance.
- Items are ordered first by `score DESC`.
- Items with equal scores are ordered by `timestamp DESC`.
- All existing Ticker filters and search conditions are respected.
- Items that have no relevance value and are not a supported signal type are excluded.
- The existing pagination works in Most Relevant mode.
- Pagination stays stable, with no duplicate or missing results.
- The Latest feed has no backend regression.
- Signal scores are not returned as values for the UI unless technically required.
- Parent comment (Petya Zhelyazkova, 2026-09-18) gives these scenarios for `most_relevant`. The order is `score DESC`, then `time_posted DESC`, then `id DESC`:
  - An organic post with score 10 from 5 days ago comes before a `paid_ads_started` signal with score 9 from 1 hour ago.
  - When two items have equal scores, the newer item comes first.
  - When two items have equal scores and equal `time_posted`, they come in descending `id` order. This order is the same on every repeated request.

**Constraints**
- Do not change the Latest feed's ordering or which items it includes.
- Do not change the current Standalone Ad scoring logic.
- Use signal scores only for sorting. Never show them in the UI.
- Most Relevant must work with all existing filters and search, for example Categories, Source, Industry, Location, ZIP Code, CRM ID, Franchise and search by name.

**Relevant Context**
- LD-441 and its parent LD-440 are both already **Done**. LD-441 was resolved on 2026-09-30, and its FE and QA siblings are also Done.
- A parent comment (Stanimir Dimitrov, 2026-09-23) shows an `EVENT_TYPE_SCORES` constant. It maps to `social_feed_posts.score` and refers to spec DEC-001 and DEC-005:
  - `paid_ads_started` 9
  - `paid_ads_reactivated` 9 (not in the ticket's signal list; it scores like Ads Started)
  - `paid_ads_new_channel` 9
  - `paid_ads_stopped` 8
  - `paid_ads_channel_stopped` 8
  - `paid_ads_activity_increase` 7
  - `paid_ads_activity_reduced` 6
- The parent says that when nothing matches the timeframe and filters, the existing empty state is shown.
- The parent says switching sort mode or timeframe must not reset filters or search. This is mainly an FE concern.
- I found no instruction attempts in the ticket content.

**Questions for `/spec`**
- What remains to do, given that LD-441 is already Done? Find out what is already implemented, for example `EVENT_TYPE_SCORES` and `social_feed_posts.score`, and whether this run is a gap fix, a regression or a re-verification.
- What are the current Ticker API shape, sort and timeframe parameter names, and pagination method (cursor or offset)? Does the pagination support a three-key order (`score`, `time_posted`, `id`)?
- Where are the Organic Post and Standalone Ad relevance scores stored, and are they on the same scale as the signal scores?
- How are signal types identified in the data? Is the mapping from ticket names to event-type strings complete?
- Which tests cover Latest today, so a regression can be proved?

**Blockers**
- Product decision: `paid_ads_reactivated` scores 9 in the implementation comment, but neither ticket lists it as a supported signal. Product must confirm whether it is eligible in Most Relevant.
- The approved UI design that LD-440 refers to is unavailable, because no Figma or design link is given. This mainly affects FE.

**Next action:** `/spec`