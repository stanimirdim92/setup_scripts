# Vendored `test-engineer` persona, `/test` now dispatches it instead of investigating inline

**Decision.** Vendored `addyosmani/agent-skills`' `test-engineer` agent into
`dotfiles/claude/agents/test-engineer.md` (MIT, same license already covering
`code-reviewer` — `dotfiles/claude/skills/ADDYOSMANI_AGENT_SKILLS_LICENSE`),
adapted the same way `code-reviewer` was: pinned `tools: Read, Edit, Write,
Bash, Grep, Glob`, `model: claude-sonnet-5`, `effort: medium` (upstream ships
neither `tools` nor `model`, which `0002` already rejected for agents in
this repo), and repointed the Composition section's `docs/agents.md` link
and `/ship`→`/test` reference at this repo's actual pipeline.

This closes a real structural gap a harness deep-review surfaced: `/build`
dispatches `executor` and `/review` dispatches reviewer personas, but `/test`
had no persona at all — its entire VERIFY workflow (read implementation,
inspect existing tests, add missing coverage, run broader verification) ran
inline in the orchestrating session, the exact pattern this repo's own
`docs/agents.md` "Context discipline" section says to avoid for anything
that would flood the main conversation with file contents it won't
reference again. `test-engineer` was the specific missing piece — the same
upstream collection that gave this repo `code-reviewer` also ships this
QA-focused persona (confirmed via the actual addyosmani/agent-skills
`docs/agents.md`, which lists it as the `/test`-wrapped persona there too),
just never vendored here.

Rewrote `commands/test.md` to match `build.md`/`review.md`'s shape:
`/test` resolves verification scope itself from task/spec docs and `/build`'s
completion report (not by re-reading the implementation), dispatches
`test-engineer` with a bounded task packet (acceptance criteria, implemented
behavior, regression surface, tests/commands already run — not the full spec
or plan), and issues VERIFY PASS/FAIL from `test-engineer`'s report rather
than from its own inline inspection. `test-engineer` does not decide the
verdict; a production defect it surfaces still routes back through `/build`,
unchanged from before.

Updated `dotfiles/claude/docs/agents.md`: added `test-engineer` to the
persona table, added a third orchestration-pattern section (`/test`: bounded
verifier dispatch) alongside `/build`'s bounded-writer and `/review`'s
read-only-fan-out shapes, and updated the direct-invocation/evidence/interop
sections that referenced the old inline-`/test` behavior. Updated `README.md`'s
agents inventory line.

**Rejected — writing a first-party verifier persona from scratch.** The
upstream persona already fits this repo's actual need almost exactly (test
strategy, coverage analysis, Prove-It pattern for bugs, right-test-level
guidance) and needed only the same tools/model adaptation every other
vendored agent here already gets — no reason to duplicate that effort.

**Rejected — keeping `/test`'s test-pyramid table as its own copy.**
`test-engineer`'s persona file already states the same "test at the lowest
level that captures the behavior" rule; `test.md` now says to rely on that
instead of restating the table, closing the exact duplicated-logic finding
the same deep review flagged (`/test`'s table vs. `test-driven-development`'s
own, verbatim).
