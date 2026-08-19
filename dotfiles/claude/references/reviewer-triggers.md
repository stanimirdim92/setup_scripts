# Reviewer trigger matrix

Single source of truth for which reviewer runs on a given diff. `/build`
and `/review` both point here instead of each defining their own copy —
the two commands drifting out of sync on this exact question is what
rule 6 ("surface conflicts, don't let two things each invent their own
pattern") is for. Edit this file when a trigger changes; don't patch
`build.md` or `review.md`'s own copy of the condition.

- **`code-reviewer`** — always. Five-axis review: correctness,
  readability, architecture, security, performance.
- **`security-auditor`** — diff touches input handling, infra, configs, secrets, 3rd party integrations, auth.
- **`distributed-systems-reviewer`** — diff crosses a process/network/
  queue boundary: an RPC or HTTP call between services, a queue
  producer/consumer, a scheduled job, or a background worker.

Give every reviewer that runs the diff plus a one-line goal and the
acceptance criteria that apply — not the full spec, not `docs/tasks/[TICKET]-plan.md`,
not another reviewer's output. Each axis/specialist reviews blind to the
others; an axis that can see another's findings starts anchoring on them
instead of forming its own.
