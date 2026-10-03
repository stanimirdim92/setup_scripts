# Sonnet 5.5 replaces Sonnet 5; the advisor moves to Fable 5.1

**Decision.** The three Sonnet-tier personas — `repo-recon`, `executor`,
`test-engineer` — move from `claude-sonnet-5` to `claude-sonnet-5-5`, released
2026-09-28 at the same price ($2 / $10 per MTok) with the same 1M context. The
role tiering from [0056](0056-role-tiered-models-blind-review-recon-width-writer-isolation.md)
is unchanged: reviewers and the session stay on `opus[1m]`. Pins stay explicit
version ids, for 0002's reason. `settings.json`'s per-model effort override
follows the id, and `dotfiles/tools/checks/validate-frontmatter.py` now requires the new pin.

**Decision.** `advisorModel` changes from the `opus` alias to `claude-fable-5-1`,
Anthropic's most capable widely released model. The advisor runs only when
consulted, so its higher per-token price ($10 / $50) is paid per consultation,
not per turn. The API requires an advisor at least as capable as the model
consulting it; Fable 5.1 satisfies that for every tier used here.

**Decision — advisor effort `high`.** Consultations are infrequent and are the
harness's hardest judgment calls, so their cost is bounded and depth is what they
are for; `medium` was the alternative considered (approver's choice between the
two). Set through `modelSettings`, keyed by the pinned id.

**Decision — effort `high`.** Sonnet 5.5 recalibrates its effort levels, so
the `xhigh` override carried over from Sonnet 5 is lowered to `high`, the
model's default (approver's call). Anthropic's guidance starts agentic coding at
`medium`; revisit from `dotfiles/docs/observation-log.md` run metrics (cost and turns for
executor and recon runs), not by assumption.

**Rejected — floating aliases (`sonnet`, `fable`).** Same reason 0002 pinned:
delegation should target a deliberately chosen version, not whatever an alias
resolves to after the next release.
