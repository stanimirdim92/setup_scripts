# Hermes research: session storage and full-text search

Part of `../hermes-adoption-plan.md` (items F1 and F2). The source is a local
clone of `NousResearch/hermes-agent`, read on 2026-10-17. The commit is in
Sources. All line numbers refer to that commit.

## Coverage

**Read in full (Hermes):**
- `hermes_state.py`, `hermes_state_common.py`, `hermes_state_schema.py`;
- `hermes_state_fts.py`, `hermes_state_search.py`;
- `hermes_state_wal.py`, `hermes_state_readpool.py`, `hermes_state_health.py`;
- `hermes_state_maintenance.py`, `hermes_state_coverage.py`, `hermes_state_repair.py`;
- `tools/session_search_tool.py`;
- `evals/session_search_schema/README.md`.

**Read in part (Hermes):**
- `hermes_state_messages.py`: the write path in full (insert, batch append, replace, archive, compaction). The read helpers in part.
- `hermes_state_errors.py` (FTS and lock classifiers), `hermes_state_dbfile.py` (`collect_state_db_stats`), `hermes_state_sessions.py` (file removal), `hermes_state_lockowners.py` (header).
- `agent/redact.py`: the header, the switch, the prefix list and the entry point. Also its call sites in `tools/`, `agent/context_compressor.py` and `hermes_cli/session_export_md.py`.
- `hermes_cli/config_defaults.py`: the `sessions` block only (2261-2300).
- `website/docs/developer-guide/session-storage.md`: the FTS, contention and search sections.
- Tests: the files named in §7. For the other test files, I read only names and docstrings, with an AST parse (`python3 -I`).

**Grep only:**
- 13 other `hermes_state_*.py` modules mention FTS, prune or redaction in passing. None of them holds search logic.
- `run_agent.py` and `agent/session_persistence.py`, for redaction.

**Not read:**
- the other 27 of the 56 `hermes_state_*.py` modules. None of them mentions FTS, trigram, prune or redaction;
- the user guides `sessions.md`, `session-storage-recovery.md` and `state-db-recovery.md`. I read the code instead;
- the CJK tokenizer library;
- most of the 197 test files in `tests/hermes_state/`.

**Our side, read:**
- `tools/agent_sessions_mcp.py`, read only. Another session has uncommitted edits in it.
- the F, M and T items of `hermes-adoption-plan.md`;
- MCP registration: `claude/mcp/setup.sh`, `codex/config.toml`, `~/.claude.json`, `~/.codex/config.toml` and the Claude desktop config (grep only);
- the episodic-memory plugin 1.4.2 under `~/.claude/plugins/cache/superpowers-marketplace/episodic-memory/1.4.2/` (file list in Sources);
- the node ABI, from `~/.nvm/versions/node/v26.9.0/include/node/node_version.h`. I ran no node or npm;
- record types in 3 local Codex rollouts, counted with a script that printed no content;
- local Python SQLite behaviour, tested on in-memory databases with my own code.

**Our side, not checked:**
- the episodic database, archive and log. They are outside the read scope of this task;
- whether episodic search still answers. That needs a run.

## 1. File map

| Path | Lines | Role |
|---|---|---|
| `hermes_state.py` | 1730 | `SessionDB` facade with 15 mixins (`:461-466`); write retry; checkpoints; `DEFAULT_DB_PATH = <home>/state.db` (`:178`) |
| `hermes_state_common.py` | 1432 | Schema version, `SCHEMA_SQL`, FTS views, tables and triggers, the rebuild lock |
| `hermes_state_schema.py` | 1379 | Schema init, column reconcile, FTS migrations and recovery |
| `hermes_state_fts.py` | 453 | CJK index, FTS setup, fail-open, rebuild pacing |
| `hermes_state_search.py` | 1368 | `search_messages`, sanitizer, routing, rebuild steps, merge |
| `hermes_state_messages.py` | 1972 | Write path: insert, batch append, replace, compaction |
| `hermes_state_wal.py` | 669 | Journal mode policy |
| `hermes_state_readpool.py` | 259 | Read-only connection pool |
| `hermes_state_health.py` | 114 | Sticky corruption latch |
| `hermes_state_maintenance.py` | 552 | Prune, vacuum, automatic upkeep |
| `hermes_state_repair.py` | 1161 | Probes, and repair on a scratch copy |
| `hermes_state_dbfile.py` | 849 | Read-only stats for `hermes doctor` |
| `agent/redact.py` | 1366 | Secret redaction for tool output, logs and exports |
| `tools/session_search_tool.py` | 800 | The model-facing `session_search` tool |
| `tests/hermes_state/` | 200 files | 197 `test_*.py` files |

