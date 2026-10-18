# Hermes research: memory

Part of `../hermes-adoption-plan.md` (items M1, M2, M3 and H2, the memory
write guard). The source is Hermes Agent at commit `5fea5a7` (2026-10-17),
read from a local clone. Hermes paths are relative to its repository root.
Paths that start with `dotfiles/` or `~` are ours.

## Coverage

**Read in full:**
- `tools/memory_tool.py`, `tools/memory_tool_store.py`;
- `tools/threat_patterns.py`, `tools/write_approval.py`;
- `agent/memory_provider.py`, `agent/memory_manager.py`, `agent/memory_context.py`;
- `agent/background_review.py`, `tools/skill_provenance.py`;
- `hermes_cli/write_approval_commands.py`;
- `hermes_cli/subcommands/memory.py`, `hermes_cli/subcommands/journey.py`;
- `tests/tools/test_threat_patterns.py`;
- the catalog entry `plugin-catalog/holographic.yaml`.

**Read in part** (line ranges are in Sources):
- `agent/redact.py`: the prefix table, the main pass and `redact_for_egress()`;
- the call sites: `agent/system_prompt.py`, `agent/agent_init.py`,
  `agent/turn_context.py`, `agent/turn_finalizer.py`, `agent/tool_executor.py`,
  `run_agent.py`;
- other scan users: `agent/prompt_builder.py`, `agent/tool_dispatch_helpers.py`,
  `tools/skills_guard.py`, `tools/ansi_strip.py`, `tools/approval_detection.py`,
  `tools/cronjob_prompt_scan.py`;
- `hermes_cli/config_defaults.py`, `hermes_cli/journey.py`, `agent/learning_graph.py`;
- `plugins/memory/__init__.py` and the two bundled providers (headers and method lists);
- `agent/memory_caller_scope.py` (header only; it isolates gateway profiles);
- `tests/tools/test_memory_tool.py` (all test names, and the scan cases in full);
- the test names in four more test files (listed in Sources);
- `website/docs/user-guide/features/memory.md` (four sections);
- the catalog entries `memory-shield`, `memory-rewind` and `memory-review` (the first 20 lines of each description).

**Not read:**
- `agent/conversation_compression.py`, which detects a leftover memory block after compaction;
- provider setup and web UI: `hermes_cli/memory_setup.py`, `memory_oauth.py`,
  `memory_provider_migration.py`, `web_server_memory.py` and the desktop and TUI code;
- `gateway/memory_monitor.py` and `gateway/memory_status.py` (the names suggest process RAM; not checked);
- `plugins/memory/config_schema.py`, `plugins/memory/query_rewrite.py`;
- the provider docs `memory-providers.md` and `memory-provider-plugin.md`;
- the other 64 memory catalog manifests beyond their `name`, `tier` and `category` lines;
- the bodies of most memory tests.

**Method for the false-positive numbers.** I copied the 36 patterns by hand
into my own script. I parsed the 56 vendor prefixes out of `agent/redact.py`
with `ast`. The copy matches all 47 cases I took from Hermes's tests (29 must
block, 18 must pass). No Hermes code ran. The permission system refused one
probe command. I judged its four example lines from the regex text and the
tests instead.

## 1. File map

| Path | Role |
|---|---|
| `tools/memory_tool.py` | The `memory` tool: schema, write gates, staging, replay |
| `tools/memory_tool_store.py` | `MemoryStore`: files, limits, edits, locks, snapshot |
| `tools/threat_patterns.py` | The shared scan: 36 patterns and 15 invisible characters |
| `tools/write_approval.py` | The approval gate and the pending store |
| `hermes_cli/write_approval_commands.py` | `/memory` pending, approve, reject, approval |
| `hermes_cli/subcommands/memory.py` | `hermes memory setup/status/off/reset` |
| `hermes_cli/config_defaults.py:1310-1325` | The `memory` config defaults |
| `agent/agent_init.py:1299-1383` | Builds the store and the provider manager |
| `agent/system_prompt.py:522-547` | Puts the snapshot into the system prompt |
| `agent/turn_context.py:758-767` | The review counter |
| `agent/turn_finalizer.py:777-791` | Starts the review after the reply |
| `agent/background_review.py` | The review fork, its prompts and its tool whitelist |
| `tools/skill_provenance.py` | Write origin and the "attended" flag |
| `agent/memory_provider.py` | The `MemoryProvider` base class |
| `agent/memory_manager.py` | Calls the providers and scrubs what they receive |
| `agent/memory_context.py` | Fences recalled context as `<memory-context>` |
| `agent/redact.py` | Secret masking for logs, tool output and egress |
| `hermes_cli/journey.py`, `agent/learning_graph.py` | `/journey` |
| `plugins/memory/` | Provider discovery and two bundled providers |

