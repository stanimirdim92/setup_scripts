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

## Skills this machine ships

Skills/agents/commands symlinked from the `setup_scripts` dotfiles repo —
its README.md has the authoritative list. Excludes marketplace-plugin
skills (`superpowers`, `feature-dev`, etc.), which version independently.

- `dotfiles-sync` (meta) — add/edit/relink a file in that repo.
- `fastapi` — FastAPI conventions.
- SDLC skills, most aliased by a same-named command: `spec-driven-development`
  (`/spec`), `planning-and-task-breakdown` (`/plan`), `git-workflow-and-versioning`,
  `incremental-implementation` (`/build`, alongside `executor` below).
  `code-review-and-quality` is no longer `/review`'s entry point — `/review`
  dispatches the `code-reviewer` agent directly now, same as `/build`'s
  review step; the skill is kept only as a reference for its
  large-diff-splitting-strategy content, linked from `git-workflow-and-
  versioning` and `references/definition-of-done.md`. `/test` and debugging
  route to the `superpowers` plugin's own skills instead of a vendored copy
  — see "Superpowers overlap" below.
- `ticket-breakdown-and-delegation` — extends `planning-and-task-breakdown`
  with sizing per assignee's level when a ticket splits across more than
  one person, not just by scope.
- `research` — spin off a background agent to chase primary sources and
  write cited findings to a file, instead of doing the reading inline.
- `handoff` — compact the current conversation into a document a fresh
  session picks up from; use before a long session's context runs out.
- `caveman` — terse chat-only response mode (drops articles/filler/
  hedging, keeps every technical detail exact). `/caveman [lite|full|
  ultra|wenyan-*|off]`. Never touches what actually gets written —
  code, commits, docs, and third-party messages stay normal prose
  regardless of mode; see its own SKILL.md's Boundaries section.
- Subagents: `infra-reviewer`, `security-reviewer`,
  `distributed-systems-reviewer` (timeouts, idempotent retries, backoff,
  circuit breakers, backpressure, checkpointing — for anything crossing a
  process/network/queue boundary), `llm-integration-reviewer` (cost/timeout
  ceilings, output validation before a model response is trusted, malformed-
  output handling, fallback path, prompt-injection surface — for anything
  calling a model), `unblock-triage` (given a batch of blocked PRs/tickets,
  sorts which need this person's own judgment call vs. which can be
  delegated, ranked by blocking radius) (all first-party), vendored
  `code-reviewer` (five-axis review), first-party `executor` (dispatched
  by `/build` to implement one planned task end-to-end; never invokes
  another agent — review and the go/no-go call stay with the orchestrator).

## Superpowers overlap

`/test` and debugging route to the `superpowers` plugin's own skills, not
a vendored copy; `/spec` and `/plan` each open with a compositional
`superpowers` step before their own vendored skill runs. Full reasoning
and rejected alternatives: `docs/TECHNICAL_DECISIONS.md`.

## Model split: Sonnet orchestrator, tiered subagents

Every dispatched agent pins a specific `model:` version explicitly in its
own frontmatter — never the floating `opus`/`sonnet` alias, never left
unset (which silently falls back to whatever the orchestrator is
running on). `executor` and `code-reviewer` (dispatched on every
`/build` run) pin `claude-sonnet-5`; `security-reviewer`,
`distributed-systems-reviewer`, `infra-reviewer`,
`llm-integration-reviewer`, and `unblock-triage` pin `claude-opus-4-8`. A
per-invocation `model` override can still bump a specific workstream or
review up to Opus when it's architecturally ambiguous or high-stakes —
see `build.md`'s "Model tier per workstream" note. Full reasoning and
rejected alternatives: `docs/TECHNICAL_DECISIONS.md`. Update that doc,
this list, and README's together when agents change — `dotfiles-sync`'s
checklist covers all three.

## Ideas, decisions, and memory

This machine's sessions keep undecided ideas in `docs/IDEAS.md`, decided-
and-mostly-built choices in `docs/TECHNICAL_DECISIONS.md`, and durable
project state in `docs/MEMORY.md` — distinct from auto-memory (this
machine only) and episodic memory (searched across every project). Full
practice, format, and the difference between the three memory systems:
`dotfiles/claude/references/documentation-practices.md`.
