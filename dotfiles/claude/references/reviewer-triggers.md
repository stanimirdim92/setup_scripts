# Reviewer trigger matrix

Single source of truth for which reviewers `/review` dispatches for a
given diff (per `../../../docs/adr/0020-build-test-review-pipeline-split.md`,
`/build` no longer dispatches reviewers itself). Edit this file when a
trigger changes; don't duplicate trigger logic in `review.md` or in an
individual reviewer agent's own file — that drift is exactly what rule 6
("surface conflicts, don't let two things each invent their own
pattern") is for.

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
