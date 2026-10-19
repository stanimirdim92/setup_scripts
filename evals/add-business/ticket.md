# ADD-1 — Add a business from places search

**Status:** To Do
**Type:** Story
**Priority:** Medium
**Assignee:** Unassigned

## Summary

An internal user adds a new business to Acme Leads. The user finds the
business in a places search. The user does not type the data by hand. The
user searches, confirms one match and submits. A duplicate check and
enrichment run in the background. The business then appears in the
Businesses list without more action. No email is sent.

Targets:

- A business is added in under 30 seconds.
- Nobody types an address or a website by hand.
- No duplicate businesses are created.

## Scope

- A centered modal with a dimmed, blurred backdrop.
- The "+ Add business" button on the Businesses page opens it.
- Two steps (Search, Confirm) and a success state.
- Empty, loading and error states. The modal works on a phone-width screen.
- Backend: business search, duplicate check, creation with the `pending`
  status, an enrichment trigger, and the change to `available` so the
  business shows in the list.

## Out of scope

- The Businesses list page itself. It exists already.
- The business detail page.
- The enrichment logic. Only the trigger and the pending handling are in
  scope.

## Constraints

- Use the existing stack: plain PHP 8.2+, vanilla JavaScript, SQLite through
  PDO. Do not add Composer or npm dependencies to the app.
- Use the existing places client (`Acme\Places\PlacesClient`). The fixture
  client is the default and makes no network calls.
- `fixtures/places.json` and the rows in `database/seed.sql` are fixed test
  data. Do not change them.
- All mail goes through `Acme\Mailer`, which writes to the `outbox` table.
  This feature sends no mail, so the `outbox` table stays empty.

## User flow

1. The user clicks "+ Add business". The modal opens in the empty state.
2. Step 1, Search. The user types a company name. A city or ZIP is
   optional. The search runs when the query has 2 or more characters.
3. The user selects one result. A change to the query clears the selection.
   "Continue" stays disabled until a result is selected.
4. Step 2, Confirm. A card shows the name, place ID, category, a Maps link,
   the street, ZIP and city, the website and the phone. The user can add
   notes. The user submits.
5. If the business already exists, a duplicate notice shows instead. It
   shows the existing record and an "Open business" action. Submit is not
   possible.
6. Submit creates the business with the `pending` status and starts
   enrichment. The success state shows a request ID and "Live in about an
   hour".
7. When enrichment finishes, the business appears in the Businesses list.
   There is no notification.

## States

1. **Default / Empty.** The search field and a hint.
2. **Searching.** A loading indicator.
3. **Results.** A dropdown with "Best matches" and "N found". Each row shows
   the name, street, ZIP, city and a category pill. A footer says the search
   is powered by places search. A row that is already in Acme Leads has an
   amber "Already in Acme Leads" badge.
4. **Selected.** The selected row is highlighted: a tint, a left accent and a
   check circle. A confirmation strip shows below the field.
5. **No results.** An icon, "No match yet", guidance, and three suggestion
   chips: "Add city", "Add ZIP", "Check spelling". Each chip moves the focus
   to the search field.
6. **Search error.** A clear error and a "Retry" button. Retry runs the same
   query again.
7. **Confirm (step 2).** The card from the user flow, an optional Notes
   field, and a note about background enrichment and the duplicate check.
8. **Submitting.** The Submit button shows an inline spinner and the label
   "Submitting". It is disabled.
9. **Submit failure.** A clear error. The step keeps the entered notes, so the
   user can submit again.
10. **Duplicate (step 2).** The same card. A notice replaces Notes and
    Submit. The notice gives the existing record ID and an "Open business"
    link.
11. **Success.** A green check, "Request received", a line about enrichment,
    a request pill (request ID, business name, city), a "Live in about an
    hour" info card, and one "Done" button.

## Duplicate rules

A place is a duplicate of an existing business when one of these rules
matches. Businesses with any status count, `pending` included. The rules are
checked in this order. The first match is the reported rule.