## 2. Schema and indexes

- **Version:** `SCHEMA_VERSION = 32` (`hermes_state_common.py:289`).
  - A new table or column needs no bump (`:284-288`). `_reconcile_columns` adds missing columns on open (`hermes_state_schema.py:756-787`).
  - The FTS layout has its own version, `FTS_STORAGE_VERSION = 3` (`hermes_state_common.py:298-312`).
- **Tables:** `sessions` has 64 columns (`:409-472`) and `messages` has 30 (`:478-507`). Search uses `role`, `content`, `tool_name`, `tool_calls`, `timestamp`, `active`, `compacted` and `display_kind`.
- **Word index** `messages_fts` (`:877-958`):
  - It reads the view `messages_fts_src`, which cuts tool rows to the first 8,192 characters (`:322`, `:881-887`).
  - `USING fts5(content, tool_name, tool_calls, content='messages_fts_src', content_rowid='id')` (`:889-895`).
  - Insert, delete and update triggers keep it in sync. The update trigger fires only `AFTER UPDATE OF content, tool_name, tool_calls, role` (`:932`).
  - Each trigger checks two rebuild markers in `state_meta`. A row is indexed when its id is at or below the progress marker, or above the high-water marker (`:849-876`).
- **Trigram index** `messages_fts_trigram`:
  - It covers every role except `tool`, with `content` and `tool_name` only (`:1003-1015`).
  - It leaves out `cron` and `subagent` sessions and delegate children (`:984-996`).
  - The comments give the reasons. Tool output is about 90% of message bytes, and a trigram index is about 2.6 times the text it covers (`:966-967`).
  - Delegate children were about 70% of the bytes on one install (`:977-979`).
- **CJK index** `messages_fts_cjk` (`hermes_state_fts.py:40-109`):
  - It uses a loadable `cjk_unicode61` tokenizer from `HERMES_FTS5_CJK_SO` or `<home>/lib/libfts5_cjk.so` (`:100-103`). It is on by default (`:106-109`).
  - Without the library, Hermes drops its triggers and sets `fts_cjk_stale` (`:243-279`).
  - The reason: short CJK terms fell back to `LIKE` and cost seconds of CPU per query (`:33-35`).
- **FTS5 probe:** `CREATE VIRTUAL TABLE temp._hermes_fts5_probe USING fts5(x)` (`hermes_state_schema.py:214`). Without FTS5, Hermes warns and disables search (`hermes_state_fts.py:230-241`).
- **Doc drift:** the developer guide says schema version 31 and `content='messages'` (`website/docs/developer-guide/session-storage.md:280`, `:313`). The code says 32 and a view. Trust the code.

## 3. Write path and secrets

- Every message goes through `_INSERT_MESSAGE_SQL` (`hermes_state_messages.py:32-38`) and `_insert_message_rows` (`:726-763`). The FTS triggers index each row in the same transaction.
- `_encode_content` stores non-text content as JSON behind a `\x00json:` prefix, and removes lone surrogates (`:110-112`, `:137-158`). It does not redact secrets.
- Batch appends take a `chunk_rows` size, because the FTS triggers run once per row (`:424-443`).
- Soft-archived rows (`active = 0`) stay in the FTS index, because the triggers do not watch `active` (`:837`). The search filter hides them (§4).
- Compaction sets `active = 0, compacted = 1`. Compacted rows stay searchable (`:969-1003`).

**Secrets:**
- Hermes stores user and assistant text as typed. I found no redaction of it on the write path.
- The tool layer redacts tool output before the agent stores it:
  - terminal output (`tools/terminal_tool_result.py:232-242`);
  - file reads (`tools/file_tools.py:485`);
  - code execution output (`tools/code_execution_tool.py:519-521`);
  - MCP connector error text, in force mode (`tools/connectors/mcp.py:418-430`).
