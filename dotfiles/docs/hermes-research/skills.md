# Hermes research: skills

Part of `../hermes-adoption-plan.md` (items S1, S2 and S3 `/lesson`). The
source is a local clone of `NousResearch/hermes-agent` at commit `5fea5a7`,
read on 2026-10-17. Hermes paths are relative to that repo root. Paths that
start with `dotfiles/` are in this repository.

No Hermes code or test was run. Every Hermes fact below comes from reading
code, tests and docs.

## Coverage

**Read in full:**
- review and capture: `agent/background_review.py`, `agent/learn_prompt.py`, `agent/review_engine.py`, `tools/skill_provenance.py`;
- write path: `tools/skill_manager_tool.py`, `tools/skill_manager_guards.py`, `tools/skill_manager_batch.py`, `tools/write_approval.py`, `hermes_cli/write_approval_commands.py`;
- checks: `tools/skill_linter.py`, `tools/skills_guard.py`;
- load path: `tools/skills_tool.py`, `agent/skill_commands.py`;
- lifecycle: `tools/skill_usage.py`, `agent/curator.py`;
- rules and tests: `skills/AGENTS.md`, `tests/skills/test_authoring_standards.py`.

**Read in part:**
- `agent/skill_utils.py`: the parser, gates, roots, project trust and the description limit. Lines 200-380, 660-714 and 737-824 were not read.
- `tools/skill_ledger.py`: the header, paths, entry shape, size cap and rollback.
- The review cadence lines in `agent/agent_init.py`, `agent/turn_iteration_prep.py`, `agent/tool_executor.py`, `agent/turn_context.py`, `agent/turn_finalizer.py` and `run_agent.py`.
- `agent/prompt_builder.py`: the skill guidance and the skill index text.
- `hermes_cli/config_defaults.py`: the `auxiliary`, `memory`, `skills` and `curator` blocks. `cli-config.yaml.example`: the `skills` block.
- Command handlers: `/refine` and `/learn` in `hermes_cli/cli_commands_mixin.py`, `/refine` in `tui_gateway/methods_slash.py`, `usage` and `purge` in `hermes_cli/curator.py`.
- Hub install: `hermes_cli/skills_hub.py:791-898` and `tools/skills_hub_install.py:60-186`.
- Docs: `website/docs/user-guide/features/skills.md` and `memory.md`, the review and approval sections only.
- Tests: the names and counts of the test files in Sources. For the `tests/skills/` contract tests, only the docstrings. Parts of the skill manager, review and linter tests.

**Not read:**
- the other hub adapters and `skills_sync*` (hub sources, bundled-skill sync on update);
- the extra scanners `skillevaluator_scan.py` and `skills_ast_audit.py`;
- `skills_tool_dedup`, `skills_tool_plugin`, `skills_tool_setup` and `skill_bundles.py`;
- `hermes_cli/skills_config.py`, the other `hermes skills` subcommands and the web routers;
- `agent/curator_backup.py` (only its config keys were read);
- the website pages `curator.md` and `creating-skills.md`;
- the 58 bundled and 153 optional skill bodies (counted only);
- most test bodies.

These parts do not change S1, S2 or S3. The reading time went to the write
path and the review loop instead.

## 1. File map

| Path | Lines | Role |
|---|---|---|
| `agent/skill_utils.py` | 871 | Frontmatter parser, gates, roots and precedence, project trust and quarantine, index description limit |
| `tools/skills_tool.py` | 765 | `skills_list` and `skill_view`; usage count on view |
| `agent/skill_commands.py` | 1001 | `/<skill>` slash commands, preload, stacking |
| `tools/skill_manager_tool.py` | 928 | `skill_manage`: validation, actions, write gate, scan, lint, locks |
| `tools/skill_manager_guards.py` | 252 | Read-before-write and delete guards |
| `tools/skill_manager_batch.py` | 308 | Atomic batches of up to 20 operations |
| `tools/write_approval.py` | 413 | Opt-in approval gate and the pending store |
| `hermes_cli/write_approval_commands.py` | 188 | `/skills pending`, `approve`, `reject`, `diff` |
| `tools/skill_linter.py` | 215 | Advisory lint |
| `tools/skills_guard.py` | 958 | Regex threat scanner and install policy |
| `tools/skill_provenance.py` | 44 | Write origin and the "attended" flag |
| `tools/skill_usage.py` | 748 | `.usage.json`, provenance, archive and restore |
| `tools/skill_ledger.py` | 633 | Audit ledger, blobs, rollback |
| `agent/background_review.py` | 1349 | The review fork and its prompts |
| `agent/curator.py` | 1212 | Stale and archive pass, optional LLM consolidation |
| `agent/learn_prompt.py` | 197 | `/learn` prompt |
| `agent/review_engine.py` | 195 | `/review`: an independent reviewer subagent |
| `skills/AGENTS.md` | 79 | Authoring rules (HARDLINE) and curator invariants |
| `tests/skills/` | 33 files | Authoring standards, doc contracts, and tests for about 25 single skills |

