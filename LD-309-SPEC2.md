# Spec2: LD-309 — Company ID search must match middle/end substrings, not just prefix

**Ticket:** https://smartico1.atlassian.net/browse/LD-309 (Leadbuster Scrum, Medium priority,
Bug). Relates to LD-210 (same underlying requirement, earlier ticket).
**Named SPEC2.md, not SPEC.md** — per your instruction, SPEC.md (LD-333) is still in
progress; this is a separate ticket, separate file.
**Not committed to a repository** — this session has no Leadbuster repo attached, only
`stanimirdim92/setup_scripts`. Move this file into the Leadbuster repo before implementation.

## Objective

Company search by Company ID (`external_id`, aka `crm_id`) only returns a match when the
search term is the **beginning** of the ID. Searching by digits from the middle or end
returns nothing.

Root cause (per Nikolay Dimitrov's ticket comment, confirmed by the `whereSearch()` code
you provided): `name_search` is a generated column combining company name + `external_id`,
searched via MySQL `FULLTEXT` in boolean mode. The default fulltext parser tokenizes on
word boundaries and only supports **prefix** matching within a token (`word*`) — so
`external_id` "12345" matches searches for "123" but never "234" or "345".

Fix (Approach A, approved): add a **separate, dedicated `FULLTEXT` index on `external_id`
using the `ngram` parser**, which tokenizes into fixed-length character n-grams instead of
whole words — this is what makes arbitrary substring matches possible. This index is
independent of `name_search`; the existing name-search `whereFullText` call is not touched
in any way, so name search behavior is provably unchanged (not just unchanged by
convention).

## Assumptions

1. "Company" in the ticket == the `Advertiser` model / `advertisers` table — inferred from
   `whereSearch()`'s website subquery joining `advertisers_websites.advertiser_id`. Not
   explicitly confirmed; flagged in Open Questions.
2. The existing `ctype_digit($search)` branch (`orWhere($query->getModel()->getQualifiedKeyName(), (int) $search)`)
   matches the model's **database primary key**, which is likely a *different* thing from
   `external_id`/Company ID — this looks like a separate, probably legacy code path
   (exact-match search by literal internal DB id), not the mechanism the ticket is about.
   Recommendation: leave it as-is, add the new substring match alongside it. Confirm once
   repo access exists — if PK and `external_id` happen to be the same value in this schema,
   this assumption is wrong and the design needs revisiting.
3. `external_id` is a plain (non-generated) column already present on the model's table.

## Explicitly out of scope

- **Website search performance.** You noted the existing `LIKE '%normalizedWebsite%'`
  subquery in `whereSearch()` is already the slowest part of this query today. That's a
  real, separate problem — but it's not in LD-309's AC ("existing search... by company
  name and other supported identifiers remains unaffected" — website search isn't asked to
  *change*, only not regress). Recommend filing it as its own ticket rather than folding a
  fix into this one.
- **Extending substring matching to company name search.** The ticket's AC explicitly
  requires name search to stay unaffected; Approach A achieves that structurally (separate
  index, separate column) rather than by convention, so there's no technical reason to
  touch name search here even though the same "root cause" (word-prefix-only fulltext)
  technically affects it too. That would be a different, larger ticket.

## Tech Stack

- Laravel 13, PHP, same `Modules/<Name>/...` structure as `LD-333-SPEC.md`'s app.
- MySQL, `FULLTEXT` indexes — currently boolean-mode default parser (`name_search`); this
  change adds a second `FULLTEXT` index on `external_id` using the **ngram parser**
  (`WITH PARSER ngram`, available since MySQL 5.7.6 — assumed available given `name_search`
  already uses `FULLTEXT`, but not explicitly version-confirmed).
- Query builder: `whereSearch()` on what's assumed to be an `Advertiser`-scoped
  `BaseBuilder`/`QueryBuilder` (custom builder classes, not vanilla Eloquent builder).

## Commands

Not confirmed — no repo attached this session, same caveat as `LD-333-SPEC.md`:

```
Test:  vendor/bin/pest       (assumed — confirm)
Style: vendor/bin/pint       (assumed — confirm)
```

## Project Structure

```
<wherever whereSearch() lives>   → the query builder class you pasted (exact path unknown — you gave the method body, not the file path)
database/migrations/..._add_external_id_ngram_fulltext_index.php   → new migration (path/convention TBD)
```

## Code Style

New branch inside the existing `whereSearch()`, added alongside (not replacing) the
current numeric PK-equality check:

