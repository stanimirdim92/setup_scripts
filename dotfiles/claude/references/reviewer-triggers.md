# Reviewer trigger matrix

Single source of truth for `/review` specialist dispatch.

- **`code-reviewer`** — always.
- **`security-auditor`** — only when the diff materially changes a security
  boundary: authentication/authorization, permissions, tenant isolation,
  secrets/credentials, cryptography, untrusted-input handling, sensitive data
  exposure, dependency/supply-chain trust, or security-sensitive infrastructure
  / third-party integration behavior.
- **`distributed-systems-reviewer`** — only when the diff materially changes
  distributed failure semantics: retries, idempotency, ordering, delivery
  guarantees, concurrency, timeout/failover behavior, queue processing,
  multi-step/background-job recovery, or state coordination across a
  process/network boundary.

A generic config edit, ordinary HTTP call, existing worker touch, or third-party
integration does **not** trigger a specialist merely because that category is
present. The change must alter a failure/trust boundary the specialist owns.

Give every reviewer that runs:

- the integrated diff;
- a one-line goal;
- relevant acceptance criteria;
- build/verify evidence needed to understand what was checked.

Do not give reviewers the full spec/plan or another reviewer's output.
