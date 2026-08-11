---
description: Conduct a five-axis code review — correctness, readability, architecture, security, performance
---

Invoke the `code-review-and-quality` skill.

Review the current changes (staged or recent commits) across all five axes:

1. **Correctness** — Does it match the spec? Edge cases handled? Tests adequate?
2. **Readability** — Clear names? Straightforward logic? Well-organized?
3. **Architecture** — Follows existing patterns? Clean boundaries? Right abstraction level?
4. **Security** — Input validated? Secrets safe? Auth checked? For changes touching nginx/mysql/redis/php-fpm config, also run the `security-reviewer` agent.
5. **Performance** — No N+1 queries? No unbounded ops?

For changes that cross a process/network/queue boundary (an RPC or HTTP
call between services, a queue producer/consumer, a scheduled job, a
background worker), also run the `distributed-systems-reviewer` agent —
these five axes don't cover timeouts, idempotent retries, backoff,
circuit breakers, backpressure, or checkpointing, and that's a different
class of bug than the ones above.

Categorize findings as Critical, Important, or Suggestion.
Output a structured review with specific file:line references and fix recommendations.
