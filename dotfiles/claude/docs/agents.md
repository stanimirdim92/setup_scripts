# Agent Personas

Specialist personas play one role with one perspective. Each persona is a
Markdown system prompt consumed by the harness.

| Persona | Role | Best for |
|---------|------|----------|
| [code-reviewer](../agents/code-reviewer.md) | Senior Staff Engineer | Five-axis review before merge |
| [security-auditor](../agents/security-auditor.md) | Security Engineer | Vulnerability detection and security audit |
| [distributed-systems-reviewer](../agents/distributed-systems-reviewer.md) | Distributed Systems Engineer | Reliability/consistency review across process/network/queue boundaries |
| [executor](../agents/executor.md) | Implementation Engineer | Executes one planned task end-to-end; resumable across a workstream |
| [test-engineer](../agents/test-engineer.md) | QA Engineer | Test strategy, coverage analysis, Prove-It pattern for bugs |

## Layers

| Layer | What it owns | Example |
|-------|--------------|---------|
| **Skill** | Reusable methodology / the *how* | `planning-and-task-breakdown` |
| **Persona** | Role, perspective, output contract / the *who* | `code-reviewer` |
| **Command** | User-facing orchestration / the *when* | `/build`, `/review`, `/ship` |

Skills are not automatically mandatory hops inside every persona. Invoke a skill
when the runtime/tooling supports it. `/build` explicitly selects a compact
`executor-development-discipline` skill for every fresh executor; the executor
definition preloads it at startup. `/build` adds only task-specific skills whose
methodology is materially required. Executors do not discover skills
autonomously.

The user or a slash command is the orchestrator. **Personas do not call other
personas.**

## Built orchestration patterns

This repo deliberately has four different orchestration shapes.

### 1. `/build`: bounded writer orchestration

`/build` dispatches one `executor` per workstream and resumes that executor for
later tasks in the same workstream.

```text
Task 1 ─┐
Task 2 ─┼─ Workstream A → executor A → resume A → resume A
Task 3 ─┘

Task 4 ─┐
Task 5 ─┴─ Workstream B → executor B
```

Rules:

- tasks inside a workstream are sequential;
- related tasks reuse context instead of paying fresh discovery cost;
- current policy allows only **one active writing executor** at a time;
- multiple writers may overlap only with isolated worktrees/branches and
  genuinely independent, dependency-ready workstreams;
- integration is sequential even if implementation is later parallelized;
- executor reports implementation + test/verification evidence, then stops;
- a fresh executor starts with `executor-development-discipline` preloaded,
  while a resumed executor reuses it and invokes only newly selected
  task-specific skills;
- `/build` does not independently VERIFY, review, or issue GO/NO-GO.

Operational source of truth: `commands/build.md`.

### 2. `/test`: bounded verifier dispatch

After `/build` completes, `/test` resolves verification scope itself (from
task/spec docs and `/build`'s completion report, not by re-reading the
implementation) and dispatches one `test-engineer` with a bounded task
packet to do the detailed inspection.

```text
/build completes
     ↓
/test resolves scope (acceptance criteria, risk areas, tests already added)
     ↓
   test-engineer → inspects, adds missing tests, runs verification
     ↓
/test issues VERIFY PASS / VERIFY FAIL / VERIFY BLOCKED from the report
```

`test-engineer` does not decide the verdict; it reports coverage findings and
verification evidence. A production defect found during verification goes
back through `/build`, not fixed inline by `/test` or `test-engineer`.

Operational source of truth: `commands/test.md`.

### 3. `/review`: independent read-only fan-out

After `/test` reports VERIFY PASS, `/review` dispatches independent reviewers
against the same integrated diff.

```text
/review
  ├── code-reviewer                    (always)
  ├── security-auditor                 (triggered)
  └── distributed-systems-reviewer     (triggered)
             ↓
      max 2 concurrently
             ↓
     reports stay separate
             ↓
       findings only
```

Reviewers do not see one another's output before forming their own judgment.
`references/reviewer-triggers.md` is the single trigger matrix.

`/review` stops at findings. The verdict belongs to `/ship`.

Operational source of truth: `commands/review.md`.

### 4. `/ship`: synthesis gate, no dispatch

After `/review` reports, `/ship` is the only gate that issues a verdict. It
dispatches nobody.

```text
/test evidence ─┐
                ├─ /ship synthesizes → GO / NO-GO + rollback plan
/review findings┘
        +
  uncovered axes (a11y, infrastructure, documentation)
  verified directly in the main context
```

