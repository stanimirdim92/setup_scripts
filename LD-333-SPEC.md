# Spec: LD-333 — Localize date/datetime format based on customer locale

**Ticket:** https://smartico1.atlassian.net/browse/LD-333 (Leadbuster Scrum, Medium priority)
**Not committed to a repository** — this session has no Leadbuster repo attached, only
`stanimirdim92/setup_scripts`. Move this file into the Leadbuster repo (e.g. `docs/specs/`)
and commit it there once you're working in that checkout.

## Objective

All dates and datetimes in Leadbuster currently render in the German dotted format
(`DD.MM.YYYY`) for every customer, regardless of where they are. This was flagged by the
Seattle Times account, whose dates in the Google Ads section display as European format
instead of the US convention.

Fix: presentation format for dates and datetimes should follow the customer's own locale
(`users.language`), reusing the locale already resolved by the existing `Localization`
middleware — no new per-field logic scattered across the app, no new DB column, and the
underlying stored date/time values never change, only how they're rendered.

Scope was widened twice during brainstorming, both confirmed by you:
- Fix applies **globally** (every Carbon field the API serializes), not just the 5 fields
  named in the ticket's stated scope (Active Since, Last Shown Ad, Last New Ad, Published,
  Last Shown) — because the mechanism (`Carbon::serializeUsing()`) is inherently global, and
  you confirmed that's the intended fix rather than a narrower per-Resource change.
- Covers **datetime** fields (date + time), not just date-only fields — you have fields
  today using `->toDateTimeString()` (or equivalent), which is an explicit format call and
  does **not** go through `Carbon::serializeUsing()`. Those call sites need to be found and
  converted too, or they'll keep rendering in the old fixed format after this ships.

## Key decisions (confirmed during brainstorming — do not re-litigate)

| Locale (`users.language`) | Date format | Datetime format | Rationale |
|---|---|---|---|
| `us` | `MM/DD/YYYY` | `MM/DD/YYYY hh:mm AM/PM` | US native convention |
| `ca` | `MM/DD/YYYY` | `MM/DD/YYYY hh:mm AM/PM` | Canada's own native format, same bucket as US |
| `gb` | `DD/MM/YYYY` | `DD/MM/YYYY HH:mm` (24h) | UK's own native format — distinct from `de` (slashes, no dots) |
| `en` (fallback — pre-login / no preference set) | `DD/MM/YYYY` | `DD/MM/YYYY HH:mm` (24h) | Treated as generic international/UK-style, not US |
| `de` | `DD.MM.YYYY` | `DD.MM.YYYY HH:mm` (24h) | Matches ticket AC exactly |
| anything unmapped | `DD.MM.YYYY` | `DD.MM.YYYY HH:mm` (24h) | "The rest of the clients are from Germany" — per Petya Zhelyazkova's ticket comment |

No new country/region column — `users.language` already stores ISO-style values (`us`,
`ca`, `gb`, `de`, ...) per your confirmation, not just language codes like `en`/`de`. Use it
as-is.

## Tech Stack

- Laravel 13, PHP, modular structure (`Modules/<Name>/...`, e.g. `Modules\Core`) — nwidart/laravel-modules-style, inferred from the existing `Modules\Core\Http\Middleware\Localization` namespace
- Carbon (`nesbot/carbon`, via `Illuminate\Support\Carbon`) for all date/time handling
- MySQL for storage
- nginx + PHP-FPM — classic request-per-process, **not** Octane/Swoole, confirmed by you. This matters: `Carbon::serializeUsing()` is static global state, and it's safe here because every request gets a fresh PHP process — no cross-request leakage to guard against.
- Frontend is a JS SPA (Vue or React — not confirmed which) consuming a JSON API. The API sends pre-formatted date strings today; the frontend just displays them as-is. **No frontend changes are in scope** — confirm this holds once the actual Resource/serialization code is visible; if any date field is instead sent raw (ISO/timestamp) and formatted client-side, that field needs a JS-side fix too and is currently unaccounted for here.