## 2. Built-in memory

- **Files:** `<HERMES_HOME>/memories/MEMORY.md` (target `memory`) and `USER.md`
  (target `user`) (`tools/memory_tool.py:38-40`).
- **Format:** entries are joined by `\n§\n` (`tools/memory_tool_store.py:25`).
  Reads use `utf-8-sig` with strict decoding (`:646-662`). So a Notepad BOM is
  dropped, and undecodable bytes refuse the write.
- **Limits:** 2,200 characters for `MEMORY.md` and 1,375 for `USER.md`. They
  count the joined text (`hermes_cli/config_defaults.py:1318-1319`;
  `tools/memory_tool_store.py:309-310`). The config comments say about 800 and
  500 tokens.
- **Over the limit at load:** the file loads with a warning. Hermes never cuts it (`:246-252`).
- **Duplicates:** load drops repeated entries (`:244`). A duplicate `add`
  returns success: "Entry already exists (no duplicate added)." (`:378-379`).
  In a batch it is a no-op (`:504-505`).
- **Actions:** `add`, `patch` and `remove` (`tools/memory_tool.py:404`).
  - `patch` replaces one span in one entry. The span must occur once (`tools/memory_tool_store.py:145-156`, `:406-439`).
  - `remove` deletes the whole entry (`:441-445`).
  - `replace` returns an error that points to `patch` (`tools/memory_tool.py:168-170`, `:280-281`).
    It stays only to replay writes staged before its removal (`:105-106`).
- **Batch:** one `operations` list per call and per store. It is all-or-nothing.
  The limit applies to the final state only (`tools/memory_tool_store.py:553-616`).
- **Matching:** an exact whole entry wins, then a substring, then a fold of
  quotes, dashes and spaces (`:72-107`). A miss returns the three closest entries (`:110-124`).
- **Refusals:**
  - a batch that would empty a store that was not empty (`:583-592`);
  - a write over a file that exists but cannot be read (`:63-69`);
  - external drift: one "entry" longer than the whole limit. That is text
    appended without `§`, by hand or by shell (`:685-700`).
    Hermes saves a `.bak.<time>` copy and refuses the edit (`:49-60`).
    `add` skips this check (`:388-390`).
- **Retry cap:** the first three failed consolidations in a turn return the
  normal error. The fourth returns "Stop retrying memory calls" with
  `done: true` (`:184`, `:204-219`). A success resets the count (`:631`).
- **Success result:** `done: true`, the usage and the entry count. It never
  echoes the entries, so the model does not "find more to fix" (`:623-636`).
- **Concurrency:** one `.lock` file per store, opened with `O_NOFOLLOW` and mode
  `0600` (`:256-296`). It uses `flock`, or `msvcrt` on Windows. Writes go to a
  temp file and then a rename (`:675-683`). Each edit reads the file again under
  the lock (`:338-367`).
- **Tool guidance:** memory holds only facts that apply to every session.
  Procedures and task lessons go to skills. Task progress, logs and TODO state
  are skipped (`tools/memory_tool.py:385-397`).

## 3. Snapshot and prompt placement

- **Load:** `agent/agent_init.py:1335-1341` builds the store with the configured
  limits and calls `load_from_disk()` once per agent.
- **Block:** each store renders as one block (`tools/memory_tool_store.py:638-644`).
  The block has a row of 46 `═`, a title with the usage, another row, and the
  entries. An example title is `MEMORY (your personal notes) [67% — 1,474/2,200 chars]`.
- **Load-time scan:** every entry is scanned with the strict scope (`:228-236`).
  A hit becomes `[BLOCKED: … threat pattern(s): <ids> …]` in the snapshot only.
  The file keeps the raw text, so the user can see and remove the entry (`:221-225`).
- **Call site:** `_memory_parts()` calls `format_for_system_prompt()`
  (`agent/system_prompt.py:522-547`, the call is at `:529`). The external
  provider's static block follows (`:535-546`).
- **Tier:** memory sits in the volatile tier, right after the skills index
  (`agent/system_prompt.py:785`). That tier comes last, so the stable prefix stays cached (`:782`).
- **Frozen:** a write during a session goes to disk only. The prompt keeps the
  load-time snapshot (`tools/memory_tool_store.py:618-621`).
  Outside tests, only agent start and `load_on_disk_store()` call `load_from_disk()`
  (`tools/memory_tool.py:47-61`). The second one serves `/memory` approvals.

