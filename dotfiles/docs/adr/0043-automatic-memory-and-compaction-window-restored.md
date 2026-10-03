# Automatic memory and the 500k compaction window restored, reversing 0037

**Decision.** `autoMemoryEnabled` is `true` and
`CLAUDE_CODE_AUTO_COMPACT_WINDOW` is `500000`. This reverses the two settings
changes [0037](0037-fixed-session-context-reduced.md) made, and is reaffirmed
against [0039](0039-runtime-catalog-narrowed-by-observed-use.md), which
restated the disabled memory as still current.

The live `settings.json` already held both values; `README.md` and the two ADRs
still described 0037's. That contradiction is what this entry resolves —
documentation follows the configuration actually in use, rather than the
configuration being reverted to match documentation nobody had reread.

**Why automatic memory.** 0037's argument was not that auto-memory is useless;
it was that *two memory systems with no defined precedence* is the conflict
rule 6 forbids. That gap has since been closed:
`references/documentation-practices.md`'s "Memory: three systems, not one"
assigns each surface a distinct writer, location, scope, retrieval mode and
intended use, and states
the deciding rule: if losing a fact on a new machine would be a problem it
belongs in `docs/MEMORY.md`; if the question is "have I hit this before,
somewhere else" it belongs to episodic memory; auto-memory holds only
machine-local, low-stakes continuity. With roles assigned the surfaces are
separated, not blended — which is what rule 6 actually asks for.

`docs/MEMORY.md` remains the only durable, reviewable, committed record, and
auto-memory is explicitly not allowed to hold anything that must survive a
clone. The precedence document was written on the assumption that auto-memory
is on; leaving the setting off made that reference describe a system that did
not exist.

**Why 500k.** 0037 was already candid that halving the window was "a trade, not
a free win": compaction happens sooner and more often, spending more
summarization passes and losing more fidelity per session in exchange for lower
per-request context. 500k takes the other side of that same trade — fewer
compaction events and more retained fidelity, at higher per-request context in
long sessions. Nothing in 0037 established which side is better here; it stated
the trade and picked one.

**Honest note.** Neither value has been measured against
`references/agent-run-metrics.md`. This entry records the configuration in use
and the reasoning for keeping it, not a measurement — the measurement 0037
asked for still has not been run, and remains the thing that would settle the
window properly.

**Rejected — restore 0037's values (memory off, 200k).** This treats the live
settings as accidental drift. They are the configuration in daily use, and the
one substantive objection behind turning memory off has been answered by a
reference document that already assumes it is on. Reverting would have made the
repo internally consistent and externally wrong.

**Rejected — keep memory on but restore 200k.** Splitting the reversal needs a
reason to treat one value as deliberate and the other as drift, and there
isn't one: both were changed in the same direction, away from the same ADR, and
0037's own text concedes the window was a judgment call rather than a finding.

**Rejected — drop `docs/MEMORY.md` now that auto-memory is on.** Auto-memory is
machine-local and uncommitted. It survives neither a fresh clone nor a second
machine nor a collaborator, which is precisely the state `docs/MEMORY.md`
exists to hold. Enabling the low-stakes surface is not a reason to delete the
durable one.

**Revisit if** a bloated auto-memory index starts crowding session start (the
"memory index is over its read limit" symptom documented in
`references/documentation-practices.md`), or if run metrics over 5-10
representative tasks show the 500k window costing more in per-request context
than it saves in compaction fidelity.
