# Public-repo and permission hardening after the 2026-10-09 review

**Context.** A full review of the harness on 2026-10-09 found four kinds of
gap. The owner chose to fix all of them.
- `~/.codex/config.toml` was a symlink into this public repository. The Codex
  app writes its state there: trusted project paths, chat-title slugs, the
  company Jira host, desktop preferences and hook trust hashes. All of it
  reached git.
- `tools/run/spec-batch.txt` listed the private backlog: about 30 ticket keys
  with feature names.
- With the sandbox off (ADR 0085), `Bash(cat:*)` and `Bash(echo:*)` let an
  agent print a credential file or a token variable without asking. The main
  session could also push and open pull requests without asking.
- Codex personas could call any MCP server, so a Codex reviewer could edit
  Jira. Claude reviewers hold only Read, Grep and Glob. The Codex main-session
  hook matched `Bash` but not Codex's own shell tool names.

**Decision.**
- `dotfiles/codex/config.toml` holds only harness settings.
  `codex/install-config.py` turns `~/.codex/config.toml` into a local file and
  merges the base into it. Base keys and tables win; the app's tables stay
  local. CI fails when the base holds machine state (`--lint`).
- `spec-batch.txt` is gitignored. `spec-batch.example.txt` shows the format.
- `permissions.deny` blocks shell commands that name a credential path or a
  token variable, and bare `env` and `printenv`. `Bash(echo:*)` is no longer
  allowed. `git push`, `gh pr create`, `gh pr merge` and `gh release` ask.
- `enableAllProjectMcpServers` is false, so a cloned repository's `.mcp.json`
  does not run unasked.
- In Codex, readers get no MCP server, executors get Figma, and test-engineer
  gets Figma and chrome-devtools, as the Claude frontmatter grants. The
  main-session hook also matches `exec_command`, `shell` and `shell_command`.
- Codex escalations go to a person (`approvals_reviewer = "user"`), and the
  `npx` MCP packages are pinned to a version.
- `validate-frontmatter.py` and the Codex harness tests pin all of this.

**Cost.**
- The shell denials match command text. A determined command can still spell
  a path another way; only the sandbox would stop that.
- Pushing from the main session now asks every time.
- The old commits keep the leaked config, backlog and `.trash` files. The
  owner chose not to rewrite history.
- The pinned packages need a manual bump.
