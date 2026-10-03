# `/ship`'s accessibility axis dropped, not improvised

**Decision.** Removed the **Accessibility** bullet from `commands/ship.md`'s
"uncovered axes" step and from its decision template. `/ship` now checks two
uncovered axes, infrastructure and documentation, instead of three.

[0028](0028-ship-command-as-synthesis-gate.md) added the axis on the reasoning
that accessibility is owned by no persona in the pipeline — which is true, and
is exactly the problem. `accessib`/`a11y`/`wcag` appeared nowhere else in the
harness: no reference checklist, no persona, no skill. Every other axis this
repo gates on has a single source of truth behind it — security has
`references/security-checklist.md`, `ai-security.md`, and `supply-chain.md`;
review has `skills/code-review-and-quality`; completion has
`references/definition-of-done.md`. Accessibility had four words in a bullet
("keyboard navigation, focus order, screen-reader labels, contrast") and nothing
to check them against, so each run would improvise its own standard. A gate that
invents its own criteria per invocation reports confidence it hasn't earned
(`CLAUDE.md` rule 7), and is worse than not claiming the coverage at all.

Infrastructure and documentation stay because they are verifiable against things
this repo actually has: the target environment, migrations, README/changelog, and
`skills/adr-recording`.

**Revisit if** a real `references/accessibility-checklist.md` exists. The axis
comes back with the checklist, not before it — restoring the bullet alone
recreates the same improvisation.

**Rejected — write the accessibility checklist now to keep the axis.** No work
in this repo currently touches a user-facing surface, so the checklist would be
speculative content maintained against nothing (`CLAUDE.md` rule 2). Writing it
when the first UI work appears means writing it against a real case.

**Rejected — keep the bullet as a soft prompt to think about accessibility.** A
`/ship` axis is not a reminder; the command requires each axis to be reported as
a result or an explicit not-applicable. A checklist-free axis makes
"not applicable" the path of least resistance on every run, which trains the
gate to be skipped rather than met.