Hermes ships 58 bundled skills in `skills/` and 153 optional skills in
`optional-skills/` (count of `SKILL.md` files).

## 2. Formats

**Frontmatter.**
- The parser strips a BOM and splits on `\n---\s*\n`. It loads YAML and falls back to `key: value` lines on a parse error (`agent/skill_utils.py:64-85`).
- Fields: `name`, `description`, `version`, `author`, `license` and `platforms` (`skills/AGENTS.md`). Under `metadata.hermes`: `tags`, `category`, `related_skills` and `config` (20-22).
- Gates decide if a skill is available on this host: `platforms` (`agent/skill_utils.py:89-160`), `environments` (162-170) and `requires_apps` (172-194).
- Conditions under `metadata.hermes` (721-727): `fallback_for_toolsets`, `requires_toolsets`, `fallback_for_tools`, `requires_tools`, `session_platforms`.

**Limits** (`tools/skill_manager_tool.py:108-113` unless noted):

| Limit | Value | Applies to |
|---|---|---|
| Name | 64 chars, `^[a-z0-9][a-z0-9._-]*$` | Every write |
| Description | 1,024 chars | Every write |
| Description in the index | 60 chars; longer text is cut to 57 plus "..." (`agent/skill_utils.py:827, 836-839`) | The system prompt |
| Description on create | 60 chars (146-179) | Create only; edits skip it (148-149) |
| Body | 100,000 chars | Every write |
| One support file | 1 MiB | `write_file` |
| Support folders | `references`, `templates`, `scripts`, `assets` | `write_file` and `remove_file` only (355-372) |
| Body soft budget | 24,000 chars (`tools/skill_linter.py:56`) | A lint warning |

**Usage record.** One record per skill in `~/.hermes/skills/.usage.json`
(`tools/skill_usage.py:51-52, 348-353`):
- `created_by`: `agent`, `learn`, `installed` or none (522-542);
- counts: `use_count`, `view_count`, `patch_count`, `patch_generation`, `last_reused_patch_generation`;
- times: `last_used_at`, `last_viewed_at`, `last_patched_at`, `created_at`, `first_seen_at`, `archived_at`;
- `state` (`active`, `stale` or `archived`) and `pinned`.

The last-activity time is computed and excludes `created_at` (123-127).
`created_by: agent` lets the curator manage a skill. It is not proof of
authorship (290-297).

**Ledger.** One JSON line per change in `~/.hermes/skills/.curator_ledger.jsonl`.
Blobs go under `~/.hermes/.curator_backups/blobs/` (`tools/skill_ledger.py:84-89`;
`hermes_cli/config_defaults.py:1482-1485`).
- Entry: `id` (12 hex chars), `ts`, `actor` (`curator`, `agent` or `user`), `action`, `skill`, `evidence`, `before` and `after` (`tools/skill_ledger.py:37, 308-313`).
- `before` and `after` list only the changed paths, with their sha256 (286-295).
- The cap is 5 MB, trimmed to 80% (38, 340-369; `skills.ledger_max_bytes`, `hermes_cli/config_defaults.py:1490`).
- It is telemetry, not a gate. A ledger failure never blocks a write (`tools/skill_ledger.py:1-9`).

**Pending record**, used only when approval is on (`tools/write_approval.py:74-89`):
`id` (8 hex chars), `subsystem`, `action`, `summary`, `origin`, `created_at`
and `payload`. It holds no base hash. It lives in
`<HERMES_HOME>/pending/{memory,skills}/<id>.json` (65-66).

## 3. Discovery and loading

- **Roots and precedence:** project, then local, then the create folder, then external folders (`agent/skill_utils.py:385-408`). An ambiguous name is refused (436-447).
- **Project skills:** `.hermes/skills` and `.agents/skills` in a trusted project, never from the home folder (501-556, 530-531). Each one is scanned. A "dangerous" verdict or a scanner error quarantines it (619-642).
- **Progressive disclosure:**
  1. The system prompt lists each name with a description cut to 60 chars (`agent/prompt_builder.py:1363-1383`).
  2. `skill_view(name)` loads the body (`tools/skills_tool.py:592-694`).
  3. `skill_view(name, file_path)` loads one support file.

  A load warning never blocks (575-589). A quarantined skill is refused (551-560). A mid-session index change arrives as a note (`agent/skills_index_delta.py:1-14`).
- **Usage on load:** a view adds one view and one use. A byte-identical repeat view returns a short stub and adds nothing (`tools/skills_tool.py:737-760`). A slash command adds one use (`agent/skill_commands.py:419-432`).
- **Slash commands:** each skill is `/<slug>` (`agent/skill_commands.py:85-89`). A name that collides with a built-in command is skipped, and `/skill <name>` still works (464-504). Up to 5 skills stack in one message (832). Preload and `auto_load` are at 926-1001.
- **Compaction:** a pruned skill leaves a `[SKILL_PRUNED]` marker, and the prompt says to reload it (`agent/prompt_builder.py:258-264`).
- **Hub install:** quarantine, scan, apply the trust policy, then ask the user (`hermes_cli/skills_hub.py:791-898`; `tools/skills_hub_install.py:60-186`).

