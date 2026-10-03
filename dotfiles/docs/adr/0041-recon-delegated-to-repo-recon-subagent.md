# Repository recon delegated to a `repo-recon` subagent

**Decision.** `/spec` and `/plan` no longer survey the repository in the main
context. Each dispatches one read-only `repo-recon` agent (`Read`, `Grep`,
`Glob`; `claude-sonnet-5`, `effort: medium`) for the affected area, which
returns a bounded pointer report: applicable instruction-source rules, the
owning module's conventions and architectural chain, test setup and
repository-defined commands, one to three closest precedents as `path:line`,
constraints and dependencies, plus explicit **No precedent found for** and
**Not surveyed** sections. A report already in the conversation is reused for
the same unchanged area, so `/plan` following `/spec` does not re-survey.

**Why.** Recon was the last unbounded cost in the pipeline and the surviving
half of the complaint that started this line of work — `/spec` and `/plan`
eating a third of a session. Everything else these commands do is bounded:
`/spec` reads one template and writes one file. Recon read an open-ended set of
rule files, sibling implementations, and module code, and every one of those
tool results stayed in the main context permanently. Subagent context is
isolated — only the final report returns — so the caller pays for conclusions
instead of for the files read to reach them.

[0037](0037-fixed-session-context-reduced.md) compressed the always-loaded
prompt baseline but deliberately left recon alone; this closes it. The larger
saving in [0035](0035-independent-verify-made-risk-triggered.md) came from *not*
spawning a subagent, and this one comes from spawning one — the principle is
the same either way: pay for a fresh context only where it is cheaper than the
alternative. Here the alternative is unbounded reads that never leave.

It also removes a duplicate. `spec-driven-development` and
`planning-and-task-breakdown` each carried their own copy of the
instruction-source list (`CLAUDE.md`, `AGENTS.md`, `.ai/rules/*.md`, …) with the
same "do not assume these paths exist" caveat. Discovery now lives once, in the
agent that performs it (rule 6).

**Report pointers, not contents.** The agent file makes this its central
constraint: a report that pastes file contents forfeits the entire benefit, so
it quotes only the two or three lines carrying a rule and gives `path:line` for
everything else. The caller then opens a named file only when a specific
unresolved question turns on that file's detail.

**The absence sections are the safety mechanism.** Delegating recon means the
caller never sees what the agent chose not to report, which is a rule 7 hazard:
silence would read as "nothing there." **No precedent found for** names the
aspects being decided without repository guidance — `/spec` must justify those
explicitly and `/plan` carries them as risks — and **Not surveyed** bounds what
the report can support, with a follow-up recon rather than an assumption when
it excludes something needed.

**Rejected — use the built-in `Explore` agent.** It does roughly this, but its
availability and output shape are the harness's, not this repo's, so neither
skill could rely on a stable contract. A first-party agent lets `/spec` and
`/plan` depend on named report sections, and pins the model per
[0002](0002-model-split-sonnet-orchestrator-tiered-subagents.md).

**Rejected — make recon risk-triggered like `/test`.** The trigger matrix in
[0035](0035-independent-verify-made-risk-triggered.md) works because `/build`
already produced verification evidence that is often sufficient. Nothing
produces recon evidence before `/spec`, and the case for skipping it — a
trivially scoped change — is the case where `spec-driven-development`'s own
"When NOT to use" says not to run `/spec` at all.

**Rejected — a shared recon reference file both skills point at instead of an
agent.** That deduplicates the instruction-source list but changes nothing about
where the reading happens; the reads would still land in the main context. The
cost is the survey, not the description of it.

**Rejected — let `/build`'s executor use it.** Executors work from a task packet
whose pointers the plan already resolved, and
[0029](0029-build-selects-executor-skills.md) keeps their capability surface
deliberately narrow. Recon belongs upstream, where its findings shape the spec
and plan that bound the executor.

**Revisit if** reports come back either too thin to spec from — forcing the
caller to re-read the area anyway, which would mean paying for both contexts —
or padded with file contents. Judge from `references/agent-run-metrics.md`
rather than from the report's apparent thoroughness.
