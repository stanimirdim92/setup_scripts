# Mock answer — Loyalty Points Service

```xml
<goal>
Build a Loyalty Points HTTP service for an online shop. The shop must award, redeem, expire,
and claw back points correctly, and it must never lose or duplicate points.
Success means every acceptance criterion below passes with an executed check.
A hidden test suite will call the HTTP API, so the API contract below is exact.

You run in a loop. Each iteration starts with no memory. The repository is your only memory.
Each iteration does ONE task, verifies it, records it, commits, and exits.
</goal>

<context>
- The shop sends purchase and refund webhooks. Payload: event_id (UUID), customer_id, order_id,
  amount_cents (int, after discounts), currency, occurred_at (ISO 8601 UTC).
- A refund has the same order_id as its purchase, and refunds are always full.
- The sender retries up to 5 times on a non-2xx response or after a 2 s timeout.
  So the same event can arrive more than once, and events can arrive out of order.
- Checkout redeems points and sends its own redemption_id. It can also retry.
- An API gateway authenticates shop and checkout calls. Admin calls are NOT behind the gateway.
- EUR only.
</context>

<requirements>
R1 Earn. A purchase awards floor(amount_cents / 100) points to the customer.
   Why: 1 point per full euro spent.
R2 Idempotent events. An event_id that was already processed changes nothing and returns
   the original result with 200.
   Why: the sender retries, and a duplicate must not award points twice.
R3 Refund clawback. A refund removes the points that its order earned.
   The balance never goes below 0. Any shortfall becomes "clawback debt".
   Future earnings repay the debt before they add to the balance.
   A refund that arrives before its purchase is stored. When the purchase arrives,
   it is applied immediately and nets to 0.
   Why: the customer must not keep points from refunded orders, and finance requires
   a non-negative balance.
R4 Redeem. Checkout can redeem N points, where N is a positive multiple of 100.
   Redemption takes points from the oldest unexpired lots first (FIFO).
   Too few points → 409, and nothing changes. A repeated redemption_id returns the
   original result.
   Concurrent redemptions never spend more than the balance.
   Why: 100 points = 1 EUR, and a double spend loses money.
R5 Expiry. Each earned lot expires 365 days after its occurred_at. Expired points are not
   available, and the history records them as expired.
   Why: points expire after 12 months.
R6 Admin adjustment. An admin can add or remove points. Each adjustment requires an
   X-Admin-Key header, which must match env ADMIN_API_KEY, plus a non-empty `reason`
   and `admin_id`. Every adjustment is stored with who, why, and when.
   A removal follows the same no-negative rule as R4 (409).
   Added points expire like earned points.
   Why: only admins may adjust, and an audit trail is required.
R7 Balance view. Show available points, clawback debt, and the points that expire in the
   next 30 days.
R8 History. List every points movement for a customer, newest first.
   Each entry has: earn, redeem, refund, expire, or adjust.

API contract (JSON; errors are {"error": {"code", "message"}}):
- POST /events/purchase         → 200 {"points_awarded"}
- POST /events/refund           → 200 {"points_removed", "debt_added"}
- POST /customers/{id}/redemptions  {redemption_id, points} → 200 {"points_redeemed", "balance"} | 409 | 422
- POST /admin/customers/{id}/adjustments {points, reason, admin_id} → 200 | 401 | 409 | 422
- GET  /customers/{id}/balance  → {"available", "debt", "expiring_30d"}
- GET  /customers/{id}/history  → [{"type", "points", "occurred_at", "ref"}]
- Validation: non-EUR currency, negative amount, or a malformed payload → 422.

Thresholds:
- Webhook response time: p95 under 300 ms for 1,000 sequential requests against a
  database with 10,000 customers.
  Why: the sender treats a response over 2 s as a failure and retries.
- Correctness under concurrency: R4 holds with 20 parallel requests.

Operational concerns:
- Required: input validation, structured JSON errors, an audit trail for admin
  adjustments, idempotency for every write.
- Out of scope: auth for shop and checkout (the gateway handles it), metrics,
  PostgreSQL, data migration tooling.

Out of scope: tiers and multipliers, notifications, any UI, multi-currency.
Build nothing outside R1..R8. If something seems missing, record it in DECISIONS.md.
Do not build it.
</requirements>

<constraints>
- Python 3.12, FastAPI, SQLAlchemy, SQLite, pytest, ruff.
  Why: this is the team stack, and the hidden suite expects it.
- Install every dependency in the first iteration and pin it in requirements.txt.
  The network is off after that.
- Points are integers. Never use floats.
  Why: rounding errors lose points.
- Time comes from an injectable clock. Tests never sleep and never use the real clock.
  Why: expiry tests must be deterministic.
- Every balance-changing write runs in one database transaction.
  Use BEGIN IMMEDIATE on SQLite.
  Why: R4 concurrency.
- Store points as an append-only ledger of lots and movements. Compute the balance from
  the ledger. Do not keep a mutable counter that can drift.
- Provide `make install`, `make test`, `make lint`, and `make run`.
- Keep it simple: write the minimum code for R1..R8, with no speculative layers or config.
</constraints>

<state>
PLAN.md      — tasks: id, R-ids, dependencies, check command, Status (Pending|Done|Blocked), attempts.
PROGRESS.md  — append-only log for each iteration: task, change, commands and results, next step.
DECISIONS.md — every assumption and choice, with its reason and the affected R-ids.
Git history  — one commit per finished task. Committed state is the truth.
</state>

<each_iteration>
1. Orient: read PLAN.md, PROGRESS.md, and DECISIONS.md. Run `git log --oneline -10` and
   `git status`. If uncommitted work exists from an interrupted iteration, verify it and
   commit it, or revert it.
2. No PLAN.md yet? Then this iteration does the setup:
   - Install and pin the dependencies.
   - Create a skeleton with a passing `make test`.
   - Split R1..R8 into small vertical tasks, in dependency order. Every task names its
     R-ids, and every R-id has a task.
   - Record the assumptions in DECISIONS.md.
   - Commit, then exit.
3. Run `make test`. If a Done task now fails, fixing it is this iteration's task.
4. Otherwise, take the first Pending task whose dependencies are Done.
5. Write the test first and confirm that it fails for the right reason.
   Then write the smallest change that passes it.
   Touch only what the task needs.
6. Run the task check, `make test`, and `make lint`. Only command output counts as evidence.
7. If everything passes, set the task to Done. Log the commands and results.
   Commit as "<task-id> (R-ids): <what>".
   If something fails, change the code based on the error. Never re-run an unchanged command.
   After 3 failed attempts, set the task to Blocked. Record the error, your hypothesis, and
   what you tried. Commit, then exit.
8. Exit. Do not start a second task.
</each_iteration>

<ambiguity>
Already decided:
- A1: the R3 clawback-debt rule and the out-of-order refund rule.
- A2: points come from amount_cents after discounts.
- A3: an admin removal can't push the balance below 0.

For anything else: choose the simplest option that keeps R1..R8 true, record it in
DECISIONS.md, and continue.
Never weaken a requirement to make a test pass. A real conflict between requirements is a
Blocked task.
</ambiguity>

<acceptance_criteria>
AC1 (R1): A purchase of 1999 cents awards 19 points.
AC2 (R2): The same purchase event sent 3 times → 19 points total. Every response is 200
          with the same body.
AC3 (R3): Earn 50, redeem 0, refund that order → balance 0, no debt.
          Earn 200, redeem 100, refund → balance 0, debt 100.
          The next purchase of 150 points → debt 0, balance 50.
AC4 (R3): A refund that arrives before its purchase, then the purchase → balance unchanged,
          and both appear in the history.
AC5 (R4): Balance 100. Twenty parallel redemptions of 100 → exactly 1 succeeds,
          19 get 409, and the balance is 0.
AC6 (R4): Redemption of 150 → 422. A repeated redemption_id → the original result, and
          no second deduction.
AC7 (R4, R5): Lots of 100 (day 0) and 100 (day 200). On day 300, redeem 100 →
          the day-0 lot is used.
AC8 (R5): A lot earned on day 0 is available on day 364 and expired on day 365.
          The history shows an expire entry.
AC9 (R6): An adjustment without the key, or with a wrong key → 401, and nothing changes.
          Without a reason → 422. A valid adjustment appears in the history with
          admin_id and reason.
AC10 (R7): Balance shows the points that expire within 30 days.
AC11 (all): `make test` covers AC1–AC10 as HTTP-level tests through the FastAPI test client.
AC12 (threshold): `make perf` reports the webhook p95 under 300 ms for the stated workload.
</acceptance_criteria>

<definition_of_done>
Check this in every iteration:
- `make test` and `make lint` pass.
- Every R-id has a passing test. Every test names its R-id.
- The code has no floats in points math, no dead code, no debug output, and no features
  outside R1..R8.
- The README states install, run, test, and the API contract.
</definition_of_done>

<completion>
When no Pending tasks remain:
1. Clean run: delete the database, then run `make install` (offline from the pinned cache),
   `make test`, `make lint`, and `make perf`.
2. Review the full diff against R1..R8 and the API contract. Look for missing behavior,
   scope creep, and untested paths. Each finding becomes a Pending task. Exit without
   the signal.
3. When everything passes, write REPORT.md:
   - For each R-id: status, test names, and the commands with their results.
   - The assumptions from DECISIONS.md.
   - The Blocked tasks.
   - Known limits, for example the use of SQLite instead of PostgreSQL.
4. Print <promise>COMPLETE</promise>.

If only Blocked tasks remain, write the same report with the blockers first, then print the
signal. Never print it while any work is unverified.
</completion>
```