## 4. Triggers and prompts

### 4.1 Foreground prompt

The main agent also edits skills, with no review fork:
- The guidance says to "record it with skill_manage for future reuse" (`agent/prompt_builder.py:259`).
- The index text says the agent "MUST load" a matching skill (1365).
- It says to fix a broken skill with `skill_manage(action='patch')` (1373).
- After hard tasks it says to "offer to save as a skill" and to "update it before finishing" (1374-1375).

### 4.2 Background review cadence

The previous version of this file did not find this. Two counters decide
when a review fork starts. Both default to 10.

| | Skill review | Memory review |
|---|---|---|
| Config key | `skills.creation_nudge_interval` | `memory.nudge_interval` |
| Code default | 10 (`agent/agent_init.py:1388-1390`) | 10 (`hermes_cli/config_defaults.py:1321`; `agent/agent_init.py:1304, 1333`) |
| Counts | One agent-loop iteration (one model call) while `skill_manage` is available (`agent/turn_iteration_prep.py:165-167`) | One user turn while the memory tool and store exist (`agent/turn_context.py:758-767`, called at 1132) |
| Resets | A `skill_manage` call (`agent/tool_executor.py:749-750`), or a fire | A `memory` call (747-748), or a fire |
| Per-turn reset | None (`agent/turn_context.py:601-602`) | None; on resume it is user turns modulo the interval (750-755) |
| Checked | At turn end (`agent/turn_finalizer.py:762-769`) | At turn start; the spawn happens at turn end |

So 10 model calls with no `skill_manage` call start a skill review at the end
of that turn. Every tenth user turn with no memory write starts a memory review.

**Spawn rules:**
1. The turn has a final response, is not interrupted, and has no `skip_background_review` (`agent/turn_finalizer.py:781-791`).
2. A subagent never reviews automatically (`run_agent.py:765-766`).
3. `auxiliary.background_review.enabled` must be true. The default is true (`hermes_cli/config_defaults.py:810`). A config read error leaves it on and logs a warning (`agent/background_review.py:243-250`).
4. Safe workers and finite gateway turns skip it (234-238). Cron (`cron/scheduler.py:2523`) and managed workers (`agent/managed_worker.py:372`) set `skip_background_review`.
5. Only one review runs at a time per agent (`agent/background_review.py:75-89`).
6. On the managed local model server, the review waits for machine idle (`run_agent.py:782-785`).

Hermes's own estimate is about 30K tokens per review (`agent/turn_finalizer.py:778`;
`cron/scheduler.py:2523`).

### 4.3 The review fork

- It runs in a daemon thread with its own counters set to 0. It does not save a session (`agent/background_review.py:995, 1002-1005`).
- It stops after 16 iterations (173).
- Its input budget is 75% of the context window, at most 600,000 tokens (180-181). It is 120,000 tokens when the window is unknown (182, 204-212). A value of 0 or less means no cap (215-225).
- On a different model it replays a digest with the last 24 messages (332-362).
- Tools (1088-1128):
  - the skills tools;
  - `memory`, only when memory is on and this run reviews memory (1094-1098);
  - `read_file` and `search_files` (1103).

  Any other tool gets a deny message (1170-1178). Dangerous commands are denied automatically (1051-1055).
- Read marks reset when a review starts (1179-1182).
- The user sees a summary of the actions (708-742, 1211-1216). The token cost goes to the parent session (777-795).

### 4.4 The review prompts (paraphrased)

The skill prompt is `_SKILL_REVIEW_PROMPT` (`agent/background_review.py:448-517`).

- **Stance:** "Be ACTIVE" (449). "Nothing to save." is allowed but should not be the default (514-516).
- **Signals** (456-467):
  - a correction of style, format or workflow;
  - a new technique or fix;
  - a loaded skill that proved wrong.
- **Preference order** (468-497):
  1. Patch a skill loaded in this session. Any loaded skill qualifies: "hand-written, installed, bundled, and pinned" (473-475).
  2. Patch an existing umbrella skill.
  3. Add a support file under an umbrella, with a pointer line in its `SKILL.md`.
  4. Create a new umbrella skill. Its name is class-level: no PR number, error string or "fix-X" (493-497).
- **Read before write** (498-505): view the target in this review. A quote in the transcript does not count. After a refusal, view once and retry once.
- **Preferences go in the skill** (506-510): memory says who the user is; a skill says how to do a task.
- **No delete** in a review (511-512).
- **Lesson layer** (`_LESSON_LAYER_BLOCK`, 393-420):
  - the procedure comes first;
  - a pitfall is "a generalizable rule + one clause of WHY" (401);
  - no PR or issue numbers, dates, ticket ids or quoted user text (404-406);
  - one rule per lesson; search for an existing one first (407-409);
  - do not repeat `AGENTS.md` (410-412);
  - use topical `references/` files, not one file per session (413-417);
  - fix the wrong sentence in place; add no "UPDATE:" line (418-419).
