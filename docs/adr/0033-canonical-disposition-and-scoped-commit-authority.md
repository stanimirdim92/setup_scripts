# Canonical release disposition, scoped commit authority, and gate-state integrity

**Decision.** Recorded for commit `2627913`, which changed four things about what
each gate may do and what evidence it must have.

**1. `/review` adds a canonical release disposition.** Each reviewer keeps its
own native severity and gains stable finding ids (`CODE-1`, `SEC-1`, `DIST-1`).
`/review` maps those onto one `BLOCKER`/`REQUIRED`/`ADVISORY` triple.
`distributed-systems-reviewer`, which previously had no stated vocabulary at all,
now declares Critical/Important/Suggestion explicitly.

This closed a real gap. `security-auditor` reports Critical/High/Medium/Low/Info
while `code-reviewer` and `distributed-systems-reviewer` report
Critical/Important/Suggestion, and `/ship`'s rules named "Critical" — which
matched two reviewers out of three and left High, Medium, Low, and Info with no
defined effect on the verdict. `/ship` now consumes only the canonical layer.

**2. `/ship` may not reclassify or deduplicate.** Findings keep their source
reviewer, native severity, disposition, id, location, and resolution. Two
findings describing the same issue are cross-referenced, never merged or
renumbered — collapsing them loses which axis found what, which is the whole
point of reviewing blind.

**3. Commit authority is scoped per command.** Invoking `/build` authorizes the
executor to create local implementation commits for its approved task after
required verification passes. Invoking `/test` authorizes only **passing**
test-only commits. Neither authorizes push, tag, deploy, release,
protected-branch mutation, history rewriting, or unrelated changes, and `/ship`'s
GO is a release-readiness verdict rather than authorization to perform any of
them. The exception is declared in `skills/git-workflow-and-versioning`, where
the "ask before every commit and push" rule it modifies already lives, rather
than as a standalone rule elsewhere.

**4. A failing reproduction never enters the candidate branch.** It is preserved
as an external patch/report artifact and its path reported to `/build`. This
reverses the earlier rule that committing the failing reproduction was
"intentional evidence for the BUILD handoff". That rule put a deliberately red
commit on the same branch `/review` then reviews and `/ship` may ship.

Gate-state integrity backs all four: each gate requires the prior gate's handoff
from the current conversation, inspects the actual branch/commits/diff, and
blocks rather than inventing scope. A candidate change after VERIFY PASS or
REVIEW invalidates that result, so a fix repeats
`/build` → `/test` → `/review` → `/ship` rather than re-entering mid-chain.
Missing gate results, an undetermined or changed candidate, missing required
reviewers, undeclared dirty state, and a missing rollback plan are non-waivable.

**Rejected — normalize every reviewer onto one severity vocabulary.** It would
flatten `security-auditor`'s five levels, which map to distinct remediation
urgency (block release / fix before release / current sprint / next sprint /
consider), and would rewrite the output contract of vendored personas against
their upstream. Preserving native severity and adding one mapping keeps both the
reviewer's precision and the verdict's comparability.

**Rejected — let `/ship` re-rank findings into a single ordered list.** That is
what the disposition layer replaces. A single ranking buries a quiet-but-real
finding from one axis under a louder one from another, and `/ship` has less
context than the reviewer that raised it.

**Rejected — a persistent store of gate results.** There is none, and pretending
otherwise would let `/ship` claim gates it never saw. Requiring the handoffs
in-conversation, and blocking when they are absent, is honest about the actual
mechanism: in a fresh conversation you supply the prior outputs or rerun the
gates.

**Rejected — keep committing failing reproductions.** The evidence value is real
but is fully served by an external patch/report artifact, without leaving a red
commit on a branch that downstream gates treat as the release candidate.
