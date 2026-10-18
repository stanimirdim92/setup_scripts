# Hermes research: agents, delegation and the agent loop

Part of `../hermes-adoption-plan.md` (items A1 and A2, and a proposed C1).
The source is `NousResearch/hermes-agent` at the commit named in §Sources. It
was read from a local clone on 2026-10-17.

Terms in this file:
- A **child** is a Hermes subagent. A **subagent** is a Claude Code or Codex one.
- **Compaction** is the step that Hermes calls compression. Code names keep the Hermes spelling.

## Coverage

**Read in full:**
- `tools/delegate_tool.py` and its helpers: `delegate_tool_child_run.py`, `_progress.py`, `_results.py`, `_dispatch.py`, `_toolsets.py` and `_tasks.py`.
- `tools/delegation_output_schema.py`.
- `agent/conversation_loop.py` (1,867 lines). Lines 820-942 and 1160-1389 were only skimmed.
- `agent/tool_guardrails.py`, `agent/repetition_guard.py`, `agent/turn_stop_gates.py`, `agent/kanban_stop.py` and `agent/iteration_budget.py`.

**Read in part:**
- `tools/delegate_tool_config.py` (lines 1-260; the rest is credential routing), `tools/delegate_tool_registry.py` and `tools/async_delegation.py`.
- `run_agent.py` (1,555 lines): tool workers, the review spawn, the delegate cap, dedupe and the guardrail wiring.
- `agent/context_compressor.py` (5,823 lines): constants, prefix, template, the parts that need no model, the prune passes, the trigger and the phases.
- `agent/context_compressor_prellm.py`, `agent/context_compressor_tail.py` and `agent/compression_marker.py`.
- The docstrings of `agent/micro_compaction.py` and `agent/conversation_compression.py`.
- 15 of the 33 `agent/turn_*.py` phase modules, at the cited lines. For the other 17, only the module docstring.
- `agent/system_prompt.py`, `agent/prompt_builder.py`, `agent/agent_runtime_helpers.py`, `agent/retry_utils.py`, `agent/chat_completion_helpers.py`, `agent/agent_init.py` and `agent/verification_stop.py`, at the cited lines.
- `hermes_cli/config_defaults.py` (the agent, compression, delegation and kanban blocks), `hermes_cli/kanban_db.py` (task completion) and `tools/kanban_tools_schemas.py`.
- Docs: `website/docs/user-guide/features/delegation.md`, `website/docs/user-guide/features/kanban.md` (lines 1-140) and `website/docs/developer-guide/agent-loop.md`.

**Not read:**
- The tests, except the imports of `tests/agent/test_stall_guards.py`. The code and the config comments state every threshold in this file.
- The Hermes `AGENTS.md`.
- The body of `agent/conversation_compression.py` (4,500 lines) and of `agent/micro_compaction.py`. Micro-compaction is off by default.
- `agent/context_compressor_summary.py`, `_retry.py` and `_telemetry.py`.
- The kanban dispatcher and worker code.

**Our repo, read for §8:**
- `claude/docs/agents.md`, `claude/hooks/require-handoff-report.sh` and the persona frontmatter.
- `tools/run/run-metrics.sh`, `tools/tests/test-run-metrics.sh` and `claude/references/agent-run-metrics.md`.
- `claude/references/component-response-contracts.md` §3, `claude/AGENTS.md` §Session and context, and `claude/settings.json`.
- `docs/observation-log.md`, `docs/IDEAS.md` and ADRs 0043, 0066, 0068, 0080, 0082 and 0084.

## 1. Agent loop and budgets

`run_conversation` (`agent/conversation_loop.py:1717`) wraps
`_run_conversation_turn` (`:1555`). The loop runs while `api_call_count` is
below `max_iterations` and the iteration budget has calls left. It also runs
while the grace flag is set (`:1656-1658`).

Each iteration runs these phases in order (`:1659-1709`):
1. `begin_iteration` and `prepare_iteration`;
2. `assemble_api_request`;
3. `run_preflight_gate`, which can start compaction;
4. `_run_api_retry_loop` (§2);
5. `normalize_model_response`;
6. `run_tool_round`, or `finish_text_response` when there are no tool calls.

An exception goes to `handle_outer_loop_error`. After the loop,
`finalize_turn` builds the result (`:1711-1714`).

| Budget | Default | Source |
|---|---|---|
| Main agent iterations | unlimited (`max_turns: None`); caps "caused silent mid-task truncation" | `hermes_cli/config_defaults.py:76-78`; `hermes_cli/config.py:1828` |
| Child iterations | 250, a fresh budget for each child | `tools/delegate_tool.py:105, 289`; `config_defaults.py:1360` |
| Run time | off (`run_budget_seconds: None`) | `config_defaults.py:82-85` |
| Outer-loop errors | `_MAX_OUTER_LOOP_ERRORS = 8`, or `max_iterations` when that is lower | `conversation_loop.py:237`; `agent/turn_loop_errors.py:147-170` |
| Compaction attempts per turn | 3 (config cap 10) | `conversation_loop.py:1645`; `config_defaults.py:576-650` |