- **Do not capture** (`_DO_NOT_CAPTURE_BLOCK`, 423-446):
  - environment failures;
  - negative claims about tools;
  - transient errors;
  - one-off narratives;
  - unresolved failures.

  Capture the setup fix instead.
- The combined prompt keeps each preference in one place only (519-569, 560-563).

### 4.5 `/refine`, `/learn` and `/review`

- **`/refine [focus]`** runs the same fork on demand, for memory and skills (`hermes_cli/cli_commands_mixin.py:1913-1931`). It appends the focus text to the prompt (`agent/background_review.py:1327-1331`). Every review guard still applies, but the run is marked attended (`tools/skill_provenance.py:29-44`). The TUI version reads the saved transcript and refuses while the agent runs (`tui_gateway/methods_slash.py:78-79, 99-109`).
- **`/learn`** builds a skill from a folder, a URL or notes (`agent/learn_prompt.py`).
  - With no argument it captures "the workflow we just went through" (139-142).
  - It treats the source as data and drops invisible and bidi Unicode (125-133).
  - It checks for an existing skill first (172-180).
  - Its authoring rules ask for a description of 60 chars or less (11-81).
  - The new skill gets `created_by: learn` (`tools/skill_usage.py:522-534`).
- **`/review`** starts an independent reviewer subagent (`agent/review_engine.py`). It finds up to 8 skills that the parent loaded, from the preload marker and from `skill_view` calls (70-96). It passes the last 10 messages, each cut to 12,000 chars (22, 26).

No Hermes command drafts a lesson for review before the write. `/refine` and
`/learn` write directly while approval is off.

### 4.6 Curator

- **Defaults:** a run every 168 hours, after 2 idle hours. Stale after 14 days, archived after 30. LLM consolidation is off (`agent/curator.py:31-35`). `prune_builtins` is off, `archive_ttl_days` is 0, and the backup keeps 2 (`hermes_cli/config_defaults.py:1496-1521`).
- **Trigger:** there is no daemon. A start-up thread calls it in the CLI (`hermes_cli/cli_tui_runtime_mixin.py:382-396`), the gateway (`gateway/run.py:4371-4373`) and the web server (`hermes_cli/web_server_sessions.py:510-515`). The first run only starts the clock (`agent/curator.py:160-179`). A run claim uses `O_EXCL` (1162-1190).
- **Deterministic pass** (209-261):
  - it touches only `created_by: agent` skills;
  - it skips pinned skills and skills that a cron job uses;
  - it never archives a young skill that was never used (248-253);
  - a stale skill that is used again becomes active (259-260).
- **LLM pass,** opt-in: skills tools only, no terminal, under the review origin (1105-1127, 434-437). A backup runs first (931-942).
- **The prompt** (290-468): use count is "absence of evidence either way" (337). It also says "fewer than 10 archives, you stopped too early" (443-446).
- **Delete:** the curator itself never deletes. An explicit `hermes curator purge` deletes archives older than `archive_ttl_days`. The default 0 disables it (`hermes_cli/curator.py:419-479`).
- **Usage report:** `hermes curator usage` prints use, view, patch, activity and last activity. It sorts, filters by provenance, and prints JSON on request (`hermes_cli/curator.py:568-631`).

The config explains why `prune_builtins` is off. In one start-up tick, 57
bundled skills vanished (`hermes_cli/config_defaults.py:1506-1509`).

## 5. Safety

### 5.1 Write approval is off by default

- `skills.write_approval` and `memory.write_approval` are `False` (`hermes_cli/config_defaults.py:1481, 1317`).
- An unset, invalid or unreadable value also means off (`tools/write_approval.py:44-52`).
- The docs agree: "By default the agent writes skills freely" (`website/docs/user-guide/features/skills.md:668-700`).

When approval is on:
- a skill write always stages, from any origin (`tools/write_approval.py:209-210`);
- a memory write asks inline in the foreground and stages in the background (211-216);
- `/skills pending`, `approve`, `reject` and `diff` handle the queue (`hermes_cli/write_approval_commands.py:35-57, 157-163`).

Weak points:
- The gate fails open when its module cannot load (`tools/skill_manager_tool.py:657-664`).
- Approval replays the stored payload (701-707). A full rewrite replays with no base check. A patch fails only when its anchor is gone.
- A disk error while staging loses the write (`tools/write_approval.py:77-78`).

### 5.2 `skill_manage`

- One lock per skill. A batch takes its locks in sorted order (`tools/skill_manager_tool.py:84-105`).
- A batch has at most 20 operations (`tools/skill_manager_batch.py:16`). A delete must be the only one (254-262).
- A batch checks every shape before any change, and rolls back on failure (118-307). With approval on, it stages as one record (266-273).
- After a write, it updates the ledger, the cache and the usage record (`tools/skill_manager_tool.py:731-765`).
- A delete from the review fork archives the skill (583-593). A foreground delete removes the folder for good (594-596).

### 5.3 Guards

