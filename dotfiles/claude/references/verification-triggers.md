# Independent verification trigger matrix

`/build` always owns implementation-time verification. `/test` is a separate,
independent verifier and is required only when extra verification is worth the
additional context and agent cost.

`/review` is the decision point. Require `/test` when any of these apply:

- `/build` could not complete a required check, or its verification evidence is
  incomplete, blocked, or not trustworthy.
- The change can corrupt, delete, migrate, or materially reinterpret persistent
  data.
- The change alters authentication, authorization, permissions, secrets,
  cryptography, tenant isolation, or another security trust boundary.
- The change alters concurrency, retries, idempotency, ordering, delivery
  semantics, queue processing, distributed state, or long-running job recovery.
- The change modifies a public/shared contract consumed outside the immediate
  implementation context.
- The change affects a critical business/user flow where a regression would have
  material operational, financial, security, or data impact.
- A bug/regression fix lacks a trustworthy reproduction or has meaningful edge
  cases not covered by the implementation-time tests.
- The user explicitly asks for independent verification.

Normally do **not** require `/test` for:

- localized deterministic changes with focused tests already green;
- refactors whose relevant before/after tests are green;
- documentation/static-content changes with deterministic validation;
- formatting or generated-file-only changes;
- routine changes where `/build` produced complete, credible verification
  evidence and none of the risk triggers above match.

When uncertain whether a material trigger matches, require `/test`.

This file is the single source of truth for the independent-verification gate.
Do not duplicate this trigger list in `/review`, `/test`, or agent definitions.
