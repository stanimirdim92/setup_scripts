# Ideas

The unjudged parking lot — things worth doing that haven't been decided
yet. Format and how this differs from `docs/adr/*.md` (judged, built) is
defined in `dotfiles/claude/references/documentation-practices.md`; don't
duplicate that explanation here.

Add freely, one line if that's all there is, but say what makes it worth
doing, not just what it is.

## Parked

- (none yet)

## Considered and rejected

| Idea | Reason rejected |
|---|---|
| — | — |

- **Delta specs merged into living per-capability specs** (from
  Fission-AI/openspec): per-ticket specs become deltas
  (ADDED/MODIFIED/REMOVED/RENAMED requirements) against
  `docs/specs/<capability>/spec.md`, and `/ship`'s Documentation attestation
  owns merging the delta after GO — fixes specs going stale after shipping.
  Needs its own decision: changes the spec storage model. See
  `docs/adr/0040-openspec-conventions-adopted.md`.
