# Hermes research: tools, doctor and cron

Part of `../hermes-adoption-plan.md` (items T1 doctor, T2 Gemini removal and
T3 scheduled health run).

The source is a local clone of `NousResearch/hermes-agent` at the commit named
in "Sources". A path without a prefix is relative to the Hermes repository
root. A path that starts with `dotfiles/` or `.github/` is in this repository.

## Coverage

**Read in full:**
- `tools/registry.py` and `toolsets.py`;
- `hermes_cli/doctor.py`, `hermes_cli/subcommands/doctor.py`, `hermes_cli/doctor_report.py`;
- every check body: `hermes_cli/doctor_platform.py`, `doctor_config.py`, `doctor_state.py`, `doctor_tools.py`, `doctor_connectivity.py`, `doctor_live.py`;
- `hermes_cli/mcp_security.py`;
- `cron/AGENTS.md`, `cron/constants.py`, `cron/occurrences.py`, `cron/scheduler_tick.py`, `cron/scheduler_preflight.py`;
- `cron/unreachable_retry.py`, `cron/incidents.py`, `cron/executions.py`;
- `tools/mcp_tool_transport.py`, `tools/mcp_tool_config.py`, `tools/mcp_tool_node_abi.py`, `tools/osv_check.py`;
- `website/docs/guides/cron-script-only.md` and `tests/hermes_cli/test_doctor_exit_status.py`.

**Read in part:**
- `model_tools.py`: the definition cache, the error filter and the dispatch path.
- `cron/scheduler.py` (4413 lines): lines 1-2080, 2530-3500 and 4018-4413. I skimmed the rest.
- `cron/jobs.py` (3484 lines): locks, the schedule parser, grace, heartbeats, the due scan, retention.
- `cron/store_health.py` and `cron/monitor.py`: the constants and the probe.
- `tools/mcp_tool.py` (742 lines): lines 1-75 and 225-742.
- `tools/mcp_tool_handlers.py`, `tools/mcp_tool_discovery.py` and `tools/mcp_tool_common.py`: the trust gate, the breaker, backoff and timeouts.
- `gateway/status.py:450-461`, `agent/delegation_context.py:166-184` and `hermes_cli/env_loader.py:135-140`.
- `tests/hermes_cli/test_doctor.py`: the `--fix` tests at lines 876-916.
- `website/docs/developer-guide/cron-internals.md`: lines 147-200. `website/docs/user-guide/features/cron.md`: search hits only.

**Not read:**
- the helpers that the doctor checks call, for example `hermes_cli/security_advisories.py`;
- 31 other `cron/` modules and the `cron/scripts/` folder, for example `delivery_queue.py`, `scheduler_liveness.py` and `scheduler_script.py`;
- 11 other `tools/mcp_tool_*.py` modules, for example `mcp_tool_health.py` and `mcp_tool_lifecycle.py`;
- the cron tests and the MCP tests, for example `tests/cron/test_cron_incidents.py` and `tests/tools/test_mcp_trust_gating.py`.

Each fact below cites a line in the files above. The unread modules hold
delivery, blueprints and the session lifecycle, which no plan item uses.

**Our side, read only:**
- `dotfiles/tools/setup/link_dotfiles.sh`, `dotfiles/claude/mcp/setup.sh`;
- `dotfiles/codex/config.toml` (working tree and `HEAD`), `install-config.py`, `install-skills.py`, `hooks.json`;
- `dotfiles/claude/hooks/worktree-readiness.sh`, ADR 0058, ADR 0087, `dotfiles/docs/HANDOFF.md`;
- the Gemini parts of `dotfiles/tools/agent_sessions_mcp.py` and `dotfiles/tools/agent_deck.py`.

I ran read-only commands on this machine: the `--check` and `--lint` modes,
the linker dry run, a link comparison and a native-module load. §5.1 lists
the results.

**Not checked:** the environment that each client passes to a stdio MCP
server. The session permission policy denied a read of the running
server's variable names. §5.6 gives a check the owner can run.

**Corrected in this version:**

| Earlier claim | Fact |
|---|---|
| The ordered doctor list (23 lines) | `DOCTOR_CHECKS` has 28 entries. The list missed the dashboard import and the checkpoint store (`hermes_cli/doctor.py:112-129`). |
| Exit 1 when any issue remains | Exit 1 when an auto-fixable or a manual issue remains. Warnings never fail. `--ack` exits 2 on an unknown id (`hermes_cli/doctor.py:137-145,194`). |
| `--live` makes the network calls | The default run already calls provider APIs, GitHub and an IPv6 route. `--live` adds probes for each tool backend (`hermes_cli/doctor_connectivity.py:124-446`). |
| Discovery scans `tools/*.py` | It also scans `tools/*/tool.py` and caches the scan on disk (`tools/registry.py:112-125,183`). |
| A flaky `check_fn` keeps the tool | Only within 60 s of the last success. That answer is not cached (`tools/registry.py:392-398`). |
| The tick takes the lock first | The stale-code check runs first. A real lock error is raised, not read as contention (`cron/scheduler_tick.py:102-112`; `cron/scheduler.py:4093-4126`). |
| The signature masks durations and numbers | Durations only. Status codes and other numbers stay (`cron/incidents.py:44-48,131-134`). |
| Repeat alerts wait for a setting | The default is 6 h. A value of 0 alerts on every failing run (`cron/scheduler.py:325-333`). |
| The unreachable retry applies to any job | Recurring jobs only, on by default. A sooner natural run wins (`cron/unreachable_retry.py:33,42-55,85-88`). |
| A terminal ledger row never changes | A queued `delivery_outcome` can settle once more (`cron/executions.py:389-402`). |
| Stuck bound: `max(3 × job timeout, script timeout, 7200 s)` | The 3× uses the inactivity timeout (600 s). So the default bound is 7200 s. A timeout of 0 turns it off (`cron/executions.py:152-170`). |
| Dead owner: the start time must not match | The start times must differ by more than 2 s (`cron/executions.py:134-149`; `gateway/status.py:450-461`). |
| OSV runs before `npx`, 12 s timeout | Also `uvx` and `pipx`. A 10 s HTTP timeout sits inside a 12 s wall clock. Only `MAL-*` ids block. The cache keeps results 1 h (`tools/osv_check.py:1-7,20,35`; `tools/mcp_tool.py:36`). |
| `trust: untrusted` allows read-only tools only | Each write-capable call needs an approval. An approval error blocks (`tools/mcp_tool.py:519-530`; `tools/mcp_tool_handlers.py:60-85`). |
| A stdio child gets only its `env` block | It gets an allowlist plus its `env` block (§4.2). |
| Two heartbeat files | Three: `ticker_heartbeat`, `ticker_last_success`, `ticker_last_error` (`cron/jobs.py:96-97,1248-1335`). |
| T1 check 6 needs new code | `install-config.py --check` and `--lint` exist (`dotfiles/codex/install-config.py:19-20,82-97`). |
| T1 check 7 (settings link) | The link check covers it. `~/.claude/settings.json` is one of the 19 linker paths (`dotfiles/tools/setup/link_dotfiles.sh:36,57`). |

