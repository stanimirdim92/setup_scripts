# Codex rules: a curated synced file, separate from the approvals file

**Decision.** Sync `dotfiles/codex/rules/harness.rules` to
`~/.codex/rules/harness.rules` and stop syncing `~/.codex/rules/default.rules`.
Codex loads every `*.rules` file in `~/.codex/rules/` and applies the strictest
matching decision, but it writes the approvals clicked in the TUI to
`default.rules`. That file was a symlink into this repository, so every one-off
approval became a committed rule.

**Why now — a recurrence.** [0044](0044-config-security-hardening-pass.md)
removed blanket `sed` and approvals left behind by other projects. By
`593f6d4` the file had grown back to 32 rules: blanket `sed -n` again (GNU sed's
`w` and `e` commands write files and run commands, so it allows arbitrary
execution), `rm -rf` on an image-generation output directory, and eight rules
hard-coded to one user's `$HOME`, including whole `bash -lc` image-generation
pipelines. The cleanup was right; the file layout guaranteed it would not last.

**Decision.** `harness.rules` keeps only rules that are generic across machines
and projects: read-only inspection, `git fetch` / `git merge --ff-only`, and the
Laravel/PHP/Yarn project checks. `["codex", "mcp"]`, which allowed
`codex mcp add`, is narrowed to `codex mcp list`. Blanket `rg` is dropped too:
`rg --pre <cmd>` runs a command, the same class as `sed -n`.

**Decision — migration.** `link_dotfiles.sh` retires a
`~/.codex/rules/default.rules` symlink that points at exactly the old repo path.
If Codex has written through the dangling link, the resulting file holds that
machine's approvals and is moved back to `~/.codex` as a real file rather than
deleted. A real `default.rules` the user owns is never touched. The repo path is
gitignored as a backstop. Covered in `tools/test-link-dotfiles.sh`.

**Rejected — keep syncing `default.rules` and prune it periodically.** That is
what 0044 did; it lasted until the next approval click.

**Rejected — curate by hand but leave the local file symlinked.** Codex would
still write through the link into the working tree.
