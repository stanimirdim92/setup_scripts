---
name: dotfiles-sync
description: How to add, edit, or relink files in this dotfiles/setup_scripts repo so tools/link_dotfiles.sh and README.md's synced-files list stay correct. Use when adding a new file meant to be symlinked into $HOME, or when editing tools/link_dotfiles.sh or the README's Synced/Not-synced sections.
---

# Adding a new synced dotfile

1. Put the real file under `dotfiles/<tool>/<name>` (e.g.
   `dotfiles/claude/agents/foo.md`).
2. Add a `link "$DOTFILES/<tool>/<name>" "$HOME/<dest>"` line in
   `tools/link_dotfiles.sh` — one call per file, or one call per directory if
   the whole directory should be symlinked as a unit (this is how `agents/`,
   `skills/`, `commands/`, `hooks/`, and `references/` are linked: as
   directories, not per-file, so new files inside them don't need a script
   change). `references/` specifically must land as a **sibling** of
   `skills/` under `~/.claude/`, not nested inside it — vendored skills
   reach it with a relative `../../references/...` path matching their
   upstream layout, and that only resolves one level up from `skills/`.
3. Update `README.md`:
   - Add the new path to the "Synced" list if it's meant to be portable
     across machines.
   - Add it to "Deliberately not synced" instead if it's machine-specific,
     holds secrets, or is runtime state (matches existing exclusions:
     `.credentials.json`, `~/.claude.json` MCP entries, `installed_plugins.json`,
     session/log directories).
4. Re-run `./tools/link_dotfiles.sh` and read its output: `ok <dest>` means
   already correct, `linked <dest> -> <src>` means newly linked, `backup
   <dest> -> <dest>.bak` means something real was in the way — check the
   `.bak` before deleting it, it may hold local settings not yet migrated
   into this repo.
5. Because these are real symlinks, letting the app itself edit
   `~/.claude/settings.json`, `~/.claude/CLAUDE.md`, etc. (via `/model`, or
   any in-app edit) writes straight back into this repo. Run
   `git status`/`git diff` here afterward to see what changed, and commit
   deliberately rather than letting live edits sit uncommitted.
6. Never symlink `~/.claude.json` directly (whole-file) — it mixes MCP
   server config with per-project trust state and can carry OAuth tokens.
   Use `dotfiles/claude/mcp/setup.sh` (a script of `claude mcp add`
   commands) instead of syncing that file.
7. If a skill is pulled in from elsewhere rather than written from
   scratch, keep its license file on disk (e.g. `ADDYOSMANI_AGENT_SKILLS_LICENSE`)
   for as long as any of that source's content remains — removing the
   skill and removing its license are one action, not two. This repo
   doesn't currently keep a separate provenance log (source URL, commit,
   refresh command) for vendored skills; if that's ever wanted again,
   write a fresh one rather than assuming an old one still applies.
