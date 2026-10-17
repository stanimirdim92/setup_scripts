# Pre-existing findings do not block

**Context.** A reviewer reads the code around a change and finds defects that
were already there. Until now such a finding blocked `/ship` like any other
BLOCKER or REQUIRED finding, so a ticket could stall on code it never touched.
It also reads as the author's fault. Anthropic's Claude Code team tags these
findings "Pre-existing" for that reason (claude.dev, "Solving code review at
Anthropic", 2026-10).

**Decision.**
- A finding is marked `pre-existing` when the defect exists at the candidate
  base and the change neither introduces it nor makes it reachable or worse.
- It keeps its disposition, so its seriousness stays visible.
- It does not block `/ship`. `/ship` lists it under follow-ups with where it
  is tracked: a ticket or an observation-log row. A pre-existing BLOCKER with
  no tracked follow-up is NO-GO.
- A change that adds a caller of the old defect, copies it, or depends on it
  makes it new. Then it is not pre-existing and blocks as usual.
- In the review SARIF, `baselineState` is `unchanged` for a pre-existing
  finding and `new` otherwise.

**Cost.** The reviewer must judge whether the change reaches the old defect.
A wrong call lets a real defect ship as a follow-up. The tracked follow-up
keeps it from being lost.