```php
if (ctype_digit($search)) {
    $query->orWhere($query->getModel()->getQualifiedKeyName(), (int) $search);

    $query->orWhereFullText(
        ['external_id'],
        $search,
        ['mode' => 'boolean']
    );
}
```

Migration (illustrative — exact syntax/convention depends on how `name_search`'s own
`FULLTEXT` index was created in this codebase; match that pattern):

```php
DB::statement('ALTER TABLE advertisers ADD FULLTEXT INDEX external_id_ngram_fulltext (external_id) WITH PARSER ngram');
```

**Note:** `ngram_token_size` is a MySQL **server-wide** variable (default 2), shared by
every ngram-parsed fulltext index on the instance. If any other ngram index already exists
elsewhere with a different token size, this change either has to accept that existing
size or the two indexes conflict. Confirm before writing the migration — see Open
Questions. A `ngram_token_size` of 2 (the default) means a **single-digit search term
would not match anything** — worth confirming this is an acceptable limitation (AC talks
about "digits," plural, and the reproduction steps use multi-digit examples, so likely
fine, but not explicitly stated).

## Testing Strategy

Framework: assumed Pest (unconfirmed).

- **Unit/feature tests** on `whereSearch()`:
  - Search by the first digits of a known `external_id` → match (already works today, must
    still work)
  - Search by digits from the **middle** of a known `external_id` → match (new)
  - Search by the **last** digits of a known `external_id` → match (new)
  - Search by company name (unrelated to `external_id`) → unchanged result set, proving
    `name_search`/`whereFullText` behavior wasn't touched
  - Search by a literal DB primary key value that is *not* a substring of any
    `external_id` → still matches via the untouched PK-equality branch (proves that
    legacy path wasn't broken)
- **Migration test/smoke check:** confirm the new `FULLTEXT ... WITH PARSER ngram` index
  is created successfully against production-shaped data (a Company ID column at real
  scale) and doesn't fail due to a conflicting `ngram_token_size` elsewhere on the instance.

## Boundaries

- **Always:** keep the existing `whereFullText(['name_search'], ...)` call byte-for-byte
  unchanged; scope the new ngram index to `external_id` only; keep the existing
  PK-equality `ctype_digit` branch intact rather than replacing it.
- **Ask first:** before changing the server's `ngram_token_size` variable if it's already
  set for another index elsewhere; before touching the `ctype_digit` PK-equality branch in
  any way beyond adding the new substring check alongside it; before doing anything about
  the website-search performance issue you flagged (separate ticket territory).
- **Never:** extend substring/ngram matching to company name search (out of this ticket's
  AC); change what `external_id` values mean or how they're generated/assigned; silently
  widen scope to "fix search generally."

## Success Criteria

- Searching by the first digits of a Company ID returns the matching company (ticket AC,
  already true today — must remain true).
- Searching by digits from the **middle** of a Company ID returns the matching company
  (new — ticket AC).
- Searching by the **last** digits of a Company ID returns the matching company (new —
  ticket AC).
- Existing search by company name is provably unaffected — same query, same index, same
  results as before this change.
- The existing PK-equality `ctype_digit` branch still works for whatever it was doing
  before (pending Open Question #2 on whether that's actually meaningful/distinct from
  Company ID search).
- Ticket is linked to LD-210 (process step, not a code change — flagging so it isn't
  dropped).

## Open Questions

1. **Model/table identity** — is "Company" really `Advertiser`/`advertisers`, and is
   `external_id` the literal column name (vs. `crm_id` or something else)? Confirm once
   repo access exists.
2. **PK vs. Company ID** — does the existing `ctype_digit` branch's primary-key match
   serve any real purpose distinct from Company ID search, or is it dead/legacy code that
   happens to coexist? Affects whether it should stay, per the Assumptions section above.
3. **`ngram_token_size` server variable** — current value, and whether any other ngram
   fulltext index already exists on this MySQL instance with a different size. A conflict
   here could block or reshape this whole approach.
4. **Migration convention and downtime risk** — how are fulltext-index migrations
   typically written/deployed in this repo, and does adding one to a large `advertisers`
   table risk a lock/rebuild that needs off-hours deployment or DBA coordination?
5. **Single-digit search term edge case** — with the default `ngram_token_size` of 2, a
   1-digit search won't match via the new index. Confirm this is acceptable (falls back
   to the untouched PK-equality branch, which does support single digits via exact numeric
   match, just not substring match).
6. **Website-search performance** (flagged by you, out of scope here) — worth its own
   ticket if you want it addressed; not folded into this spec.