## 4. Write scan (`tools/threat_patterns.py`)

- **Shape:** each pattern is `(regex, id, scope)`. Scopes are cumulative:
  `strict` includes `context`, which includes `all` (`:114-125`). So a strict
  scan runs all 36 patterns.
- **Callers:**

| Caller | Scope | Effect of a hit |
|---|---|---|
| Memory write (`tools/memory_tool_store.py:28-31`) | strict | The write is refused |
| Memory load (`tools/memory_tool_store.py:228-236`) | strict | The entry is replaced in the snapshot |
| Project context files (`agent/prompt_builder.py:100-109`) | context | The whole file becomes `[BLOCKED: …]` |
| The user's own `SOUL.md` (`agent/prompt_builder.py:103-107`) | context | A warning; the file loads |
| Tool results (`agent/tool_dispatch_helpers.py:545-563`) | context | An advisory finding; never blocks |

- **Order:** invisible characters are checked on the raw text. Then NFKC runs,
  then the patterns (`:138-145`). NFKC folds full-width letters. It does not
  fold Cyrillic look-alikes (`:141-142`).
- **Cap:** the scan reads the first 65,536 characters (`:17`, `:138`). It does
  not scan the text after them (`tests/tools/test_threat_patterns.py:260-262`).
- **Invisible characters (15):** U+200B to U+200D, U+2060, U+2062 to U+2064,
  U+FEFF, U+202A to U+202E, and U+2066 to U+2069 (`:110-112`).
  The finding id is `invisible_unicode_U+XXXX`.
- **Patterns (36):**

| Scope | Lines | Count | Ids |
|---|---|---|---|
| all | `:27-38`, `:75-77` | 11 | `prompt_injection`, `sys_prompt_override`, `disregard_rules`, `bypass_restrictions`, `html_comment_injection`, `hidden_div`, `translate_execute`, `deception_hide`, `exfil_curl`, `exfil_wget`, `read_secrets` |
| context | `:41-69` | 17 | `role_hijack`, `role_pretend`, `leak_system_prompt`, `remove_filters`, `fake_update`, `identity_override`, `c2_node_registration`, `c2_heartbeat`, `c2_task_pull`, `c2_network_connect`, `forced_action`, `anti_forensic_oneliner`, `anti_forensic_disk`, `env_var_unset_agent`, `known_c2_framework`, `c2_explicit`, `c2_explicit_long` |
| strict | `:78-104` | 8 | `send_to_url`, `context_exfil`, `ssh_backdoor`, `ssh_access`, `hermes_env`, `agent_config_mod`, `hermes_config_mod`, `hardcoded_secret` |

- **Shapes that matter for H2:**
  - `exfil_curl` and `exfil_wget`: `curl` or `wget`, then a `$VAR` whose name
    ends in `KEY`, `TOKEN`, `SECRET`, `PASSWORD` or `CREDENTIAL` (`:21`, `:75-76`).
  - `read_secrets`: `cat` with `.env`, `credentials`, `.netrc`, `.pgpass`,
    `.npmrc` or `.pypirc` (`:77`).
  - `ssh_backdoor`: the bare word `authorized_keys` (`:82`).
  - `ssh_access`: a write verb or a redirect, then `~/.ssh` or `$HOME/.ssh`
    (`:87-89`). Read-only mentions pass (`tests/tools/test_threat_patterns.py:331-338`).
  - `hardcoded_secret`: `api_key`, `token`, `secret` or `password`, then `=` or
    `:`, a quote and 20 or more token characters (`:102-104`).
    A value that is an env-var name passes (`tests/tools/test_threat_patterns.py:361-373`).
- **Gaps:**
  - A bare vendor token, such as `ghp_…` outside an assignment, passes. The 56
    vendor prefixes live only in `agent/redact.py:147-216`, which masks and never blocks.
  - Unicode tag characters (U+E0000 to U+E007F) pass. Hermes strips them from
    terminal output (`tools/ansi_strip.py:24-42`) and checks them in approval
    text (`tools/approval_detection.py:349`), but not here.
- **False positives under strict scope.** The comment at `:64-66` asks for
  distinctive brand names only. But `known_c2_framework` also lists "havoc",
  "sliver" and "mythic" (`:67`). Strict scope blocks each note below:

| Note | Blocked by | Evidence |
|---|---|---|
| "The flaky test caused havoc in CI" | `known_c2_framework` | My copy of the patterns |
| "Pull tasks from the Jira board" | `c2_task_pull` | My copy of the patterns |
| "Check in with the reviewer before merging" | `c2_heartbeat` | My copy of the patterns |
| "Send the report to https://example.atlassian.net/wiki" | `send_to_url` | My copy of the patterns |
| "Update CLAUDE.md after adding a skill" | `agent_config_mod` | The regex at `:91`; the test cases at `tests/tools/test_memory_tool.py:85-87` |

## 5. Background review and approval

- **Counter** (`agent/turn_context.py:758-767`): each user turn adds one when
  the `memory` tool and the store exist. At the interval the counter resets and the review fires.
- **Interval:** `memory.nudge_interval`, default 10 (`hermes_cli/config_defaults.py:1321`;
  `agent/agent_init.py:1304`, `:1333`). The value 0 turns it off.
- **Reset:** when the model calls `memory` itself, the counter goes back to 0
  (`agent/tool_executor.py:747-748`). On resume it starts at
  `prior user turns % interval` (`agent/turn_context.py:750-755`).
- **Skill trigger:** separate. It counts tool iterations since the last
  `skill_manage` call, default 10 (`agent/agent_init.py:1388-1390`;
  `agent/turn_finalizer.py:762-769`). When both fire, one combined prompt runs.
- **Start:** after the reply is delivered, and only when the turn was not
  interrupted (`agent/turn_finalizer.py:777-791`). The comment there puts the
  cost at about 30K tokens per review. The review runs in a daemon thread (`run_agent.py:824`).
  Subagents never start one (`run_agent.py:766-767`).
- **Switch:** `auxiliary.background_review.enabled`, default on. A config read
  error keeps it on and logs a warning (`agent/background_review.py:228-250`).
  One-shot runs (`chat -q`) and safe-worker mode skip it (`:237-238`).
- **Limits:**
  - one review at a time per agent (`:75-89`);
  - 16 iterations (`:173`);
  - an input budget of 75% of the context window, 600,000 tokens at most (`:174-182`);
  - a new user turn cancels a running review and waits 2 s at most (`:25`, `:129-167`).
- **Isolation:** on the same model, the fork reuses the session id and the
  cached prompt for cache hits (`:1016-1018`). It writes no session record and
  loads no external provider (`:921-945`, `:1002-1005`). Its own counters are
  0, so it cannot start a review (`:995`). It denies dangerous shell commands
  automatically (`:1048-1055`).
- **Tools:** the fork gets the `memory` tool only when the memory trigger fired
  (`:1088-1098`). It always gets the skill tools, `read_file` and `search_files` (`:1103`).
- **Prompts:**
  - Memory: "Review the conversation above and consider saving to memory if
    appropriate." With nothing to save, the answer is "Nothing to save." (`:383-388`).
  - Routing (`:370-381`): `USER.md` holds who the user is: preferences, style,
    expectations. `MEMORY.md` holds environment facts: tool quirks, conventions, paths.
  - "One fact goes to ONE store, never both." The comment cites double writes
    that filled both files (`:367-369`).
  - Combined: a user-preference lesson goes into the skill that owns the task.
    `USER.md` takes it only when no skill owns it (`:557-563`).
- **Unattended deletes:** in an automatic review, `add` writes at once. A
  `patch` or `remove`, alone or in a batch, is staged for approval
  (`tools/memory_tool.py:179-219`). The message says "Background review may not
  delete memory entries unattended". If staging fails, the call is denied (`:214-219`).
- **Attended review:** `/refine` runs the same fork but marks it attended. It
  keeps all memory actions (`tools/skill_provenance.py:29-44`; `agent/background_review.py:1159`).
- **`memory.write_approval`:** off by default (`hermes_cli/config_defaults.py:1317`;
  `tools/write_approval.py:44-60`). When it is on:
  - a background write is staged;
  - a foreground write asks inline when a person can answer, and is staged otherwise (`tools/write_approval.py:201-248`);
  - the gate refuses only when the person says no (`:201-205`).
- **Pending store:** `<HERMES_HOME>/pending/memory/<id>.json`, with an
  8-character hex id (`:65-66`, `:79`). A staged `patch` or `remove` stores the
  full entry it matched. Approval applies to that exact entry or refuses
  (`tools/memory_tool.py:64-81`, `:353-370`).
- **Commands** (`hermes_cli/write_approval_commands.py:35-57`):