## Planted traps and where the prompt handles them

| Trap in the packet | What a weak prompt does | Where the answer handles it |
|---|---|---|
| Retries and the `event_id` field | Gives points twice | R2, AC2 |
| Checkout retries | Spends the same points twice | R4 `redemption_id`, AC6 |
| Events arrive out of order | A refund before its purchase is lost | R3, AC4 |
| "Must not keep points" conflicts with "never negative" | The agent picks one rule at random | R3 clawback debt, A1 |
| "Expire after 12 months" | Unclear which points expire first | Lots, FIFO, the 365-day boundary, AC7 and AC8 |
| Two redemptions at the same time | Spends more than the balance | Transaction constraint, AC5 |
| "Fast and reliable" | No number to test against | p95 300 ms, based on the 2 s retry timeout |
| Only admins may adjust, and admin calls skip the gateway | Leaves the admin endpoint open | R6, 401, AC9 |
| "Tiers later" | The agent builds tiers | Out-of-scope list |
| Fresh context each iteration, network off | The agent loses progress or tries to install packages mid-run | State files, install pinned in the first iteration |
| A hidden HTTP test suite | Endpoints get invented names | Exact API contract |

Say these in the interview:

- For A1 (clawback debt), say you would confirm it with the product owner. Then name the debt rule you would use if you cannot ask.
- Say the 2-second webhook timeout is where the 300 ms threshold comes from.
