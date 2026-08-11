# Global working rules

Applies to every project unless a project's own CLAUDE.md/AGENTS.md says
otherwise — project files win on anything specific (versions, commands,
paths, package choices).

Rules 1-4 are Andrej Karpathy's, from his January 2026 post on recurring LLM
coding failure modes. Rules 5-7 are three of the community extensions
credited to @mnilax. Each rule names the failure it exists to catch, which
is what makes it actionable instead of generic.

## Karpathy's four

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

## Kept extensions

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

Don't apply this to a small repo that doesn't need it — six files for a
project with one contributor and no history worth recording is the same
mistake as one file trying to hold everything.

## Skills this machine ships

Skills/agents/commands symlinked from the `setup_scripts` dotfiles repo —
its README.md has the authoritative list. Excludes marketplace-plugin
skills (`superpowers`, `feature-dev`, etc.), which version independently.

- `dotfiles-sync` (meta) — add/edit/relink a file in that repo.
- `fastapi` — FastAPI conventions.
- SDLC skills, most aliased by a same-named command: `spec-driven-development`
  (`/spec`), `planning-and-task-breakdown` (`/plan`), `test-driven-development`
  (`/test`), `code-review-and-quality` (`/review`),
  `debugging-and-error-recovery`, `git-workflow-and-versioning`.
- `research` — spin off a background agent to chase primary sources and
  write cited findings to a file, instead of doing the reading inline.
- `handoff` — compact the current conversation into a document a fresh
  session picks up from; use before a long session's context runs out.
- Subagents: `infra-reviewer`, `security-reviewer` (first-party), vendored
  `code-reviewer` (five-axis review).

Update this list and README's together — `dotfiles-sync`'s checklist
covers both.

## Ideas vs. decisions

Both are records of things considered and rejected. They're not the same
document, because they answer different questions.

**`docs/IDEAS.md`** is for what's *not yet* decided — an explicitly
unjudged parking lot, so a half-formed thought stops occupying working
memory and stops getting rediscovered from scratch every few sessions.
- Add freely, one line if that's all there is. A half-formed idea recorded
  beats a good one forgotten.
- Say what makes it worth doing, not just what it is. "Add caching" is
  unactionable in six weeks; "answers repeat across tenants, so a
  semantic cache could cut model spend" is.
- Tag rough size (**S**/**M**/**L**) if it helps spot the cheap-and-valuable
  ones — gut-feel, not an estimate anyone should hold you to.
- **Idea graduates → move it into the real plan/implementation doc and
  delete it here.** Two copies of the same idea start disagreeing the
  moment one gets built and the other doesn't get updated.
- **Idea rejected → move it to a "Considered and rejected" table with the
  reason, don't just delete it.** This is the part that saves the most
  time: an idea with no recorded verdict comes back and gets re-litigated
  with no memory that it already lost once.
- A conditional/parked entry gets its condition written down explicitly
  ("revisit when X"), and gets revisited the moment X actually changes —
  not before, and not forgotten after.
- A stale entry gets struck through and marked for deletion at the next
  prune, not silently removed — the correction is worth as much as the
  original entry.

**`docs/TECHNICAL_DECISIONS.md`** is for what *was* decided — why the
system is built the way it is right now. Each entry states the decision,
the reasoning, and everything seriously considered and rejected along the
way, including — especially — choices reversed after contact with
reality; those are the ones worth rereading.
- Format per entry: **Decision.** statement and reasoning, then
  **Rejected — *(name the alternative).*** and why, repeated for every
  alternative that was seriously considered, not just the one that won.
- A rejection needs a reason concrete enough to stop the same alternative
  from being re-proposed with no new information — "didn't like it"
  doesn't qualify, a measurement or a specific broken assumption does
  (rule 14).
- Cross-reference the other docs instead of re-explaining them inline —
  "reconciliation is still open, see `docs/IDEAS.md`" instead of
  restating what's already recorded there. Two explanations of one fact
  drift apart; rule 6 again, applied to documentation instead of code.
- The difference from `docs/IDEAS.md` in one line: ideas are unjudged and
  unbuilt; decisions are judged and (mostly) built. An idea that ships
  moves out of `IDEAS.md`; a decision that gets reversed stays in
  `TECHNICAL_DECISIONS.md` as a rejected entry on the *new* decision, not
  a deletion of the old one — the reversal is exactly the part worth
  keeping.

## Memory: three systems, not one

Three memory systems exist side by side and are not interchangeable,
despite two of them sharing a name:

| | **Auto-memory** | **`docs/MEMORY.md`** | **Episodic memory** |
|---|---|---|---|
| Written by | Claude, automatically | Whoever's working, deliberately | Nobody — it indexes conversations you already had |
| Lives in | `~/.claude/projects/<project>/memory/` — local to this machine | The repo itself — committed, git-tracked | `~/.config/superpowers/` — local SQLite + vector index, local to this machine |
| Scope | This project, this machine | This project, every clone/collaborator | **Every** project, every Claude Code + Codex session, this machine |
| Retrieval | Auto-loaded at session start | Read deliberately (read first, update last) | Searched on demand, semantically, when something seems worth recalling |
| Good for | Low-stakes continuity: preferences picked up mid-session, small facts worth not re-explaining tomorrow. | Anything that must survive a clone or be visible to someone else: why the last session ended where it did, what was measured, what's mid-flight. | "Did I already solve something like this, in some other repo, months ago?" |

The failure mode this prevents: treating auto-memory or episodic memory as
if either were durable, shareable project state. Neither is committed,
neither survives a fresh clone or a different machine — so anything that
actually matters to the next session or the next person goes in
`docs/MEMORY.md` explicitly. Rule of thumb: if losing it on a new machine
would be a problem, it belongs in `docs/MEMORY.md`; if it's "have I hit
this before, somewhere else," reach for episodic memory (the
`episodic-memory` plugin — ask it to search past conversations rather than
re-deriving something you already worked out).
