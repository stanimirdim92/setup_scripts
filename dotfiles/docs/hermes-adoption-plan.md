# Plan: ideas from Hermes Agent for this harness

Status: Draft, 2026-10-17. Not approved. Nothing here is built yet.

Scope: Claude Code and Codex only. Sources: the Hermes Agent site and docs,
read on 2026-10-17 (homepage, about, README, architecture, security, memory,
skills, cron, tools, session storage, agent loop, native Windows, memory
providers, delegation, code execution, curator). Several Hermes pages were
truncated; claims marked *(summary)* come from the truncated part.

## Starting point

The harness works, and token use is not a problem. So this plan adds small,
deterministic pieces. It does not rebuild anything that works. Three rules
from the harness apply to every item:

- Deterministic before probabilistic (AGENTS.md §5). A script beats a model call.
- Changes to skills, rules and memory go through a reviewed commit. The agent
  never rewrites its own harness unasked.
- The harness-v1 freeze excludes new **gates** until the observation log has
  enough runs (`docs/observation-log.md`). Items that add a gate wait in Phase 4.

What Hermes does that this harness already has:

| Hermes | Here |
|---|---|
| Progressive skill loading (index, then body, then files) | Native in Claude Code and Codex: the description is indexed, the body loads on use |
| Subagents with fresh context, summary-only return | `claude/docs/agents.md`, task packets, spawn depth 1 |
| Session search (SQLite FTS5) | The episodic-memory plugin: vector, text, or both, over Claude and Codex history. Its text mode is a substring `LIKE`, not FTS |
| Dangerous-command approval | Hook guards with tests, fail closed (ADR 0087) |
| Persistent memory | Auto-memory, `docs/MEMORY.md`, episodic memory, the ticket ledger (ADR 0088) |
| `hermes doctor` | Nothing. See Tools T1. |

## Found while reading: episodic memory is broken

Episodic memory has indexed nothing since 2026-09-18. Every sync fails with
`ERR_DLOPEN_FAILED`: `better-sqlite3` was built for Node ABI 115, and the
machine now runs Node v26 (ABI 147). Search still answers from the old index,
so the fault is silent. This is item M1 and should go first.

---

## 1. Skills

**Now.** 19 committed skills, 5 explicit-only. Codex adapters in
`codex/skills/` read the Claude sources. `validate-frontmatter.py` checks
frontmatter. Nothing measures which skills are used.

**Hermes ideas.** The agent writes and patches skills after hard tasks. A
curator counts use, marks unused skills stale after 14 days and archives
them after 30. It never deletes, and every change goes in a ledger with
rollback. Skills capture "lessons, not logs". A linter flags oversized
bodies.

**Plan.**

- **S1 — Skill usage report.** Size S. No ADR.
  - Add `tools/run/skill-usage.py`. It reads Claude transcripts
    (`~/.claude/projects/*/*.jsonl`, `Skill` tool calls) and Codex rollouts
    (`~/.codex/sessions/**/rollout-*.jsonl`, skill loads).
  - Output: per skill, the count of loads and the last use, for 30 and 90 days.
  - It reports only. It never archives or edits. A person decides.
  - Verify: fixture transcripts in `tools/tests/test-skill-usage.py`; one run
    on this machine.
- **S2 — Skill lint in CI.** Size S. No ADR.
  - Extend `validate-frontmatter.py`, or add `check-skills.py`. Warn when:
    - a body is over about 24k characters;
    - a description is over the client's index limit;
    - a "Pitfalls" item holds a date, a PR number or a ticket key
      ("lessons, not logs").
  - Fail only when a `references/` link is broken, because
    `check-references.py` already owns that rule and can extend to it.
  - Verify: test fixtures; CI green on the current 19 skills.
- **S3 — `/lesson`: draft a skill change from a session.** Size M. ADR needed.
  - A command that reads the current session's corrections and dead ends.
    It then drafts either a patch to one existing skill or one new skill.
  - It writes the draft to a branch or a diff for review. It never commits to
    `main` and never edits `~/.claude/skills` directly.
  - The command checks the draft with S2 before it shows it.
  - This is Hermes's learning loop with the human approval that Hermes leaves
    off by default.
  - Verify: run it on two past sessions, such as LD-365's DEC drift. Check that
    the draft is one rule plus a reason, not a log.

**Rejected.**

- Background review every N turns. It spends tokens on every session to find
  rare lessons. S3 runs only when you ask.
- Automatic archive or delete. S1 gives the data, and you decide.
- Hermes's `platforms:` and toolset-conditional frontmatter. Neither client
  reads it.

## 2. Hooks

**Now.** Nine bash hooks in `claude/hooks/`, all need `jq`. Codex runs the
same scripts through `codex/hooks/policy.py`, so both clients need bash and
`jq`. Six test suites cover them. The command guards fail closed without `jq`
(ADR 0087).

**Hermes ideas.** One approval layer on all tool calls, a fixed blocklist that
holds in every mode, and secret scrubbing before data leaves the machine.

**Plan.**