- Read before write applies only to the review origin, `/refine` included (`tools/skill_manager_guards.py:211-221`). A foreground write needs no read.
- The delete guard refuses pinned, external, protected, hub, bundled and unmanaged skills. It fails closed (164-208). It does not gate content writes (165-167).
- A pin blocks deletion only (143-161). A consolidation delete must name `absorbed_into` (232-252).

### 5.4 Lint: advisory only

`tools/skill_linter.py` returns findings. It never blocks a write.

- Errors: `name-format` and `name-dir-mismatch` (85-90).
- Warnings:
  - a description over 60 chars (94-98);
  - marketing words, missing metadata, author capitals, a bad `platforms` value;
  - a body over 24,000 chars (128-133);
  - a backticked shell utility in prose, where a native tool exists (134-138);
  - no "When to Use" section (139-141);
  - incident log: 4 or more PR or issue refs, and 0.5 or more per 1,000 prose chars (46-47, 142-148);
  - a missing `references/`, `templates/` or `assets/` file; `scripts/` is excluded (151-161);
  - platform gating; forbidden files such as `README.md` and `.env` (41); more than 60 reference files (51).
- It has no date rule and no "UPDATE:" rule.
- It runs on create, on a `SKILL.md` patch (new findings only) and on a `references/` write (`tools/skill_manager_tool.py:426-444, 490, 555-558, 622-625`).

### 5.5 Scanner

`tools/skills_guard.py` is version `skills-guard-v10` (21).

- It has 134 regex patterns in 12 categories: 51 critical, 45 high, 33 medium and 5 low. The largest categories are exfiltration (27), persistence (20) and injection (19).
- 17 invisible Unicode chars give a high finding (599-606, 718-723).
- Agent config files such as `AGENTS.md`, `CLAUDE.md`, `.claude/settings` and `.codex/config` have their own patterns (449-475).
- Token shapes: `ghp_`, `sk-`, `sk-ant-`, `AKIA`, `glpat-` and private keys (476-499).
- A critical finding gives "dangerous". A high finding gives "caution" (949-952).
- Structure: at most 50 files and 256 KB per file. The 5 MB total is info only. A binary or an escaping symlink is critical (588-596, 848-890).
- The install policy depends on trust (26-33):

  | Trust | Effect |
  |---|---|
  | builtin | Allow all |
  | trusted | Block "dangerous" |
  | community | Block "caution" and "dangerous" |
  | agent-created | Ask on "dangerous" |

- The scan after an agent write is off by default (`skills.guard_agent_created`; `tools/skill_manager_tool.py:41-47`). A scan error fails open (62-64). A blocked write restores the old file (395-414).

### 5.6 Rollback

Rollback fails closed (`tools/skill_ledger.py:557-633`):
1. Every path must be under `HERMES_HOME`.
2. Every blob is checked first.
3. It writes a `pre-rollback` entry, restores the files, then writes a `rollback` entry.

## 6. Where docs and code disagree

| Topic | Docs or comment | Code |
|---|---|---|
| Skill review interval | 15, "every N tool-calling iterations" (`cli-config.yaml.example:1166-1170`) | 10 (`agent/agent_init.py:1388-1390`); the key is not in `config_defaults.py` |
| `/refine` with reviews off | "/refine still works" (`hermes_cli/config_defaults.py:802`) | A bare `/refine` passes `focus=None`, so the `enabled` gate applies (`hermes_cli/cli_commands_mixin.py:1928`; `run_agent.py:768-772`). Read only; no test found |
| `/refine` origin | `refine_review` (`run_agent.py:797`) | No code uses it. `/refine` runs as `background_review`, marked attended (`tools/skill_provenance.py:29-44`) |
| Protected built-ins | "currently: plan" (`agent/curator.py:324-325`) | `PROTECTED_BUILTIN_SKILLS` is empty (`tools/skill_usage.py:40`) |
| HARDLINE rules | "enforced by" the authoring test (`skills/AGENTS.md:24`) | The test checks rule 1 and six other rules. Rules 2-8 have no test there |
| Curator scope | Only `created_by: agent` skills (`skills/AGENTS.md:73`) | True for the curator. The review fork may patch any loaded skill (`agent/background_review.py:473-475`) |

## 7. For this harness

### 7.1 What we have (checked on 2026-10-17)

**Skills and install.**
- 19 tracked `SKILL.md` files in `dotfiles/claude/skills/`, plus 3 vendor license files.
- `figma-design-to-code` and `synced/` are not tracked (repo `.gitignore:6, 12`).
- Every tracked skill name matches its folder and Hermes's name pattern.
- `~/.claude/skills` links to `dotfiles/claude/skills`. Codex adapters link from `~/.agents/skills/<name>` to `dotfiles/codex/skills/<name>` (`dotfiles/codex/install-skills.py:9-16`).
- So a session that edits a skill edits the dotfiles checkout. No hook blocks that edit. The reviewed-commit rule is prose only (`hermes-adoption-plan.md`, "Starting point").

