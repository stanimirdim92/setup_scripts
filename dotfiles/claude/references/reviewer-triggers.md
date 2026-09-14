# Reviewer trigger matrix

Single source of truth for `/review` specialist dispatch.

- **`code-reviewer`** — always.
- **`blind-reviewer`** — always. The same diff read with no intent at all; see
  the packet rule below, which is what makes it a second opinion rather than a
  second copy.
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

Give `code-reviewer` and every triggered specialist:

- the integrated diff;
- a one-line goal;
- relevant acceptance criteria;
- build/verify evidence needed to understand what was checked.

Give `blind-reviewer` **the integrated diff and nothing else** — no goal, no
acceptance criteria, no build evidence, no ticket id in the packet text. It is
reviewing whether the code is right on its own terms, and a reviewer that knows
the intent reads the code as confirming it. Leaking any of the above turns this
dispatch into a more expensive duplicate of `code-reviewer`.

Do not give reviewers the full spec/plan or another reviewer's output.
