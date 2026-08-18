# Replaced `llm-integration-reviewer` with the `llm-application-dev` plugin's builder trio

**Decision.** Dropped the first-party `llm-integration-reviewer` agent
and vendored `amoustakas/claude-code-plugins`' `llm-application-dev`
plugin in full instead: three agents (`ai-engineer`, `prompt-engineer`,
`vector-database-engineer`), its eight skills (`langchain-architecture`,
`rag-implementation`, `llm-evaluation`, `prompt-engineering-patterns`,
`embedding-strategies`, `similarity-search-patterns`,
`vector-index-tuning`, `hybrid-search-implementation`), and its three
commands (`/ai-assistant`, `/langchain-agent`, `/prompt-optimize`),
MIT-licensed under `dotfiles/claude/skills/SETH_HOBSON_LLM_APPLICATION_DEV_LICENSE`.
As with `code-reviewer`'s prior vendoring, the three agents' frontmatter
was adapted to this repo's convention rather than kept as-is: the
upstream files used `model: inherit` and no `tools`/`effort` fields at
all, which this repo's `0002-model-split-sonnet-orchestrator-tiered-subagents.md`
decision explicitly rejects ("give it a pinned model deliberately...
don't leave it on the default"). All three landed on
`model: claude-sonnet-5`, `effort: medium` — the same tier as
`executor`/`code-reviewer`, since these are routine-implementation builder
personas (direct-invocation, not dispatched unconditionally on every
`/build` run), not the architecturally-ambiguous-by-default case Opus is
reserved for. `ai-engineer` and `vector-database-engineer` kept the full
`Read, Edit, Write, Bash, Grep, Glob` set `executor` uses, since both
implement and run code; `prompt-engineer` dropped `Bash` — its own
skill's bundled `scripts/optimize-prompt.py` is a reference asset never
invoked from the skill's own instructions, and the persona's job
(display/iterate on prompt text, per its "Required Output Format"
section) doesn't call for executing anything.

This is a category swap, not a like-for-like replacement:
`llm-integration-reviewer` was a reviewer wired into `/build`/`/review`'s
automatic fan-out (`references/reviewer-triggers.md`), while the three
new agents are builders with no reviewer role. Rather than force one of
them into the old trigger slot with a reviewer's tools it doesn't have,
the trigger was dropped outright — `references/reviewer-triggers.md`,
`build.md`, `review.md`, and `docs/agents.md` no longer mention an
LLM-call-site reviewer at all. **Fail loud about the gap this leaves:**
`/build` and `/review` no longer automatically check LLM call sites for
unbounded cost/timeout, unvalidated model output reaching a record,
missing fallback paths, or prompt-injection surface — nothing currently
replaces that coverage. If a future session wants it back, that's a new
reviewer-shaped agent, not a repurposing of `ai-engineer`/
`prompt-engineer`/`vector-database-engineer`.
