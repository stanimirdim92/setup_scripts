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

## Document set

Once a project outgrows a single README, split docs by role instead of
letting one file try to be all of them — mixing them buries rules in
changelog and decisions in rules.

| File | Holds |
|---|---|
| `README.md` | The system as it is now. |
| `CLAUDE.md` (project-level) | Rules — add one only once something already cost you something, not because it's "good practice." Name the failure it catches, same as above. |
| `docs/PATTERNS.md` | Recurring shapes in the codebase, and what's deliberately absent. |
| `docs/TECHNICAL_DECISIONS.md` | Why a choice was made, and what was rejected. |
| `docs/IDEAS.md` | Parking lot, plus a table of rejected candidates and why. |
| `docs/MEMORY.md` | Session state — the committed half of dual memory below. Read it first, update it last. |

Don't apply this to a small repo that doesn't need it — six files for a
project with one contributor and no history worth recording is the same
mistake as one file trying to hold everything.

## Dual memory

Two memory systems exist side by side and are not interchangeable, despite
sharing a name:

| | **Auto-memory** | **`docs/MEMORY.md`** |
|---|---|---|
| Written by | Claude, automatically | Whoever's working, deliberately |
| Lives in | `~/.claude/projects/<project>/memory/` — local to this machine | The repo itself — committed, git-tracked |
| Travels with | Nothing. A new machine or a `git clone` starts empty. | The repo. Every clone, every collaborator, every agent gets it. |
| Good for | Low-stakes continuity: preferences picked up mid-session, small facts worth not re-explaining tomorrow on this machine. | Anything that must survive a clone or be visible to someone else: why the last session ended where it did, what was measured, what's mid-flight. |

The failure mode this prevents: treating auto-memory as if it were durable
project state. It isn't committed, isn't shared, and isn't there on a fresh
clone or a different machine — so anything that actually matters to the
next session or the next person goes in `docs/MEMORY.md` explicitly, never
left to auto-memory to carry. Rule of thumb: if losing it on a new machine
would be a problem, it belongs in `docs/MEMORY.md`, not auto-memory.
