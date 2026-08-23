# `docs/agents.md` moved to `dotfiles/claude/docs/`, now synced

**Decision.** `agents.md` (persona roster, orchestration shapes,
context-discipline, evidence/cost rules) moved from repo-root `docs/` to
`dotfiles/claude/docs/agents.md`, and `dotfiles/claude/docs/` is now
symlinked as a whole directory into `~/.claude/docs/` alongside
`agents/`, `skills/`, `commands/`, `hooks/`, and `references/` — per
direct instruction. This makes the persona/orchestration reference
available at runtime in every session on every machine, the same way
skills and agents already are, instead of living only in this specific
repo's own documentation tree.

This also cleaned up an accidental duplicate: a `dotfiles/claude/docs/agents.md`
already existed alongside the repo-root one from an earlier edit, and the
two had diverged (the repo-root copy kept receiving the latest rewrites —
`Layers`, `Built orchestration patterns`, `Context discipline`,
`agent-run-metrics.md` references — while the `dotfiles/claude/docs/`
copy was a stale snapshot from before that). Took the repo-root version's
content as canonical (it was the one actually being maintained), fixed
its persona-table links for the new location (`../agents/*.md`, not
`../dotfiles/claude/agents/*.md`), and deleted the repo-root file.

Repo-root `docs/` keeps everything that's specific to *this* repo and has
no reason to sync elsewhere: `docs/adr/*.md`, `docs/IDEAS.md`,
`docs/MEMORY.md`. Only `agents.md` moved, since it's operational
reference content like the personas/skills/commands it describes, not a
record of this repo's own build decisions.

Updated: `tools/link_dotfiles.sh` (new `docs/` directory link),
`README.md`'s synced-files list, `dotfiles-sync/SKILL.md`'s
whole-directory-sync enumeration, and `security-auditor.md`'s one live
cross-reference to the file (`CLAUDE.md`'s own mention already resolved
correctly, since it was already written as a bare `docs/agents.md`
relative to `CLAUDE.md`'s own location).

**Rejected — linking `agents.md` as a single file instead of the whole
`docs/` directory.** Matches the existing convention for `agents/`,
`skills/`, `commands/`, `hooks/`, `references/`: whole-directory sync
means a future second file under `dotfiles/claude/docs/` needs no
`link_dotfiles.sh` change, consistent with why those five are already
directories and not per-file links.