## Commands

Not confirmed — no repo attached this session. Best-effort assumption based on this being a Laravel 13 app and your own global Claude Code tooling conventions (which always-ask before running Pint/PHPStan/Deptrac on PHP projects):

```
Test:  vendor/bin/pest            (Laravel 13 defaults to Pest — confirm PHPUnit isn't used instead)
Style: vendor/bin/pint            (confirm Pint is actually configured in this repo)
Static analysis: vendor/bin/phpstan analyse   (confirm PHPStan is configured)
```

**Confirm these before the implementation phase** — do not assume they're correct.

## Project Structure

```
Modules/Core/Http/Middleware/Localization.php   → existing locale-resolution middleware (edit here)
Modules/Core/Support/DateLocaleFormat.php       → new: locale → format-pattern map (exact path/namespace TBD — confirm this module's convention for "support"/"helper" classes)
Modules/Core/Tests/...                          → unit test for DateLocaleFormat (exact test directory convention TBD)
```

Exact locations for the new class and its test are unconfirmed — nwidart/laravel-modules
apps vary on whether tests live under `Modules/<Name>/Tests/` or a root-level `tests/`
directory. Confirm against this repo's existing test layout before creating new files.

## Code Style

Match the existing middleware's style exactly — `declare(strict_types=1)`, grouped `use`
imports, PHPDoc on public methods:

```php
<?php

declare(strict_types=1);

namespace Modules\Core\Support;

final class DateLocaleFormat
{
    private const DATE_PATTERNS = [
        'us' => 'm/d/Y',
        'ca' => 'm/d/Y',
        'gb' => 'd/m/Y',
        'en' => 'd/m/Y',
        'de' => 'd.m.Y',
    ];

    private const DATETIME_PATTERNS = [
        'us' => 'm/d/Y h:i A',
        'ca' => 'm/d/Y h:i A',
        'gb' => 'd/m/Y H:i',
        'en' => 'd/m/Y H:i',
        'de' => 'd.m.Y H:i',
    ];

    public static function datePattern(?string $locale): string
    {
        return self::DATE_PATTERNS[$locale] ?? self::DATE_PATTERNS['de'];
    }

    public static function datetimePattern(?string $locale): string
    {
        return self::DATETIME_PATTERNS[$locale] ?? self::DATETIME_PATTERNS['de'];
    }
}
```

And the middleware change, in `setupLocale()` right after `$locale` is resolved:

```php
session()->put('locale', $locale);
App::setLocale($locale);
Date::setLocale($locale);
Carbon::setLocale($locale);
CarbonPeriod::setLocale($locale);
CarbonInterval::setLocale($locale);
CarbonImmutable::setLocale($locale);

Carbon::serializeUsing(
    fn (Carbon $date) => $date->format(DateLocaleFormat::datetimePattern($locale))
);
```

Note this uses one pattern (`datetimePattern`) for *all* Carbon serialization by default,
since `Carbon::serializeUsing()` can't tell whether a given field is conceptually
"date-only" or "datetime" — it only sees a Carbon instance. Date-only fields need an
explicit `->format(DateLocaleFormat::datePattern($locale))` call wherever they're built,
since they can't be distinguished from datetime fields by the global hook alone. **This is
the main open risk in this spec — see Open Questions.**

## Testing Strategy

Framework: assumed Pest (see Commands — unconfirmed).

- **Unit tests** on `DateLocaleFormat`: one case per mapped locale (`us`, `ca`, `gb`, `en`,
  `de`) plus one for an unmapped/unknown value, for both `datePattern()` and
  `datetimePattern()`.
- **Feature tests**: hit the Ads Overview endpoint as a `us`-locale user and as a
  `de`-locale user, assert the returned JSON strings match the expected format for each of
  the 5 named fields.
