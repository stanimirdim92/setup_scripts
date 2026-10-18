# Reviewer changes are rescored

**Context.** Anthropic scores every reviewer change against real shipped
bugs before trusting it (claude.dev, "Solving code review at Anthropic",
2026-10). The harness has the tool for this, `review-eval` (ADR 0093), but
nothing asked for a run. A prompt edit could make review worse and nobody
would know until a bug shipped. The owner agreed and asked what it costs.

**Decision.**
- A commit that changes a reviewer persona, `/review`, the reviewer triggers,
  the risk tiers, or a Codex reviewer role carries a `Review-eval:` trailer.
  The trailer holds the result against the baseline, or `not run - <reason>`.
- `check-rescore.py` runs in CI over the pushed commits or the pull request.
  It fails a watched commit with no trailer or a bare "not run".
- The owner decides when a run is worth it. "Not run" with a reason is
  allowed, so a typo fix costs nothing; the reason is on record.
- The rule starts with this ADR. Four earlier commits in this session changed
  `/review` or `code-reviewer` without a rescore; they are listed, not
  rewritten.

**Cost.** Each case is one headless `/review`, capped by `--budget` (default
$10). A rescore reuses the stored baseline: one run per case, two to trust a
small difference. Eight cases cost 8 to 16 runs, at most $80 to $160 at the
cap. The real figure is the `Cost:` line the first run prints. Cases are
gitignored and come from the "Shipped bugs" table (ADR 0100, 0110).