The "500" and "50" in `agent/iteration_budget.py:3-5` and
`website/docs/developer-guide/agent-loop.md:184-185` are stale. They are the
source of the "50" in the previous version.

**Grace call.** It is not a general extra call after the budget. Only the
reasoning-only stall path sets it (`agent/turn_truncation.py:630-636`). The
next iteration uses it (`agent/turn_iteration_prep.py:406-411`). Without it, a
spent budget ends the loop with `budget_exhausted` (`:412-416`).

**Budget spent.** The finalizer first reuses a withheld, verified answer.
Otherwise it makes one summary call with no tools, and retries once on an
empty reply (`agent/turn_finalizer.py:124-171`;
`agent/chat_completion_helpers.py:2278-2332`). A kanban worker also records
the event (`turn_finalizer.py:173-194`).

**Run-time notice.** When a run budget is set, a one-time wrap-up notice goes
into the newest tool result at 80% (`conversation_loop.py:76-80, 124-156`).

**Iteration checkpoint.** It is opt-in, and kanban workers use 0.9 of the
budget. Its text says that "a diff or commit alone is not completion evidence"
(`turn_iteration_prep.py:41-99, 83`).

**Other loop facts:**
- Unanswered tool calls get error results before the turn ends. A local bug ends the turn at once (`turn_loop_errors.py:120-170`).
- The context estimate never goes below the provider's last real prompt size (`conversation_loop.py:392-419`).
- After 3 failed compaction attempts, the turn returns a partial result with `compression_exhausted=True` (`conversation_loop.py:1097-1157`).

## 2. API retries and backoff

| Layer | Count | Wait | Source |
|---|---|---|---|
| OpenAI SDK | 2 retries | SDK default | `config_defaults.py:130-133` |
| Hermes, per call | `api_max_retries` 3, floor 1 | `min(2·2^(n−1), 60)` s plus up to 50% jitter; a `Retry-After` wins, up to 600 s | `agent/agent_init.py:1442-1447`; `agent/turn_recovery.py:1401-1465`; `agent/retry_utils.py:121-134, 182` |
| Fallback chain | each configured provider | — | `agent/turn_api_error.py:358-398` |
| Auto-recovery ladder | 5 cycles | jittered 15/30/60/60/60 s; a `Retry-After` wins, up to 120 s | `agent/turn_recovery_autorecover.py:1-11, 26-31, 49-56`; `config_defaults.py:134-139` |
| Empty reply | 3 retries; 1 when one empty attempt costs $0.25 or more | — | `config_defaults.py:145-153` |

With the defaults, a failing call gets 3 attempts, with waits of about 2-3 s
and 4-6 s. Then the fallback chain runs. The ladder runs last. It takes only
overload, server errors and timeouts, and only when no answer reached the user.
Auth, format, billing and content-policy errors never enter it.

## 3. Loop and stall protection

### 3.1 Tool guardrails (`agent/tool_guardrails.py`)

| Detector | What it counts | Warn | Hard stop | Lines |
|---|---|---|---|---|
| Exact failure | the same tool and arguments fail again, with no change between | 2nd | block before the 5th | 116-132, 357-373 |
| Same-tool failure | one tool fails with different arguments | 3rd | halt at 8; never for `terminal`, `execute_code` and the other failure-tolerant tools | 56-58, 375-433 |
| No progress | a read-only tool gives the same result for the same arguments | 2nd | block at 5 | 116-132, 375-433 |
| Identical-call streak | any tool, same arguments and same result, back to back | notice at the 3rd | halt at 5 | 38, 438-489 |
| Cycle | a repeating batch of 2-4 calls with the same results | notice at 3 laps | halt at 5 laps | 45-47, 491-523 |
| Result stub | the 2nd identical result of 512 chars or more, not an error | — | the context gets a short stub; the tool still runs | 50, 485-489 |
| Loop caps | `web_search` calls and child spawns per turn | — | 50 each, always on | 80-81, 101-103 |

Hard stops are off by default. They switch on only for unattended platforms.
The attended set is `cli`, `tui`, `desktop`, `acp`, `subagent` and
`api_server` (`tool_guardrails.py:85, 93-97, 143-144`). So a Hermes child gets
only warnings, and the cap of 50 spawns is the backstop.

Other rules:
- Pollers never get the identical-call notice (`:35-36`).
- A successful write, patch or command resets the failure counts (`:62-66`).
- On a halt, the reply says what happened and asks how to continue. It shows no decision codes (`run_agent.py:1248-1255`).

No `agent/stall_guards*.py` module exists. `stall_guards` is a config switch,
on by default (`config_defaults.py:177-181`). `tests/agent/test_stall_guards.py`
imports from `tool_guardrails` and `agent_runtime_helpers`.

### 3.2 Continuation nudges

Three nudges share one counter, with at most 2 for each turn
(`agent/turn_final_response.py:172-249`):
- **Stall:** a reply of 400 chars or fewer, with no tool calls, ends on an announced next action. Only its last 160 chars are checked (`agent/agent_runtime_helpers.py:3381-3399`).
- **Degenerate final:** a short fragment ends a turn that did real tool work.
- **Ack:** an intermediate acknowledgement with no action.