- Compaction summaries and session exports always redact, in force mode (`agent/context_compressor.py:1169-1173`; `hermes_cli/session_export_md.py:169-179`).
- Redaction is on by default through `HERMES_REDACT_SECRETS` (`agent/redact.py:103`). The vendor prefix list has 56 patterns (`:147-216`). The entry point is `redact_sensitive_text` (`:893`).
- `state.db` and its `-wal` and `-shm` files get mode 0600 (`hermes_state.py:244-300`).
- Deleting a session also deletes its transcript files, which "can carry plaintext secrets" (`hermes_state_sessions.py:1619-1625`).

## 4. Search (`search_messages`)

**Sanitizer** (`_sanitize_fts5_query`, `hermes_state_search.py:817-852`), in this order:

1. Cut the query to 2,048 characters (`hermes_state_common.py:335`).
2. Hold balanced `"…"` phrases behind placeholders. A stray `"` becomes a space.
3. Replace each character of `+{}():"^@/#&|~[]<>,;!?$=\'` with a space (`:38`). Also remove `%`, unless the query has CJK text (`:837-839`).
4. Collapse runs of `*`. Drop a `*` at the start of a token.
5. Remove one `AND`, `OR` or `NOT` at each end. The match ignores case (`:844-845`).
6. Quote dotted, hyphenated and underscored terms in one pass (`:848`). Two passes would double-quote `my-app.config`.
7. Put the phrases back.

**Routing** (`_search_messages_impl`, `:1086-1190`):
- A `tool` role filter skips FTS and uses `LIKE` (`:1110-1112`).
- A stale index also uses `LIKE` (`:1113-1116`). When FTS is off, the result is empty (`:1117-1118`).
- CJK text goes to the CJK index (`_search_cjk`, `:1192-1219`).
- Latin text uses `messages_fts MATCH` with `snippet(…, -1, '>>>', '<<<', '...', 40)` (`:938`).
- The order is BM25 `rank`. When the caller asks for newest or oldest, time sorts first (`:58`).
- A syntax error (`OperationalError`) returns `[]`. Corruption (`DatabaseError`) starts fail-open and `LIKE` (`:1130-1144`).
- While a rebuild runs, a `LIKE` scan covers the rows that are not indexed yet (`:1146-1155`, `:1221-1236`).
- With zero hits, Hermes retries in this order:
  1. the CJK index, then the trigram index if every token has 3 or more characters (`:1157-1174`, `:891-896`);
  2. an OR-relaxed query, if there are 2 or more terms and no explicit `OR` or `NOT` (`:876-889`, `:1176-1189`). It skips CJK and stale cases.

**Visibility** (`:163-190`): `(active = 1 OR compacted = 1)` and `display_kind <> 'hidden'`. The `after` and `before` bounds filter `sessions.started_at` inside SQL.

**Result** (`:1032-1084`):
- Each hit has a snippet, plus one message before and one after it in the same session (`:60-73`).
- Context content is cut to 200 characters. The default limit is 20.
- A query slower than 1,000 ms is logged (`:27-33`).

**Operator case mismatch.** FTS5 treats only uppercase `AND`, `OR` and `NOT` as operators. Hermes compares them without case in three places (`:844-845`, `:883-885`, `:978`):
- `docker or tls` runs in FTS5 as three terms joined by AND;
- the OR relaxation then refuses it, because it sees an `OR`;
- the `LIKE` fallback runs the same query as `docker OR tls`.

On SQLite 3.46.1, `alpha or beta` found 0 rows and `alpha OR beta` found 3 (my in-memory test).

## 5. The model tool (`session_search`)

- **Call shapes** (`tools/session_search_tool.py:4-8`):
  - discover (`query`);
  - scroll (`session_id` and `around_message_id`);
  - read (`session_id` alone);
  - browse (no arguments).
