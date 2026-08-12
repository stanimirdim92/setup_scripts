---
name: ticket-breakdown-and-delegation
description: Breaks an epic or ticket into subtasks sized for the specific person each one goes to, not just for scope. Use when splitting work across a team of engineers at different levels, handing a ticket off to someone else, or a breakdown needs to account for who actually does each piece — as opposed to solo planning, where planning-and-task-breakdown already covers sizing by scope alone.
---

# Ticket Breakdown and Delegation

## Overview

`planning-and-task-breakdown` sizes tasks by scope: how many files, how
much risk, what order dependencies force. That's necessary but not
sufficient the moment more than one person is doing the work — the same
scope is a different-sized task for a junior than for a senior, and a
breakdown that ignores who's holding each piece produces subtasks that
are technically well-formed and still wrong for the team doing them.

## When to Use

- Splitting an epic or ticket across two or more named people
- Handing a single ticket off to someone else to own
- A breakdown needs to leave room for someone's growth without leaving
  them stuck
- You're the one accountable for the ticket landing, not just for writing
  the plan

**When NOT to use:** Solo work with one owner — that's
`planning-and-task-breakdown` alone, no delegation layer needed.

## Process

1. **Name the assignee for each subtask before deciding its granularity.**
   Size follows the person, not the other way around — don't split first
   and then look for someone to fit each piece.
2. **Split by ownership boundary, not file boundary.** A subtask should be
   independently completable and independently reviewable by one person.
   Two people sharing a file because the split was drawn by module instead
   of by owner produces merge conflicts and diffused accountability.
3. **Size by level, not by ticket size alone:**
   - Senior/independent: fewer, larger subtasks; state the outcome, not
     the steps; check in at completion, not mid-flight.
   - Growth/junior: smaller subtasks, but leave real decision-making room
     in at least one of them — don't strip every judgment call out just
     to make it safe. Pair the ambiguity with a review checkpoint, not
     with removing the ambiguity.
   - Unknown level: ask. Guessing here is the single most expensive
     mistake in this skill — a wrongly-sized subtask wastes the time of
     whoever it went to, not just the plan's accuracy.
4. **State the definition of done per subtask explicitly**, same bar as
   `../../references/definition-of-done.md`. Delegation without an
   explicit done-state drifts silently — the assignee's idea of finished
   and yours diverge and nobody notices until review.
5. **Surface blocking order.** If subtask B can't start until subtask A
   lands, say so and sequence them — don't let two people discover a
   dependency at standup that the breakdown should have caught.
6. **Report the breakdown as a table**, not prose: subtask, assignee,
   size, definition of done, blocked-by. A delegation plan that can't be
   scanned in ten seconds doesn't get referred back to.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "Splitting by file is faster" | File boundaries and ownership boundaries aren't the same thing; the fast split creates the merge conflict later. |
| "They're senior, they'll figure out the size themselves" | Still state the definition of done — ambiguity there costs senior time on rework, not a fair challenge. |
| "I'll size it once I know who's free" | Reorder: level gates granularity regardless of who ends up assigned; re-check size after assignment, don't skip sizing until then. |
| "It's obviously two people's work, I don't need to write it down" | The write-up is what lets someone else pick up the plan if you're unavailable — "obvious" plans are the ones that go unrecorded and get re-litigated. |

## Red Flags

- A subtask with no named assignee and no explicit "unassigned — needs
  owner" marker
- Every subtask sized identically regardless of who's on it
- A dependency between subtasks discovered mid-sprint instead of at
  breakdown time
- No definition of done per subtask, only for the ticket as a whole

## Verification

- [ ] Every subtask names an assignee (or is explicitly marked unassigned)
- [ ] Every subtask's size matches that assignee's level, not just the
      ticket's overall size
- [ ] Every subtask states its own definition of done
- [ ] Blocking order between subtasks is explicit
