# Acme Leads

Internal tool for the sales team. It keeps a list of businesses (leads).

## Stack

- PHP 8.2+ with the `pdo_sqlite` extension. No framework, no Composer.
- Vanilla JavaScript and CSS in `public/assets/`. No build step, no npm in
  the app.
- SQLite through PDO.

## Commands

Run all commands from the repository root.

| Task | Command |
| --- | --- |
| Reset the database (schema + seed rows) | `php bin/migrate` |
| Start the dev server on http://127.0.0.1:8000 | `bin/serve` |
| Run open enrichment requests (cron in production) | `php bin/enrich` |
| Run the tests | `php tests/run.php` |
| Run some tests | `php tests/run.php <part of the test name>` |
| Lint the PHP files | `find bin public src templates tests -name '*.php' -exec php -l {} \;` |

`bin/serve` reads `PORT` and `HOST`. Run `php bin/migrate` once before the
first `bin/serve`.

## Environment

| Variable | Default | Meaning |
| --- | --- | --- |
| `ACME_DB` | `var/app.sqlite` | SQLite file |
| `ACME_PLACES` | `fixture` | `fixture` or `http` (the real places API) |
| `ACME_PLACES_FIXTURE` | `fixtures/places.json` | Places for the fixture client |
| `ACME_PLACES_FAIL` | unset | `1` makes the fixture client throw `PlacesUnavailable` |
| `ACME_PLACES_URL`, `ACME_PLACES_KEY` | unset | The real places API (`http` only) |

## Layout

- `public/index.php` — front controller and the route table.
- `src/` — namespace `Acme\`. `Acme\Foo\Bar` lives in `src/Foo/Bar.php`
  (autoloader in `src/bootstrap.php`).
- `src/App.php` — builds services from the environment.
- `src/Controller/` — one class per area. HTML pages render
  `templates/<name>.php` through `Http::render()`.
- `src/DuplicateChecker.php` — the duplicate rules for adding a business.
- `src/Places/` — the places API client. `PlacesClient` is the interface.
  `FixturePlacesClient` is the default. `CurlPlacesClient` is the real API.
- `database/schema.sql` — the whole schema. `bin/migrate` drops and recreates
  every table, then loads `database/seed.sql`. Add tables and columns here.
- `tests/` — `*Test.php` files. Each returns an array of
  `'name' => callable`. Use the helpers in `tests/helpers.php`.

## Conventions

- `declare(strict_types=1);` in every PHP file.
- API responses are JSON. Errors are `{"error": "<snake_case_code>"}` with the
  right HTTP status. Use `Http::json()` and `Http::error()`.
- Escape all output in templates with `Http::e()`.
- Use prepared statements for every query with input.
- Front end: put shared helpers (`api()`, `el()`) and features in
  `public/assets/app.js`. Use the CSS tokens in `public/assets/app.css`.
- Mail goes only through `Acme\Mailer`, which writes to the `outbox` table.
- `fixtures/places.json` and the rows in `database/seed.sql` are fixed test
  data. Do not change them. Tests that need other data build it themselves.
- Add a test for each behavior change. Run `php tests/run.php` before you
  commit.