Rules:

- no persona dispatch — a missing required reviewer is a `/review` gap, not a
  second dispatch path;
- unresolved Critical finding → default NO-GO, user-acceptable only explicitly;
- no GO without a concrete rollback plan;
- fixes return through `/build`, then re-enter `/test`;
- release mechanics come from `skills/git-workflow-and-versioning`.

This is why `/ship` is not upstream's `/ship`: upstream fans out
`code-reviewer`/`security-auditor`/`test-engineer` in parallel, which here
would be a second orchestration path to the personas `/test` and `/review`
already own.

Operational source of truth: `commands/ship.md`.

## Direct persona invocation

Use direct invocation when the user wants one perspective on one artifact.

- "Review this PR" → `code-reviewer`
- "Security review this auth change" → `security-auditor`
- "Check this worker for retry/idempotency problems" → `distributed-systems-reviewer`
- "Design tests for this" / "what coverage is missing here?" → `test-engineer`

`executor` is the exception: it is dispatched through `/build`, not used as a
free-form coding assistant. `test-engineer` is dispatched through `/test` for
the VERIFY gate, but also answers direct test-design/coverage-analysis
requests outside that pipeline.

## Decision matrix

```text
Need implementation?
├── Planned bounded task(s)
│    └── /build → workstreams → executor/resume
└── Not planned / ambiguous
     └── /spec or /plan first

Need independent judgment on an integrated change?
├── One requested specialist perspective → invoke that reviewer directly
└── Review gate → /review fan-out after VERIFY PASS

Need a go/no-go on shipping it?
└── /ship after /review — synthesis only, no dispatch
```

Do not add a `meta-orchestrator` persona whose only job is deciding which persona
to call. Routing belongs in commands; a routing-only persona adds context,
latency, paraphrasing loss, and cost without domain value.

## Context discipline

A subagent should receive a **task packet**, not the parent conversation.

For implementation this normally means:

- outcome;
- acceptance criteria;
- dependencies/workstream;
- expected scope;
- verification;
- applicable rule/module pointers;
- one or two closest precedents;
- relevant shared contract/invariant.

Do not copy the full spec/plan into every executor. Reviewers get even less:
integrated diff, one-line goal, and relevant acceptance criteria.

See `skills/context-engineering/SKILL.md`.

## Evidence and cost

Agent completion is not evidence by itself.

Implementation reports include exact verification commands and outcomes;
unverified checks remain explicit. `/test` dispatches `test-engineer` to
independently verify acceptance criteria; `/review` independently judges the
integrated diff; `/ship` issues the verdict from both.

Use the configured model default for routine work. Override upward only when the
specific workstream/review genuinely needs the reasoning tier.

Track actual run signals defined in
`references/agent-run-metrics.md`; never estimate unavailable
token/cost/time data.

## Rules for personas

1. One persona = one role and one output contract.
2. Personas do not invoke other personas.
3. A persona may invoke skills only when its runtime/tool set supports that.
4. A command that dispatches a skill-capable persona selects the permitted
   skills; the persona does not browse the catalog or broaden its own role.
5. Every persona file ends with a Composition block describing where it fits.
6. Writing personas should receive bounded scope and explicit verification.
7. Read-only fan-out is easier to parallelize than writing; shared mutable state
   changes the concurrency rule.

## Claude Code interop

These personas are compatible with Claude Code subagents.

- `/build` uses `executor` as a resumable implementation subagent.
- `/test` uses `test-engineer` as a bounded verifier subagent.
- `/review` uses reviewer subagents as independent read-only fan-out.
- `/ship` uses no subagents; it synthesizes the earlier gates' reports.
- Subagents report back to the main agent; they do not spawn subagents.
- Agent Teams can support teammate-to-teammate communication, but no current
  command depends on that experimental capability.
- Plugin-agent frontmatter should not rely on unsupported `hooks`, `mcpServers`,
  or `permissionMode` behavior.

## Adding a persona

1. Create `agents/<role>.md` with `name`, `description`, `tools`, `model`, and
   `effort`.
2. Define one role, its scope, output contract, and stop conditions.
3. Give it the minimum tools needed for that role.
4. Add a Composition block.
5. Add it to the table above.
6. If it creates a new orchestration shape, document the command-level policy
   here and record a durable architectural decision when warranted.