## 1. Tool registry and toolsets

Hermes owns its tools. Both of our clients own theirs, so this section is
background for the doctor and MCP parts.

- **Self-registration:** each module calls `registry.register(...)` at import (`tools/registry.py:709-714`). The call takes:
  - name, toolset, schema and handler;
  - `check_fn`, `requires_env`, `is_async`, description and emoji;
  - a result-size cap and dynamic schema overrides;
  - `override`, `scope` and an execution timeout.
- **Schema check:** a bad schema is refused at registration (`tools/registry.py:718-728`).
- **Discovery:** an AST scan of `tools/*.py` and `tools/*/tool.py` finds the `register` calls (`tools/registry.py:112-118`).
  - It skips `__init__`, `registry` and `mcp_tool` (`tools/registry.py:141`).
  - The scan is cached in `<home>/cache/tool_discovery_cache.json`, keyed by mtime and size (`tools/registry.py:121-125,150-185`).
- **Override protection** (`tools/registry.py:743-773`):
  - Re-registering in the same toolset replaces the tool.
  - Shadowing a tool from another toolset without `override=True` is refused.
  - A plugin also needs `plugins.entries.<id>.allow_tool_override: true`.
  - Deregistration is gated. MCP tools are exempt (`tools/registry.py:788-844`).
- **Availability** (`tools/registry.py:258-262,392-419`):
  - `check_fn` answers are cached for 30 s, at most 512 entries.
  - A failure within 60 s of the last success serves that success, uncached.
  - A `False` answer is cached.
  - A dropped core tool is logged once.
- **Errors:** cut to 2048 characters with the marker `… [truncated]` (`tools/registry.py:51-54,67-81`). `model_tools.py:622-640` also strips role tags and adds `[TOOL_ERROR] `.
- **Dispatch:** the registry passes only the arguments the handler accepts (`tools/registry.py:947,1076-1086`). Exception text is sanitized (`tools/registry.py:954-964`).
- **Toolsets:** `toolsets.py:11-40` lists the core tools. The webhook-safe set has no file or system tools (`toolsets.py:42-43`).
- **Pre-dispatch hooks:** a plugin `pre_tool_call` runs first, then an edit approval. A guard failure blocks `write_file` and `patch` (`model_tools.py:766-802`).

## 2. Doctor

### 2.1 Shape

- **Order:** one ordered tuple of 28 checks. The order is visible to the user (`hermes_cli/doctor.py:111-129`).
- **Result:** each check returns a `Finding` with three parts (`hermes_cli/doctor_report.py:54-65`):
  - `issues`: the run fails, and the `--fix` tip shows;
  - `manual_issues`: the run fails, and only a person can fix it;
  - `fixed`: the count of repairs made.
- **Rows:** ✓, ⚠ or ✗ for each line (`hermes_cli/doctor_report.py:12-16`). A ⚠ row never fails the run.
- **Crash safety:** a best-effort check that raises keeps its partial result (`hermes_cli/doctor_report.py:68-85`).
- **Summary** (`hermes_cli/doctor.py:148-169`):
  - "Fixed N issue(s)." with a count of manual ones;
  - "Found N issue(s) to address:" with a numbered list;
  - "All checks passed!".
- **Exit:** `int(bool(issues or manual_issues))` (`hermes_cli/doctor.py:194`). The tests pin each case: a fix with manual issues left still exits 1 (`tests/hermes_cli/test_doctor_exit_status.py:7-13`).
- **Flags** (`hermes_cli/subcommands/doctor.py`; `hermes_cli/doctor.py:132-145`):
  - `--fix` runs the repairs.
  - `--ack <advisory-id>` stores an ack in `config.yaml` and runs no checks. It exits 2 for an unknown id and 1 when the save fails.
  - `--live` runs one bounded, read-only probe for each tool backend after the static checks.
- **Live probes** (`hermes_cli/doctor_live.py`):
  - The default timeout is 10 s, with a 1 s minimum (`hermes_cli/doctor_live.py:18,165-169`).
  - They run one after another (`hermes_cli/doctor_live.py:160-162`).
  - For MCP, each server gets `initialize` and `tools/list` (`hermes_cli/doctor_live.py:176-186`).
  - A failure becomes a manual issue (`hermes_cli/doctor.py:189-192`).
- **Network in the default run:** check 23 calls each provider's `/models` (10 s) and GitHub. It probes an IPv6 route (2 s). It uses an 8-worker pool and prints in a fixed order (`hermes_cli/doctor_connectivity.py:124-446`).

### 2.2 The 28 checks

Paths: `platform`, `config`, `state` and `tools` mean `hermes_cli/doctor_<name>.py`.

