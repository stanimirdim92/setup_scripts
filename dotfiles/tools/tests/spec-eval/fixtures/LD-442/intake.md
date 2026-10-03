### LD-442 — FE: Implement Ticker Sorting - Latest / Most Relevant

**Status:** Done  
**Type:** Sub-task  
**Priority:** Medium  
**Assignee:** Stanimir Dimitrov

**Subtasks / Child Issues**
- None. (Checked with JQL `parent = LD-442`, which returned 0 results.)

**Related Issues**
- Parent: LD-440 — Ticker Sorting - Latest / Most Relevant — Done
- Sibling sub-task of LD-440: LD-441 — BE: Implement Ticker Latest / Most Relevant Sorting — Done
- Sibling sub-task of LD-440: LD-462 — QA: Ticker Sorting – Latest / Most Relevant (FE) — Done
- LD-440 implements (Polaris work item link): LD-436 — LB: Ticker Sorting - Latest / Most Relevant — Ready for Dev (Spike)

**Source Coverage**
- Tickets: 2 unique discovered (LD-442, parent LD-440); enumeration complete — 2 fully read, 0 partially read, 0 unread.
- LD-442 — read — description and FE acceptance criteria. It has no comments, links or attachments.
- LD-440 — read — description, acceptance criteria and both comments.
- LD-441, LD-462 and LD-436 are outside intake scope because they are siblings or a link of the parent. They were not read.
- Figma `nesnGzq4y7Bfo40fTaDw4y` (canvas `0:1`, "Design") — read through metadata and screenshots. It has 4 frames:
  - `8:2575` "Initial"
  - `2:3891` "Latest"
  - `1:5247` "Most relevant (closed)"
  - `2:3075` "Most relevant (open)"
- Screenshots read: tabs `8:2594` (Initial), tabs `2:5164` (Latest), and the tab and dropdown area `2:3093` (Most relevant open). `get_design_context` was not called, so exact tokens and spacing are still unread.

**Requirements**
- Add a sorting control above the Ticker list: **Latest | Most Relevant (Last 7 Days) ▾**.
- Latest:
  - Shows the existing chronological feed.
  - Current behavior stays unchanged.
  - No timeframe selector is required.
- Most Relevant:
  - Requests the relevance-ranked feed from the backend.
  - Shows the selected timeframe inside the tab.
  - Clicking the arrow opens a dropdown with Last 24 Hours, Last 3 Days and Last 7 Days.
  - The default is Last 7 Days.
  - Changing the timeframe reloads the feed with the new period.
- Keep all active search and filter state when the user switches Latest ↔ Most Relevant or changes the timeframe. This covers search, Categories, Source, Location, Industry, CRM ID, Franchise and other existing filters. Only the dataset and sorting change.
- Do not show any score anywhere: not on cards, overlays, tooltips, badges or labels. This covers Organic Post and Standalone Ad Relevance Scores and the hardcoded Signal scores.
- Do not change the content or structure of existing Ticker cards or overlays.
- The only new UI is the tab navigation, the timeframe dropdown, and the loading and state handling for the feed.
- Reuse the existing loading patterns. Use the standard Ticker empty state when no results match.
- Existing pagination and infinite loading must work in both modes.
- Figma details:
  - Latest has a clock icon and Most Relevant has a calendar icon.
  - The active tab is underlined.
  - The dropdown header reads "RANK POST FROM".
  - The selected option is highlighted.
  - The tab chevron points up while the dropdown is open.

**Acceptance Criteria**
- UI matches the approved Figma design.
- Latest and Most Relevant tabs are implemented.
- Latest loads the existing chronological feed.
- Most Relevant loads the relevance-ranked feed from the backend.
- Most Relevant shows the selected timeframe.
- The dropdown arrow shows Last 24 Hours, Last 3 Days and Last 7 Days.
- Last 7 Days is the default.
- Changing the timeframe requests the correct result set.
- Filters and search stay active when the user switches tabs or changes the timeframe.
- No Relevance Score is shown for Organic Posts or Standalone Ads.
- No hardcoded score is shown for Signals.
- Existing cards and overlays look the same as before.
- The standard loading behavior shows while results are fetched.
- The standard empty state shows when no results match.
- Pagination and infinite loading work in both modes.
- The existing Latest Ticker has no visual or functional regression.

**Constraints**
- The UI must not show scores.
- Existing cards and overlays must not change.
- Latest feed behavior must not change.
- Reuse the existing loading, empty-state and pagination mechanisms.

**Relevant Context**
- All tickets in scope are already **Done**: LD-442, parent LD-440, and siblings LD-441 (BE) and LD-462 (QA). The work may already exist in the codebase.
- Backend contract from LD-440:
  1. Apply the timeframe first.
  2. Apply the active filters and search.
  3. Rank the eligible items in one combined set.
  4. Sort by score DESC, then timestamp DESC.
  5. Paginate without duplicates or missing items.
- Eligible items are:
  - Organic Posts and Standalone Ads that have a relevance score.
  - These Signals: Ads Started 9, New Google Channel Started 9, Ads Stopped 8, Google Channel Stopped 8, Ads Increased 7, Ads Decreased 6.
  - Other items are excluded.
- LD-440 comment by Petya Zhelyazkova: the backend mode is named `most_relevant`. The order is `score DESC`, `time_posted DESC`, `id DESC`, and repeated requests return the same order.
- LD-440 comment by Stanimir Dimitrov: the backend defines `EVENT_TYPE_SCORES` in `social_feed_posts.score`. `paid_ads_reactivated` also scores 9 (spec DEC-005), so seven event types are scored.

**Questions for `/spec`**
- Is LD-442 already implemented in the repo? If yes, what is left (gaps, regressions or follow-up), given that the ticket is Done?
- What request parameters does the backend use for sort mode and timeframe (e.g. `most_relevant` plus a period value), and through which endpoint?
- Where does the Ticker keep its filter, search and pagination state, so that switching sort mode keeps it?
- Should the sort mode and timeframe persist in the URL or query state?
- Do the translation keys for the tabs, dropdown header and options already exist (EN/DE)?
- What does the "Initial" Figma frame (`8:2575`) mean? It shows "Most Relevant" without a timeframe or chevron, and neither tab is clearly active.

**Blockers**
- The Figma dropdown (`2:3075`/`2:3093`) shows **four** options, including **"Last 14 Days"**. LD-442 and LD-440 both list only three options. The product owner must decide whether Last 14 Days is in scope.
- The Figma "Latest" frame (`2:5164`) shows "Most Relevant (Last 7 Days) ▾" with a chevron while Latest is active. This may conflict with "no timeframe selector is required" in Latest mode. The product owner must decide what the inactive Most Relevant tab shows.

**Next action:** `/spec`