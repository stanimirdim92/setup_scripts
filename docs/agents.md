# Agent Personas

Specialist personas that play a single role with a single perspective. Each persona is a Markdown file consumed as a system prompt by your harness (Claude Code, Cursor, Copilot, etc.).

| Persona | Role | Best for |
|---------|------|----------|
| [code-reviewer](../dotfiles/claude/agents/code-reviewer.md) | Senior Staff Engineer | Five-axis review before merge |
| [security-auditor](../dotfiles/claude/agents/security-auditor.md) | Security Engineer | Vulnerability detection, OWASP-style audit |
| [distributed-systems-reviewer](../dotfiles/claude/agents/distributed-systems-reviewer.md) | Distributed Systems Engineer | Reliability/consistency review for anything crossing a process/network/queue boundary |
| [executor](../dotfiles/claude/agents/executor.md) | Implementation Engineer | Executes one planned task end-to-end, resumable across a workstream's later tasks |
| [unblock-triage](../dotfiles/claude/agents/unblock-triage.md) | Tech Lead Triage | Sorting a batch of blocked items into needs-your-judgment vs. delegate |

## How personas relate to skills and commands

Three layers, each with a distinct job:

| Layer | What it is | Example | Composition role |
|-------|-----------|---------|------------------|
| **Skill** | A workflow with steps and exit criteria | `code-review-and-quality` | The *how* — invoked from inside a persona or command |
| **Persona** | A role with a perspective and an output format | `code-reviewer` | The *who* — adopts a viewpoint, produces a report |
| **Command** | A user-facing entry point | `/review`, `/build` | The *when* — composes personas and skills |

The user (or a slash command) is the orchestrator. **Personas do not call other personas.** Skills are mandatory hops inside a persona's workflow.

## When to use each

### Direct persona invocation
Pick this when you want one perspective on the current change and the user is in the loop.

- "Review this PR" → invoke `code-reviewer` directly
- "Are there security issues in `auth.ts`?" → invoke `security-auditor` directly

### Slash command (single persona behind it)
Pick this when there's a repeatable workflow you'd otherwise re-explain every time.

- `/test` → the independent VERIFY gate after `/build`; runs/adds test coverage against acceptance criteria and reports VERIFY PASS or VERIFY FAIL — not a persona wrapper, `/build`'s dispatched `executor` already owns TDD execution discipline directly (see `agents/executor.md`)

### Slash command (orchestrator — fan-out)
Pick this only when **independent** investigations can run against the same diff and produce reports that a single agent then merges.

- `/review` → the independent REVIEW gate after `/test`; dispatches `code-reviewer` always, plus `security-auditor` / `distributed-systems-reviewer` per `references/reviewer-triggers.md`, capped at 2 reviewers running at once (never all of them concurrently, even on a diff that trips every trigger), then issues the GO/NO-GO verdict

This is the only orchestration pattern this repo has built. See `commands/review.md`'s dispatch/concurrency/verdict sections for the actual rules — don't re-derive them here. `/build` only implements (see `commands/build.md`) — it explicitly does not review, verify, or issue a verdict; those gates live downstream in `/test` and `/review`.

## Decision matrix

```
Is the work a single perspective on a single artifact?
├── Yes → Direct persona invocation
└── No  → Are the sub-tasks independent (no shared mutable state, no ordering)?
         ├── Yes → Slash command with fan-out (/review's dispatch step)
         └── No  → Sequential slash commands run by the user (/spec → /plan → /build → /test → /review)
```

## Worked example: valid orchestration

`/review`'s dispatch step, once `/test` has reported VERIFY PASS:

```
/review (dispatch step)
  ├── code-reviewer      → review report          (always runs)
  ├── security-auditor   → audit report            (if a trigger matched)
  └── distributed-systems-reviewer → reliability report (if a trigger matched)
                  ↓
     batched 2-at-a-time, not all at once
                  ↓
        merge phase (main agent) — each axis reported under its own
        heading, never blended into one ranked list
                  ↓
        go/no-go decision
```

Why this works:
- Each reviewer operates on the same diff but produces a **different perspective**
- They have no dependencies on each other, and review blind to each other's output — an axis that can see another's findings starts anchoring on them
- Each runs in a fresh context window → main session stays uncluttered
- The merge step is small and benefits from full context, so it stays in the main agent

Why it's capped at 2, not fully parallel: `references/reviewer-triggers.md` can match 3+ specialists on a high-risk diff, but this repo's own cost-gate decision (see `docs/adr/0004-reviewer-batch-cap-no-high-risk-exception.md`) treats predictable spend as worth more than a few saved wall-clock minutes — a high-risk diff earns every reviewer's pass, just in sequential batches of 2, not a faster concurrent burn. That cap and the trigger-matrix dispatch originated inside `/build`'s own review step; both moved to `/review` when the pipeline split implementation from verification/review (see `docs/adr/0020-build-test-review-pipeline-split.md`) — the rule itself didn't change, just which command enforces it.

## Worked example: invalid orchestration (do not build this)

A `meta-orchestrator` persona whose job is "decide which other persona to call":

```
/work-on-pr → meta-orchestrator
                  ↓ (decides "this needs a review")
              code-reviewer
                  ↓ (returns)
              meta-orchestrator (paraphrases result)
                  ↓
              user
```

Why this fails:
- Pure routing layer with no domain value
- Adds two paraphrasing hops → information loss + 2× token cost
- The user already knows they want a review; let them call `/review` directly
- Replicates work that slash commands already do

## Rules for personas

1. A persona is a single role with a single output format. If you find yourself adding a second role, create a second persona.
2. **Personas do not invoke other personas.** Composition is the job of slash commands or the user. On Claude Code this is also a hard platform constraint — *"subagents cannot spawn other subagents"* — so the rule is enforced for you.
3. A persona may invoke skills (the *how*).
4. Every persona file ends with a "Composition" block stating where it fits.

## Claude Code interop

The personas in this repo are designed to work as Claude Code subagents without modification:

- **As subagents:** auto-discovered when this plugin is enabled (no path config needed). Use the Agent tool with `subagent_type: code-reviewer` (or `security-auditor`, `distributed-systems-reviewer`). `/review`'s dispatch step is the working example.
- **As Agent Teams teammates** (experimental, requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`): reference the same persona name when spawning a teammate. The persona's body is **appended to** the teammate's system prompt as additional instructions (not a replacement), so your persona text sits on top of the team-coordination instructions the lead installs (SendMessage, task-list tools, etc.). Not currently used by any command in this repo — noted here as a platform capability, not an active pattern.

Subagents only report results back to the main agent. Agent Teams let teammates message each other directly. This repo's own fan-out (`/review`'s dispatch step) only needs the subagent shape — each reviewer reports back independently and the orchestrator merges, no teammate-to-teammate messaging required.

Plugin agents do not support `hooks`, `mcpServers`, or `permissionMode` frontmatter — those fields are silently ignored. Avoid relying on them when authoring new personas here.

## Adding a new persona

1. Create `agents/<role>.md` with the same frontmatter format used by existing personas (`name`, `description`, `tools`, `model`, `effort`).
2. Define the role, scope, output format, and rules.
3. Add a **Composition** block at the bottom (Invoke directly when / Invoke via / Do not invoke from another persona).
4. Add the persona to the table at the top of this file.
5. If the persona enables a new orchestration pattern, document it in this file's "When to use each" / "Worked example" sections — don't invent a pattern inside the persona file itself, and don't reference a pattern-catalog file that doesn't exist yet.
