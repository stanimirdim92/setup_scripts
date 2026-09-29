# Sonnet 5.5 replaces Sonnet 5; the advisor moves to Fable 5.1

**Decision.** The three Sonnet-tier personas — `repo-recon`, `executor`,
`test-engineer` — move from `claude-sonnet-5` to `claude-sonnet-5-5`, released
2026-09-28 at the same price ($2 / $10 per MTok) with the same 1M context. The
role tiering from [0056](0056-role-tiered-models-blind-review-recon-width-writer-isolation.md)
is unchanged: reviewers and the session stay on `opus[1m]`. Pins stay explicit
version ids, for 0002's reason. `settings.json`'s per-model effort override
follows the id, and `tools/validate-frontmatter.py` now requires the new pin.

**Decision.** `advisorModel` changes from the `opus` alias to `claude-fable-5-1`,
Anthropic's most capable widely released model. The advisor runs only when
consulted, so its higher per-token price ($10 / $50) is paid per consultation,
not per turn. The API requires an advisor at least as capable as the model
consulting it; Fable 5.1 satisfies that for every tier used here.

**Open — effort calibration.** Sonnet 5.5 recalibrates its effort levels;
Anthropic's guidance starts agentic coding at `medium`. The existing `xhigh`
override is carried over unmeasured. Revisit from `docs/observation-log.md`
run metrics (cost and turns for executor and recon runs), not by assumption.

**Rejected — floating aliases (`sonnet`, `fable`).** Same reason 0002 pinned:
delegation should target a deliberately chosen version, not whatever an alias
resolves to after the next release.