After 2 nudges, the next stop ends the turn. Other caps:
- a dropped tool call gets at most 3 re-prompts in a row (`turn_final_response.py:290`);
- an unknown tool name gets 3 strikes, then a partial exit (`agent/turn_tool_validation.py:129-137`);
- malformed JSON arguments get 3 retries (`:205-216`).

### 3.3 Repetition guard (`agent/repetition_guard.py`)

| Check | Rule | Used on | Lines |
|---|---|---|---|
| `is_repetition_dominated` | 400 chars or more; one 60-char window repeats 5 or more times and covers 50% | a reply cut by the length limit, before a "continue" nudge; tool arguments from a dropped stream | 17-23, 52-71; `turn_truncation.py:260`; `chat_completion_helpers.py:3281` |
| `is_runaway_repetition` | the rule above, and at most 50% distinct lines | a completed answer of 16,000 chars or more ends the turn as truncated; a fixed marker replaces an interrupted partial | 29, 41, 46, 139-150; `turn_final_response.py:270-282`; `agent/turn_api_call.py:196` |
| `RunawayStreamWatch` | first check at 16,000 chars, then at doubling gaps up to a 64,000-char tail | a live stream | 50, 163-194; `chat_completion_helpers.py:3054-3057` |

### 3.4 Watchdogs and stop gates

- **Turn liveness:** a turn with no progress for 600 s is force-interrupted. The poll runs every 15 s, and time asleep does not count (`agent/turn_liveness.py:23-24, 113-143`; `config_defaults.py:289-294`).
- **Stop gates:** four gates run before a final answer. The LSP gate allows 3 nudges, and the answer stays as a fallback (`agent/turn_stop_gates.py:7-9, 95, 141-156`).
- **Verify-on-stop:** off by default, because it gave "more noise than signal". It allows 2 attempts (`config_defaults.py:216-221`; `agent/verification_stop.py:160-166`).
- **Kanban terminal tool:** a worker that stops without a terminal kanban call gets at most 2 nudges (`agent/kanban_stop.py:22-30, 83-98`).

## 4. Delegation

### 4.1 Limits

| Item | Value | Source |
|---|---|---|
| Depth | `max_spawn_depth` 1 (flat), floor 1 | `tools/delegate_tool_config.py:21, 151-163`; `config_defaults.py:1380` |
| Role | orchestrator when orchestration is on and the child's depth is below the limit; otherwise leaf | `delegate_tool.py:232-234` |
| Concurrent children | 10, floor 1, no ceiling | `delegate_tool_config.py:17, 93-108` |
| Background children | 3 is only a function default | `tools/async_delegation.py:47, 906, 934` |
| One-shot children | 2 | `delegate_tool_config.py:85-90` |
| Wall-clock timeout | none; a 30 s floor when set | `delegate_tool_config.py:24-27, 134-149` |
| Images per task | 8 | `tools/delegate_tool_tasks.py:125` |
| Tool workers per agent | 8 | `run_agent.py:142` |

- At the depth limit, the call fails with an error (`delegate_tool.py:520-527`). The model's own `max_iterations` is ignored (`:530-537`).
- Too many tasks give an error, not truncation (`delegate_tool_tasks.py:81-86`). Placeholder goals, and batch goals under 10 chars, are refused (`:9-65`).
- There is no timeout by default, because fixed caps killed deep reviews and research mid-task (`delegate_tool_config.py:24-27`).
- Top-level delegations always run in the background. Children at depth 1 or more run synchronously (`delegate_tool.py:782-788`; `run_agent.py:1335-1348`).
- At capacity, a background dispatch falls back to a synchronous batch (`delegate_tool_config.py:121-132`; `tools/delegate_tool_dispatch.py:418-468`).
- Results arrive only between turns, and the model must not poll (`delegate_tool.py:630-636`; `delegate_tool_dispatch.py:325-346`).

### 4.2 What a child gets

- **Blocked tools:** `delegate_task`, `clarify`, `memory`, `send_message` and `cronjob_manage` (`tools/delegate_tool_toolsets.py:14-22`).
- **Removed toolsets:** `delegation` and `kanban`. An orchestrator gets delegation back, and kanban stays off (`:56-65, 116-122`).
- **Safety:** dangerous commands are denied by default (`delegate_tool_config.py:35-59`). Worktree isolation is off by default and degrades silently (`:115-119`; `tools/delegate_tool_child_run.py:385-404`).
- **State:** a dedicated handle on the session database, linked by `parent_session_id`, and the parent's credential pool (`delegate_tool.py:275-289, 321-326`).

**Child prompt** (`tools/delegate_tool_progress.py:180-219`):
1. a "focused subagent" opening (`:190`);
2. the CONTEXT block (`:191-192`);
3. the workspace path and the project files `AGENTS.md`, `CLAUDE.md` and `.cursorrules`, marked as binding (`:193-210`);
4. completion instructions, and a note for an orchestrator or a leaf (`:148-178`).