- **Regression check** (manual, pre-merge): grep the codebase for `toDateTimeString(`,
  `toDateString(`, and any hardcoded `->format('d.m.Y')`/`->format('Y-m-d...')`-style calls
  on the fields in scope — each one bypasses `Carbon::serializeUsing()` and needs to be
  converted to call `DateLocaleFormat` explicitly instead. You mentioned you already have
  such fields ("I have such dates") — enumerate them once repo access exists, since this
  spec was written without seeing the actual codebase.

## Boundaries

- **Always:** derive the format from `users.language` via `DateLocaleFormat`; keep the
  existing `Carbon::setLocale()` (translation locale) call untouched — this change is
  presentation-format only, not a translation change; default unmapped locale values to the
  German pattern (`de`), matching "the rest of the clients are from Germany."
- **Ask first:** before converting any explicit `->toDateTimeString()`/`->format()` call
  site you find during implementation that touches a field *not* named in this spec or the
  ticket — confirm it's actually meant to be locale-aware before changing it, since the
  full inventory of such call sites is unknown until the repo is explored.
- **Never:** add a new DB column/migration for country or region (explicitly rejected —
  reuse `users.language` as-is); change the underlying stored date/time values; touch
  frontend/JS code unless the "no frontend changes needed" assumption above turns out to be
  wrong for a specific field.

## Success Criteria

- `us`/`ca` accounts see date fields as `MM/DD/YYYY` and datetime fields as
  `MM/DD/YYYY hh:mm AM/PM`.
- `gb`/`en`(fallback) accounts see date fields as `DD/MM/YYYY` and datetime fields as
  `DD/MM/YYYY HH:mm` (24h).
- `de` and unmapped accounts see date fields as `DD.MM.YYYY` and datetime fields as
  `DD.MM.YYYY HH:mm` (24h) — matches the ticket's literal acceptance criteria.
- Format is consistent across Ads Overview, list view, and Ad Detail View (ticket AC).
- Every other Carbon field serialized by the API (not just the 5 named Ads fields) follows
  the same locale map, via the single global `Carbon::serializeUsing()` hook.
- All known explicit `->toDateTimeString()`/hardcoded-format call sites are converted to go
  through `DateLocaleFormat` — no field silently left on the old fixed format.
- Underlying stored date/time values are provably unchanged (DB rows, non-presentational
  internal use) — only rendered strings differ.

## Open Questions

1. **Date-only vs datetime distinction**: `Carbon::serializeUsing()` sees only a Carbon
   instance, not whether the field is conceptually date-only or datetime. The code sketch
   above defaults every raw-serialized Carbon field to the *datetime* pattern. Are any of
   the 5 named Ads fields (Active Since, Last Shown Ad, Last New Ad, Published, Last Shown)
   date-only today (no time component shown), and if so, do they need an explicit
   `->format(DateLocaleFormat::datePattern(...))` call instead of relying on the global
   hook? Needs the actual Resource/serialization code to answer.
2. **Test framework/commands** — Pest vs PHPUnit, exact commands. Confirm once repo is
   attached.
3. **Module conventions** — correct namespace/path for a new "support" class and its test,
   matching this app's existing patterns (not just `Modules/Core`, guessed).
4. **Full inventory of explicit format call sites** — you mentioned datetime fields using
   `toDateTimeString()` exist; list them (or grant repo access so I can grep) before
   implementation starts, since each one is a separate edit this spec can't enumerate yet.
5. **External consumers** — does anything outside Leadbuster's own frontend (exports,
   webhooks, third-party integrations) parse these API date fields expecting a fixed
   (e.g. ISO) format? The global `serializeUsing` hook would change their output too. Not
   mentioned in the ticket, but worth a quick check given the blast radius is app-wide.
6. **Existing `Carbon::serializeUsing()` call**, if any — is one already defined elsewhere
   (a service provider, likely) producing today's hardcoded `d.m.Y` output? If so, this
   change should replace/remove that one rather than leave two competing definitions.
