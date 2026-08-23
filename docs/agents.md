# Agent Personas

Specialist personas play one role with one perspective. Each persona is a
Markdown system prompt consumed by the harness.

| Persona | Role | Best for |
|---------|------|----------|
| [code-reviewer](../dotfiles/claude/agents/code-reviewer.md) | Senior Staff Engineer | Five-axis review before merge |
| [security-auditor](../dotfiles/claude/agents/security-auditor.md) | Security Engineer | Vulnerability detection and security audit |
| [distributed-systems-reviewer](../dotfiles/claude/agents/distributed-systems-reviewer.md) | Distributed Systems Engineer | Reliability/consistency review across process/network/queue boundaries |
| [executor](../dotfiles/claude/agents/executor.md) | Implementation Engineer | Executes one planned task end-to-end; resumable across a workstream |
| [unblock-triage](../dotfiles/claude/agents/unblock-triage.md) | Tech Lead Triage | Sorts a batch of blocked items by who actually needs to decide |

## Layers

| Layer | What it owns | Example |
|-------|--------------|---------|
| **Skill** | Reusable methodology / the *how* | `planning-and-task-breakdown` |
| **Persona** | Role, perspective, output contract / the *who* | `code-reviewer` |
| **Command** | User-facing orchestration / the *when* | `/build`, `/review` |

Skills are not automatically mandatory hops inside every persona. Invoke a skill
when the runtime/tooling supports it. A constrained persona may inline the
required discipline instead; `executor` does this for incremental implementation
and TDD because it intentionally has no `Skill` tool.

The user or a slash command is the orchestrator. **Personas do not call other
personas.**

## Built orchestration patterns

This repo deliberately has two different orchestration shapes.

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
- `/build` does not independently VERIFY, review, or issue GO/NO-GO.

Operational source of truth: `dotfiles/claude/commands/build.md`.

### 2. `/review`: independent read-only fan-out

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
         GO / NO-GO
```

Reviewers do not see one another's output before forming their own judgment.
`references/reviewer-triggers.md` is the single trigger matrix.

Operational source of truth: `dotfiles/claude/commands/review.md`.

## Direct persona invocation

Use direct invocation when the user wants one perspective on one artifact.

- "Review this PR" → `code-reviewer`
- "Security review this auth change" → `security-auditor`
- "Check this worker for retry/idempotency problems" → `distributed-systems-reviewer`
- Batch triage for a lead → `unblock-triage`

`executor` is the exception: it is dispatched through `/build`, not used as a
free-form coding assistant.

## Decision matrix

```text
Need implementation?
├── Planned bounded task(s)
│    └── /build → workstreams → executor/resume
└── Not planned / ambiguous
     └── /spec or /plan first

Need independent judgment on an integrated change?
├── One requested specialist perspective → invoke that reviewer directly
└── Shipping review gate → /review fan-out after VERIFY PASS
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

See `dotfiles/claude/skills/context-engineering/SKILL.md`.

## Evidence and cost

Agent completion is not evidence by itself.

Implementation reports include exact verification commands and outcomes;
unverified checks remain explicit. `/test` independently verifies acceptance
criteria; `/review` independently judges the integrated diff.

Use the configured model default for routine work. Override upward only when the
specific workstream/review genuinely needs the reasoning tier.

Track actual run signals defined in
`dotfiles/claude/references/agent-run-metrics.md`; never estimate unavailable
token/cost/time data.

## Rules for personas

1. One persona = one role and one output contract.
2. Personas do not invoke other personas.
3. A persona may invoke skills only when its runtime/tool set supports that.
4. Constrained personas may inline required methodology when that constraint is
   deliberate and documented.
5. Every persona file ends with a Composition block describing where it fits.
6. Writing personas should receive bounded scope and explicit verification.
7. Read-only fan-out is easier to parallelize than writing; shared mutable state
   changes the concurrency rule.

## Claude Code interop

These personas are compatible with Claude Code subagents.

- `/build` uses `executor` as a resumable implementation subagent.
- `/review` uses reviewer subagents as independent read-only fan-out.
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
