# Global working rules

These are defaults for every project.

Project-local instructions override these rules only for their project scope
when they are more specific. Do not combine conflicting rules into a new
hybrid. Surface the conflict and follow the more specific project rule.

Project files define versions, commands, paths, architecture, dependencies,
and repository-specific conventions.

## Rules

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Ask only when ambiguity materially changes:
- external behavior or API contracts
- data/schema changes
- security or permissions
- destructive/irreversible actions
- architecture with multiple materially different options

Before implementing:
- For non-trivial work, plan before editing.
- Skip formal planning for obvious, localized changes.
- If a simpler approach exists, say so. Push back when warranted.
- If multiple interpretations materially affect the outcome, surface them.
- If ambiguity does not materially affect the outcome, state the assumption and proceed.
- Stop and ask only when the ambiguity meets the criteria above.
- *Catches: confidently building the wrong thing.*

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.
- *Catches: a 200-line solution to a 20-line problem.*

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- If a requested change requires broad refactoring, surface why before expanding scope. Do not expand scope silently.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.
*Catches: unrelated diffs that make review impossible.*

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals and use the cheapest meaningful
verification:

- behavior change → targeted test
- bug → reproduce first; add a regression test when practical
- refactor → existing tests before and after
- config/build change → validate, lint, or build
- docs → verify referenced commands, paths, and examples
- *Catches: declaring success without running anything.*

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

## 5. Deterministic Before Probabilistic

Use plain code when the same result can be expressed deterministically
with reasonable complexity.

Use LLMs only when the task genuinely requires semantic judgment,
interpretation, extraction, classification, ranking, or generation.

Never use an LLM for formatting, arithmetic, routing known values,
validation expressible as rules, or other deterministic transformations.
- *Catches: paying latency and nondeterminism for work `if`/`else` would do.*

## 6. Surface Conflicts, Don't Average Them

When two patterns in the codebase contradict each other, pick one and say why. Never blend them
into a third thing that matches neither.
- *Catches: inventing a novel pattern nobody chose.*

## 7. Fail Loud

Surface uncertainty, skipped steps, and unverified claims explicitly. Never let "I couldn't check this" read as "this works".
- *Catches: silent gaps the reader assumes were covered.*

## Session defaults

- **Caveman mode is on by default, every session** — don't wait for
  "/caveman lite" or "use caveman lite" to turn it on. Terse chat responses, full
  technical accuracy kept. Persists until "stop caveman"/"normal mode" is
  said. Per the `caveman` skill's own Boundaries section, this never
  touches what actually gets written — code, commits, docs, and
  third-party messages always stay normal prose regardless of mode.

## Context discipline

Keep tool output and resolved investigation out of active reasoning once it is no longer necessary.

Before a natural context boundary, ensure durable information is recorded
in the appropriate project document.

### Compact instructions

When compacting, preserve:
- current goal and success criteria
- explicit user decisions
- architectural decisions made this session
- changed files and why
- test/verification results
- unresolved blockers and remaining work

Drop:
- raw tool output
- rejected hypotheses
- superseded plans
- investigation already reduced to conclusions

## Project Structure

```
skills/<skill>/ → Core skills (SKILL.md per directory)
agents/         → Reusable agent personas
hooks/          → Session lifecycle hooks
commands/       → Slash commands (/spec, /plan, /build, /test, /review)
references/     → Supplementary checklists (definition-of-done, security-checklist, reviewer-triggers, documentation-practices) and templates/ (canonical spec/plan/task document shapes)
docs/           → Setup guides for different tools
```

## Agent orchestration defaults

These are cross-project invariants; detailed dispatch policy lives in the
commands that own it.

- Delegate bounded outcomes with acceptance criteria and explicit verification,
  not vague projects.
- Slash commands/user orchestration compose agents. Agents do not delegate to
  other agents.
- Reuse the same implementation agent across related tasks in one workstream
  when the harness supports resume.
- Never run multiple writing agents concurrently against the same checkout.
  Parallel writers require isolated worktrees/branches and genuinely independent
  workstreams.
- Keep subagent context selective: task-local rules, closest precedents, and
  relevant contracts/invariants. Prefer pointers over copied full documents.
- Completion claims require evidence: exact checks and outcomes; skipped checks
  stay explicitly unverified.
- Do not broaden tool permissions or seek secrets merely to avoid an orchestration
  boundary. Surface capabilities that require approval.

See `commands/build.md` and `docs/agents.md` for the operational shapes.

## Model policy

Agent definitions own their default `model:` selection.
Per-invocation overrides are reserved for work that genuinely needs a
different tier — see `commands/build.md`'s "Model tier per workstream" note.
    
## Ideas, decisions, and memory

`docs/IDEAS.md`
- unresolved possibilities only
- remove an idea once accepted or rejected

`docs/adr/*.md`
- decisions with architectural consequences
- capture the decision and its reasoning, plus every alternative seriously
  rejected (Decision/Rejected format — see `references/documentation-practices.md`)
- create only after a decision is actually made

`docs/MEMORY.md`
- current durable project facts needed by future sessions
- store conclusions, not investigation logs
- update when implementation changes the project's durable state

Full practice, format, and the difference between the three memory systems: `references/documentation-practices.md`.
