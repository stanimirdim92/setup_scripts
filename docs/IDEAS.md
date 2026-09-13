# Ideas

The unjudged parking lot — things worth doing that haven't been decided
yet. Format and how this differs from `docs/adr/*.md` (judged, built) is
defined in `dotfiles/claude/references/documentation-practices.md`; don't
duplicate that explanation here.

Add freely, one line if that's all there is, but say what makes it worth
doing, not just what it is.

## Parked

- **Main-session read-size gate (the `shunt` pattern)** — **S**. Spotify's
  `shunt` plugin (`spotify/portal-ai-plugins` → `plugins/shunt/`, v0.2.0; the
  `sorantis` fork stops six days before it landed) turns "don't read big files
  inline" from a CLAUDE.md sentence into a `PreToolUse` hook: a `Read` without
  `offset`/`limit`, or `cat|head|tail|less|more`, on a file over 350 lines is
  denied with a redirect to a bulk reader. Same lesson 0044/0049/0055 applied
  here — a guarantee the config states is one the harness enforces — and the
  sentences it would enforce are still advisory:
  `dotfiles/claude/references/repository-precedent.md` §1 "Do not turn a
  bounded check into an inline repository survey" and `CLAUDE.md` §Session and
  context "Keep raw tool output … out of active context". The reader half is
  already the stronger one here: `repo-recon` reports `path:line` pointers
  (`agents/repo-recon.md` rule 1), which shunt's worker cannot — `bulk-read`
  streams unnumbered `cat` output and its README lists editing under "What
  doesn't get delegated". Only the forcing half is missing. Shape if adopted:
  one hook on `Read` + `Bash`, **main session only** — hook input carries
  `agent_id` inside a subagent, so every persona is exempt and recon and
  executors keep whole-file reads; `hookSpecificOutput` deny form, not shunt's
  legacy `decision`; fixtures in `tools/test-hooks.sh` including the cases
  shunt's own evals get wrong (`cat f 2>/dev/null` and `cat a b c` pass its
  `>`/first-argument checks; `head -100 f` is blocked and eval #5 asserts it).
  Adopting it amends ADR 0051, which rejected size as a dispatch trigger — a
  size gate forces dispatch by size in practice. **Revisit when** the
  observation period's `run-metrics.sh` "LARGE TOOL RESULTS" section shows the
  main session repeatedly taking whole-file results over the threshold in areas
  a bounded check or recon should have covered, or 0051's own revisit clause
  fires (bounded checks expanding into inline surveys). Not before: it is a new
  gate, and the harness-v1 freeze excludes gates. Related, same freeze: run
  `repo-recon` on a cheaper model for pure inventory questions — the cost lever
  shunt actually pulls (Gemini 2.5 Flash worker); ours is isolated context at
  the same per-token price. Source: Spotify Engineering, "Portal by Spotify cut
  my Claude Code token usage by 90%" (2026-09). The 90% is displaced
  main-context input estimated as chars/4 on an internal 162K-line Java
  monorepo; worker-side tokens and the follow-up targeted read an edit needs
  are not counted, and the committed fixtures (largest 602 lines) cannot
  reproduce the table.

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