1. `place_id` — the place ID is equal.
2. `cid` — the CID is equal.
3. `domain` — the normalized root domain of the website is equal. To
   normalize: read the URL (no scheme means `http://`), take the host in
   lower case, drop a leading `www.`, and keep the last two labels. Keep three
   labels when the second-to-last label is `co`, `com`, `net`, `org`, `gov` or
   `ac` and the last label has two letters (`shop.example.co.uk` →
   `example.co.uk`). A place or business without a website never matches.
4. `name_zip` — the normalized name and the ZIP are equal. To normalize a
   name: lower case, replace each character that is not a letter or a digit
   with a space, collapse spaces, trim.
5. `phone` — the normalized phone is equal. To normalize: keep the digits
   only, then keep the last 10 digits. A phone with fewer than 10 digits, or
   no phone, never matches.

A match blocks creation and shows the existing record.

## Interaction rules

- The search runs when the trimmed query has 2 or more characters. A shorter
  query sends no request.
- Matching is multi-token. Split the query on spaces and commas. A place
  matches when each token, case-insensitive, is a substring of its name,
  street, ZIP, city or category.
- A change to the query clears the selection.
- "Continue" is disabled until a result is selected. The footer hint changes
  from "Select a business to continue" to "Ready when you are".
- Submit shows the spinner and "Submitting", then the success state.
- The step indicator goes from step 1 to step 2. The completed step shows a
  check icon and the connector turns purple.
- Close (X), "Cancel" and "Done" close the modal and reset it to the empty
  state.

## Copy

Use these strings exactly. Quotes are not part of the string.

| Where | Text |
| --- | --- |
| Button on the Businesses page | "+ Add business" |
| Modal title | "Add business" |
| Step names | "Search", "Confirm" |
| Search field label | "Search for a business" |
| Empty hint | "Search is powered by places search. Add a city or ZIP to narrow it down." |
| Searching | "Searching..." |
| Results header | "Best matches", "{N} found" |
| Results footer | "Powered by places search" |
| Badge | "Already in Acme Leads" |
| Confirmation strip | "Selected: {name}" |
| Footer hint, nothing selected | "Select a business to continue" |
| Footer hint, selected | "Ready when you are" |
| No results | "No match yet", "Try another name, or add a city or ZIP." |
| Chips | "Add city", "Add ZIP", "Check spelling" |
| Search error | "Search is unavailable right now." |
| Maps link | "Open in Maps" |
| Notes label | "Notes (optional)" |
| Confirm note | "We enrich the data and check for duplicates in the background." |
| Submit failure | "We could not submit this business. Please try again." |
| Duplicate notice | "This business is already in Acme Leads.", "Existing record #{id}" |
| Success title | "Request received" |
| Success line | "We are enriching the data. The business appears in your list when it is ready." |
| Info card | "Live in about an hour" |
| Buttons | "Cancel", "Continue", "Back", "Submit", "Submitting", "Retry", "Open business", "Done" |
| Close button (X) | accessible name "Close" |

## Accessibility contract

Tests find elements by role, label and the copy above. They do not use CSS
classes.

- The modal is `role="dialog"` with `aria-modal="true"`. Its accessible name
  is "Add business". When closed, it is removed or hidden.
- The step indicator is a list with the accessible name "Progress". The
  current step has `aria-current="step"`. A completed step contains an image
  (`role="img"`) with the accessible name "Completed".
- The search field has the label "Search for a business".
- The results are a `role="listbox"` with the accessible name "Search
  results". Each result is a `role="option"`. The selected one has
  `aria-selected="true"`. A click selects a result.
- The Searching indicator is inside a `role="status"` element.
- The search error, the submit failure and the duplicate notice are inside
  `role="alert"` elements.
- "Open business" links to `/businesses/{id}`.
- At a 375 px wide viewport, the modal fits the viewport and the page does
  not scroll horizontally.

## API contract

All bodies are JSON. Errors are `{"error": "<code>"}` plus the fields named
below.