- Every shape returns stored messages and makes no model call (`:8`, `:664`). The tool opens the database read-only (`:630-633`).
- **Discover** (`_discover`, `:354-431`):
  - It scans up to 300 rows (`:43`). The default role filter is user and assistant (`:370`).
  - It hides `kanban`, `subagent` and `tool` sessions (`:23`, `:371`). Title matches and browse hide them too (`:290`, `:494`).
  - It ranks `cron` sessions below the user's own sessions, with a stable sort (`:32`, `:378`).
  - A title match comes first (`:276-311`).
  - It keeps one hit per lineage. It skips the current lineage, unless that lineage has live context (`:394-416`).
  - Only the top hit gets full detail (`:420-421`).
  - With zero hits, the reply teaches `OR`, quoted phrases, `NOT` and `deploy*` (`:380-384`).
- **Context:** the tool does not use the 200-character context of `search_messages` (`:50`). It reads a window around the hit with `get_anchored_view(window=5, bookend=3)` (`:334`).
- **Caps:**
  - 1,200 characters per bookend message (`:326`) and 4,000 per window message (`:347`);
  - 2,000 characters per message in a read (`:40`). A read returns the first 20 and the last 10 messages (`:447-462`);
  - browse asks for `limit + 15` rows, with a 3 s timeout (`:493-494`).
- **Limits:**
  - `limit` is 3 by default, from 1 to 10 (`:585`);
  - `window` is from 1 to 20 (`:538`);
  - at most 20 `exclude_session_ids` (`:45`);
  - `after` and `before` take ISO dates or `24h`, `7d`, `2w` (`:47-48`).
- **Index status:** while a rebuild runs, the reply carries an `index_rebuild` note with a percentage (`:314-322`).
- **Schema size matters.** A smaller tool schema cut the cost from 1,570 to 695 tokens per call (`evals/session_search_schema/README.md`).
  - Accuracy rose from 49 to 52 of 54 cases.
  - The teaching text moved into reply hints.

## 6. Concurrency, upkeep and repair

**Writes** (`hermes_state.py`):
- Each write runs in `BEGIN IMMEDIATE` and retries the whole callback (`:1006-1123`). The SQLite timeout is only 1 s (`:800`).
- The retry budget is 20 s for normal writes, 60 s for transcript writes and 0.5 s for activity writes (`:484`).
- The jitter is 20 to 150 ms for the first 2 s, then 250 to 1,000 ms (`:497-499`).
- Every 50 writes, a PASSIVE checkpoint runs (`:501`).
- Every 1,000 writes, a bounded FTS merge runs: at most 500 pages and 4 commands per index (`:504`, `:1054-1059`).
- Hermes keeps `optimize` out of this path. It takes 9 to 18 s per index on a 10 GB database (`hermes_state_search.py:1341-1368`).

**Reads:** a pool of at most 8 read-only handles per file and 24 per process (`hermes_state_readpool.py:35`, `:44`). The busy timeout is 5 s (`hermes_state.py:195`).

**Journal mode** (`hermes_state_wal.py`):
- WAL is the default. `database.journal_mode` can choose `delete` (`:157-167`).
- On NFS, SMB, some FUSE, WSL1 and ZFS, Hermes falls back to the rollback journal and logs one ERROR (`:25-29`, `:343-416`). It does not refuse to open.
- On virtiofs or 9p mounts, it refuses to turn on WAL (`:177-184`, `:331-339`).
- It never switches a live WAL database back to DELETE (`:265-267`).
- SQLite 3.7.0 to 3.51.2 has the WAL-reset bug; 3.50.7 and 3.44.6 have the fix. With an affected library, Hermes does not turn on WAL for a non-WAL file (`:131-134`, `:450-485`).

**Rebuilds:**
- A rebuild indexes 500 rows per step. It then sleeps at least 4 times the step cost, with a 0.2 s floor (`hermes_state_fts.py:434-436`).
- The reason: one blocking rebuild held the write lock for about 16 minutes on a 25 GB database (`:429`).
- Each step claims its rows and writes its progress in one `BEGIN IMMEDIATE` transaction (`hermes_state_search.py:337-376`).
- A file lock, `<db>.fts_rebuild.lock`, lets one process rebuild (`hermes_state_common.py:1378`). It waits up to 120 s (`:1182`). A lock file that cannot open fails closed (`:1381-1388`).
- On POSIX, Hermes breaks a lock whose holder is provably dead (`:1248-1270`). The Windows `msvcrt` path has no such break (`:1348-1364`).
- `rebuild_fts` fails closed (`hermes_state_search.py:1295-1339`).

