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
  (ADDED/MODIFIED/REMOVED/RENAMED requirements) against a living
  `docs/specs/<capability>/spec.md`, and `/ship` owns merging the delta —
  fixes specs going stale after shipping, since nothing currently owns
  updating them. The `### Requirement:`/`#### Scenario:` anchors adopted in
  0040 are the prerequisite that makes the merge mechanical. Scope: ~3
  harness edits (`spec-driven-development`, `templates/spec.md`, `ship.md`)
  plus an ADR; artifacts live per project; no new skill — fold the sync into
  `/ship`'s Documentation attestation. Open decisions before adopting:
  (a) capability taxonomy — who names/bounds capabilities (proposed default:
  `/spec` proposes the capability name, approved with the spec);
  (b) bootstrap — lazy founding, where the first delta in an area *is* the
  initial living spec (proposed default), vs backfilling from shipped specs;
  (c) merge timing — proposed default: merge is required for the
  Documentation PASS, so GO cannot be issued with an unmerged delta (before
  GO writes truth for a possible NO-GO; after GO risks the forgetting this
  cures);
  (d) concurrent tickets touching one requirement — merge in dependency
  order, re-read the living spec from disk, mirroring sequential
  integration. A delta whose implementation was withheld is never merged.
  Cost honestly: a standing per-ship obligation and a new failure mode (a
  stale merge makes the living spec lie, worse than no spec); pays off with
  repeated tickets in the same area, overhead for one-offs. See
  `docs/adr/0040-openspec-conventions-adopted.md`.