- **H1 — One Python hook core for both clients.** Size L. ADR needed.
  - Move the guard logic from bash into one Python module (`hooks/core/`),
    standard library only. Claude `settings.json` and Codex `hooks.json` both
    call it.
  - Migrate one hook at a time. For each hook, run the existing bash fixtures
    against the Python version, and delete the bash copy only when both agree.
  - Result: no `jq`, no duplicated logic between Claude and Codex, and hooks
    that run on Windows (W2).
  - Risk: a missing Python interpreter is a new fail-open case. Keep the
    ADR 0087 rule: the launcher line must deny when Python cannot start.
  - Verify: the six suites pass against both versions during migration; one
    suite per hook after.
- **H2 — Memory write guard.** Size S. ADR needed (new guard).
  - A `PreToolUse` hook on `Write` and `Edit` into the auto-memory folder and
    `~/.codex/memories/`. Deny invisible Unicode and a secret-shaped string.
    Do not deny a duplicate line; Hermes treats it as a no-op.
  - Start in warn mode, because a new deny hook is a gate under the freeze.
    Switch to deny after the freeze. Details: `hermes-research/memory.md`.
  - This is Hermes's memory write scan. Memory is loaded into every session, so
    an injected line there persists.
  - Verify: fixtures in `test-hooks.sh`.
- **H3 — PowerShell tool coverage.** Size S. Part of W1.

**Rejected.**

- An LLM risk judge for commands (Hermes `smart` mode). Fixed rules are
  testable; a model judge is not, and it costs a call per command.

## 3. Memory

**Now.** Three systems (`references/documentation-practices.md` §Memory):
auto-memory (local, loaded each session, 200 lines / 25 KB cap), `docs/MEMORY.md`
(committed), and episodic memory (local index). Codex also writes
`~/.codex/memories/`. The ticket ledger holds open items (ADR 0088).

**Hermes ideas.** Small fixed budgets (about 800 + 500 tokens), a frozen
snapshot per session, writes that fail loudly over the limit, a review
timeline (`/journey`), and secret scrubbing.

**Plan.**

- **M1 — Fix episodic memory now.** Size XS. No ADR.
  - Rebuild the native module in the plugin folder
    (`npm rebuild better-sqlite3`), or reinstall the plugin.
  - Verify: the next sync in `~/.config/superpowers/logs/episodic-memory.log`
    ends without error, and the newest indexed exchange is today.
- **M2 — Memory health report.** Size S. No ADR.
  - Add `tools/checks/memory-health.py`. It reports, for auto-memory and
    Codex memories:
    - size against the load limit (200 lines / 25 KB for Claude);
    - index lines that point at a missing file, and files with no index line;
    - entries that name a path or flag that no longer exists in the repo;
    - the age of the newest episodic index entry (catches the M1 fault).
  - It reports only. T1 runs it.
  - Verify: fixture memory folders in a test; one run on this machine.
- **M3 — Memory review list.** Size XS. No ADR.
  - A flag on M2 (`--recent 14`) lists memory files changed in the last N days
    with their first line. That is the useful part of `/journey`, as a
    read-only list.

**Rejected.**

- External memory providers (Honcho, Mem0 and others). They are cloud
  services, and they add a prefetch and a sync on every turn. Episodic memory
  already covers recall, locally.
- A hard token budget on auto-memory writes. Claude Code owns that file; M2
  reports the size instead.

## 4. Agents

**Now.** Seven Claude personas, eight Codex roles, parity tested by
`test-codex-harness.py`. Spawn depth 1. Writers isolated by worktree. The
handoff hook checks writer reports.

**Hermes ideas.** A result schema with one correction turn, stall detection
(450 s idle, 1200 s in a tool), an explicit `unknown` state for orphaned work,
and an error instead of silent truncation when a batch is too large.

**Plan.**

- **A1 — Stall and timeout signals in `run-metrics.sh`.** Size S. No ADR.
  - From transcripts, report subagents with long gaps between turns and tool
    calls that ran over a threshold. Start with Hermes's numbers (450 s and
    1200 s) and calibrate from the observation log.
  - Measurement only.
  - Verify: a fixture in `test-run-metrics.sh`.
- **A2 — Reviewer result shape check.** Size M. ADR needed. Phase 4 (a gate).
  - Extend the handoff hook to reviewers. A review must end with findings in
    the `component-response-contracts.md` shape (id, disposition, file, claim),
    and the hook allows one correction turn, as Hermes's `output_schema` does.
  - Wait for the freeze: it is a new gate.
- **C1 — Compaction rule wording.** Size S. No ADR.
  - Add to the global compaction rule: the latest request first, the user's
    own instructions and constraints word for word, and where the full record
    lives. Details: `hermes-research/agents.md`.
  - Verify: check one compacted session by hand against the rule.
- **A3 — Generate Codex role files from Claude personas.** Size M. ADR needed.
  - Only if parity drift appears in practice. Today the parity test catches it,
    so this stays parked in `IDEAS.md`.

**Rejected.**

- Ten concurrent children by default. ADR 0054/0055 gate concurrency by
  conditions; a fixed high number is the opposite.
