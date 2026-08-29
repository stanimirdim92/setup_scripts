# Four conventions adopted from Fission-AI/openspec; nothing vendored

**Decision.** Compared this harness against the thirteen skills in
Fission-AI/openspec (MIT) and adopted four conventions as ideas, vendoring no
files: every openspec skill is generated from templates and hard-coupled to the
`openspec` CLI (`status --json`, `instructions`, stores, schemas), which is
their artifact-dependency engine; this harness's engine is the command chain
itself, so the text does not transfer even where the method does.

1. **Greppable requirement anchors.** `references/templates/spec.md` gains a
   `## Requirements` section using `### Requirement:` / `#### Scenario:`
   headings (GIVEN/WHEN/THEN under each scenario). The exact heading forms are
   load-bearing: `/test` and `/review` can enumerate them mechanically and map
   coverage requirement-by-requirement instead of interpreting prose.
   `/test`'s packet passes the enumerated list when the spec has the anchors.

2. **Authorization does not carry forward.** `/spec` and `/plan` now state that
   the request which invoked them authorizes specification/planning only, even
   when it says to build or fix something, and that the instruction does not
   carry past the command. This closes the gap in the previous "Stop. Do not
   implement" wording, which did not cover treating the original "build X"
   request as standing permission once planning ended.

3. **Target selection.** New `references/target-selection.md`: explicit
   argument wins; else infer from conversation; else auto-select a sole
   candidate; else ask with recent candidates and their state — and always
   announce the resolved target ("Using: <target>") with the override path.
   `/build`, `/test`, `/review`, and `/ship` point at it from their first step;
   previously each run improvised when the argument was omitted. Single-sourced
   in `references/` per rule 6, like `reviewer-triggers.md`.

4. **Two reviewer/gate disciplines.** `/review` and `/ship` re-read handoff and
   spec/plan artifacts from disk even when they appeared earlier in the
   conversation (files change between gates — this session's own recurring
   pattern). All three reviewers gain the anti-inflation ladder: when uncertain
   which severity applies, choose the lower — severity now maps straight to
   release disposition, so an inflated finding becomes a false BLOCKER at
   `/ship`.

Also fixed in passing: `agents/code-reviewer.md` listed **Required** as its
middle severity — introduced in `399587d` under a sentence claiming the labels
match the `code-review-and-quality` skill, while the skill, `commands/review.md`'s
disposition table, and the agent's own output template and rules all say
**Important**. Restored **Important**.

**Rejected — vendoring openspec's delta-spec model (ADDED/MODIFIED/REMOVED
requirement deltas merged into living per-capability specs).** Their strongest
idea and this repo's real gap — per-ticket specs go stale after `/ship` because
nothing owns updating them — but it changes the spec storage model, not a
command's wording, and deserves its own decision. Recorded in `docs/IDEAS.md`
rather than half-adopted here.

**Rejected — an explore/thinking-partner skill.** A stance, not a workflow;
plain conversation plus `/spec`'s clarify phase covers it, and
[0039](0039-runtime-catalog-narrowed-by-observed-use.md) just removed this
category of always-on catalog weight.

**Rejected — openspec's three-dimension verification report
(Completeness/Correctness/Coherence).** Completeness and correctness are
already owned by `/test` and `/review`; the novel axis, coherence against
design decisions, only becomes checkable once anchored specs (adoption 1) are
in real use. Revisit then.