The goal arrives as the first user turn (`:187-189`). The child agent gets
`skip_context_files=True` and `skip_memory=True` (`delegate_tool.py:279-292`).
That drops SOUL.md and memory from the system prompt
(`agent/system_prompt.py:550-556, 715-728`). The child prompt then adds the
project files back, and it is not cached (`system_prompt.py:772`;
`agent/turn_context.py:1352-1353`).

### 4.3 Liveness

| Path | Check | Stale after | Then | Source |
|---|---|---|---|---|
| Synchronous | heartbeat every 30 s | 15 idle cycles (450 s), or 40 cycles in a tool (1,200 s) | a 2 s grace for a result that just finished, then a `timeout` or `error` entry | `delegate_tool.py:106-116`; `delegate_tool_child_run.py:313-331, 882-964` |
| Background | monitor every 30 s | 450 s idle, 1,200 s in a tool | "stalling", an interrupt, and after 120 s a forced `stalled` result | `async_delegation.py:85-88, 1096-1198` |
| Owner died | on restart | — | state `unknown`; partial children replay with transcript tails and a git hint | `async_delegation.py:282-331` |

Progress means that the API call count, the current tool or the activity clock
moved (`delegate_tool_child_run.py:313-321`). A child that waits for a model
reply is alive, because its activity clock ticks (`:248-257`). The stale
message says the child "stopped making progress after N API call(s)"
(`:934-938`). A child that made no API calls gets a diagnostic dump
(`:169-220`).

### 4.4 Result contract (`delegate_tool_child_run.py:553-650`)

| Field | Values |
|---|---|
| `status` | `completed`, `failed`, `interrupted`; the waiter adds `timeout` and `error`; the background path adds `stalled` and `unknown` |
| `exit_reason` | `completed`, `max_iterations`, `interrupted`, `error` |
| `truncated` | true when `exit_reason` is `max_iterations` (`:602`) |
| `summary` | the last text; "(empty)" counts as a failure (`:560-562`); an interrupt returns the last real text (`:564-574`) |
| Runtime facts | tokens, tool trace, cost, `failure_reason` (`:592-623`) |
| Schema fields | `schema_valid`, `schema_retries`, `schema_errors`, `schema_note` (`:629-641`) |
| `missed_steer` | steer text that arrived too late (`:643-649`) |

`failed`, `error` and `timeout` count as failures (`delegate_tool_progress.py:17`).

### 4.5 Output schema (`tools/delegation_output_schema.py`)

1. The child sees an OUTPUT CONTRACT block with the schema (`:45-57`).
2. The parent validates the reply and lists up to 10 errors (`:103-105`).
3. One correction retry carries the errors verbatim (`:109-115`). It is skipped when the reply is valid, empty or interrupted (`delegate_tool_child_run.py:479-519`).
4. There is only one retry, because more retries made the model drop fields (`delegation_output_schema.py:1-8`).
5. A failed check keeps the raw text and adds `schema_valid: false` and a "raw, UNVALIDATED" note. The run does not fail (`delegate_tool_child_run.py:580-585, 629-641`).
6. Without the `jsonschema` package, any parsed JSON passes (`delegation_output_schema.py:98-100`).

The tool description tells the model to keep schemas forgiving
(`delegate_tool.py:728-733`).

### 4.6 Summary size

A child summary is capped at 24,000 chars. When 50% of the parent's free
context is lower, that is the cap, with a floor of 2,000 chars. The rest goes
to a file. The parent gets a 75/25 head-and-tail excerpt and a `read_file` offset
footer (`tools/delegate_tool_results.py:165-279`).

### 4.7 Control

- `delegate_task` takes the actions `list`, `steer` and `stop`; spawn is the default (`tools/delegate_tool_registry.py:198`).
- `steer` adds text to the child's last tool result at its next iteration boundary. It never cuts a running tool (`:124-136`).
- `stop` ends a child at its next iteration boundary. The partial result returns as a normal completion (`website/docs/user-guide/features/delegation.md:494`).
- `/stop` on the parent stops the whole tree (`delegation.md:585-590`).
- A pause flag blocks new spawns (`delegate_tool_registry.py:15-46`).
- `subagent_start` and `subagent_stop` hooks fire around each child (`delegate_tool.py:332-339`; `delegate_tool_results.py:361-392`).

### 4.8 Tool round and background reviews

- Each tool call is saved before it runs. A failed save ends the turn (`agent/turn_tool_round.py:1-6, 56-59, 130-153`).
- Duplicate calls in one turn are dropped, and the first one wins. The arguments are compared as canonical JSON with sorted keys (`run_agent.py:1194-1210`).
- `delegate_task` calls above the concurrency limit in one turn are dropped with a warning (`run_agent.py:1174-1191`).
- The background review spawn never runs in a child. It copies the history, waits for an idle machine on local models, and is queued again 3 times at most (`run_agent.py:757-850`).
- A memory review runs every 10 user turns (`agent/agent_init.py:1304, 1333`; `agent/turn_context.py:758-767`). A skill review runs after 10 iterations (`agent_init.py:1388-1390`; `turn_finalizer.py:762-769`).

