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

Before every commit, inspect `git diff --cached` against the authorized files
and hunks; explicit `git add` paths do not exclude previously staged work.
Isolate the intended commit while preserving unrelated staged and unstaged
content, including changes in the same file. After committing, inspect the
resulting commit diff and remaining status before claiming completion.

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

## Session and context

- Caveman mode is the default chat style: terse responses, full technical
  accuracy. It never changes the quality/style of code, commits, docs, or
  third-party messages.
- Keep raw tool output and resolved investigation out of active context once the
  conclusion is recorded.
- Before compaction/session boundaries, preserve only goal/success criteria,
  user decisions, architectural decisions, changed files, verification evidence,
  blockers, and remaining work.

## Worktrees

Ticket-scoped work defaults to one isolated worktree per ticket.

- Start it with `claude --worktree <ticket>` (Codex: choose Worktree in a new
  chat). Both create a managed worktree branched from the remote default
  branch. `worktree.baseRef` selects the base: `fresh` (default) branches from
  the remote default branch, `head` from local `HEAD`.
- Claude Code places managed worktrees in `.claude/worktrees/`, which belongs in
  the project's `.gitignore`. Prefer that location: `.worktreeinclude`,
  subagent `isolation: worktree`, and the cleanup sweep only apply there.
- Gitignored files a worktree needs — `.env`, local config, credentials
  templates — go in a project-root `.worktreeinclude` using gitignore syntax.
  Claude Code and Codex both copy matching **ignored** files into every managed
  worktree; tracked files are never duplicated. A `WorktreeCreate` hook replaces
  this, so copy inside the hook script instead.
- A worktree is a fresh checkout: dependencies are not installed and no build
  or test command works until they are. Specification and planning work needs
  none of them; anything that builds, tests, or lints does.
- Use `git worktree add` directly only to check out an existing branch or to
  place a worktree outside the repository. Remove with `git worktree remove`,
  never `rm -rf` — that strands metadata, recoverable with `git worktree prune`.
- A branch lives in exactly one worktree. Free it with `git worktree remove`
  before checking it out elsewhere.
- Concurrency is bounded by the conditions in `commands/build.md`, not by a
  fixed count. Worktrees isolate git and files only; a database, queue, cache,
  or fixed port is still shared, and concurrent writers need their own instance
  of every mutable resource their checks touch.

## Agent orchestration

- Delegate bounded outcomes with acceptance criteria and verification.
- Commands/user orchestrate; personas do not dispatch personas.
- Reuse one implementation executor across related tasks in a workstream.
- Parallel writers require separate worktrees/branches; sequential is the
  token-efficient default.
- Give subagents small task packets: outcome, criteria, relevant rules,
  precedents, contracts, and verification. Prefer file pointers over copied docs.
- Do not widen tools/permissions or seek secrets to bypass an orchestration
  boundary.
- Completion claims require executed evidence.

Operational policy lives in `commands/build.md`, `commands/review.md`,
`references/verification-triggers.md`, and `docs/agents.md`.

## Models

Agent definitions own default models. Override upward only for materially
high-risk or ambiguous work where a wrong decision is expensive to undo.

## Durable project records

- `docs/IDEAS.md` — unresolved possibilities only.
- `docs/adr/*.md` — accepted architectural decisions and rejected alternatives.
- `docs/MEMORY.md` — current durable project facts and conclusions, not logs.
