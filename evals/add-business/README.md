# Add-business pipeline eval

This eval runs the whole harness on one realistic full-stack ticket. The
pipeline is `/spec` → `/plan` → `/build` → `/test` → `/review`. It runs in a
fresh sandbox project. Hidden tests then score the result. The agent under
test never sees them.

The ticket is `ADD-1` for a small fictional app, "Acme Leads". A user adds a
business from a places search in a two-step modal. The backend checks for
duplicates, creates the business as pending, and enrichment makes it
available. Read [ticket.md](ticket.md) for the full ticket.

## Contents

| Path | What it is |
| --- | --- |
| `ticket.md` | The ticket, the API contract and the exact UI copy. The grader relies on this file only. |
| `seed/` | The starting app: plain PHP, vanilla JS, SQLite. The agent builds on it. |
| `setup.sh DEST` | Copies `seed/` to DEST, writes the intake, makes the first commit. |
| `hidden/` | The grader's checks: PHP API checks and Playwright UI checks. Never copied to DEST. |
| `grade.sh DEST` | Runs `hidden/` against DEST and prints one JSON object. |
| `reference/` | A reference solution. It proves the grader can pass. |

## One-time setup

You need:

- PHP 8.2 or later with the `pdo_sqlite` extension (`php -m` lists `pdo_sqlite`).
- Node.js 20 or later, with npm.
- Git.
- Chromium for Playwright:

```bash
cd evals/add-business/hidden
npm ci
npx playwright install chromium
```

## Run it

1. Create the sandbox outside this repository:

   ```bash
   evals/add-business/setup.sh /tmp/add-business-run
   ```

2. Run the pipeline in the sandbox. Start a session there and give the
   commands one by one. Approve the spec and the plan as you would for real
   work.

   ```bash
   cd /tmp/add-business-run
   claude
   /spec ADD-1
   ```

   Then `/plan ADD-1`, `/build ADD-1`, `/test ADD-1` and `/review ADD-1`.

3. Score the result:

   ```bash
   evals/add-business/grade.sh /tmp/add-business-run > result.json
   ```

`grade.sh` exits 0 only when every check passes. It exits 1 when a check
fails, and 2 when it cannot run. Set `GRADE_KEEP=1` to keep the logs. Each
check has an id, a criterion (`AC1` to `AC7`, `IR` for the interaction rules,
`BASE` for the baseline), `pass` and a short `detail`.

## Self-test

The grader must pass the reference and fail the untouched seed. CI runs this
in the "Add-business eval grader" step. To run it by hand:

```bash
evals/add-business/grade.sh evals/add-business/reference   # 37/37, exit 0
evals/add-business/grade.sh evals/add-business/seed        # baseline 2/2, feature 0/35, exit 1
```

Each run takes about 10 to 25 seconds after the one-time setup.

## What it covers

- Every acceptance criterion in the ticket, with at least one API or UI check.
- Each duplicate rule (place ID, CID, root domain, name and ZIP, phone), and
  null values that must never match.
- The 2-character minimum, multi-token search, selection clearing, and
  Continue disabled until a selection.
- Search error with Retry, and a submit failure that keeps the notes. The UI
  checks simulate both by intercepting the API calls.
- Close, Cancel and Done reset the wizard. The modal fits a 375 px screen.
- Enrichment (`php bin/enrich`) moves the business from pending to the list.
  No email goes to the outbox.

## What it does not cover

- Recon on a large codebase. The seed is small on purpose.
- Visual design: colors, the blurred backdrop, the purple connector, spacing.
- The 30-second target and the real places API. The fixture client is used.
- How good the spec, the plan or the review is. Only the shipped behavior is
  scored.

## Cost

Unmeasured. One run is a full pipeline on a medium ticket.