A **Place** is:

```json
{
  "place_id": "plc_F201",
  "cid": "7770201",
  "name": "Sunrise Bakery",
  "street": "1550 Irving St",
  "zip": "94122",
  "city": "San Francisco",
  "category": "Bakery",
  "website": "https://sunrisebakery.com",
  "phone": "+1 415-555-0301",
  "maps_url": "https://www.google.com/maps?cid=7770201"
}
```

`website` and `phone` can be `null`.

A **Business** is the existing shape from `GET /api/businesses`:
`id` (integer), `name`, `place_id`, `cid`, `street`, `zip`, `city`,
`category`, `website`, `phone`, `maps_url`, `notes`, `status`
(`"pending"` or `"available"`).

### `GET /api/places/search?q={query}`

- `200` — `{"query": "...", "results": [Result, ...]}`. A Result is a Place
  plus `"existing"`. `existing` is `null`, or
  `{"id": 101, "name": "...", "status": "available", "rule": "domain"}` when
  the duplicate rules match. `rule` is one of `place_id`, `cid`, `domain`,
  `name_zip`, `phone`. Results keep the order of the places client.
- `422` — `{"error": "query_too_short"}` when the trimmed query has fewer than
  2 characters.
- `502` — `{"error": "places_unavailable"}` when the places client fails.

### `POST /api/businesses`

Body: `{"place_id": "plc_F201", "notes": "optional text"}`. The server gets
the place data from the places client. It never takes the address, website or
phone from the request.

- `201` — `{"request_id": "REQ-7K2M9QXA", "business": Business}`. The
  business has `"status": "pending"` and the given notes (`null` when empty).
  The request ID is `REQ-` and 6 or more upper-case letters or digits. The
  server records an enrichment request for the business.
- `409` — `{"error": "duplicate", "existing": {"id": 101, "name": "...",
  "status": "available", "rule": "domain"}}`. Nothing is created.
- `404` — `{"error": "place_not_found"}` when the places client has no place
  with that ID.
- `422` — `{"error": "invalid_request"}` when `place_id` is missing or empty,
  or `notes` is longer than 1000 characters.

### `GET /api/businesses` (exists)

`200` — `{"businesses": [Business, ...]}`. Only `available` businesses. A
`pending` business is not in this list and not on the Businesses page.

### Enrichment command: `php bin/enrich`

Runs every open enrichment request. The business of each request becomes
`available`. The command prints `Enriched {N} business(es)` and exits with 0.
Production runs it from cron. The enrichment logic itself is out of scope.

## Test hooks

- `ACME_DB` — the SQLite file. `php bin/migrate` resets it to the schema and
  the seed rows.
- `ACME_PLACES_FIXTURE` — the fixture file for the fixture places client.
  The default is `fixtures/places.json`.
- `ACME_PLACES_FAIL=1` — the fixture places client fails every call. The
  search endpoint then returns `502`.
- The UI calls the endpoints above with `fetch`, so a test can intercept them
  to simulate a slow call or a failure.

## Acceptance criteria

1. A user opens the modal and searches by name, city or ZIP.
2. Results come from the places search. Each shows the name, the address, the
   category, and the "Already in Acme Leads" badge when the business exists.
3. "Continue" shows the Confirm step prefilled from the place. Nothing is
   typed by hand.
4. Submit creates the business as `pending` and triggers enrichment.
5. The duplicate rules detect duplicates and block creation. The existing
   record shows with an "Open business" action.
6. All 11 states render and work on a phone-width screen.
7. After enrichment, the business appears in the Businesses list. No
   notification or email is sent.

## Sub-tasks

- ADD-2 — BE: business search endpoint
- ADD-3 — BE: duplicate detection and pending creation
- ADD-4 — BE: enrichment trigger and publish to the list
- ADD-5 — FE: add-business modal (2-step wizard, all states)
- ADD-6 — FE: integration with the APIs
- ADD-7 — QA: edge cases