| # | Check | What it tests | Fails as | `--fix` does |
|---|---|---|---|---|
| 1 | Security Advisories (`platform:388`) | Installed packages against known advisories | manual, with the `--ack` command. Acked but still installed: warn | nothing; use `--ack` |
| 2 | MCP Server Security (`config:153`) | Each `mcp_servers` entry against three blocked shapes (§4.3) | warn row and manual: review or remove, rotate credentials | nothing |
| 3 | Python Environment (`platform:431`) | Python below 3.8; 3.10 or 3.11; the SQLite WAL-reset bug | issue; warn; warn | macOS privacy anchor only (`platform:352`) |
| 4 | SSL / CA Certificates (`platform:477`) | A TLS context loads | manual | nothing |
| 5 | Required Packages (`platform:490`) | `openai`, `rich`, `dotenv`, `ruamel.yaml`, `httpx`; optional `croniter`, `telegram`, `discord` | issue; warn | nothing |
| 6 | Dashboard import (`platform:529`) | Imports the web dashboard in a subprocess, 120 s timeout | issue. A missing optional extra: warn | nothing |
| 7 | Configuration Files (`config:171`) | `.env` exists | issue | creates it with mode 0600 |
| 8 | Config file (`config:336`) | `config.yaml` exists and validates | issue | seeds a missing file |
| 9 | Config drift (`config:527`) | Version, stale root keys, a ghost `HERMES_MAX_ITERATIONS`, deprecations, legacy `custom_providers` | issue. Deprecations: warn only. Legacy providers: manual | migrates, moves stale keys, removes the ghost key |
| 10 | xAI Model Retirement (`config:545`) | Config names a retired model | manual | nothing |
| 11 | Session Reset (`config:559`) | Config uses removed reset timers | manual | nothing |
| 12 | Auth Providers (`hermes_cli/doctor.py:71-93`) | Login state of each provider | warn only | nothing |
| 13 | Directory Structure (`state:187`) | Home folders, `SOUL.md`, caches of 1 GiB or more | issue. Large caches: warn | creates the folders and `SOUL.md` |
| 14 | State database (`state:480`) | Retired WAL holders, write health, FTS, schema, size, WAL over 50 MB | issue. Structural damage: manual | repairs with a backup; PASSIVE checkpoint |
| 15 | Cron store (`state:496`) | Writable, and at least 100 MiB free (`cron/store_health.py:31`) | issue | nothing |
| 16 | Checkpoint store (`state:512`) | The rollback store is over its cap | warn | nothing |
| 17 | Gateway supervision (`platform:581`) | systemd linger, s6, Windows autostart | issue | turns on Windows autostart (`platform:502-525`) |
| 18 | Command installation (`platform:588`) | The `hermes` link and `PATH` | own wrong link: issue. User-managed target: manual. Not on `PATH`: manual | relinks or creates its own link only |
| 19 | External Tools (`tools:184`) | `git` and `rg` | warn | nothing |
| 20 | Terminal backend (`tools:300`) | Docker `version`, SSH (`ConnectTimeout=5`, `BatchMode=yes`) and others | issue | nothing |
| 21 | Node and browser (`tools:398`) | Node, `agent-browser`, Chromium, Lightpanda | warn or issue | installs `agent-browser` |
| 22 | npm audit (`tools:462`) | `npm audit --json`, 30 s timeout | critical or high: manual | nothing |
| 23 | API Connectivity (`hermes_cli/doctor.py:96-108`) | Provider APIs, Bedrock, Azure, GitHub, IPv6 | issue, unless an OAuth fallback works | nothing |
| 24 | Tool Availability (`tools:504`) | Missing keys for enabled tools | issue for CLI-enabled tools only | nothing |
| 25 | Skills Hub (`state:577`) | Hub state and quarantined skills | warn | nothing |
| 26 | Memory Provider (`state:620`) | The configured provider loads | issue for a missing plugin, else warn | nothing |
| 27 | NeMo Relay Plugins (`config:100`) | Relay plugin config | manual | nothing |
| 28 | Profiles (`state:640`) | Orphan aliases; credentials shared across profiles | warn; manual | nothing |

`_check_update_provenance` exists (`state:546-553`) but is not in the tuple.

### 2.3 Rules worth copying

- **Repair only what you own.** A link the doctor made is relinked. A user-managed target is reported, "not changed" (`platform:629-631`).
- **Report, do not delete.** A legacy checkout is never deleted (`state:114-183`). Channel records are reported only (`config:495-523`).
- **Prescribe only fixes that last.** Do not suggest a local fix that the next install undoes (`tools:417-427`).
- **A fix must verify.** The tests reject a `--fix` that claims success without a check (`tests/hermes_cli/test_doctor.py:876-916`).
- **Read the source of truth.** Deprecated variables come from the `.env` file, not from the process environment (`config:29-37`).
- **Read without opening.** The SQLite journal mode comes from header byte 18, so the check opens no database (`platform:74-91`).
- **Deprecations warn and never fail** (`config:81-96,434-441`).

## 3. Cron

### 3.1 Files

| File | Holds |
|---|---|
| `<home>/cron/jobs.json` | The jobs (`cron/jobs.py:90`) |
| `<home>/cron/output/<job>/<timestamp>.md` | Run output. 50 files are kept for each job (`cron/jobs.py:3,114,3354-3359`) |
| `<home>/cron/executions.db` | The execution ledger and the incidents (`cron/executions.py:51`; `cron/incidents.py:60`) |
| `ticker_heartbeat`, `ticker_last_success`, `ticker_last_error` | Liveness markers. The heartbeat holds `<epoch> <pid>` (`cron/jobs.py:96-97,1248-1335`) |
| `<home>/cron/.tick.lock` | The tick lock (`cron/AGENTS.md:30-31`) |

### 3.2 Tick order

The ticker runs every 60 s (`cron/jobs.py:100`). One tick does these steps
(`cron/scheduler_tick.py:92-204`):

1. Yield to a fresher gateway when the code on disk changed. This runs before the lock.
2. Take the lock without blocking. Contention returns 0. An unwritable store degrades the tick.
3. Stop on the emergency pause (`hermes pause`).
4. Stop when the gateway drains.
5. Housekeeping: reap dead owners every 300 s, and clean worktrees every 6 h (`cron/scheduler.py:4020-4024`).
6. Find the due jobs. Sweep stale in-flight runs. Refuse agent jobs when no gateway runs.
7. Stop when the store is known to be unwritable.
8. Advance `next_run_at` **before** any run, so each slot runs at most once.
9. Run the jobs in a pool, then release the lock.

