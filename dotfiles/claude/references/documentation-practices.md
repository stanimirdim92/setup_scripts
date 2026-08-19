# Documentation Practices

How this machine's sessions record project knowledge across two documents
that answer different questions, plus how the three memory systems in play
differ. Moved out of the global `CLAUDE.md` so it's still reachable on
demand without being force-loaded into every subagent's context — none of
this is operationally needed by a subagent implementing or reviewing one
task; it's for whoever is planning or documenting the work.

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

**`docs/adr/*.md`** is for what *was* decided — why the
system is built the way it is right now. Each entry states the decision,
the reasoning, and everything seriously considered and rejected along the
way, including — especially — choices reversed after contact with
reality; those are the ones worth rereading.
- Format per entry: **Decision.** statement and reasoning, then
  **Rejected — *(name the alternative).*** and why, repeated for every
  alternative that was seriously considered, not just the one that won.
- A rejection needs a reason concrete enough to stop the same alternative
  from being re-proposed with no new information — "didn't like it"
  doesn't qualify, a measurement or a specific broken assumption does.
- Cross-reference the other docs instead of re-explaining them inline —
  "reconciliation is still open, see `docs/IDEAS.md`" instead of
  restating what's already recorded there. Two explanations of one fact
  drift apart; rule 6 again, applied to documentation instead of code.
- The difference from `docs/IDEAS.md` in one line: ideas are unjudged and
  unbuilt; decisions are judged and (mostly) built. An idea that ships
  moves out of `docs/IDEAS.md`; a decision that gets reversed stays in
  `docs/adr/*.md` as a rejected entry on the *new* decision, not
  a deletion of the old one — the reversal is exactly the part worth
  keeping.
- This is a per-project convention, not unique to this repo. The
  `adr-recording` skill applies it in any project — numbering, the
  Decision/Rejected shape, index maintenance, and the no-silent-overwrite
  rule for reversals — so it doesn't have to be re-explained from scratch
  each time.

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

Don't relocate auto-memory's folder into the repo (`docs/memory/`,
`./memory/`, `.claude/memory/`) to "organize" it — that just commits
machine-local scratch into git, the exact thing this table exists to
prevent. It stays at its default path, untouched.

**Keeping auto-memory's `MEMORY.md` small:** Claude Code only loads the
first 200 lines / 25KB of it at session start; past that, content silently
never loads. Symptoms of a bloated one: the "memory index is over its read
limit" error, or Claude re-asking things it should already know.
- `MEMORY.md` itself stays an *index* — one line per fact, e.g.
  `- Build fails on M1 with mixed npm+yarn lockfiles → debugging.md#node-arch`.
- Move anything longer than a line into a topic file in the same
  `memory/` directory (`debugging.md`, `api-conventions.md`, ...). Topic
  files aren't loaded at startup — Claude opens them on demand — so
  nothing is lost by moving detail out, only by leaving it inline.
- Drop or merge stale entries instead of letting them accumulate.
- To check size or trim by hand: run `/memory` in a session in that repo,
  pick the auto-memory folder, and edit `MEMORY.md` and its topic files
  directly (plain markdown) — or ask Claude to do the trim for you.

**Moving a project to a different machine:** auto-memory doesn't come with
it — by design, not by bug (see the table above). `autoMemoryDirectory`
only accepts an absolute path, so it can't be pointed at something inside
the repo and expected to travel with a clone. Don't fight this. Instead,
while trimming auto-memory, promote any entry that would actually be
missed on a new machine into `docs/MEMORY.md` (committed, travels with the
repo) and delete it from auto-memory once promoted — same
graduate-or-reject discipline `docs/IDEAS.md` uses.