**Explicit-only.**
- Five shared skills have a Codex `allow_implicit_invocation: false` policy (`dotfiles/tools/checks/harness-map.py:400-408`).
- The test pins three of them, plus the seven command adapters (`dotfiles/tools/tests/test-codex-harness.py:257-273`).
- In Claude, two skills set `disable-model-invocation: true`.

**Checks.**
- `validate-frontmatter.py` checks persona frontmatter and settings for ADR 0055. It has no skill rule (`dotfiles/tools/checks/validate-frontmatter.py:1-12`).
- `check-references.py` checks only targets that start with `./`, `../` or `templates/` (`dotfiles/tools/checks/check-references.py:75`).
- CI has no skill lint (`.github/workflows/ci.yml`).

**Skill measurements.**
- Descriptions are 158 to 610 chars. Each one says when to use the skill.
- 9 skills put that trigger after char 60.
- One body is over 24,000 chars: `code-review-and-quality` (24,795). Next are `api-and-interface-design` (23,168) and `security-and-hardening` (22,151).
- `vercel-composition-patterns` ships `rules/`, `AGENTS.md` and `metadata.json` (vendored).
- `vite` and `vitest` hold 25 bare `](references/...)` links. All resolve, and no check covers them.
- Dates occur in vendored or example text: `vite/SKILL.md:23`, `vitest/SKILL.md:34` and examples in `test-driven-development`.
- One ticket key, `LD-329`, occurs twice in `git-workflow-and-versioning/references/branching.md`.

**Usage data on this machine.**
- A Claude skill load has three shapes:
  1. a `Skill` tool call with `input.skill`;
  2. `<command-name>/spec</command-name>` in a user message, for a typed command;
  3. `<command-name>` with no slash in a subagent transcript, for a persona `skills:` preload.
- Subagent transcripts live in `<session>/subagents/*.jsonl`. One sample count found 129 of them against 107 main transcripts.
- The plan's glob `~/.claude/projects/*/*.jsonl` misses them. `run-metrics.sh` already reads them (`dotfiles/tools/run/run-metrics.sh:18, 73-77`).
- Codex has 193 rollouts. A load is an `exec` call that reads `.../skills/<name>/SKILL.md`. One `<skill><name>` block was found, and no `$skill` message.
- `~/.claude.json` has `skillUsage`: 44 entries of count and last use. It counts commands and skills, but not preloads.
- Six of our skills never appear in `skillUsage`. One of them, `test-driven-development`, loads in every executor run (`dotfiles/claude/agents/executor.md:5-7`).

### 7.2 S1 — usage report (Phase 1, report only)

Keep the plan, with these changes:
1. Read main and subagent transcripts: `~/.claude/projects/*/*.jsonl` and `~/.claude/projects/*/*/subagents/*.jsonl`.
2. Count all three Claude shapes. Tag each load as `tool`, `slash` or `preload`.
3. For Codex, count `exec` reads of `skills/<name>/SKILL.md`. Map each path to a skill name.
4. Count once per session, not per call. Hermes also ignores repeat views (`tools/skills_tool.py:737-760`).
5. Print columns like `hermes curator usage`: sessions in 30 and 90 days, last seen, and the shape split. List the skills never seen. Offer `--json`.
6. Never archive or edit. In Hermes, 57 bundled skills vanished in one start-up tick (`hermes_cli/config_defaults.py:1506-1509`). ADR 0039 calls counters "weak evidence" (`dotfiles/docs/adr/0039-runtime-catalog-narrowed-by-observed-use.md:38-40`).
7. Do not read `~/.claude.json`. It holds account data, and it misses preloads.

Verify with fixture transcripts: one per shape, one subagent preload and one
Codex read. Then run it once on this machine.

### 7.3 S2 — skill lint (Phase 1, warnings only)

1. Add `dotfiles/tools/checks/check-skills.py`. Do not extend `validate-frontmatter.py`, which guards ADR 0055.
2. Scan tracked skills only (`git ls-files`). This keeps `synced/` and the ignored skill out.
3. Exit 0 in Phase 1. A failing rule is a new gate, so it waits for Phase 4.
4. Use these rules:

   | Rule | Hermes source | Hits today |
   |---|---|---|
   | Body over 24,000 chars | `tools/skill_linter.py:56, 128-133` | 1: `code-review-and-quality` |
   | Description over 1,024 chars | `tools/skill_manager_tool.py:109` | 0 |
   | Bad name format, or name differs from folder | `tools/skill_linter.py:85-90` | 0 |
   | No "Use when" trigger in the description | Ours; Hermes checks a "When to Use" section (`tools/skill_linter.py:139-141`) | 0 |
   | Incident log: 4 or more refs, and 0.5 or more per 1,000 prose chars | `tools/skill_linter.py:46-47, 142-148` | 0 |

   For the incident rule, count PR and issue refs as Hermes does. Add ticket keys from a list of project prefixes.
