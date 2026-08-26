# `unblock-triage` persona removed

**Decision.** Deleted `agents/unblock-triage.md` (Tech Lead Triage — sorted a
batch of blocked PRs/tickets into needs-you-now vs. delegate, ranked by blocking
radius). Its function is now covered by the pipeline's own per-gate blocked
contracts: `/test` returns **VERIFY BLOCKED**, `/review` returns **REVIEW
BLOCKED**, and `/ship` returns **SHIP BLOCKED**, each required to name the exact
blocking condition, the evidence distinguishing it from a product defect, and
the smallest action or decision needed to unblock. Triage of a block now belongs
to the gate that produced it, where the evidence already is.

It was also the only persona outside the
`/spec` → `/plan` → `/build` → `/test` → `/review` → `/ship` chain, and the only
one whose input was a batch of external items rather than a diff or a task
packet. No command dispatched it and no command composed it.

That isolation is what made it rot. Its two remaining references — the persona
table and the direct-invocation matrix in `docs/agents.md`, plus the description
in `README.md` — outlived the file itself by two commits before being caught,
because nothing in the pipeline exercised them.

`0002`'s mention of `unblock-triage` stays as written. That entry records which
personas its model-tier decision did *not* cover, which was true when it was
made; the model-split decision itself is unaffected and is not superseded here.

**Rejected — keep it as a direct-invocation-only persona.** Direct invocation
alone does not keep a persona correct. Nothing routes to it, nothing composes
it, and no gate's output feeds it, so its references drift silently (as they
already did) and its judgment is never exercised against a real pipeline state.

**Rejected — convert it to a skill.** Same problem in a different layer, and the
judgment it encoded is now distributed across the gates' BLOCKED contracts. A
skill restating that would be the duplicate rule 6 exists to prevent.

**Revisit if** batch triage across many independent blocked items becomes real
recurring work here. The gates' BLOCKED contracts handle one candidate at a
time; they are not a ranking mechanism across a queue.