| Command | Effect |
|---|---|
| `/memory` | The gate state and the pending list |
| `/memory pending` | The pending list, with the entry each write targets |
| `/memory approve <id>` or `all` | Apply, and show any overwritten, patched or removed entry |
| `/memory reject <id>` or `all` | Discard (`deny` and `drop` are aliases) |
| `/memory approval on` or `off` | Set the gate (`mode` is an alias) |

- **Shell command:** `hermes memory` configures providers: `setup`, `status`,
  `off`, and `reset --target all|memory|user` (`hermes_cli/subcommands/memory.py:10-34`).
- **Fail-open import:** when `tools/write_approval.py` cannot load, the write
  goes through (`tools/memory_tool.py:84-90`).

## 6. Providers and egress

- **Interface** (`agent/memory_provider.py`):
  - Required: `name`, `is_available()` (config only, no network),
    `initialize(session_id, **kwargs)` and `get_tool_schemas()` (`:109-161`).
  - Optional: `unavailable_reason`, `system_prompt_block`, `prefetch` ("Must be
    fast"), `queue_prefetch`, `recall_status` and `sync_turn` (non-blocking) (`:130-157`).
  - Optional: `handle_tool_call`, `shutdown`, `on_turn_start`,
    `identity_signature`, `on_session_end` (real session ends only) and `on_session_switch` (`:163-192`).
  - Optional: `on_pre_compress`, `on_delegation`, `get_config_schema`,
    `save_config`, `on_memory_write` and `backup_paths` (`:194-225`).
- **Manager** (`agent/memory_manager.py`):
  - one external provider beside the built-in store (`:288-298`);
  - each provider call is isolated, so one failure does not stop the others (`:256-266`);
  - external prefetch waits 8 s at most, and a stuck provider is skipped until it returns (`:38`, `:376-420`);
  - sync runs in order on one background worker (`:453-500`);
  - shutdown waits 5 s for queued writes, then reports what it dropped (`:37`, `:818-864`);
  - a provider tool cannot take a core tool's name (`:320-344`);
  - staged or failed built-in writes are not mirrored (`:747-756`);
  - a `patch` is mirrored as a `replace` of the whole entry (`:795-804`).
- **Egress scrub:** every string, also inside nested data, passes
  `redact_for_egress()` before a provider gets it (`:169-215`). This holds when
  `security.redact_secrets` is off. A token masked once is masked everywhere in that hand-off (`:205-214`).
- **Recall block:** prefetched recall rides in the user turn, not in the system
  prompt (`agent/memory_context.py:128-130`). It is fenced as
  `<memory-context>`, with a note that it is not user input (`:169-185`).
  Repeated bullets are dropped (`:123-166`). The fences are stripped from output, also in streams (`:23-116`).
- **`redact_for_egress()`** (`agent/redact.py:1164-1176`): the full pattern pass
  with `force=True`, plus a `Bearer` sweep. If the pass raises, the result is
  `[redaction-unavailable]`, never the raw text.
- **Pattern pass** (`agent/redact.py:893-1002`):
  - 56 vendor prefixes (`:147-216`), with word guards on both sides (`:589-590`);
  - env, config and JSON assignments with secret-like names;
  - `Authorization` headers and API-key headers;
  - private-key blocks (`:521`), database URLs and JWTs (`:555`);
  - Telegram tokens, form bodies and phone numbers.
- **Bundled providers** (`plugins/memory/`):

| Provider | Backend | Hooks it implements |
|---|---|---|
| `byterover` | The local `brv` CLI, optional cloud sync | prompt block, prefetch, queue_prefetch, sync_turn, `on_memory_write` (3-argument form), on_pre_compress, tools, shutdown |
| `retaindb` | A cloud API; needs `RETAINDB_API_KEY` | prompt block, prefetch, queue_prefetch, sync_turn, `on_memory_write` (3-argument form), tools, shutdown |

- **Discovery order:** bundled, user, project (opt-in), then entry points.
  Bundled wins, so a folder in the work tree cannot shadow a shipped provider (`plugins/memory/__init__.py:1-8`).
- **Catalog:** 65 catalog manifests have `category: memory`, all community tier.
  `honcho`, `hindsight`, `supermemory`, `mem0`, `openviking` and `holographic`
  are the ones the config names (`hermes_cli/config_defaults.py:1322-1323`).
- **Holographic** (`plugin-catalog/holographic.yaml`): it moved out of the tree
  to a community repository. It is a local SQLite store with FTS5 keyword
  search, trust scores and HRR recall. It makes no network call unless embeddings are on.
- **Two catalog plugins close to our items:**
  - `memory-shield`: one `pre_tool_call` hook. It checks `memory` calls, and
    `write_file`, `patch`, `terminal` and `execute_code` calls that write a memory file.
    It can block, ask or log, and it snapshots each file before an allowed edit.
    It is the nearest precedent for H2.
  - `memory-rewind`: git history for `MEMORY.md`, `USER.md`, `SOUL.md` and the
    skills, with diff and restore.

## 7. `/journey`

- `hermes journey` (aliases `learning` and `memory-graph`) shows learned skills
  and memory entries on a timeline (`hermes_cli/subcommands/journey.py:8-22`).
  The TUI and the desktop app have `/journey`.
- Memory entries carry no dates. Each entry gets the file's modification time
  plus its position (`agent/learning_graph.py:171-180`). Its title is its first line.
- `list`, `delete <node>` and `edit <node>` prune and fix entries
  (`website/docs/user-guide/features/memory.md:263-281`).

## 8. For this harness

### What we have

- **Auto-memory:** on (`autoMemoryEnabled: true` in `dotfiles/claude/settings.json`; ADR 0043).
  - Location: `~/.claude/projects/<project>/memory/` (`dotfiles/claude/references/documentation-practices.md:118`).
  - Scope: one project on this machine (`:119`). This machine has 17 project memory folders.
  - Claude Code loads the first 200 lines or 25 KB of the index `MEMORY.md`.
    Topic files load on demand (`:138-147`).
- **`docs/MEMORY.md`:** committed (`dotfiles/docs/MEMORY.md`). Read it first, update it last.
- **Codex memories:** on (`dotfiles/codex/config.toml:22-28`). The keys are
  `memories`, `generate_memories` and `use_memories`.
  - `~/.codex/memories/` holds `MEMORY.md`, `memory_summary.md`, `raw_memories.md`,
    `rollout_summaries/`, `skills/` and `extensions/`.
  - Not verified: which files Codex loads, and whether it writes them through tool calls.
    The `rollout_summaries/` folder suggests a generation step of its own.
- **Episodic memory:** still failing. Its log has 183 `ERR_DLOPEN_FAILED` lines.
  The first follows a 2026-09-20 timestamp, and the last is from 2026-10-17.
- **Hooks:** no hook matches `Write` or `Edit` today.
  - Claude: `PreToolUse` on `Bash` and `Agent|Task`, and `SessionStart` on
    `startup|resume` (`dotfiles/claude/settings.json`).
  - Codex: `PreToolUse` on shell and agent tools only (`dotfiles/codex/hooks.json`).
    `dotfiles/codex/hooks/policy.py:207` treats `apply_patch` as an edit, but
    `hooks.json` does not send it there.
  - The SessionStart hook already returns a warning as `systemMessage` and
    `additionalContext` (`dotfiles/claude/hooks/warn-stale-base.sh:32-34`).
- **Secrets:** `permissions.deny` has `Edit(~/.ssh/**)` (`dotfiles/claude/settings.json`). The sandbox is off, so a
  shell command can still read a credential file (ADR 0085). A secret can reach
  the context that way, and then a memory write.
- **Freeze:** `dotfiles/docs/IDEAS.md:39-40` calls a new deny hook "a new gate".
  The harness-v1 freeze excludes new gates.

### M1: episodic memory

Phase 0 is declined, so M1 waits. The fault is live. The freshness line in M2
shows it on every run.

### M2: memory health report (keep it; widen the scan)

Report only. T1 runs it. It reads all auto-memory folders, `~/.codex/memories/`
and the repository's `docs/MEMORY.md`.

Checks:
- each index `MEMORY.md` against 200 lines and 25 KB, with a usage line in
  Hermes's form `NN% — X/Y` (`tools/memory_tool_store.py:318-320`);
- index lines that name a missing topic file, and topic files that no index line names;
- entries that name a path that no longer exists;
- exact duplicate lines (Hermes drops them at load; M2 reports them);
- the age of the newest episodic index entry;
- the threat scan, with every class in the H2 table below.

Report the file, the line and the id. Never rewrite a memory file: Hermes
keeps the raw text so a person can see the hit (`tools/memory_tool_store.py:221-225`).

Option for later: run the same scan for the current project in the existing
SessionStart hook, as a warning. That is Hermes's load-time defense without the
redaction, and it adds no gate.

### H2: memory write guard (build it narrow, in two phases)

The decision stands. The guard denies only two classes: text a person cannot
see, and credentials. Everything else goes to the M2 report.

| Class | Id | Source | H2 | M2 |
|---|---|---|---|---|
| Invisible characters (15) | `invisible_unicode_U+XXXX` | `tools/threat_patterns.py:110-112` | Deny | Report |
| Unicode tag characters | `invisible_unicode_tag` (new) | `tools/ansi_strip.py:24-42` | Deny | Report |
| Assignment-shaped secret | `hardcoded_secret` | `tools/threat_patterns.py:102-104` | Deny | Report |
| Vendor-prefixed secret (56) | `vendor_secret` (new) | `agent/redact.py:147-216`, guards at `:589-590` | Deny | Report |
| Private-key block | `private_key` (new) | `agent/redact.py:521` | Deny | Report |
| JWT | `jwt` (new) | `agent/redact.py:555` | No | Report |
| All-scope text (11) | as in section 4 | `tools/threat_patterns.py` | No | Report |
| Context-scope text (17) | as in section 4 | `tools/threat_patterns.py` | No | Report |
| Strict text (5) | `send_to_url`, `context_exfil`, `ssh_backdoor`, `ssh_access`, `agent_config_mod` | `tools/threat_patterns.py` | No | Report |
| Hermes paths (2) | `hermes_env`, `hermes_config_mod` | `tools/threat_patterns.py` | No | Skip |

Why the line falls there:
- **Measured.** I ran the patterns over the 313 committed text files of this
  harness. The text patterns flag 9 lines in 8 files, and all are rule or test text.
  - `agent_config_mod` flags 4, `ssh_access` 2, and `prompt_injection`,
    `read_secrets` and `env_var_unset_agent` 1 each.
  - The invisible, tag, `hardcoded_secret`, vendor-prefix, private-key and JWT checks flag 0.
- **Memory notes here look like that text.** The notes in section 4 are normal
  for Jira and harness work, and strict scope blocks each one.
- **The earlier draft denied four more shapes.** `ssh_access` hits committed
  text. `exfil_curl` blocks any curl note with a `$…TOKEN` variable
  (`tests/tools/test_threat_patterns.py:195-202`). `send_to_url` and
  `ssh_backdoor` block ordinary notes too. `Edit(~/.ssh/**)` is already denied.
- **Hermes can block more.** Its memory holds about 2,200 characters of
  cross-task facts, and procedures go to skills (`tools/memory_tool.py:385-397`).
- **The two denied classes escape review.** A reader cannot see invisible
  text. A secret does harm before anyone reads it: it goes to the model provider each time the file loads.
- **The JWT check stays a warning.** Its one-part form matches any base64 JSON.

Hook rules:
- Remove one leading U+FEFF before the scan, as Hermes does (`agent/prompt_builder.py:98-99`).
  Windows editors add it, and W1 makes Windows likely.
- Check invisible and tag characters on the raw text. Apply NFKC before the
  patterns (`tools/threat_patterns.py:139-144`).
- Scan the whole `content` of a `Write` and the whole `new_string` of an `Edit`.
  Do not copy the 65,536-character cap.
- Do not deny duplicates. Hermes treats a duplicate as success
  (`tools/memory_tool_store.py:378-379`). The plan's H2 line lists "an exact
  duplicate line", so the plan must change. M2 reports duplicates instead.
- Deny U+200D everywhere, as the memory scan does. The cron scan allows it
  beside an emoji (`tools/cronjob_prompt_scan.py:103`). Memory notes need no emoji sequences.
- Return one deny reason with the id and the fix, as `first_threat_message()`
  does (`tools/threat_patterns.py:148-159`).
- Write it in Python with the standard library only, as H1 plans. One pattern
  module serves both M2 and H2.

Where it runs:
- **Claude:** `PreToolUse` on `Write|Edit` for paths under
  `~/.claude/projects/*/memory/`. One global hook covers all 17 folders.
- **Codex:** leave `~/.codex/memories/` to M2 for now. First check that Codex
  writes it through a tool that fires `PreToolUse`. Then add `apply_patch` to the matcher.
- **Known gap:** a shell append such as `echo >> MEMORY.md` passes a
  `Write|Edit` hook. M2 finds it on the next run. `memory-shield` also checks
  shell calls, at the cost of a command parser.

Phases, because of the freeze:
1. **Phase A, now:** M2, plus H2 in warn mode for the Deny rows. The write goes
   through, and the hook returns a warning. No gate. `warn-stale-base.sh` warns
   this way at SessionStart. Check which `PreToolUse` output field the model sees.
2. **Phase B, after the freeze:** the two classes switch from warn to deny. One ADR
   records both phases and the switch condition.

If you treat a safety deny hook as outside the freeze, skip Phase A. That choice is yours.

Verify:
- Before you build, log one `PreToolUse` payload for an auto-memory write. It
  confirms that Claude writes memory with `Write` or `Edit`.
- Add fixtures to `dotfiles/tools/tests/test-hooks.sh`:
  - one fixture for each denied id;
  - the 15 clean lines from `tests/tools/test_memory_tool.py:31-52`, which must pass;
  - a file that holds only a BOM, and a clean index of 30 KB.
- Run the probe over the committed harness text again. Expect zero denials.

### M3: memory review list (keep)

`/journey` also dates memory entries by file time (`agent/learning_graph.py:171-180`).
So a list of recently changed files with their first lines gives the same view.
Keep it read-only, and do not copy Journey's `delete` and `edit`.

### Do not copy

- External providers, with their prefetch and sync on every turn.
- The background memory review. The plan rejects a review every N turns.
- The 2,200- and 1,375-character budgets. Claude Code owns its limits, and M2 reports them.
- The strict-scope text patterns as deny rules.
- The 65,536-character scan cap.

### Open questions

- Does the installed Claude Code still have `MultiEdit`? This repository never
  names it. Check before you add it to a matcher.
- Does Codex fire `PreToolUse` for `apply_patch`? Does it write `~/.codex/memories/` through tools at all?
- The prefix table has no Atlassian or Figma token shape, and this machine uses
  both services. Add their prefixes only after you confirm them in the vendor docs.

## Sources

Hermes Agent, commit `5fea5a7a4bf6d02b3427fc0bcae95502222cea2e` (2026-10-17).

Read in full:
- `tools/memory_tool.py`, `tools/memory_tool_store.py`, `tools/threat_patterns.py`
- `tools/write_approval.py`, `tools/skill_provenance.py`
- `agent/memory_provider.py`, `agent/memory_manager.py`, `agent/memory_context.py`
- `agent/background_review.py`
- `hermes_cli/write_approval_commands.py`, `hermes_cli/subcommands/memory.py`, `hermes_cli/subcommands/journey.py`
- `tests/tools/test_threat_patterns.py`
- `plugin-catalog/holographic.yaml`

Read in part:
- `agent/redact.py` (1-40, 100-230, 504-600, 893-1012, 1155-1200, 1272-1290)
- `agent/system_prompt.py` (480-600, 736-800)
- `agent/agent_init.py` (1280-1400)
- `agent/turn_context.py` (730-790, 1120-1140)
- `agent/turn_finalizer.py` (750-800)
- `agent/tool_executor.py` (735-760)
- `run_agent.py` (750-840)
- `hermes_cli/config_defaults.py` (1295-1360)
- `agent/prompt_builder.py` (88-125)
- `agent/tool_dispatch_helpers.py` (545-580)
- `tools/skills_guard.py` (590-610)
- `agent/learning_graph.py` (1-12, 161-191)
- `hermes_cli/journey.py` (1-60)
- `agent/memory_caller_scope.py` (1-40)
- `plugins/memory/__init__.py` (1-60 and the function list)
- `plugins/memory/byterover/` and `plugins/memory/retaindb/` (`plugin.yaml`, module headers, method lists)
- `tools/ansi_strip.py`, `tools/approval_detection.py`, `tools/cronjob_prompt_scan.py` (the matching lines)
- `tests/tools/test_memory_tool.py` (28-112 and all test names)
- test names in `tests/tools/test_write_approval.py`, `tests/agent/test_background_review_memory_scope.py`,
  `tests/agent/test_memory_sync_redaction.py` and `tests/tools/test_memory_target_contract.py`
- `website/docs/user-guide/features/memory.md` (7-66, 176-234, 263-330, 425-441)
- `plugin-catalog/*.yaml` (the `name`, `tier` and `category` lines)
- `plugin-catalog/memory-shield.yaml`, `memory-rewind.yaml`, `memory-review.yaml` (the first 20 lines of each description)

Our repository: `dotfiles/claude/settings.json`, `dotfiles/claude/hooks/`,
`dotfiles/claude/references/documentation-practices.md`, `dotfiles/codex/config.toml`,
`dotfiles/codex/hooks.json`, `dotfiles/codex/hooks/policy.py`, `dotfiles/docs/MEMORY.md`,
`dotfiles/docs/IDEAS.md`, `dotfiles/docs/observation-log.md` and ADRs 0043, 0085, 0087 and 0088.

Machine state, checked with `ls` and counts only: `~/.claude/projects/*/memory/`,
`~/.codex/memories/` and `~/.config/superpowers/logs/episodic-memory.log`.