5. For broken support links, extend `check-references.py` to bare `references/` and `assets/` targets. I pick this over a new rule because it is the same rule class. The 25 links resolve today, so CI stays green. It widens an existing gate, so confirm that the freeze allows it.
6. Drop three rules from the plan:
   - **The 60-char rule.** Hermes needs it because its own index cuts at 60 (`agent/skill_utils.py:827`). Hermes applies it on create only. 9 of our 19 skills would fail. Our clients' index limits were not checked.
   - **The folder allowlist in CI.** Hermes applies it only to new support files (`tools/skill_manager_tool.py:355-372`). `vercel-composition-patterns` ships `rules/`.
   - **Dates and "UPDATE:" in CI.** Hermes lints neither. Our dates are in vendored and example text. Keep these rules in `/lesson`, on added lines only.

Verify with one fixture per rule. A run on the 19 skills must print exactly
one warning: the body of `code-review-and-quality`.

### 7.4 S3 — `/lesson` (approved; Phase 3; ADR needed)

Hermes has no command that drafts a lesson for review (§4.5). It writes
directly by default (§5.1). So `/lesson` copies the prompt rules and adds a
review step.

1. **Input.** Read the current session transcript, main and subagents. The transcript keeps corrections that compaction removed from the context.
   - Claude: put `${CLAUDE_SESSION_ID}` in the command text. A string search of the local Claude Code 2.1.302 binary shows that it substitutes this in skill text. Test it with a one-line command first.
   - Codex: the rollout file name ends with the session UUID. The Codex 0.158.0 binary contains `CODEX_THREAD_ID` and `CODEX_SESSION_ID`. Nobody has checked that a shell command sees them. If it does not, ask the user for the path.
2. **Signals,** in this order (`agent/background_review.py:456-467`): your corrections; a fix found after a dead end; a loaded skill that proved wrong. With no signal, say "Nothing to save." and stop.
3. **Do not capture** the classes in `_DO_NOT_CAPTURE_BLOCK` (423-446). They need judgment, so the rule stays in the prompt.
4. **Target,** in Hermes's order (468-497):
   1. a skill loaded in this session;
   2. another existing skill;
   3. a `references/` file under it;
   4. a new skill with a class-level name.

   Find loaded skills from the three transcript shapes, as `/review` does (`agent/review_engine.py:70-96`).
5. **Repo.** Resolve the target's real path through the symlink. Then run `git -C <dir> rev-parse --git-common-dir`. The session's own project is usually a different repo.
6. **Read before write.** Read the target in this run, and record its sha256. Hermes enforces the read only in the review fork, and stores no base hash (`tools/skill_manager_guards.py:211-221`; `tools/write_approval.py:74-89`).
7. **Draft.** Write a unified diff with a header: target, base sha256, session id and signal. Save it as `<git-common-dir>/lessons/<id>.patch`. In a worktree `.git` is a file, so do not hard-code `.git/lessons`.
8. **Check the added lines** with a script:
   - the S2 rules;
   - the folder allowlist for a new file (`tools/skill_manager_tool.py:113, 355-372`);
   - the name rules (108, 112);
   - invisible Unicode (`tools/skills_guard.py:599-606`) and token shapes (476-499), shared with H2;
   - a date, a ticket key or "UPDATE:" (`agent/background_review.py:404-406, 418-419`).
9. **Show** the diff. Wait for an explicit yes.
10. **Apply** only if the sha256 has not changed. This is stricter than Hermes, which replays a full rewrite with no base check (`tools/skill_manager_tool.py:701-707`).
11. **Commit** in a temporary worktree outside the repo, on branch `lesson/<id>`. Never switch or commit in the main checkout, which holds other uncommitted work. Remove the worktree with `git worktree remove`.
12. **Ledger.** Use the commit trailers `Lesson-Id`, `Lesson-Session` and `Lesson-Base-Sha256`. Rollback is `git revert`. A rejected draft stays in the lessons folder. Drop the separate JSONL ledger.
13. **Both clients:**
    - add `dotfiles/claude/commands/lesson.md`;
    - add `dotfiles/codex/skills/lesson/SKILL.md` with an explicit-only `agents/openai.yaml`;
    - add `lesson` to `STAGES` (`dotfiles/tools/tests/test-codex-harness.py:258`);
    - run `install-skills.py`, and regenerate the harness map.
14. **Script and tests.** Put every deterministic step in one tested script: transcript lookup, loaded skills, repo, sha256, checks, apply and commit. The model only finds the signal and writes the diff. Use these fixtures:
    - a real correction;
    - an environment failure only, which must give "Nothing to save.";
    - a stale base sha256, where apply must refuse;
    - a correction that occurs only in a subagent transcript;
    - a target behind a symlink.
15. **ADR.** The next free number today is 0089.
16. **Windows (W1).** Step 5 needs links. If W1 installs copies, add a map from each copy back to the repo.

**Do not copy:**
- the automatic review after 10 model calls or 10 user turns, at about 30K tokens each (§4.2);
- the "Be ACTIVE" stance (`agent/background_review.py:449`);
- the "fewer than 10 archives" quota (`agent/curator.py:443-446`);
- a gate or scan that fails open (`tools/skill_manager_tool.py:62-64, 657-664`);
- foreground self-edits such as "update it before finishing" (`agent/prompt_builder.py:1374-1375`);
- the foreground hard delete (`tools/skill_manager_tool.py:594-596`).

