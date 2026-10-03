# Spec approval state, change-impact semantics, and requirement traceability

**Decision.** Compared this harness's DEFINE stage against GitHub Spec Kit,
Fission-AI/openspec, Kiro's bugfix specs, AWS AI-DLC, cc-sdd and BMAD, and
adopted six changes. Nothing was vendored; as with
[0040](0040-openspec-conventions-adopted.md), the methods transfer and the text
does not.

1. **Approval is document state.** The spec header gains
   `Status` (`Draft` / `Approved` / `Needs reapproval` / `Superseded`), `Ticket`,
   `Change kind`, `Supersedes`, `Approved by` and `Approved at`. `/spec` moves
   `Draft` → `Approved` only on explicit human approval; a behavioral edit sets
   `Needs reapproval` in the same edit that makes it; `/plan` refuses any other
   status. Approval previously existed only as an instruction and as
   conversation history — which a later session, a compaction boundary, or a
   downstream stage cannot see.

2. **Change-impact semantics.** A `## Change Impact` section records behavior
   added, modified, removed, renamed, **explicitly preserved**, and the
   compatibility/migration constraints. Required whenever `Change kind` is not
   `New`. The preserved-behavior line is the one that earns the section: it turns
   the characteristic brownfield failure — fixing one path while silently
   altering its neighbour — into a testable requirement.

3. **Requirement ids are mandatory** for any spec entering `/plan`, with a
   `Source:` line, assigned once and never renumbered. `/plan` maps every
   requirement to tasks and reports `Unmapped requirements: None` /
   `Orphan tasks: None`; `/test` and `/review` report evidence per id; `/ship`
   blocks GO on any requirement missing implementation or verification evidence.
   Previously ids were conditional on spec length, so the trace existed as prose
   re-read at four separate gates.

4. **A bugfix spec template.** `references/templates/bugfix-spec.md` leads with
   reproduction evidence and makes preserved behavior its own requirement, with
   a regression test required to fail before the fix. Root cause and fix
   mechanism stay in `/plan`, preserving the WHAT/WHY versus HOW boundary. It
   does not lower the bar for when a bug needs a spec.

5. **The closure pass gained requirements-quality assertions**: measurability,
   scenario coverage, applicable operational concerns as requirements or explicit
   exclusions, validated assumptions, no duplicate or conflicting requirements.
   Folded into the existing pass rather than becoming another checklist artifact,
   and explicitly scoped to applicable concerns — a column of `N/A` lines is the
   appearance of coverage, not coverage.

6. **A material-decisions log.** `DEC-###` entries record product, domain,
   contract and lifecycle decisions that changed specified behavior, so a
   resolved `OPEN QUESTION` leaves a trace instead of dissolving into the final
   prose. Technical decisions stay in the plan's Decisions and Provenance.

**Single-sourced, not restated.** 1, 3 and 5 have five consumers between them
(`/spec`, `/plan`, `/test`, `/review`, `/ship`), so their rules live in one new
`references/spec-quality-gates.md` and every consumer points at a section of it
— the `reviewer-triggers.md` pattern, for the same reason: five copy-pasted
versions of one rule set is how the copies start disagreeing.

**Honest note on cost.** `spec-driven-development/SKILL.md` was already about
6,350 tokens before this change — above the ~5,000-token per-skill
post-compaction re-attachment cap that
[0037](0037-fixed-session-context-reduced.md) flagged, where truncation is
silent. Moving the substance into the reference and templates held the skill's
growth to roughly +870 tokens rather than the +1,400 an inline version cost, but
it still grew, and it is still over the cap. That pre-existing condition is not
fixed here. The obvious extraction, if it becomes a problem: Phase 0's capability
map, the invariant mechanism-proof rules, and the data-lifecycle rules are three
self-contained blocks that would move to `references/` on the same pattern and
take the skill well under the cap. Not done in this pass because it is a
restructure of existing policy, not an addition, and deserves to be judged on
its own.

**Rejected — Spec Kit's separate checklist files.** Its requirements-quality
idea is the good part and is adopted in 5; the delivery mechanism is a second
document that duplicates what the spec already says and then drifts from it. The
closure pass already reads the whole spec at exactly the right moment.

**Rejected — Spec Kit's tests-optional default.** Weaker than the existing
Testing Strategy bar, which requires automated verification for any behavior
whose failure would produce wrong data, break a user journey, open an
authorization gap, or violate an invariant. Adopting it would be a regression
dressed as flexibility.

**Rejected — OpenSpec's archive/merge storage model, again.** 2 adopts the delta
*vocabulary* inside a single spec, which is a section in a template. Living
per-capability specs with `/ship` owning the merge is a different decision about
where specs live, still parked in `docs/IDEAS.md` with its four open questions
per [0040](0040-openspec-conventions-adopted.md). Adopting the vocabulary does
not commit to the storage model and does not resolve those questions.

**Rejected — Kiro's design-first bugfix workflow.** It puts a design document
between the bug report and the tasks, which collides with the SPEC/PLAN boundary
[0034](0034-spec-driven-development-narrowed-to-define.md) drew. The
reproduction-evidence and preserved-behavior structure transfers without it.

**Rejected — AI-DLC's artifact tree and workflow manifest.** Its traceability
model is adopted in 3; its delivery is a directory of generated artifacts plus a
manifest, which is an engine this harness does not have and does not need — the
command chain is the engine, and the plan's coverage table plus the task
packets' ids *are* the traceability matrix. A third artifact would be a copy
that drifts.

**Rejected — cc-sdd's fixed 1-3-hour task sizing and fresh context per task.**
Both contradict decisions already measured here: sizing is XS-XL heuristic with
recorded exceptions per
[0029](0029-build-selects-executor-skills.md)/the planning skill, and
[0031](0031-parallel-executors-via-worktree-isolation.md) resumes one executor
across a workstream precisely to avoid paying fresh discovery cost per task. Its
mandatory-requirement-ids idea is the part worth taking, and 3 takes it.

**Rejected — BMAD's PRD/UX/architecture/epic ceremony and extra agent roles.**
Nothing here that right-sized routing and `docs/adr/*.md` do not already cover,
and [0039](0039-runtime-catalog-narrowed-by-observed-use.md) just removed
always-on catalog weight of exactly this kind.

**Revisit if** the `REQ-###` trace turns out to be recorded but not used — if
`/ship` never actually blocks on a missing requirement across several real
tickets, the coverage table is ceremony and should be cut back to `/plan`'s
existing prose trace.
