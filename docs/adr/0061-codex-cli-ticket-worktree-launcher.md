# Codex CLI ticket worktree launcher

**Decision.** Install `dotfiles/codex/bin/codex-worktree` as
`~/.local/bin/codex-worktree`. The user wants independent terminal Codex sessions
working on different tickets simultaneously, analogous to starting Claude with
`--worktree`. The inspected Codex CLI rejects that flag, so the launcher creates
or reuses `<main-checkout>/.codex/worktrees/<ticket>` on `codex/<ticket>` and
starts `codex -C` there. This supplies the CLI startup mechanism missing from
[0059](0059-codex-native-roles-and-hook-adapters.md), without changing child-agent
dispatch or the desktop app's separate managed-worktree behavior.

**Decision.** New branches start at the invoking checkout's committed HEAD;
existing ticket branches keep their history and edits. The main registered
checkout owns the directory even when invoked from a child checkout. Ticket
names are validated, unknown paths and symlink destinations are rejected, and
the launcher never resets, switches, pulls, commits, or deletes the source
checkout. A per-ticket lock covers setup and the entire CLI lifetime: different
tickets run concurrently, while a duplicate launcher for one ticket fails.
Checkouts remain after exit or failure for inspection and retry. Only the local
Git exclusion file is updated to ignore the worktree directory.

**Decision.** Copy the intersection of the target's `.worktreeinclude` rules
and the source's actual ignored files, using Git for pattern evaluation. Keep
existing destination files, skip source symlinks, and exclude nested worktree
directories. Reuse the shared branch/infrastructure guard and run a project's
executable `bin/worktree-setup.sh`, when available. Leadbuster already owns
dependency reconciliation and test runtime isolation; the global launcher does
not duplicate those policies or run database cleanup. Setup failure prevents
CLI startup. `--no-setup` supports specification/planning; `--dry-run` is read-only.

**Rejected — one conversation spawning all ticket agents.** The user explicitly
wants separate sessions, each independently startable and steerable. Existing
subagent/workstream orchestration can still run inside a ticket session.

**Rejected — share one checkout or dependency symlinks.** Separate sessions
would race on Git state or mutable files. Worktrees isolate files and branches;
project runners must additionally isolate test databases, queues, caches and ports.

**Rejected — silently update existing worktrees or delete failed setup.** Either
can destroy or mix ongoing ticket work. Explicit diagnostics and a retained
checkout make retry and integration reviewable.

**Decision.** Fixture tests use real Git worktrees with stub setup/CLI processes
to cover concurrent sessions, duplicate-session rejection, argument forwarding,
copy filtering, preservation, branch/path conflicts, and failures without model
calls. Installation tests verify the executable symlink and rollback behavior.