## 5. Verifying child results, and kanban

Hermes never takes a child's text as fact:
- The tool description calls child summaries "SELF-REPORTS, not verified facts" (`delegate_tool.py:647-650`). It tells the parent to check them.
- Children cannot close tracked work (`:651-652`).
- The parent gets runtime facts next to the summary: the tool trace, the files read and written, and orphaned background processes (`delegate_tool_child_run.py:521-551, 992-1047`).
- A reminder fires when sibling children wrote the same files (`:971-990`).
- A file-mutation check, on by default, lists up to 10 failed writes that never landed (`agent/turn_explainers.py:114-232`; `config_defaults.py:883`).
- The completion guidance tells the model never to fabricate results (`agent/prompt_builder.py:386-396`).

**Kanban** is a durable SQLite task board with worker processes and a review
lane (`website/docs/user-guide/features/kanban.md:1-140`). Its defaults
(`config_defaults.py:1895-1950`):
- review dispatch on, a dispatch interval of 60 s, and a failure limit of 2;
- 2 to 8 tasks in progress, from the machine's memory;
- a stale task times out after 14,400 s.

`complete_task` checks claims in code (`hermes_cli/kanban_db.py:2547-2754`):
- Claimed new cards must exist and belong to this worker. Phantom ids raise an error.
- Empty completion evidence raises an error.
- A PR task needs GitHub acceptance at the exact head commit (`hermes_cli/kanban_pr_acceptance.py:1-12`).
- A task that runs under a live claim cannot be completed by another run.
- Declared artifacts must exist (`tools/kanban_tools_schemas.py:129-165`).

The prompt says that `delegate_task` does not replace the board
(`prompt_builder.py:343`).

## 6. Context compaction

### 6.1 Trigger

The trigger is 50% of the usable input window: the window minus the output
reservation (`agent/context_compressor.py:2749-2807`). It has three limits:
- a floor of 64,000 tokens (`agent/model_metadata.py:274`);
- 75% or more for windows under 512K tokens (`:1151-1152`);
- at most 85% when the floor binds (`:2724`).

So a 200K window compacts near 150K tokens, and a 1M window near 500K.

Other controls:
- at most 3 attempts per turn (`config_defaults.py:576-650`);
- after ineffective passes, a 300 s block, then one probe (`context_compressor.py:2732-2735`);
- summary cooldowns: 60, 300 and 900 s after timeouts (`:794`), and 600 s after other failures (`:1124`);
- after 3 overload aborts in a row, the deterministic fallback goes in instead (`:806`);
- idle compaction, proactive pruning and micro-compaction are off by default (`config_defaults.py:576-650, 695`).

### 6.2 Order (`compress()`, `context_compressor.py:5526-5667`)

1. **Prune, with no model.** Duplicate tool results collapse. Old results become one-line summaries, such as `[read_file] read {path} from line {offset} (N chars)` (`:1946-1974, 3283-3321`).
2. **Boundaries.** The head keeps the first 3 messages. The tail keeps a token budget, with a floor of 8 messages (`:1136, 2232-2243, 2810`).
3. **Summary.** One model call per attempt (`:1001-1009`). It is skipped when the middle is under 10%, or after 2 fallbacks (`agent/context_compressor_prellm.py:13-16, 39-91`).
4. **Assembly.** The summary goes in with its prefix and end marker. With no summary, a deterministic fallback of up to 8,000 chars goes in (`:1127`).

Phase 1 rules:
- Tool-call arguments are never rewritten.
- The pending tool round is spared.
- Only the 3 newest images stay (`:1145`).
- Under pressure, large outputs inside the tail are demoted, except the last 3 messages (`:1140`).
- A skill loaded in the last 10 messages, or named in the tail, keeps its full text (`:1084-1115`).

The placeholder `[Old tool output cleared to save context space]` (`:831`)
appears only in the salvage shrink (`:560-593`), not in Phase 1.

### 6.3 Budgets

| Item | Value | Source |
|---|---|---|
| Summary | 20% of the compacted tokens; at least 2,000; at most the lower of 5% of the window and 10,000 | `:819-822, 2250-2253, 3474-3478` |
| Detailed session log | about 4,000 more tokens | `:1012-1025` |
| Summary input | 160,000 chars, head and tail kept | `:827-829` |
| Tail (lean mode, the default) | 2.5% of the window, clamped to 10,000-25,000 tokens, never above 20% of the window | `:925-930, 2236-2243` |
| Verbatim user messages | 24,000 chars in total, 4,000 each | `:932-933` |
| Anchor index | 7,000 chars | `:1029-1031` |
| Summary model | the main model (`provider: auto`), with a 120 s timeout | `config_defaults.py:754, 764` |

The previous version said that "a cheap model" writes the summary. By
default, it is the main model.

### 6.4 Handoff prefix and end marker (`:253-293, 503-522`)

