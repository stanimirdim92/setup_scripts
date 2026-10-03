# `adr-recording` compared against adr.github.io, vercel/ai's `adr-skill`, and ECC's ADR skill

**Decision.** Compared this repo's `adr-recording` skill against three
external references the user pointed at: [adr.github.io](https://adr.github.io/)
(the community standard — umbrella concept, no single prescribed format,
points at Nygard/MADR/Y-statements), `vercel/ai`'s `adr-skill` (a heavyweight
Node-tooled skill built for agentic coding: 4-phase Socratic intake, an
"Implementation Plan" section embedded in the ADR itself, a review-checklist
gate, and scripts for numbering/index/status), and `affaan-m/ECC`'s
`architecture-decision-records` skill (lightweight, Nygard-based, sequential
numbering, explicit read-workflow for "why did we choose X").

Found this repo's format already stronger than ECC's on the one rule that
matters most — never editing a superseded file's text, only marking its
index row and writing a new one — and found nothing in either external
skill resembling the `Common Rationalizations`/`Red Flags` tables already
here, which pre-empt the actual ways this practice gets skipped or gamed
rather than just describing the format.

Adopted four real gaps, all additive (no format change to existing files,
no renumbering):

1. **Proactive triggers** (from both vercel and ECC) — a short list of
   signals that should prompt suggesting an ADR unprompted: new
   dependency/plugin, establishing a pattern others must follow,
   contradicting an existing ADR, or about to write a multi-sentence "why"
   comment in code instead of a linked record. The skill was previously
   purely reactive.
2. **Consulting Existing Decisions** (from ECC's read-workflow) — the skill
   had a write-workflow only; added the check-before-proposing and
   answer-from-the-file steps as their own section, since this applies
   before any architectural suggestion, not just before writing a new ADR.
3. **Optional `Revisit if` block** (inspired by vercel's "monitor revisit
   conditions") — states a concrete future condition that would actually
   change the call, e.g. a library hitting a stated limit. Explicitly
   optional; a Red Flag entry warns against manufacturing one just to fill
   the section.
4. **`Deprecated` status**, distinct from `Superseded by NNNN` — for a
   decision that became moot with nothing replacing it (the feature it
   governed was removed entirely). Previously only `Accepted`/`Superseded`
   existed, which had no honest label for "no longer applies, and there's
   no new decision to point at instead."
5. **Explicit code-linkage convention** (from vercel's ADR↔code
   bidirectional linking) — named as a stated rule what this repo's own
   ADRs already do in practice (SKILL.md prose pointing at `docs/adr/NNNN-*.md`):
   name affected paths in the Decision paragraph, leave a one-line pointer
   at the governed code/config site back to the file.

**Rejected — full MADR/Nygard section scaffolding** (separate Context /
Decision Drivers / Considered Options / Consequences sections, as both
vercel's `adr-madr.md` template and ECC's format use). This repo's fused
`**Decision.**` paragraph (statement + reasoning together, not split across
sections) was a deliberate earlier choice, validated by real usage — 18
ADRs written in this repo alone read fast specifically because there's one
place to look, not four. More mandatory sections adds scaffolding-filling
friction for exactly the use case this skill serves (an agent recording
many small decisions per session), no added rigor for it.

**Rejected — a formal `deciders`/approver field** (ECC's header, vercel's
"who needs to approve" intake question). This is a solo/small-team personal
config practice, not an enterprise governance record; the existing
`Rejected` block's own bar — "a direct instruction from whoever owns the
call" qualifies as a reason — already captures authority when it matters,
without a field that's empty in the overwhelming majority of entries here.

**Rejected — a `Proposed` status value** (all three of ECC, vercel, and the
Nygard/MADR templates default to one). This repo's own convention
(`documentation-practices.md`) already routes undecided ideas to
`docs/IDEAS.md` — an ADR here is written only once something is actually
decided, per the skill's own "When NOT to use." Adding `Proposed` would
create two places tracking the same not-yet-decided state.

**Rejected — Node/script tooling** (vercel's `new_adr.js`/`set_adr_status.js`/
`bootstrap_adr.js`). The numbering step is genuinely deterministic (rule 5:
mechanical work gets plain code, not model judgment), but at this skill's
actual firing frequency — a handful of times per month, across whatever
project it's invoked in, which may not even have Node available — a script
to save one directory-listing-and-increment is tooling maintenance that
outweighs what it saves. Revisit if usage frequency or project language
mix changes this tradeoff.
