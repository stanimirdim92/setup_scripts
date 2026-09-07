# Target selection

How a gate command resolves *what it operates on* — the ticket, task set,
change, or candidate — when the invocation's argument is missing or ambiguous.
Single source for `/build`, `/test`, `/review`, and `/ship`; don't restate this
in a command.

1. **Explicit argument wins.** Use it verbatim.
2. **Infer from the conversation** when the user already named the ticket,
   task, or candidate this session.
3. **Auto-select when exactly one candidate exists** — one active ticket under
   `docs/tasks/`, one BUILD COMPLETE handoff, one reviewed candidate.
4. **Otherwise ask**, listing the plausible candidates (most recently modified
   first) with enough state to choose — e.g. "3/7 tasks done", "VERIFY PASS",
   "REVIEW BLOCKED".

Whatever the path, **announce the resolved target** — "Using: `<target>`" —
and how to override it (re-invoke with an explicit argument), so a silent
wrong guess can't survive the first line of output. Never proceed on a guess
the user can't see.

## Gate handoffs

`/test`, `/review`, and `/ship` accept a predecessor completion message only
when either:

- the complete message appears in the current conversation; or
- in a new conversation, the user manually supplies the complete message.

Do not substitute a saved report, memory, agent summary, or a model's claim that
the earlier stage completed. Reconcile the supplied message against git before
using it. A mismatch or an incomplete message blocks the pipeline gate.

Every completion message must identify the repository root, branch, base
revision, HEAD, commit range, and clean/dirty state, plus the pinned spec and
plan revisions when they exist. If the authorized candidate contains
uncommitted work, also list its staged, unstaged, and untracked paths and a
deterministic hash of each diff or file set. Later stages accept only the exact
candidate described by those fields, plus test-only commits declared by a
matching `VERIFY PASS`.
