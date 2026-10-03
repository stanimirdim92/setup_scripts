# Plain writing, an `/explain` review page, a generated harness map, and ticket-scoped plan recall

Drawn from a Karpathy post (2026-10) on agents that write for the human who
must review their work: constrained English, and a visual page per change
instead of a wall of report text. Three ideas apply here. A fourth decision
comes from the first real plan-recall run (LD-441).

**Decision — human-facing prose follows a simplified technical English.**
`AGENTS.md` §Writing for humans adopts the core of ASD-STE100: one instruction
per sentence, 20 words or fewer per instruction and 25 per description, active
voice, one word for one thing, noun clusters of three words or fewer, vertical
lists, result first. It covers reports, gate results, handoffs, updates, and
the prose in specs, plans and ADRs. It does not cover code, commits,
identifiers, or quoted evidence. It is an 80% rule: break it when a longer
sentence is clearer. Full STE (its fixed dictionary of approved words) was
rejected: it fights domain vocabulary and no tool here can check it.

**Decision — `/explain` renders one HTML review page per candidate.** It reads
the spec, plan, diff, and the gate messages already in the conversation. It
writes an offline page: requirement trace, touched-module diagram,
blind-reviewer's "what this change appears to do" next to the spec's goal,
unplanned files, open findings, rollback. It dispatches nobody, judges
nothing, and writes under `$(git rev-parse --git-common-dir)/explain/`, so the
candidate's tree stays clean for `/review` and `/ship`. No gate reads the
page. A missing source shows as "not available", never as a reconstruction.
Making it a `/review` or `/ship` output was rejected: a gate's evidence must
stay the completion message, and a page would add a second, unchecked copy.
The Codex adapter `$explain` is explicit-only like the stage commands.

**Decision — the harness map is generated, and CI fails when it is stale.**
The hand-drawn `docs/harness-map.html` (stamped at 3e6280f) still said six
personas, Sonnet 5 and nineteen skills months after each changed.
`tools/harness-map.py` now renders it from the files that own each fact:
agent and command frontmatter, `settings.json`, hook header comments, skill
frontmatter with the Codex invocation policy, CI step comments, and the ADRs.
The output carries no timestamp or commit id, so `--check` compares it byte
for byte, and the `Harness map is current` CI step runs it. Only the gate
order and the human decision points stay as constants in the generator: no
source file states them as data. The hand-drawn SVG diagrams were dropped;
their arrows and labels were the part that drifted. Deleting the map was the
alternative ADR 0055's era allowed; a map that cannot go stale is cheaper than
no map.

**Decision — plan recall scopes to the ticket and ignores pipeline files.**
The first real run scored LD-441 at 10% recall over a range that also held
LD-442, worktree-isolation infrastructure, agent configuration and pipeline
artifacts. Its 89% precision was the real signal. `recall.py --ticket ID` now
unions only the commits whose message names the ticket, and default excludes
drop `docs/specs/*`, `docs/tasks/*`, `CLAUDE.md`, `AGENTS.md`, `.claude/*`,
`.codex/*`, `.ai/*` and `.worktreeinclude`, which no task plans
(`--no-default-excludes` restores them). A file added and removed inside the
ticket is dropped.
