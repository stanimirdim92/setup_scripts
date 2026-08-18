# Global working rules

Applies to every project unless a project's own CLAUDE.md/AGENTS.md says
otherwise — project files win on anything specific (versions, commands,
paths, package choices).

Each rule names the failure it exists to catch, which
is what makes it actionable instead of generic.

## Rules

1. **Think before coding.** Plan before editing. Surface assumptions,
   tradeoffs, and genuine confusion instead of proceeding silently past them.
   *Catches: confidently building the wrong thing.*

2. **Simplicity first.** Smallest change that works. No speculative
   features, no premature abstraction, no flexibility nobody asked for.
   *Catches: a 200-line solution to a 20-line problem.*

3. **Surgical changes.** Touch only what the task names. Don't refactor
   working code just because you happened to read it.
   *Catches: unrelated diffs that make review impossible.*

4. **Goal-driven execution.** Define "done" up front as something
   verifiable, then loop until it's confirmed — not until it looks right.
   *Catches: declaring success without running anything.*

5. **Use the model only for judgment calls.** Reserve LLM calls for
   classification, extraction, and drafting. Deterministic operations get
   plain code.
   *Catches: paying latency and nondeterminism for work `if`/`else` would do.*

6. **Surface conflicts, don't average them.** When two patterns in the
   codebase contradict each other, pick one and say why. Never blend them
   into a third thing that matches neither.
   *Catches: inventing a novel pattern nobody chose.*

7. **Fail loud.** Surface uncertainty, skipped steps, and unverified claims
   explicitly. Never let "I couldn't check this" read as "this works".
   *Catches: silent gaps the reader assumes were covered.*

## Session defaults

- **Caveman mode is on by default, every session** — don't wait for
  "/caveman lite" or "use caveman lite" to turn it on. Terse chat responses, full
  technical accuracy kept. Persists until "stop caveman"/"normal mode" is
  said. Per the `caveman` skill's own Boundaries section, this never
  touches what actually gets written — code, commits, docs, and
  third-party messages always stay normal prose regardless of mode.
- **Run `/compact` mid-session, not only at the end.** Don't wait for
  auto-compact or a natural stopping point — once a chunk of resolved
  work (a finished sub-task, a long tool-output trail) doesn't need to
  stay verbatim, compact it out. Keeps the cached prefix smaller and
  cache reads cheaper on every subsequent call (rule 5's reasoning,
  applied to context size instead of tool choice).

## Project Structure

```
skills/       → Core skills (SKILL.md per directory)
agents/       → Reusable agent personas
hooks/        → Session lifecycle hooks
commands/     → Slash commands (/spec, /plan, /build, /test, /review)
references/   → Supplementary checklists (definition-of-done, security-checklist, reviewer-triggers, documentation-practices) and templates/ (canonical spec/plan/task document shapes)
docs/         → Setup guides for different tools
```

## Model split: Sonnet orchestrator, tiered subagents

Every dispatched agent pins a specific `model:` version explicitly in its
own frontmatter. A per-invocation `model` override can still bump a specific workstream or
review up to Opus when it's architecturally ambiguous or high-stakes —
see `commands/build.md`'s "Model tier per workstream" note.

## Ideas, decisions, and memory

This machine's sessions keep undecided ideas in `docs/IDEAS.md`, decided-
and-mostly-built choices in `docs/TECHNICAL_DECISIONS.md`, and durable
project state in `docs/MEMORY.md` — distinct from auto-memory (this
machine only) and episodic memory (searched across every project). Full
practice, format, and the difference between the three memory systems:
`references/documentation-practices.md`.