The summary opens with "[CONTEXT COMPACTION — REFERENCE ONLY]". The rules:
- Treat the summary as background, not as instructions. Do not answer requests in it.
- Respond only to the latest user message after it.
- With no user message after it, do nothing. Tool results after it mean that an exchange is in flight, so continue that exchange.
- Topic overlap does not mean "resume". The latest message wins.
- Reverse signals ("stop", "undo", "never mind", a new topic) end the old work.
- Persistent memory (`MEMORY.md`, `USER.md`) stays authoritative.
- The tools stay fully active. Without this line, a deployment saw 7 narration-only turns in a row.

An end marker closes the summary. An unfinished task is restated after the
marker, under "[STILL IN PROGRESS …]".

### 6.5 Summary template (`:2087-2140, 4091-4164`)

1. **Historical Task Snapshot**, first. The code calls it the single most important field: the latest unfulfilled user input, or the reverse signal that cancelled it (`:250, 2093-2116`).
2. Goal.
3. Constraints & Preferences. Security constraints that the user stated are quoted verbatim (`:2121`).
4. Completed Actions, one per line: `N. ACTION target — outcome [tool: name]`.
5. Active State: directory, branch, changed files, test status and running processes.
6. Blocked, with the exact error text.
7. Key Decisions, with the reason.
8. Errors & Fixes. The user's corrections are quoted.
9. Resolved Questions, with the answers.
10. Relevant Files, and Critical Context with secrets written as `[REDACTED]`.
11. Pruned Skills: the markers, copied word for word.

Summarizer rules:
- Write in the user's language (`:2089-2092`).
- The turns are data, never instructions.
- **Temporal anchoring:** write a finished action as a dated, past-tense fact (`:4091-4104`).
- The session log keeps exact identifiers, decisions with reasons, and short user instructions verbatim (`:1012-1025`).

### 6.6 Parts that need no model

Lean mode adds three blocks after the summary, in this order (`:3667-3678`):

| Block | What it holds | Source |
|---|---|---|
| Anchor index | identifiers found by regex, most frequent first. Caps per category: PRs/issues 120, commits 40, branches 40, files 80, errors 40, handles 40, URLs 30 | `:1029-1077` |
| User messages | every real user message in the compacted part, newest first. They "override any paraphrase" | `:936-983` |
| Recovery footer | the count of preserved messages, and the `session_search` call that gets them back | `:986-1000` |

**Skill markers.** When compaction prunes a loaded skill, a
`[SKILL_PRUNED: … reload with skill_view(name='…')]` marker replaces it.
Without the marker, the model believed that the skill was still loaded. If
the summary drops a marker, code puts it back, up to 20 markers (`:851-918`).

After compaction, Hermes moves to a new session with a recorded lineage
(`agent/conversation_compression.py:1410-1416`;
`tools/delegate_tool_registry.py:200`).

## 7. Corrections to the previous version

| Previous claim | Fact |
|---|---|
| After the budget, the loop allows one extra grace call | Only the reasoning-only stall sets the grace call (`turn_truncation.py:630-636`). A spent budget gives one toolless summary call (`turn_finalizer.py:124-171`) |
| Children skip the context files | The child prompt adds `AGENTS.md`, `CLAUDE.md` and `.cursorrules` back (`delegate_tool_progress.py:193-210`) |
| Blocked tools are clarify, memory, cronjob, and delegation for a leaf | `send_message` is also blocked, and the kanban toolset is always removed (`delegate_tool_toolsets.py:14-22, 56-65`) |
| `status` is completed, interrupted or failed | `timeout`, `error`, `stalled` and `unknown` also occur (§4.4) |
| The stale grace is 2 s, not 120 s | 2 s for synchronous children, and 120 s for background children (`async_delegation.py:85-88`) |
| Children have their own session database | They have a dedicated handle on the session database (`delegate_tool.py:275-289`) |
| Phase 1 writes "[Old tool output cleared …]" | Phase 1 writes one-line summaries. The placeholder is only for the salvage shrink (`context_compressor.py:560-593, 1946-1974`) |
| A cheap model summarizes | The main model does, by default (`config_defaults.py:754, 764`) |
| The template starts at Goal | It starts at the Historical Task Snapshot (`context_compressor.py:250, 4107`) |
| The review counter was not found | Memory: every 10 user turns. Skills: after 10 iterations (§4.8) |
| The second identical result becomes a stub | Only a result of 512 chars or more that is not an error (`tool_guardrails.py:50, 485-489`) |
| Streaks append guidance, then halt the turn | They halt only with hard stops, and attended platforms, `subagent` included, do not have them (`tool_guardrails.py:85`) |
| The kept tail is 2.5% of the window, 10k-25k, at most 20% | Correct, for lean mode (`context_compressor.py:925-930, 2236-2243`) |
| The summary is 20% of the compacted text, 2,000-10,000 tokens | Correct, and the maximum is also capped at 5% of the window (`:2250-2253`) |

## 8. For this harness

### 8.1 What we already have (checked)

