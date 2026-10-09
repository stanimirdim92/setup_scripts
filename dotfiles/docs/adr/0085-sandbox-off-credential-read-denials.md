# The OS sandbox is off; credential files keep Read denials

**Context.** ADR 0068 turned on Claude Code's Bash sandbox. It denied
sandboxed commands the credential files, unset token variables and allowed
only package and GitHub hosts. On the owner's machine the sandbox failed:
commands stopped with `bwrap: loopback: Failed RTM_NEWADDR` and worked only
when rerun outside it. The LD-380 harness test counted three such failures in
one session. The owner removed the `sandbox` block from `settings.json` on
2026-10-08 (commit 6b7b37d).

**Decision.**
- The sandbox stays off. Bash commands run under the permission rules and the
  PreToolUse hooks only.
- `permissions.deny` keeps `Read` denials for `~/.ssh`, `~/.aws`,
  `~/.config/gh`, `~/.git-credentials`, the Docker, npm and Composer
  credential files, `~/.claude/.credentials.json` and `~/.codex/auth.json`.
- `validate-frontmatter.py` no longer requires the sandbox. It requires a
  `Read` denial for the four core paths instead.

**Cost.** A `Read` denial stops the Read tool, not a shell command. An agent
can still run `cat ~/.ssh/id_ed25519` or read a token variable, subject only
to the permission prompt and the hooks. The network allowlist is gone too.
This is the protection ADR 0068 added, and it is now lost.

To turn the sandbox back on, restore the block from commit 6b7b37d's parent
and install `bubblewrap` and `socat`. Then check `/sandbox` on the machine.

Supersedes the sandbox decision of ADR 0068. Its other decisions stand.