**Fail-open:** on index corruption, Hermes drops the FTS triggers inside `BEGIN IMMEDIATE` and sets `fts_stale` (`hermes_state_fts.py:354-426`). Search then uses `LIKE` until a later open rebuilds the index.

**Prune and vacuum** (`hermes_state_maintenance.py`):
- `prune_sessions` deletes ended sessions older than 90 days. It skips pinned sessions and removes their transcript files (`:332-376`).
- Automatic pruning is off by default (`hermes_cli/config_defaults.py:2271`). When it is on, it runs at most once per 24 h (`:444-552`).
- VACUUM needs pruned rows, 30 days since the last VACUUM, a free-page ratio above 0.25 and no other holders.

**Health and repair:**
- A corruption verdict stays set per process and path until restart (`hermes_state_health.py:15-17`). A store that flips between ok and corrupt would hide the fault.
- The repair probe runs `integrity_check`, a read of each FTS table, and an FTS write probe that it always rolls back (`hermes_state_repair.py:757-833`).
- The write probe catches a store where reads pass but every append fails (#100227).
- Repairs run on a scratch copy, least destructive first: rebuild FTS, reindex, dedupe the schema, drop the FTS rebuild (`:1129-1139`).
- `hermes doctor` reads stats through `collect_state_db_stats` (`hermes_state_dbfile.py:745-815`). It opens read-only with a 2 s timeout, avoids `SessionDB` and never raises.

## 7. Tests worth copying

**Sanitizer** (`tests/hermes_state/test_hermes_state.py:1041-1078`):
- `C++` loses `+`. `"unterminated` loses `"`. `(problem` and `{test}` lose the bracket.
- `hello AND` gives `hello`, and `OR world` gives `world`.
- `***` gives an empty query, and `deploy*` stays.
- `TODO: fix` gives `TODO fix`, so there is no column filter.
- 50,000 quotes plus 10,000 words finish in under 1 s.

**Character class** (`test_hermes_state.py:6435-6514`). Each input must parse against a real FTS5 table:
- `it's`, `gateway/run.py`, `user@host`, `a,b`, `why?`, `e=mc2`;
- `a;b`, `a!b`, `a&b`, `a|b`, `x~y`, `#tag`, `$dollar`, `[bracket]`, `<tag>`, `C:\path\file`;
- `"exact phrase"` stays; `my-app.config.ts` gets quotes; `gate*` matches; `50%` loses `%`.

**OR relaxation** (`test_search_or_relaxed_fallback.py`):
- `sarah standup scheduled` becomes `sarah OR standup OR scheduled`.
- `alpha AND beta` becomes `alpha OR beta`.
- `"docker networking" tls` becomes `"docker networking" OR tls`.
- No rewrite for one term, one phrase, `alpha OR beta` or `python NOT java`.
- No rewrite for a CJK miss. The role filter still applies. Nonsense still returns nothing.

**Index behaviour** (all in `tests/hermes_state/`):
- `test_fts_update_of_narrowing.py`: an update to another column does not touch the index.
- `test_fts_tool_write_bounds.py`: the index keeps a bounded prefix of tool rows, and `LIKE` finds the rest.
- `test_fts_index_fail_open.py` and `test_fts_runtime_rebuild.py`: stale search keeps `NOT`; corruption of the source fails closed.
- `test_state_db_fts_segment_collision_probe.py`: the write probe (#100227).
- `test_fts_projection_integrity.py`: drift between index and source (#114169).
- `test_readonly_fts_decode_error.py`: a bad byte in a read-only open (#98924).
- `test_fts_trigram_cron_exclusion.py` and `test_fts_trigram_subagent_exclusion.py`.

**Tool** (`tests/tools/test_session_search.py`):
- the user's sessions rank above cron, and cron stays reachable;
- compacted rows are found, and rewound rows are not;
- the time window applies in SQL, not as a later filter;
- `exclude_session_ids` drops the whole lineage;
- reads are capped.

## 8. For this harness

### Facts on our side (checked 2026-10-17)

**Episodic memory (plugin 1.4.2):**
- Text mode is not full-text search. It is one `LIKE '%query%'` over user and assistant text, newest first, with no rank (`dist/search.js:148-161`).
  - A query of several words matches only that exact substring.
  - `%` and `_` in a query act as wildcards.
  - The plugin stores tool calls (`dist/db.js:139-148`), but text mode does not search them.
- The default mode is `both`, vector plus text (`dist/search.js:115`).
- The native module targets ABI 115 (`node_modules/better-sqlite3/build/config.gypi:361`). The `node` on PATH, v26.9.0, has ABI 147 (`node_version.h:104`). This matches the plan's `ERR_DLOPEN_FAILED` finding.
- better-sqlite3 loads its native part only when a database opens (`lib/database.js:45-48`). So the MCP server can start, and the fault appears on first use.
- The sync copies transcripts into its archive before it opens the database (`dist/sync.js:66-118`).
  - Sources run in this order: Claude, then Codex (`dist/paths.js:35-46`). The first open error ends the run (`dist/sync-cli.js:111-120`).
  - Inference, not run: Claude transcripts still reach the archive, but no source gets indexed, and Codex is not copied.
  - A later fix needs a catch-up run too. A normal sync skips a file whose archive copy is current (`dist/sync.js:28-33`).
  - `index-cli` has an unprocessed mode and a repair mode (`dist/indexer.js:211`, `dist/index-cli.js:58-62`).
- No part of the plugin reports the fault:
  - its `doctor` checks only the Codex setup (`dist/doctor.js:41-97`);
  - the MCP wrapper checks that packages exist, not that they load (`cli/install-check.js`);
  - the session-start hook runs the sync in the background (`hooks/hooks.json`).
- The plan says search still answers from the old index (plan line 38). I could not check this. A search opens the database first (`dist/search.js:121`), so on node v26 it should fail too.

**Transcript retention:**
- `cleanupPeriodDays` is not set in `claude/settings.json`, the target of the `~/.claude/settings.json` link.
- The oldest top-level Claude transcript is dated 2026-09-17, 30 days ago. This matches the documented Claude Code default of 30 days. I did not verify that default here.
- So raw Claude transcripts from the episodic gap start to go on 2026-10-18. Nine of them are dated 2026-09-18 or 2026-09-19.
- If the archive inference is right, copies survive in the plugin's archive. That folder is internal to the plugin.

**`tools/agent_sessions_mcp.py`** (535 lines now, 411 in commit 504215e):
- Its contract is metadata only: "No file contents, no tool output" (`:19-21`).
- It reads the first 400 lines and the last 96 KiB of each file (`:31-32`). `text_of` keeps only the first text block (`:59-70`).
- It parses three formats: Claude, Codex and Gemini. `--serve` also runs an HTTP dashboard (`:429`, `:509-531`).
- Only the Claude desktop app registers it (`~/.config/Claude/claude_desktop_config.json`). `~/.claude.json`, both Codex configs and `claude/mcp/setup.sh` do not.
- The untracked `tools/agent_deck.py` imports it.
- So the plan's "already parses Claude and Codex transcripts" (plan line 252) overstates the reuse.

**Codex rollouts:**
- The same user and assistant text appears twice: in `response_item` messages and in `event_msg` `item_completed` items.
- In one local rollout, 36 of 73 item texts repeated a message text.
- Rollouts also hold `developer` messages and injected context.

**Local SQLite** (Python 3 standard library, in-memory tests):
- version 3.46.1, with FTS5 and the trigram tokenizer;
- inside the WAL-reset-bug range (`hermes_state_wal.py:131-134`);
- operators are case-sensitive (§4).

**Repo:** `tools/doctor.sh` does not exist yet (T1). Tool tests live in `tools/tests/`.

### F1: watch, do not fix (re-judged)

The previous version began F1 with "Fix it (M1)". The user declined Phase 0, so F1 now only reports. Each check below is deterministic and changes nothing. They fit Phase 1.

1. **Native module line (T1).** Compare `node_module_version` in the plugin's `config.gypi` with `node -p process.versions.modules`. Report FAIL on a mismatch.
2. **Freshness line (M2, run by T1).** Read `MAX(timestamp)` per `harness` from `exchanges`, read-only. Compare it with the newest transcript time per agent.
   - One line per agent catches a parser that drops only Codex.
   - Do not query `vec_exchanges`, because standard `sqlite3` has no `vec0` module. Test the `exchanges` read in T1's fixtures.
   - Keep this line in one place, M2's script. T1 calls it.
3. **Retention line (T1).** Print `cleanupPeriodDays`, or 30 when it is unset, next to the index age. Proposed rule: FAIL when the index age is within 7 days of it.

Drop the canary. The per-agent freshness line catches the same faults. A canary also needs a fake transcript in `~/.claude/projects`, which session lists would show. It also needs node to run a search.

Keep the Hermes rule: report a fault where the user looks. T3 runs T1 weekly and alerts once per new problem. Hermes does the same with a read-only stats call that never raises (`hermes_state_dbfile.py:745-815`). An upstream issue for a session-start warning stays optional.

**Decision for the user (time-sensitive).** Raw transcripts from the gap start to go on 2026-10-18. Phase 0 stays declined. The options are:
- raise `cleanupPeriodDays` in `claude/settings.json`, for example to 365. It is small and reversible, and it keeps every later option open. The cost is more plaintext transcripts on disk;
- do M1 now;
- accept the loss.

### F2: own FTS5 search (re-judged)

**Trigger.** The plan says "only if F1 fails twice". The previous version said "again". With M1 declined, F1 cannot fail, so neither trigger works.
- Proposed trigger: the T1 freshness line reports FAIL on two weekly runs in a row.
- With M1 declined, this fires about two weeks after T1 and T3 land. So the real choice is M1 or F2.
- F2 stays in Phase 4, with an ADR.

The new facts make F2 stronger than before:
- episodic text mode is a substring scan, not ranked search;
- episodic breaks on node upgrades, and nothing reports it;
- Python's `sqlite3` is in the standard library, so F2 has no native module to rebuild. FTS5 and trigram work on this machine.

**Design changes from the previous version:**
- **Own module and MCP server,** for example `tools/session_index.py`, not a tool inside `agent_sessions_mcp.py`. The reasons:
  - that file promises metadata only, and it has an HTTP mode;
  - it reads only the head and tail of each file;
  - another session owns it now.

  Register the new server in `claude/mcp/setup.sh` and `codex/config.toml`. The alternative is to widen the lister's contract. Decide this in the ADR.
- **No T2 dependency.** Index Claude and Codex only, from day one.
- **One standalone FTS5 table,** with metadata in `UNINDEXED` columns, plus a small `files` table for offsets.
  - This gives one write per message, no triggers and no index drift.
  - Hermes needs a test file for drift between index and source (`test_fts_projection_integrity.py`).
- **Rollback journal, not WAL.** The local SQLite is in the WAL-reset-bug range, and F2 has one writer.
- **Writes:** claim the work and store the file offset in one `BEGIN IMMEDIATE`, as Hermes does (`hermes_state_search.py:337-376`). Set a busy timeout. Two MCP processes then cannot index the same bytes twice.
- **Reading files:**
  - Index only complete lines. Store the offset after the last newline.
  - If a file shrank or its first line changed, delete its rows and index it again.
  - If a file is gone, keep its rows. The index then outlives the 30-day cleanup.
- **What to index:**
  - Claude: `user` and `assistant` text blocks. Skip `isSidechain` and `isMeta` lines, as the lister does (`agent_sessions_mcp.py:195`, `:205`).
  - Codex: `response_item` messages with role `user` or `assistant` only. Skip `event_msg` items, which repeat them, and `developer` messages.
  - Skip injected context. Reuse the prefixes in the lister's `SKIP_PREFIXES` (`agent_sessions_mcp.py:34-35`).
  - Skip tool output and subagent transcripts in v1. Hermes also hides subagent sessions (`session_search_tool.py:23`).
- **Secrets:** scrub vendor prefixes before insert, with the same list as the H2 memory guard. Keep one list in the harness. Set the file mode to 0600, as Hermes does (`hermes_state.py:244-300`).
- **Query builder,** simpler than the seven Hermes steps. On SQLite 3.46.1, 40 hostile inputs parsed with these rules. Only empty queries needed the guard in step 5.
  1. Cut the query to 2,048 characters.
  2. Split it into balanced `"…"` phrases and words.
  3. Keep uppercase `AND`, `OR` and `NOT`. Of two adjacent operators, keep the last. Drop operators at either end.
  4. Put every other word in double quotes, and double any `"` inside it. Keep one trailing `*` outside the quotes.
  5. If nothing is left, return no results and a hint. Do not run `MATCH`.
- **Search:** BM25 with `snippet`. With zero hits, retry once with `OR` between the terms. Drop lowercase `and`, `or` and `not` from that retry, because they match almost every row.
- **Reply:**
  - snippet, one message before and one after (200 characters each), session id, agent, project and time;
  - the index status in every reply, as Hermes does (`session_search_tool.py:314-322`);
  - usage hints in the reply, not in the tool schema (`evals/session_search_schema/README.md`).
- **No FTS5:** say so in T1 and in the reply. Do not add a `LIKE` fallback. For native Windows, W1 must confirm FTS5 in its Python build.
- **History depth:** the first build sees only 30 days of Claude history. Older history is only in the episodic archive, which is internal to the plugin. The ADR must decide if a one-time import is worth that coupling.
- **Tests:** fixture transcripts for both agents, a Codex duplicate pair, a shrunk file and a partial last line. Use the Hermes cases in §7 as inputs.

### Corrections for the plan

- Line 29 and lines 239-241: episodic text mode is a substring `LIKE`, not full-text search.
- Line 38: "search still answers" is not verified. On node v26, a search should fail at the database open.
- Lines 249-251: the F1 and F2 text assumes M1, which the user declined.
- Lines 252-253: `agent_sessions_mcp.py` reads only heads and tails, for metadata.

## Sources

Hermes commit `5fea5a7a4bf6d02b3427fc0bcae95502222cea2e` (2026-10-17). Paths are relative to the repository root.

- `hermes_state.py`
- `hermes_state_common.py`
- `hermes_state_schema.py`
- `hermes_state_fts.py`
- `hermes_state_search.py`
- `hermes_state_messages.py` (part)
- `hermes_state_wal.py`
- `hermes_state_readpool.py`
- `hermes_state_health.py`
- `hermes_state_maintenance.py`
- `hermes_state_coverage.py`
- `hermes_state_repair.py`
- `hermes_state_errors.py` (part)
- `hermes_state_dbfile.py` (part)
- `hermes_state_sessions.py` (part)
- `hermes_state_lockowners.py` (part)
- `tools/session_search_tool.py`
- `agent/redact.py` (part)
- `tools/terminal_tool_result.py`, `tools/file_tools.py`, `tools/code_execution_tool.py`, `tools/connectors/mcp.py` (redaction call sites)
- `agent/context_compressor.py`, `hermes_cli/session_export_md.py` (redaction call sites)
- `hermes_cli/config_defaults.py` (part)
- `evals/session_search_schema/README.md`
- `website/docs/developer-guide/session-storage.md` (part)
- `tests/hermes_state/test_hermes_state.py` (part) and the FTS test files named in §7
- `tests/tools/test_session_search.py` (part)

Episodic-memory plugin 1.4.2, under `~/.claude/plugins/cache/superpowers-marketplace/episodic-memory/1.4.2/`:

- `dist/search.js`, `dist/db.js`, `dist/sync.js`, `dist/sync-cli.js`, `dist/paths.js`, `dist/doctor.js`
- `dist/indexer.js` (part), `dist/index-cli.js` (part), `dist/mcp-server.js` (grep)
- `cli/episodic-memory.js`, `cli/mcp-server-wrapper.js`, `cli/install-check.js`, `hooks/hooks.json`
- `node_modules/better-sqlite3/lib/database.js` (part), `node_modules/better-sqlite3/build/config.gypi`

Our repository (`dotfiles/`): `tools/agent_sessions_mcp.py`, `docs/hermes-adoption-plan.md`, `claude/settings.json`, `claude/mcp/setup.sh` and `codex/config.toml`.