**The lock** uses `fcntl.flock` on POSIX and `msvcrt.locking` on Windows,
both non-blocking (`cron/scheduler.py:4093-4112`). Contention errnos differ by
platform (`cron/scheduler.py:1319-1329`). Any other error is raised. The code
comment names the reason: a swallowed error once made the scheduler look
healthy while no job ran (#87644).

### 3.3 Schedules and missed runs

| Input | Result |
|---|---|
| `30m`, `every 2h` | A recurring interval (`cron/jobs.py:783-786,847`) |
| `in 30m` | A one-shot run (`cron/jobs.py:835-845`) |
| `every monday 9am`, `weekdays at 9am` | A cron expression (`cron/jobs.py:791-800`) |
| 5- or 6-field cron | Used as written |
| ISO time | A one-shot run |

The guide says a bare `30m` is one-shot (`website/docs/guides/cron-script-only.md:204`).
The code makes it recurring. The code comment calls recurring the
"documented tool contract" (`cron/jobs.py:833-834`).

- **Grace:** `max(120 s, min(period / 2, 7200 s))` (`cron/jobs.py:933-943`). A one-shot run has 120 s (`cron/jobs.py:115`).
- **Late start:** a run up to 300 s late shows as on time (`cron/jobs.py:949-959`).
- **Backlog:** a job more than one period late fast-forwards, but fires **once** now (`cron/jobs.py:2858-2866`). `catch_up_missed: false` skips that run (`cron/jobs.py:3098-3126`).
- **Pending slot:** a slot is restored once, "never N replays" (`cron/occurrences.py:58-103`).
- **Crash loops:** "one missed run beats a crash-loop burst" (`cron/jobs.py:2695-2700`).
- **Recurring jobs** are never disabled without a record (`cron/jobs.py:2380-2420`).
- **`last_failure`** stays after a later success (`cron/jobs.py:2360-2365`).

### 3.4 Incidents (`cron/incidents.py`)

- **States:** `detected`, `alerted`, `resolved`, `closed`. Only `closed` is terminal (`cron/incidents.py:30-32`).
- **Failure types:** rate limit, timeout, auth, delivery, config, script, agent (`cron/incidents.py:33-41`).
- **Signature:** `sha256(job_id + error)[:12]` (`cron/incidents.py:131-134`). Before the hash, the error is:
  1. collapsed to single spaces and lowercased (`cron/incidents.py:114-116`);
  2. stripped of durations, which become `#s`;
  3. cut to 200 characters.
- **Numbers count:** "Status codes and other numbers still count" (`cron/incidents.py:44-45`).
- **Incident id:** the first 6 characters of the job id, then the signature (`cron/incidents.py:137-138`).
- **Upsert** (`cron/incidents.py:156-197`):
  - A resolved incident that fails again returns to `detected`.
  - A closed incident stays closed.
  - New error text opens a new incident.
- **Stored error:** redacted, then cut to 500 characters (`cron/incidents.py:42,119-128`).
- **Recovery:** a successful run resolves the job's incidents (`cron/scheduler.py:2939-2985`).
- **Alert gate** (`cron/scheduler.py:325-376`):
  - An `alerted` incident is quiet for `failure_repeat_alert_hours`, default 6 h.
  - A missing `alerted_at` sends the alert.
  - A broken incident store sends the alert.
- **Alerted mark:** set only when delivery succeeded or no target exists (`cron/scheduler.py:3201-3202`).

### 3.5 Unreachable retry (`cron/unreachable_retry.py`)

- **Origin:** "inspired by" Claude Cowork's silent re-runs (`cron/unreachable_retry.py:3-5`; `cron/scheduler.py:3098-3107`).
- **Delays:** 300, 900 and 1800 s (`cron/unreachable_retry.py:33`).
- **Trigger:** a transient network error **and** zero model calls (`cron/unreachable_retry.py:58-65`).
- **Scope:** recurring, unpaused jobs; `cron.retry_unreachable` is on by default (`cron/unreachable_retry.py:42-55,68-70`).
- **Order:** a sooner natural run wins (`cron/unreachable_retry.py:85-88`).
- **Count:** retries do not use up a `repeat` run (`cron/unreachable_retry.py:96,125-132`).
- **Notice:** the failure notice waits while a retry is pending (`cron/unreachable_retry.py:15-17`).

### 3.6 Preflight (`cron/scheduler_preflight.py`)

- It checks the provider key, the delivery target, the skills and the MCP servers (`cron/scheduler_preflight.py:86-384`).
- It blocks only on an affirmative answer. Each check fails open (`cron/scheduler_preflight.py:387-406`).
- A blocked job alerts once (`cron/scheduler.py:1702-1757`).
- An MCP server with zero tools warns once per outage.
- `cron.preflight: false` turns it off (`cron/scheduler_preflight.py:80-83`).

### 3.7 Execution ledger (`cron/executions.py`)

- **Purpose:** an audit ledger, not a retry queue. Recovery marks abandoned rows `unknown`, with no retry (`cron/scheduler.py:4295`).
- **Row first:** each attempt gets a `claimed` row before it runs (`cron/executions.py:213-233`).
- **Guarded moves:** every update names the expected state and owner, and checks `rowcount == 1` (`cron/executions.py:293-340`).
- **After terminal:** only a queued `delivery_outcome` can settle once (`cron/executions.py:389-402`).
- **Dead owner** (`cron/executions.py:134-149`):
  - The pid must be gone, or its start time must differ by more than 2 s.
  - An unknown answer counts as alive.
- **Stuck owner:** silence since `progress_at` over `max(3 × inactivity timeout, script timeout, 7200 s)` (`cron/executions.py:152-185`). The process is not killed.
- **Recovery race guard:** the update repeats `claimed_at` and `progress_at` (`cron/executions.py:426-499`).
  - It skips its own process.
  - It gives a handoff 30 s (`cron/executions.py:34`).
- **Size:** the newest 1000 terminal rows stay (`cron/executions.py:33,201-210`).

### 3.8 Script-only jobs

- **`no_agent` jobs:** a script runs and no model is called (`cron/scheduler.py:1522-1574`).
- **Output mapping** (`website/docs/guides/cron-script-only.md:142-148`):
  - empty output: silent;
  - output: delivered;
  - non-zero exit: an error alert.
- **Limits:** scripts must sit in `~/.hermes/scripts/`. Shebangs are ignored (`cron-script-only.md:154,163`).
- **No credentials:** scripts do not inherit provider credentials (`cron-script-only.md:31`).
- **Timeouts:** 3600 s for a script; a heartbeat every 60 s; a 180 s grace (`cron/scheduler.py:1391-1395`).
- **Change gate:** a monitor delivers only when the output hash changes. Scripts must emit stable output (`cron/monitor.py:1-11`). A failure is never a change (`cron/monitor.py:44-46`).
- **OS cron advice:** a watchdog that must fire while the gateway is down belongs in OS cron (`cron-script-only.md:271`).
- **Overdue:** `hermes cron status` flags a run more than 15 minutes overdue (`website/docs/user-guide/features/cron.md:367`).

## 4. MCP

### 4.1 Transports and recovery

Hermes supports stdio, streamable HTTP and SSE. HTTP checks the content type
first and falls back to SSE (`tools/mcp_tool_transport.py:428-648`).

| Setting | Value |
|---|---|
| Connect timeout | 60 s (`tools/mcp_tool.py:238`) |
| Retries | 3 for the first connect, 5 for a reconnect (`tools/mcp_tool.py:239-240`) |
| Reconnect backoff cap | 60 s (`tools/mcp_tool.py:241`) |
| Parked self-probe | every 300 s (`tools/mcp_tool.py:244`) |
| Respawn wait, keepalive | 15 s, 180 s (`tools/mcp_tool.py:247,251`) |
| Connect cooldown | 30 s, growing to 600 s (`tools/mcp_tool.py:500`; `tools/mcp_tool_discovery.py:47-52`) |
| Circuit breaker | opens after 3 failures, 60 s cooldown, then a half-open probe (`tools/mcp_tool.py:502-517`) |
| Tool call timeout | 300 s (`tools/mcp_tool_common.py:41`) |

After the breaker opens, the tool returns "server unreachable" and tells the
model to stop. The comment cites a 90-iteration loop (#10447).

### 4.2 Safe environment for stdio servers

`_build_safe_env` builds the child environment (`tools/mcp_tool_config.py:184-210`).
The child gets:

- `PATH`, `HOME`, `USER`, `LANG`, `LC_ALL`, `TERM`, `SHELL`, `TMPDIR` (`tools/mcp_tool_config.py:147`);
- on Windows, any case of: `ALLUSERSPROFILE`, `APPDATA`, `COMMONPROGRAMFILES`, `COMMONPROGRAMFILES(X86)`, `COMMONPROGRAMW6432`, `COMPUTERNAME`, `COMSPEC`, `HOMEDRIVE`, `HOMEPATH`, `LOCALAPPDATA`, `NUMBER_OF_PROCESSORS`, `OS`, `PATHEXT`, `PROCESSOR_ARCHITECTURE`, `PROGRAMDATA`, `PROGRAMFILES`, `PROGRAMFILES(X86)`, `PROGRAMW6432`, `PUBLIC`, `SYSTEMDRIVE`, `SYSTEMROOT`, `TEMP`, `TMP`, `USERDOMAIN`, `USERNAME`, `USERPROFILE`, `WINDIR` (`tools/mcp_tool_config.py:150-156`);
- every `XDG_*` variable;
- every name an external secret source set, with the active profile's value (`tools/mcp_tool_config.py:197-203`; `hermes_cli/env_loader.py:135-140`);
- `HERMES_KANBAN_DB` and `HERMES_KANBAN_BOARD`;
- the server's own `env` block, which overrides the above.

The allowlist is not secret-free. It passes secret-source names on purpose.
Everything else stays out, for example API keys from the shell, proxy variables,
`NODE_OPTIONS` and other `LC_*` names. A delegated child only loses its
kanban variables (`agent/delegation_context.py:173-184`).

### 4.3 Config checks

- **Interpolation:** `${VAR}` and `${env:VAR}` expand. An unset variable stays literal (`tools/mcp_tool_config.py:533-547`).
- **Remote fail-closed:** an unresolved variable in a remote URL or header blocks the server (`tools/mcp_tool_config.py:550-564`).
- **Hidden whitespace** in a value warns (`tools/mcp_tool_config.py:571-594`).
- **Bare commands** skip Hermes-managed bin folders (`tools/mcp_tool_config.py:345-386`).
- **Suspicious shapes** (`hermes_cli/mcp_security.py`). The scan runs at save and at spawn (`hermes_cli/mcp_security.py:1-7`). It blocks three shapes (`hermes_cli/mcp_security.py:89-135`):
  - a shell interpreter (`hermes_cli/mcp_security.py:15-17`) with an egress tool such as `curl`, `wget`, `nc` or `/dev/tcp/` (`hermes_cli/mcp_security.py:19-26`);
  - a persistence target such as `authorized_keys`, `/etc/sudoers`, `crontab` or `.bashrc` (`hermes_cli/mcp_security.py:35-45`);
  - a known indicator string (`hermes_cli/mcp_security.py:49-56`).
- The module says it is "intentionally not a whitelist".

### 4.4 OSV malware check (`tools/osv_check.py`)

- **When:** before a stdio spawn through `npx`, `uvx` or `pipx`, including `.cmd` and `.exe` forms (`tools/osv_check.py:195-199`).
- **Order:** the check sees the real command. The cached-`npx` swap comes after it (`tools/mcp_tool.py:39-71`).
- **Query:** `POST https://api.osv.dev/v1/query` with the package, ecosystem and version (`tools/osv_check.py:19,258-269`).
- **Block:** only `MAL-*` ids. CVEs are ignored (`tools/osv_check.py:1-7,269`).
- **Timeouts:** 10 s for HTTP inside a 12 s wall clock. On timeout the spawn goes on (`tools/osv_check.py:20`; `tools/mcp_tool.py:36,46-52`).
- **Cache:** 1 h, 256 entries, in `<home>/cache/osv_check.json`. Failures are not cached (`tools/osv_check.py:22-40`).
- **Why a cache:** revival loops once made 779K DNS queries in 16 h (#75485, `tools/osv_check.py:31-32`).

### 4.5 Trust tiers

- `trust: full` is the default. An unknown value means `untrusted`, so a typo cannot turn off the gate (`tools/mcp_tool.py:519-530`).
- On an untrusted server, each write-capable call asks for approval. Read-only means `readOnlyHint` is exactly true.
- An approval error blocks the call (`tools/mcp_tool_handlers.py:60-85`).

### 4.6 Native module errors (`tools/mcp_tool_node_abi.py`)

- The markers are `NODE_MODULE_VERSION` and `ERR_DLOPEN_FAILED` (`tools/mcp_tool_node_abi.py:16`).
- A match is a permanent error. The server parks instead of retrying (`tools/mcp_tool_node_abi.py:21-23`).
- The message names two fixes: delete the `npx` cache entry, or run `npm rebuild` with the right Node first on `PATH` (`tools/mcp_tool_node_abi.py:50-66`).

This is the fault class of plan item M1.

## 5. For this harness

### 5.1 What a doctor finds on this machine today

I ran each command read-only on 2026-10-17.

| Check | Command | Result |
|---|---|---|
| Tools | `command -v git python3 jq node` | all present |
| Links | compare each linker path with its source | 18 of 19 linked. `~/.claude/remote-settings.json` is a real file, and `remote-settings.json.bak` exists |
| Linker | `bash dotfiles/tools/setup/link_dotfiles.sh --dry-run` | exit 1: "Refusing to overwrite existing backup" (preflight, `link_dotfiles.sh:113-119`) |
| Codex skills | `python3 dotfiles/codex/install-skills.py --check` | exit 1: `explain`, `vercel-composition-patterns`, `vite`, `vitest` missing. `caveman`, `context-engineering`, `laravel-worktree-isolation` retired but still linked |
| Codex config | `python3 dotfiles/codex/install-config.py --check` | exit 1: `~/.codex/config.toml` is still a symlink into the repository |
| Codex base | `python3 dotfiles/codex/install-config.py --lint` | exit 1: `/home/`, `[desktop`, `[hooks.state`, `[marketplaces`, `[mcp_servers.node_repl`, `[plugins`. `HEAD` is clean |
| Hook trust | the snippet in §5.3, check 6 | 3 of 3 handlers have a trust entry |
| Episodic module | the command in §5.3, check 7 | `ERR_DLOPEN_FAILED`: built for ABI 115; Node v26.9.0 needs 147 |
| Episodic index | `stat` on `db.sqlite` | last change 2026-09-19, 28 days ago |
| Memory sizes | `wc -l -c ~/.claude/projects/*/memory/MEMORY.md` | largest 8 lines, 1062 bytes. `~/.codex/memories`: 81 files, 884 KB |

Three findings matter:

- **The Codex app writes into the repository.** The symlink sends its machine state into `dotfiles/codex/config.toml`. The uncommitted 67 lines are that state. `install-config.py` (ADR 0086) and HANDOFF open item 1 describe the fix.
- **The linker cannot run.** The `.bak` conflict stops it at preflight, so the Codex merge and the skill links wait too.
- **A require test gives a false pass.** `require('better-sqlite3')` loads, because the addon loads on the first `new Database()`. Check 7 must open a database.

### 5.2 T1 — one health command (changed)

**Changed recommendation:** write `dotfiles/tools/setup/doctor.py`, Python
standard library only, not `tools/doctor.sh`. Reasons:

- Native Windows is decided. Git for Windows ships no `jq` (ADR 0087).
- H1 moves the hooks to Python. A bash doctor would add one more bash script to port.
- The installers it calls are Python already (`install-config.py`, `install-skills.py`).
- T3 needs a lock that works on Windows. Hermes uses `fcntl` or `msvcrt` (`cron/scheduler.py:4093-4112`).
- `setup/` holds the linker. The doctor checks what setup made (`dotfiles/tools/README.md`).

**Copy from Hermes:**

- an ordered list of named checks, one row each: `PASS`, `WARN`, `FAIL` or `ACK`;
- two kinds of `FAIL`: fixable by a harness command, or manual;
- `WARN` never fails the run;
- exit 0 when no `FAIL` row is left, 1 otherwise, 2 for a usage error;
- one summary with a numbered list of what to do;
- a repair command on each fixable row, and only repairs that the next install keeps (`hermes_cli/doctor_tools.py:417-427`).

**Rules:**

- **No changes in v1.** The plan says "Changes nothing". A later `--fix` runs only owned repairs, then runs the check again (`tests/hermes_cli/test_doctor.py:876-916`).
- **Never touch user-managed files.** A real file at a link path is a manual row (`hermes_cli/doctor_platform.py:629-631`).
- **Use the published checks.** Call `install-skills.py --check` and `install-config.py --check`. Do not copy their logic.
- **Add `--check` to the linker.** It exits 1 when any path would change, like the two installers. Then the doctor does not copy the 19 path pairs.
- **Add `--ack <check>:<reason>` now.** Phase 0 keeps checks 7 and 8 red. A doctor that always fails gets ignored. An acked row prints `ACK` and does not fail. The ack drops when the check passes.
- **Offline by default.** `--live` adds the network checks.
- **Take a home folder.** Add `--home DIR`. `Path.home()` ignores `HOME` on Windows. `agent_sessions_mcp.py:29` uses the same override pattern.
- **Keep the name apart.** `bin/worktree-doctor.sh` is the project contract of ADR 0058. Share its shape: no changes, exit 0 when current, clear text otherwise.

**Verify:**

- a test with a fixture home, like `dotfiles/tools/tests/test-link-dotfiles.sh:15-16,42`;
- one run on this machine that shows the §5.1 failures;
- the Windows path in W1's CI job, because CI runs only `ubuntu-latest` (`.github/workflows/ci.yml:31`).

### 5.3 T1 check list

| # | Id | Exact command | Fails as | Repair the row prints |
|---|---|---|---|---|
| 1 | `tools` | `command -v git python3 jq` | FAIL, manual | install it. Without `jq`, every guarded shell command is denied (ADR 0087) |
| 2 | `links` | `bash dotfiles/tools/setup/link_dotfiles.sh --check` (new flag) | missing or foreign link: FAIL, fixable. Real file: FAIL, manual | `bash dotfiles/tools/setup/link_dotfiles.sh` |
| 3 | `codex-skills` | `python3 dotfiles/codex/install-skills.py --check` | FAIL, fixable | `python3 dotfiles/codex/install-skills.py` |
| 4 | `codex-config` | `python3 dotfiles/codex/install-config.py --check` | FAIL, fixable | `python3 dotfiles/codex/install-config.py` |
| 5 | `codex-base` | `python3 dotfiles/codex/install-config.py --lint` | FAIL, manual | do not commit; merge first (row 4), then remove the machine state from the repository file |
| 6 | `codex-hook-trust` | the snippet below | FAIL, manual | open `/hooks` in Codex and trust the hook |
| 7 | `episodic-module` | `node -e 'const D = require(process.argv[1]); new D(":memory:").close()' "$P/node_modules/better-sqlite3"` | FAIL, manual | M1: `npm rebuild better-sqlite3` in the plugin folder |
| 8 | `episodic-index` | `python3 -c 'import os, sys, time; sys.exit(time.time() - os.path.getmtime(sys.argv[1]) > 2 * 86400)' ~/.config/superpowers/conversation-index/db.sqlite` | FAIL, manual | same as row 7 |
| 9 | `memory-size` | `wc -l -c ~/.claude/projects/*/memory/MEMORY.md` | over 200 lines or 25 KB: WARN | trim the index |
| 10 | `mcp-connect` (`--live`) | `claude mcp list` | a server not "Connected": WARN | export the variable, or run `/mcp` |
| 11 | `mcp-osv` (`--live`) | the `curl` below, once per pinned `npx` package | a `MAL-*` id: FAIL, manual. Network error: WARN | remove the server; pick a clean version |

Notes:

- **Row 6 snippet** (tested here; it prints `ok` or `MISS` for each handler):

  ```python
  import json, pathlib, re
  home = pathlib.Path.home()
  hooks = home / '.codex' / 'hooks.json'
  cfg = (home / '.codex' / 'config.toml').read_text()
  snake = lambda s: re.sub(r'(?<!^)(?=[A-Z])', '_', s).lower()
  for ev, groups in json.loads(hooks.read_text())['hooks'].items():
      for g, group in enumerate(groups):
          for h, _ in enumerate(group.get('hooks', [])):
              key = f'[hooks.state."{hooks}:{snake(ev)}:{g}:{h}"]'
              print('ok  ' if key in cfg else 'MISS', key)
  ```

- **Row 6 limit:** the check sees a missing trust entry, not a changed handler. I could not find the input of `trusted_hash`. A SHA-256 of the command, the handler, the group or the whole file did not match.
- **Row 7:** `$P` is the newest folder in `~/.claude/plugins/cache/superpowers-marketplace/episodic-memory/`. Match the Hermes markers in stderr (§4.6). No `node` is also a manual FAIL.
- **Row 8:** use the main file only. Every open gives `db.sqlite-wal` a fresh mtime; today it is 0 bytes with today's date. Plan M2 replaces this proxy with the newest exchange.
- **Row 9:** the limits come from plan M2. I did not verify them. Codex memories get a size line only, because no limit is known. When M2 lands, call it instead.
- **Row 10:** `claude mcp list` starts the stdio servers, so it is a `--live` row.
- **Row 11 command:**

  ```bash
  curl -sS --max-time 10 -d '{"package":{"name":"chrome-devtools-mcp","ecosystem":"npm"},"version":"1.10.1"}' https://api.osv.dev/v1/query
  ```

  Repeat it for `mcp-remote` version `0.14.3`. Fail when any `vulns[].id` starts with `MAL-`.
  I did not run it; this task had no network.

### 5.4 T2 — Gemini removal (deferred)

Phase 0 is declined, so T2 waits. The wait condition also still holds:
`agent_sessions_mcp.py` has uncommitted edits, and `agent_deck.py` is
untracked.

- **Gemini code:**
  - `dotfiles/tools/agent_sessions_mcp.py`: lines 2, 10, 17, 286-325 (`scan_gemini`), 342, 400 and 469;
  - `dotfiles/tools/agent_deck.py`: lines 2, 31 (`AGENTS["gemini"]`) and 329.
- **Correction to the plan:** `agent_deck.py` has no `--print`. The plan's check covers only `agent_sessions_mcp.py`.
- **Test 1** must fail before the change:
  1. Write `$FX/.gemini/tmp/p1/chats/s1.json` with `{"sessionId":"g1","messages":[{"type":"user","content":"hi"}]}`.
  2. Run `AGENT_SESSIONS_HOME="$FX" python3 dotfiles/tools/agent_sessions_mcp.py --print`.
  3. Fail when any entry in `sessions` has `"agent": "gemini"`.
- **Why that variable:** `AGENT_SESSIONS_HOME` overrides the home folder (`agent_sessions_mcp.py:29`). It works on native Windows, where `HOME` does not.
- **Test 2:** import `agent_deck` and assert that `"gemini"` is not in `AGENTS`. The import starts no server; `main` runs only as a script (`agent_deck.py:502`).

### 5.5 T3 — scheduled health run (changed)

Copy the incident logic and the run log. Change the trigger and the key.

**Trigger: the session-start hook, not cron.** When the last finished run is
older than 7 days, the hook runs the offline doctor with a 5 s bound.
Reasons:

- Native Windows has no cron or systemd. W1 says the harness needs no scheduled task.
- One code path then serves Linux and Windows.
- Nothing needs to fire while no session runs. Our "gateway" is the session itself. Hermes sends a watchdog to OS cron only for that case (`cron-script-only.md:271`).
- The bound copies the worktree readiness check (`dotfiles/claude/hooks/worktree-readiness.sh:34`).
- This needs H1 first, so the hook can call the doctor in Python.

**Alternative:** an OS scheduler on each platform: a systemd user timer with
`Persistent=true`, and a Windows scheduled task. That gives two install
paths, and it contradicts W1. I do not recommend it.

**Design:**

- **Key:** `<check id>:<reason code>`. Each check emits a fixed code, for example `episodic-module:abi-mismatch`. Do not hash the message. Hermes keeps numbers in its signature (`cron/incidents.py:44-45`), so a changing count would open a new incident each run.
- **States:** `detected` → `alerted` → `resolved`. A recurrence returns to `detected` (`cron/incidents.py:156-197`).
- **Acks:** an ack closes the incident. Unlike Hermes, a pass drops the ack. A fixed fault that returns is new information.
- **Alerts:** one banner line for each `detected` incident. Mark it `alerted` only after the hook printed it (`cron/scheduler.py:3201-3202`).
- **No reminders.** Hermes reminds every 6 h by default (`cron/scheduler.py:325`). At our cadence that is every run.
- **Broken state file:** show the alert anyway, as Hermes does (`cron/scheduler.py:355-376`).
- **Run log:** `~/.cache/harness/doctor-runs.jsonl`. Write a start record before the checks and an end record after them. Keep the last 100 runs.
- **Unfinished run:** the next run holds the lock, so the earlier run has ended. Mark its open record `unknown`. Hermes needs a pid and start-time test only because its ledger has no such lock (`cron/executions.py:134-149`).
- **Lock:** `fcntl.flock` or `msvcrt.locking`, non-blocking (`cron/scheduler.py:4093-4112`). Contention: exit quietly. Any other error: print it. Do not use `flock(1)`; it is a util-linux tool.
- **No retry ladder.** Hermes retries because a cron run costs tokens (`cron/unreachable_retry.py:33`). Our run is free, and the next session start retries.
- **No model call** anywhere, like Hermes `no_agent` jobs (`cron/scheduler.py:1522-1574`).

All state goes in `~/.cache/harness/doctor-state.json`: acks, incidents and
the last run time.

### 5.6 MCP environment findings

| Client | Server | Transport | Credential source |
|---|---|---|---|
| Claude | `github` | HTTP | header `Bearer ${GITHUB_TOKEN}` (`dotfiles/claude/mcp/setup.sh:52-55`) |
| Claude | `apify` | HTTP | header `Bearer ${APIFY_TOKEN}` (`setup.sh:58-61`) |
| Claude | `jira` | HTTP | OAuth through `/mcp` (`setup.sh:76-82`) |
| Claude | `figma` | HTTP | OAuth through `/mcp` (`setup.sh:84-95`) |
| Claude | `context7` | HTTP | header `Bearer ${CONTEXT7_API_KEY}`, only when set at setup (`setup.sh:107-114`) |
| Claude | `structurizr` | HTTP | none (`setup.sh:116-120`) |
| Claude | `chrome-devtools` | stdio, `npx -y chrome-devtools-mcp@1.10.1 --isolated` | none; no env block (`setup.sh:130`) |
| Codex | `phpstorm` | HTTP to `127.0.0.1:64443` | none (`dotfiles/codex/config.toml:30-31`) |
| Codex | `atlassian` | stdio, `npx -y mcp-remote@0.14.3 <url>` | OAuth in `mcp-remote`; no env block (`config.toml:33-36`) |
| Codex | `chrome-devtools` | stdio, same pin | none; no env block (`config.toml:38-40`) |
| Codex | `node_repl` | stdio, written by the Codex app | 13 env keys: paths, flags, versions; no credential names (working tree only) |

Findings:

1. **Tokens live in the client's environment.** The client expands `${VAR}`, so `GITHUB_TOKEN` and `APIFY_TOKEN` must be exported where Claude Code starts (`setup.sh:13-18`).
2. **One stdio server can see them.** If Claude Code passes its full environment to stdio servers, `chrome-devtools-mcp` gets both tokens. `--isolated` isolates the Chrome profile only (`setup.sh:125-126`).
3. **Not verified:** what each client passes to a stdio server. Hermes passes only the §4.2 allowlist. Hermes also keeps credentials from cron scripts (`cron-script-only.md:31`).
4. **Owner check, names only:** run `tr '\0' '\n' < /proc/<pid>/environ | cut -d= -f1` for the `chrome-devtools-mcp` process. Look for token names.
5. **The client reported the `github` server as failed in this session:** "Authorization header is badly formatted". That fits an unset `GITHUB_TOKEN` (`setup.sh:42-49`). I did not check further.
6. **`node_repl` is machine state.** The `--lint` check flags it. It must not reach `HEAD`.

Recommendation: this stays a review task. Run check 4 first. Decide on
changes after it. Neither client offers Hermes's allowlist, so the only
levers are the environment that starts the client and a per-server env block.

### 5.7 Do not copy

- the tool registry and the toolsets: both clients own their tools;
- cron agent jobs: Claude routines exist if scheduled model runs are ever needed;
- the unreachable retry ladder (§5.5);
- the OSV check on every spawn: our versions are pinned, so a weekly `--live` row is enough;
- trust tiers: both clients own their approvals;
- the 6 h repeat-alert default (§5.5).

## Sources

Hermes commit `5fea5a7a4bf6d02b3427fc0bcae95502222cea2e` (2026-10-17), from a
local clone. Paths are relative to the repository root.

Read in full:
- `tools/registry.py`, `toolsets.py`
- `hermes_cli/doctor.py`, `hermes_cli/subcommands/doctor.py`, `hermes_cli/doctor_report.py`
- `hermes_cli/doctor_platform.py`, `hermes_cli/doctor_config.py`, `hermes_cli/doctor_state.py`
- `hermes_cli/doctor_tools.py`, `hermes_cli/doctor_connectivity.py`, `hermes_cli/doctor_live.py`, `hermes_cli/mcp_security.py`
- `cron/AGENTS.md`, `cron/constants.py`, `cron/occurrences.py`, `cron/scheduler_tick.py`, `cron/scheduler_preflight.py`
- `cron/unreachable_retry.py`, `cron/incidents.py`, `cron/executions.py`
- `tools/mcp_tool_transport.py`, `tools/mcp_tool_config.py`, `tools/mcp_tool_node_abi.py`, `tools/osv_check.py`
- `website/docs/guides/cron-script-only.md`, `tests/hermes_cli/test_doctor_exit_status.py`

Read in part:
- `model_tools.py`, `cron/scheduler.py`, `cron/jobs.py`, `cron/store_health.py`, `cron/monitor.py`
- `tools/mcp_tool.py`, `tools/mcp_tool_handlers.py`, `tools/mcp_tool_discovery.py`, `tools/mcp_tool_common.py`
- `gateway/status.py`, `agent/delegation_context.py`, `hermes_cli/env_loader.py`
- `tests/hermes_cli/test_doctor.py`
- `website/docs/user-guide/features/cron.md`, `website/docs/developer-guide/cron-internals.md`