- A Python RPC sandbox like `execute_code`. Neither client exposes tools over
  RPC to a script, and the gain is fewer turns, which is not a problem here.

## 5. Windows

**Now.** The harness runs only under WSL2. Native Windows breaks three things:
the hooks need `jq` and bash, the Bash-tool guards do not see the PowerShell
tool, and the linker needs real symlinks. Hermes uses the same approach as
Claude Code: Git Bash as the tool shell, PowerShell only for install.

Decision first: do you need native Windows, or is WSL2 enough? WSL2 needs no
work. The steps below are for native Windows.

**Plan.**

- **W1 — Native Windows with Git Bash, phase one.** Size M. ADR needed.
  - Add `.gitattributes` with `*.sh text eol=lf` and `*.py text eol=lf`.
  - Write the prerequisites in `dotfiles/README.md`: Git for Windows, `jq`
    (`winget install jqlang.jq`), Python 3, Developer Mode for symlinks.
  - `link_dotfiles.sh`: refuse to run when `ln -s` would copy instead of
    link. Test for it with a probe link, and print the
    `MSYS=winsymlinks:nativestrict` fix.
  - Add the PowerShell tool to the guard matchers, or deny it in
    `permissions`, after you confirm the tool name your Claude Code version
    uses. Codex: confirm whether its Windows build runs the same hook events.
  - Set `PYTHONUTF8=1` for hook commands (Hermes forces UTF-8 stdio for the
    same reason: cp1252 consoles break on non-ASCII).
  - Verify: a `windows-latest` CI job runs `test-hooks.sh` and the Python tests
    under Git Bash.
- **W2 — No `jq` on Windows.** This is H1. After H1, Windows needs only Git
  Bash and Python.

**Not needed.** A Windows service or scheduled task. Neither client runs a
gateway.

## 6. Full-text search

**Now.** Episodic memory has a `mode` of `vector`, `text` or `both`, over
Claude and Codex conversations, plus a `tool_calls` table. Its `text` mode is
one substring `LIKE`, not FTS. It is a month out of date (M1).

**Hermes ideas.** FTS5 with triggers, results with a snippet plus one message
before and after (200 characters each), session lineage across compaction, and
a query sanitizer for hyphenated terms.

**Plan.**

- **F1 — Fix and watch the existing index.** That is M1 plus the freshness line
  in M2. No new code.
- **F2 — Own FTS5 search, only if F1 fails twice.** Size M. ADR needed.
  - Add a `search_sessions` tool to `tools/agent_sessions_mcp.py`, which
    already parses Claude and Codex transcripts. Use Python's built-in
    `sqlite3` FTS5, an index file under `~/.cache/`, and Hermes's result shape
    (snippet, context, session id, time, project).
  - Index user and assistant text only, not tool output, to keep secrets out.
  - Verify: fixture transcripts; a query for a known LD-365 phrase.

## 7. Tools

**Plan.**

- **T1 — `tools/doctor.sh`: one health command.** Size S. No ADR.
  - Checks:
    - `jq`, Python and Git are present;
    - every link from `link_dotfiles.sh` points at the repo;
    - the episodic-memory native module loads, and its index is fresh;
    - M2's memory sizes;
    - Codex hook trust is current after a `hooks.json` change (the handoff
      lists this as a manual step).
  - Prints PASS / WARN / FAIL per line. Changes nothing.
  - This is the `hermes doctor` idea. It would have found the M1 fault on day one.
  - Verify: run on this machine; a test with a fake `$HOME`.
- **T2 — Keep only Claude and Codex in the session tools.** Size XS. No ADR.
  - Remove the Gemini CLI parts from `tools/agent_sessions_mcp.py`.
  - Verify: `--print` lists only Claude and Codex sessions.
- **T3 — Scheduled health run, scripts only.** Size S. No ADR.
  - A user cron entry or systemd timer runs T1 and S1 weekly and writes the
    report to `~/.cache/harness/`. No model call.
  - From Hermes cron, copy only two ideas: check before you spend tokens, and
    alert once per new problem, not every run.

---

## Order

| Phase | Items | Why this order |
|---|---|---|
| 0 — now | M1, T2 | A real fault, and your Claude-and-Codex request |
| 1 — small, no gates | T1, M2, M3, S1, S2, A1 | Deterministic reports; they find the next fault early |
| 2 — Windows, if wanted | W1 | Needs your decision on native Windows vs WSL2 |
| 3 — larger | H1, H2, S3, T3 | H1 removes `jq` and the bash/Python split; S3 is the reviewed learning loop |
| 4 — after the freeze | A2, F2 if needed, the read-size gate in `IDEAS.md` | New gates wait for observation data |

## Decisions (answered 2026-10-17)

1. **Windows:** native Windows. W1 comes first, then H1.
2. **Lessons:** build `/lesson` (S3). The design is in `hermes-research/skills.md`.
3. **Memory write guard (H2):** no preference from you. My recommendation is a
   narrow guard, built in H1. The reasons are in `hermes-research/memory.md` §6.
4. **Phase 0:** declined. Do not rebuild episodic memory, and do not remove
   Gemini yet.

The research for each area is in `hermes-research/`, one file per area.