- **Spawn depth 1.** `claude/settings.json:10-12` sets `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=1`. It also turns off agent teams and forked subagents.
- **Seven Claude personas and eight Codex roles** (`claude/agents/`; `codex/agents/`, which adds `executor-high`).
- **Task packets** instead of the parent conversation (`claude/docs/agents.md:130-142`). This file is `claude/docs/agents.md`. A `docs/agents.md`, as the brief names it, does not exist.
- **Turn caps:** 100 for the read-only personas. Writers have no cap (ADR 0080).
- **Handoff hook** `claude/hooks/require-handoff-report.sh`:
  - It is a `Stop` hook in the executor and test-engineer frontmatter, which runs as `SubagentStop` (`claude/agents/executor.md:17-20`; `component-response-contracts.md:81-87`).
  - It checks only those two writers (`:30-33`).
  - It blocks at most twice (`:22`), and it fails open (`:19-20`).
  - It looks for verification outcomes, a commit, the tree state and an announced next step (`:59-73`).
  - It is a "shape check, not a truth check" (`:13`).
- **`tools/run/run-metrics.sh`** reports batching, tokens, the subagent split, large results and FAILURE SIGNALS (`:220-257`). The signals are errored results, denials, sandbox failures, handoff blocks, turn-cap mentions and repeated commands. It has no timing figures.
- **Compaction setup:**
  - the compaction window is 500,000 tokens (`claude/settings.json:7`; ADR 0043);
  - each pipeline stage starts in a fresh context (ADR 0084);
  - `/build` resumes from the task status committed in git (ADR 0068);
  - the global rule is `claude/AGENTS.md:142-147`. It is linked as `~/.claude/CLAUDE.md`, `~/.claude/AGENTS.md` and `~/.codex/AGENTS.md` (`tools/setup/link_dotfiles.sh:34-68`).

**Drift in our repo.** ADR 0080 says that `run-metrics.sh` reports turns per
agent. It does not. It only counts text that mentions a turn cap
(`run-metrics.sh:245`). The "Max turns used" column of its `--row` output is a
FILL placeholder (`run-metrics.sh:110`).

### 8.2 A1 — stall signals in `run-metrics.sh` (keep: Phase 1, size S, measurement only)

The previous mapping was wrong in one point. Hermes counts a model wait as
alive (`delegate_tool_child_run.py:248-257`). A Claude transcript writes no
record while the model works. So a long gap before an assistant record is
model time, not a stall. The previous third row, "a report just after the
stale mark", has no meaning here, because nothing marks a subagent stale.

| Hermes signal | Transcript fact | Start threshold |
|---|---|---|
| In a tool too long (40 × 30 s) | the time from a `tool_use` to its `tool_result` | 1,200 s |
| Abandoned work (`unknown`) | a `tool_use` with no `tool_result` in the transcript | any |
| Idle (15 × 30 s) | the time before an assistant record, labelled "slow model reply", not a stall | 450 s |

How to build it:
1. Pair the records by tool id. `run-metrics.sh` already pairs them in jq.
2. Report the counts in FAILURE SIGNALS, with the main session and each subagent apart.
3. Name the tool and its input for each long call.
4. Never kill or retry anything.

A long tool time can be a permission prompt that waits for a person. Say this
next to the count. Calibrate both thresholds from the observation log.

**Optional extension:** count the assistant replies in each subagent
transcript. This fills the "Max turns used" column and makes ADR 0080 true. It
is measurement only.

**Verify:** add a fixture to `tools/tests/test-run-metrics.sh`. Give it a
subagent transcript with a 1,300 s tool call, an unanswered `tool_use` and a
500 s model gap. Assert the three counts.

### 8.3 A2 — reviewer report shape check (keep: Phase 4, a gate, an ADR)

The code adds five points:
1. **Allow one correction turn, not two.** Hermes found that more retries make the model drop fields (`delegation_output_schema.py:1-8`). The writer hook's two blocks serve another purpose: unfinished work (ADR 0066).
2. **Name each missing piece in the block reason**, at most 10. The writer hook already does this (`require-handoff-report.sh:77-78`).
3. **Skip the block for an empty report or a capped partial.** Hermes skips its retry for empty or interrupted output (`delegate_tool_child_run.py:479-519`). Our contract accepts a capped partial (`component-response-contracts.md:316-318`).
4. **Let a failed report through, marked.** Hermes keeps the raw text with `schema_valid: false`. A hook cannot edit the report, so `/review` must list it as unvalidated.
5. **Keep the check forgiving.** Match lines for each finding, not a whole template (`delegate_tool.py:728-733`).

**Fix the contract first.** The fields are the id, the disposition,
`file:line`, the confidence and the finding text. "Claim", as the plan writes
it, is not a contract term. Two conflicts need one answer before a validator
exists:
- `blind-reviewer` intent-dependent findings have no disposition (`component-response-contracts.md:288, 407`).
- Confidence is `high|med|low` in two templates (`:254, 280`), but `high`/`medium`/`low` in the shared rule (`:314`).

The Codex adapter (`codex/hooks/policy.py:143`),
`tools/tests/test-handoff-hook.sh` and `tools/checks/validate-frontmatter.py`
change with it.

### 8.4 Adopt now, as wording only: subagent reports are self-reports

