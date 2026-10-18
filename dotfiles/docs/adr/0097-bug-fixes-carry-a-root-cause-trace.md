# Bug fixes carry a root-cause trace

**Context.** A bugfix spec required a reproduction, and its plan required
three proofs: the bug reproduces before the fix, the fix gives the expected
behavior, and preserved behavior holds. Nothing required the plan to show
where the bug comes from, so a fix could guard the symptom at a later line
while the fault stayed. Nothing asked the reviewer to check that either.
Anthropic's reviewer looks for the root cause on every bug fix (claude.dev,
"Solving code review at Anthropic", 2026-10, layer 2). The owner asked for a
real validation: files, paths, lines and a logical trace.

**Decision.**
- A plan for a Bugfix spec has a `### Root-Cause Trace`: the Trigger, the Path
  as numbered `file:line` hops with the value or state at each, the Fault
  line and its wrong assumption, the Other paths that reach the fault (from a
  search), and the Proof test.
- `check-plan.py` fails a bugfix plan without the section, without any of its
  five fields, or with no `file:line` in the Path or the Fault.
- `/review` gives the trace to `code-reviewer`, which walks it against the
  code hop by hop. A broken hop is REQUIRED. A fix that guards the symptom
  while the fault stays is a BLOCKER. A missed caller that reproduces the bug
  is a BLOCKER. A proof test that does not drive the trigger is REQUIRED.
- `code-reviewer` reports the walk under "Root-cause check", one line per hop.

**Cost.** A longer bugfix plan and a longer review. The trace can be wrong;
the walk is what catches that.
