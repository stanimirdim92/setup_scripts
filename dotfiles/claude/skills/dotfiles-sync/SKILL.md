---
name: dotfiles-sync
description: How to add, edit, or relink files in this dotfiles/setup_scripts repo so dotfiles/tools/setup/link_dotfiles.sh and dotfiles/README.md's synced-files list stay correct. Use when adding a new file meant to be symlinked into $HOME, or when editing dotfiles/tools/setup/link_dotfiles.sh or dotfiles/README.md's Synced/Not-synced sections.
---

# Adding a new synced dotfile

1. Put the real file under `dotfiles/<tool>/<name>` (e.g.
   `dotfiles/claude/agents/foo.md`).
2. In `dotfiles/tools/setup/link_dotfiles.sh`, append the source to `SOURCES=(...)` and the
   destination to `DESTINATIONS=(...)` at the same index — the two arrays are
   paired by position. One pair per file, or one pair per directory if
   the whole directory should be symlinked as a unit (this is how `agents/`,
   `skills/`, `commands/`, `hooks/`, `references/`, and `docs/` are linked: as
   directories, not per-file, so new files inside them don't need a script
   change). `references/` specifically must land as a **sibling** of
   `skills/` under `~/.claude/`, not nested inside it — vendored skills
   reach it with a relative `../../references/...` path matching their
   upstream layout, and that only resolves one level up from `skills/`.
3. Update `dotfiles/README.md`:
   - Add the new path to the "Synced" list if it's meant to be portable
     across machines.
   - Add it to "Deliberately not synced" instead if it's machine-specific,
     holds secrets, or is runtime state (matches existing exclusions:
     `.credentials.json`, `~/.claude.json` MCP entries, `installed_plugins.json`,
     session/log directories).
   - If the new file is a skill, agent, or command, fold it into the
     relevant "Synced" bullet's prose list too (e.g. the `agents/` or
     `skills/` line enumerates what's inside, not just the directory path)
     — `dotfiles/claude/AGENTS.md` doesn't keep a separate skills-list
     section, so README's own bullets are the one place this needs to stay
     current.
4. **New Claude skill or command? Add its Codex adapter too.** Create
   `dotfiles/codex/skills/<name>/SKILL.md` by copying an existing adapter
   (same frontmatter `name`, the Claude skill's `description`, and a
   relative link to the shared body). Stage-style entry points that must
   only run when the user starts them also get an `agents/openai.yaml`
   with `allow_implicit_invocation: false`. Update dotfiles/README.md's adapter
   count ("all N local skills … and all M commands"), then run
   `python3 dotfiles/codex/install-skills.py --check`.
5. Re-run `./dotfiles/tools/setup/link_dotfiles.sh`. It prints the plan for every
   destination and asks before changing anything; `--dry-run` shows the plan
   and stops, `--yes` skips the prompt. Read the output: `ok <dest>` means
   already correct, `linked <dest> -> <src>` means newly linked, `backup
   <dest> -> <dest>.bak` means something real was in the way — check the
   `.bak` before deleting it, it may hold local settings not yet migrated
   into this repo. A `BACKUP` line in the plan is a real **directory** about
   to be moved aside whole; its contents do not merge with the repo's.
6. Because these are real symlinks, letting the app itself edit
   `~/.claude/settings.json`, `~/.claude/CLAUDE.md`, etc. (via `/model`, or
   any in-app edit) writes straight back into this repo. Run
   `git status`/`git diff` here afterward to see what changed, and commit
   deliberately rather than letting live edits sit uncommitted. The shared
   instructions file is `dotfiles/claude/AGENTS.md`, linked as
   `~/.claude/CLAUDE.md`, `~/.claude/AGENTS.md`, and `~/.codex/AGENTS.md` —
   an in-app edit to any of them changes Codex's rules too.
7. **Removing a synced path?** Don't just delete its `SOURCES`/`DESTINATIONS`
   pair — that leaves a dangling link on machines already set up. Move it to
   `RETIRED_DESTINATIONS`/`RETIRED_SOURCES` in `dotfiles/tools/setup/link_dotfiles.sh` so the
   next run retires the old link. Removed Codex adapters need no such entry:
   `install-skills.py` cleans up links to adapters that no longer exist.
   Codex TUI approvals stay in the local `~/.codex/rules/default.rules`;
   curated rules go in `dotfiles/codex/rules/harness.rules`
   (dotfiles/docs/adr/0062).
8. Never symlink `~/.claude.json` directly (whole-file) — it mixes MCP
   server config with per-project trust state and can carry OAuth tokens.
   Use `dotfiles/claude/mcp/setup.sh` (a script of `claude mcp add`
   commands) instead of syncing that file.
9. If a skill is pulled in from elsewhere rather than written from
   scratch, keep its license file on disk (e.g. `ADDYOSMANI_AGENT_SKILLS_LICENSE`)
   for as long as any of that source's content remains — removing the
   skill and removing its license are one action, not two. This repo
   doesn't currently keep a separate provenance log (source URL, commit,
   refresh command) for vendored skills; if that's ever wanted again,
   write a fresh one rather than assuming an old one still applies.