Add this to `claude/docs/agents.md` §Context discipline (`:130-142`): "A
subagent report is a self-report. Check its claims against evidence before
you act on them." `/build` already says that an executor summary alone is not
evidence (`claude/commands/build.md:266-269`). `/review` has no such sentence,
although the previous version said that it had.

### 8.5 C1 — compaction instructions (proposed, wording only)

The adoption plan has no C1 item yet. Add it to the plan, or drop the id.

Our rule (`claude/AGENTS.md:142-147`) keeps the goal, decisions, changed
files, evidence, blockers and remaining work. Proposed additions, from §6.5
and §6.6:
1. Put the latest unfinished request first. Quote it, and any "stop" or change of task, in the user's words.
2. Quote user decisions, corrections and stated security constraints verbatim.
3. Keep exact identifiers: SHAs, ticket ids, paths, commands and error text.
4. Write finished work as dated, past-tense facts.
5. Name where the full record lives: the transcript, `docs/tasks/<TICKET>-open.md` and git.

Do not copy the Hermes rule "do nothing when no user message follows". The
Claude Code message after compaction tells the model to continue the task.
This session shows that message. `/build` depends on that resume (ADR 0068).

**Not verified:** whether the automatic compaction of each client reads this
rule. **Verify:** compact one long session by hand, check the five points, and
log the result.

### 8.6 Park in `docs/IDEAS.md` (gates, so after the freeze)

- **Tail-only next-step check.** Hermes checks only short replies, and only their last 160 chars (`agent_runtime_helpers.py:3381-3399`). Our hook matches the phrase anywhere in the report, and also matches "I'm going to" (`require-handoff-report.sh:68-73`). So a long report can trip it. Revisit when the observation log records a false positive (`docs/observation-log.md:238-239`).
- **One truth check.** Confirm that the reported commit exists, like the kanban phantom-card check (`kanban_db.py:2547-2602`).

### 8.7 Do not copy

- `steer`, `stop`, background delegation and a credential pool. The clients own these, and the harness keeps spawn depth 1.
- 250-iteration budgets. Hermes removed its main-agent cap because caps truncated work silently. Our writers have no cap, and a capped reviewer reports a partial (ADR 0080).
- Ten concurrent children. The plan already rejects them (ADR 0054, ADR 0055).
- The kanban board. The ticket ledger (ADR 0088) and the committed task status (ADR 0068) hold durable state.
- Tool guardrails, loop caps and the stall monitor. The client owns the tool loop, and Hermes gives its own children only warnings.

## Sources

Hermes: `NousResearch/hermes-agent`, commit
`5fea5a7a4bf6d02b3427fc0bcae95502222cea2e`, local clone, 2026-10-17. Paths are
relative to the repository root.

- Delegation: `tools/delegate_tool.py`, `tools/delegate_tool_child_run.py`, `tools/delegate_tool_config.py`, `tools/delegate_tool_dispatch.py`, `tools/delegate_tool_progress.py`, `tools/delegate_tool_registry.py`, `tools/delegate_tool_results.py`, `tools/delegate_tool_tasks.py`, `tools/delegate_tool_toolsets.py`, `tools/delegation_output_schema.py`, `tools/async_delegation.py`
- Loop: `run_agent.py`, `agent/conversation_loop.py`, `agent/iteration_budget.py`, `agent/agent_init.py`, `agent/retry_utils.py`, `agent/chat_completion_helpers.py`
- Phase modules, at the cited lines: `agent/turn_api_call.py`, `agent/turn_api_error.py`, `agent/turn_context.py`, `agent/turn_context_compaction.py`, `agent/turn_explainers.py`, `agent/turn_final_response.py`, `agent/turn_finalizer.py`, `agent/turn_iteration_prep.py`, `agent/turn_liveness.py`, `agent/turn_loop_errors.py`, `agent/turn_recovery.py`, `agent/turn_recovery_autorecover.py`, `agent/turn_stop_gates.py`, `agent/turn_tool_round.py`, `agent/turn_tool_validation.py`, `agent/turn_truncation.py`
- Phase modules, docstring only: the other 17 `agent/turn_*.py` files
- Guards: `agent/tool_guardrails.py`, `agent/repetition_guard.py`, `agent/agent_runtime_helpers.py`, `agent/verification_stop.py`, `agent/kanban_stop.py`, `tests/agent/test_stall_guards.py` (imports only)
- Prompts: `agent/system_prompt.py`, `agent/prompt_builder.py`
- Compaction: `agent/context_compressor.py`, `agent/context_compressor_prellm.py`, `agent/context_compressor_tail.py`, `agent/compression_marker.py`, `agent/micro_compaction.py` (docstring), `agent/conversation_compression.py` (part), `agent/model_metadata.py`
- Kanban: `hermes_cli/kanban_db.py`, `hermes_cli/kanban_pr_acceptance.py`, `tools/kanban_tools_schemas.py`
- Config: `hermes_cli/config_defaults.py`, `hermes_cli/config.py`
- Docs: `website/docs/user-guide/features/delegation.md`, `website/docs/user-guide/features/kanban.md`, `website/docs/developer-guide/agent-loop.md`
