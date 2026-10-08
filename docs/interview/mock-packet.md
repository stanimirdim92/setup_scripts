# Mock packet — Loyalty Points Service

## 1. Business requirements (from the product owner)

> We want a loyalty program for our online shop. Customers earn 1 point per euro
> they spend. They can use points at checkout: 100 points = 1 EUR discount.
> Points expire after 12 months.
>
> When an order is refunded, the customer must not keep the points from that order.
> Finance insists that a customer balance is never negative.
>
> Customer support needs to add or remove points manually, for example as a goodwill
> gesture. Only admins may do this, and we need to know who did it and why.
>
> Customers should see their balance and how many points expire soon.
>
> The API must be fast and reliable. We cannot lose points or give points twice.
>
> Marketing would love tiers later (Silver, Gold), with bonus multipliers.

## 2. Context

- The shop is an existing system. It sends a webhook for each purchase and each refund.
- Webhook payload: `event_id` (UUID, unique per event), `customer_id`, `order_id`,
  `amount_cents` (integer, after discounts), `currency`, `occurred_at` (ISO 8601 UTC).
  A refund carries the same `order_id` as the purchase. Refunds are always full refunds.
- The webhook sender retries up to 5 times on a non-2xx response or after a 2-second timeout.
  It can deliver events out of order.
- The shop sells in EUR only.
- Checkout calls the service to redeem points. It sends its own `redemption_id`.
- An API gateway authenticates the internal services (shop, checkout). Admin tools call
  this service directly.
- Team stack: Python 3.12, FastAPI, SQLAlchemy, pytest, ruff. Production uses PostgreSQL;
  this exercise uses SQLite.
- The repository is empty except for a README stub.

## 3. Agent spec (the harness)

- Agent: "Builder". One agent, autonomous. No human is available during the run.
- Loop: the harness sends the same prompt in every iteration. **Each iteration starts with a
  fresh context.** The only thing that persists is the repository on disk.
- Tools: shell, file read/write, git. Package install is allowed in the first iteration only.
  After that, the network is off.
- The harness gives no feedback between iterations.
- Stop: the harness stops when the agent prints `<promise>COMPLETE</promise>`, or after
  40 iterations.
- Grading: a hidden test suite calls the HTTP API. A human reviewer reads the code and
  `REPORT.md`.

## 4. Your task

Write the prompt for the Builder. Time limit: 45 minutes.