### 7.5 Corrections to the previous version

| Old claim | Fact | Source |
|---|---|---|
| Every skill write stages for approval | Approval is off by default; writes go straight to disk | `hermes_cli/config_defaults.py:1481`; `tools/write_approval.py:44-52` |
| The review cadence was not found | 10 model calls for skills, 10 user turns for memory | §4.2 |
| Read before write is a general rule | It applies only to the review fork and `/refine` | `tools/skill_manager_guards.py:211-221` |
| The folder allowlist suits a CI lint | Hermes applies it only to new support files | `tools/skill_manager_tool.py:355-372` |
| Lint can flag dates and "UPDATE:" | Hermes has no such rule; it flags incident density | `tools/skill_linter.py:142-148` |
| The curator never deletes | True, but `curator purge` and a foreground `delete` do | `hermes_cli/curator.py:419-479`; `tools/skill_manager_tool.py:594-596` |
| The authoring test checks eight HARDLINE rules | It checks rule 1 plus six other rules | `tests/skills/test_authoring_standards.py` |
| `tests/skills/` has one test per skill | About 25 of 211 skills have their own test | `tests/skills/` listing |
| `validate-frontmatter.py` checks skill frontmatter | It checks persona frontmatter and settings only | `dotfiles/tools/checks/validate-frontmatter.py:1-12` |
| Drafts go to `.git/lessons/` | In a worktree `.git` is a file; use `--git-common-dir` | §7.4 step 7 |
| The input cap is 75% of context, up to 600k | Also 120k when the window is unknown; 0 or less means no cap | `agent/background_review.py:180-225` |

## Sources

Hermes commit `5fea5a7a4bf6d02b3427fc0bcae95502222cea2e` (2026-10-17), local
clone. Paths are relative to the repo root.

**Read in full:**
- `agent/background_review.py`
- `agent/curator.py`
- `agent/learn_prompt.py`
- `agent/review_engine.py`
- `agent/skill_commands.py`
- `hermes_cli/write_approval_commands.py`
- `skills/AGENTS.md`
- `tests/skills/test_authoring_standards.py`
- `tools/skill_linter.py`
- `tools/skill_manager_batch.py`
- `tools/skill_manager_guards.py`
- `tools/skill_manager_tool.py`
- `tools/skill_provenance.py`
- `tools/skill_usage.py`
- `tools/skills_guard.py`
- `tools/skills_tool.py`
- `tools/write_approval.py`

**Read in part:**
- `agent/agent_init.py`
- `agent/managed_worker.py`
- `agent/prompt_builder.py`
- `agent/skill_utils.py`
- `agent/skills_index_delta.py`
- `agent/tool_executor.py`
- `agent/turn_context.py`
- `agent/turn_finalizer.py`
- `agent/turn_iteration_prep.py`
- `cli-config.yaml.example`
- `cron/scheduler.py`
- `gateway/run.py`
- `hermes_cli/cli_commands_mixin.py`
- `hermes_cli/cli_tui_runtime_mixin.py`
- `hermes_cli/config_defaults.py`
- `hermes_cli/curator.py`
- `hermes_cli/skills_hub.py`
- `hermes_cli/web_server_sessions.py`
- `run_agent.py`
- `tools/skill_ledger.py`
- `tools/skills_hub_install.py`
- `tui_gateway/methods_slash.py`
- `website/docs/user-guide/features/memory.md`
- `website/docs/user-guide/features/skills.md`
- tests, names and counts: `tests/skills/`, `tests/agent/test_background_review.py`, `tests/agent/test_curator.py`, `tests/agent/test_learn_prompt.py`, `tests/agent/test_refine_focus.py`, `tests/agent/test_skip_background_review.py`, `tests/tools/test_skill_ledger.py`, `tests/tools/test_skill_linter.py`, `tests/tools/test_skill_manager_tool.py`, `tests/tools/test_skill_provenance.py`, `tests/tools/test_skill_usage.py`, `tests/tools/test_write_approval.py`, `tests/tui_gateway/test_slash_refine_live.py`

**This repository**, read only:
- `dotfiles/docs/hermes-adoption-plan.md`, `dotfiles/docs/observation-log.md`, `dotfiles/docs/adr/0039-runtime-catalog-narrowed-by-observed-use.md`
- `dotfiles/claude/skills/` (19 tracked skills), `dotfiles/claude/agents/executor.md`, `dotfiles/claude/hooks/`
- `dotfiles/codex/install-skills.py`, `dotfiles/codex/skills/plan/`
- `dotfiles/tools/checks/validate-frontmatter.py`, `check-references.py`, `harness-map.py`, `check-writing.py`
- `dotfiles/tools/tests/test-codex-harness.py`, `dotfiles/tools/run/run-metrics.sh`
- `.github/workflows/ci.yml`, `.gitignore`
- local Claude and Codex transcripts: shapes and counts only
