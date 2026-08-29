# Plugin set: dropped `feature-dev`, added four `@claude-plugins-official`

**Decision.** `feature-dev@claude-plugins-official` removed from
`settings.json` — it ships its own `code-explorer`/`code-architect`/
`code-reviewer` agents running a 7-phase pipeline that duplicated this
repo's own `/spec` → `/plan` → `/build` → `/review`, one of the two
"active router" collisions raised via `addyosmani/agent-skills`'
`docs/comparison.md`. Added `typescript-lsp`,
`code-simplifier` (referenced by `references/definition-of-done.md`'s
Quality section), and `playwright`.

**Rejected — keep `domain-modeling` and/or `improve-codebase-architecture`
as standalone cherry-picks.** Floated as low-risk additive skills (no
tracker dependency, nothing here plays either role today) while
evaluating LD-329 against all three repos. Rejected on later, more
direct instruction: no Matt Pocock content stays vendored, full stop —
simpler than maintaining a policy of "his router is out, but individual
skills are still in," and this team's preference is explicitly to lean
into the SDLC/phase-mapped shape addyosmani's collection already
provides rather than blend in a second author's individual skills.
