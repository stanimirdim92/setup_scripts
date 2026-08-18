---
name: adr-recording
description: Records a technical/architectural decision as one file in that project's docs/adr/*.md, in the Decision/Rejected format this machine uses everywhere. Use whenever a real choice between alternatives gets made — a technology pick, a config flip, a pattern change, or a decision that reverses an earlier one — that a future session or teammate would otherwise re-litigate from scratch with no memory it was already settled. Not for routine implementation where only one reasonable option existed, and not for undecided ideas (those belong in docs/IDEAS.md — see documentation-practices.md if this project has it).
---

# Recording a technical decision

## Overview

A decision with no recorded reasoning gets re-proposed and re-litigated
every time someone forgets — or never knew — it already lost once. This
skill is the portable version of the practice this machine's own
`setup_scripts` repo uses on itself: one file per decision under
`docs/adr/`, an index that keeps them scannable, and a hard rule that a
reversed decision stays on the record instead of being edited away.

## When to Use

- You (or the user) just picked one real alternative over another —
  library, pattern, config, architecture — and can state why.
- A prior decision is being reversed, extended, or narrowed by new
  information.
- Someone will plausibly ask "why is this built this way" later, in a
  session that doesn't have this conversation's context.

**When NOT to use:**
- Only one reasonable option existed — that's not a decision, it's the
  obvious move, and doesn't need a record.
- The idea isn't decided yet — park it in `docs/IDEAS.md` instead (see
  `documentation-practices.md`'s Ideas vs. decisions section); a decision
  record for something unbuilt just becomes a lie the moment plans
  change.

## Process

1. **Find or create `docs/adr/`** in the current project's repo root (not
   this machine's own dotfiles repo unless that's literally the project
   in scope). If it doesn't exist yet, create it along with the index
   file from step 5 — don't write a lone decision file with no index.
2. **Number it.** 4-digit, zero-padded, one past the highest existing
   `NNNN-*.md` in the directory (MADR-style — `0001`, not `1`). Never
   reuse or renumber an existing file's number, even if it's later
   superseded.
3. **Title it.** Short, kebab-case, distinctive enough to identify the
   decision from the filename alone — `0003-executor-concurrency-sequential-only.md`,
   not `0003-fix.md`.
4. **Write the file** as an H1 matching the title, then the two-part
   shape, repeated per alternative:
   - `**Decision.**` — the statement and the reasoning behind it in the
     same paragraph. Don't separate "what" from "why" into different
     sections; the reasoning is what makes the record worth rereading.
   - `**Rejected — *(name the alternative).***` — one block per
     alternative seriously considered, not just the one that won. The
     reason must be concrete enough to stop the same alternative being
     re-proposed with no new information — a measurement, a specific
     broken assumption, or a direct instruction from whoever owns the
     call. "Didn't like it" doesn't qualify.
5. **Update `docs/adr/README.md`** (create it if this is the first
   decision in the project) with one row: number, link, one-line title,
   status. Keep the README to the index table plus a short pointer to
   wherever the project's own format/convention is explained — don't
   re-explain the format in every project's README; that's what step 4
   already encodes structurally.
6. **Reversing a prior decision?** Leave the old file's text exactly as
   it was written — don't edit its Decision or Rejected paragraphs, even
   though they're now out of date. Write a *new*, higher-numbered file
   stating the reversal and linking back to the old one by number. Mark
   the old row's Status column `Superseded by NNNN` in the index. The
   old decision being wrong in hindsight is exactly the part worth
   keeping — it's evidence for whoever reads it next, not an error to
   erase.
7. **Splitting an existing running decisions doc into per-decision
   files?** Record that as its own decision (per step 6 — it likely
   reverses whatever earlier choice kept decisions in one file), and
   repoint every reference to the old location (other docs, code
   comments, other ADRs' cross-references) at the new specific file that
   now holds each decision, not a generic directory pointer. Grep for the
   old filename across the repo before considering the split done.

## Format Reference

```
# <Short, distinctive title>

**Decision.** <What was decided, and the reasoning for it, in one
narrative — not split into separate "what" and "why" sections.>

**Rejected — *(alternative name).*** <Why it lost — concrete enough to
block re-proposal.>

**Rejected — *(another alternative, if any).*** <Why it lost.>
```

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "It's obvious why we did this" | Obvious now, forgotten in three months — that's exactly the failure mode this skill exists to prevent. |
| "I'll just edit the old ADR to reflect the new decision" | That deletes the historical record. Write a new file that supersedes it; leave the old one alone. |
| "One file is fine, no index needed yet" | The index costs one row and stops the second decision from needing to be discovered by directory listing. Write it from decision #1. |
| "The rejected alternative wasn't that serious" | If it was considered enough to write a sentence about, it's worth a `Rejected` block — otherwise it comes back next quarter with no memory it lost. |
| "This project doesn't have a docs/ folder" | Create `docs/adr/` anyway — it's the decision record, not a doc dump; don't skip it because the surrounding structure is thin. |

## Red Flags

- A decision file with no `Rejected` block at all, when alternatives were
  actually discussed — that's a conclusion with the reasoning stripped
  out.
- An edited old ADR whose Decision paragraph no longer matches what
  actually shipped, with no new file explaining why.
- A `docs/adr/` directory with files but no `README.md` index.
- A rejection reason that's a feeling ("didn't like it," "seemed risky")
  instead of a concrete, checkable fact.

## Verification

- [ ] File is `docs/adr/NNNN-kebab-title.md`, number one past the
      current highest
- [ ] Contains `**Decision.**` plus at least one `**Rejected —**` block
      with a concrete reason
- [ ] `docs/adr/README.md` has a row linking the new file
- [ ] If this reverses a prior decision: the old file is untouched, and
      its index row says `Superseded by NNNN`
