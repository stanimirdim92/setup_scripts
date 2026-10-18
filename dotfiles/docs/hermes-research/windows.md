# Hermes research: native Windows

Part of `../hermes-adoption-plan.md` (item W1 with H3, and H1 for the hooks).

Hermes facts come from a local clone of `NousResearch/hermes-agent`, read on
2026-10-17. The commit is in Sources. Facts about our repo come from HEAD
`504215e`. Three tags mark facts that do not come from Hermes source:

- **[DOCS]**: a Hermes docs page.
- **[BIN]**: strings in the local Claude Code 2.1.302 or Codex 0.158.0 binary.
- **[EXT]**: general Windows or Python behaviour that this session did not verify.

No Windows host was used. §14.7 lists the checks that need one.

## Coverage

**Read in full:**

- `scripts/check-windows-footguns.py` (970 lines), `scripts/check_no_tmp_literals.py`, `scripts/check_bash_shebangs.py`
- `scripts/run_tests.sh`, `scripts/install.ps1`
- `hermes_bootstrap.py`, `hermes_cli/stdio.py`, `pm/shell.py`, `tools/environments/local.py`
- `.gitattributes`
- `.github/workflows/`: `lint.yml`, `tests-os.yml`, `windows-install-update-e2e.yml`, `windows-venv-e2e.yml`
- `tests/pm/test_shell_candidates.py`, `tests/tools/test_approval_windows.py`

**Read in part** (the line ranges cited below):

- Hooks and subprocess: `agent/shell_hooks.py`, `hermes_cli/_subprocess_compat.py`
- Commands: `tools/approval_detection.py` (the Windows tier), `tools/terminal_tool_guards.py`, `tools/code_execution_env.py`
- Process cleanup: `gateway/status.py`, `agent/deadline.py`, `hermes_cli/local_runtime/processes.py`, `hermes_cli/gateway_windows.py`
- Links and paths: `hermes_cli/_launchers.py`, `hermes_cli/profiles.py`, `hermes_cli/worktree_ops.py`, `pm/store.py`, `pm/filesystem.py`
- Platform: `hermes_dir_acl.py` (header), `hermes_platform/AGENTS.md`, `hermes_platform/resolver/core.py`, `hermes_constants.py` (scratch folder)
- PowerShell: `setup-hermes.ps1` and `activate.ps1` (the encoding lines)
- Tests: `tests/conftest.py` (Windows markers and fixtures), `tests/_fixtures/platform_gating.py`, `tests/AGENTS.md`, `tests/e2e/core/windows/test_terminal_tool.py`, `tests/pm/test_long_paths_windows_live.py`, `tests/scripts/test_powershell_script_syntax.py`, `scripts/tests/test-install-ps1-longpath.ps1`
- Config and CI: `pyproject.toml` (the ruff section), `.github/workflows/case-collision-check.yml`
- [DOCS] `website/docs/user-guide/windows-native.md`, `skills/autonomous-ai-agents/hermes-agent/references/windows-quirks.md`

**Not read, with the reason:**

- `tools/terminal_tool.py` (grep only). Its Windows logic sits in `tools/environments/local.py`, which was read in full.
- `tools/approval.py`. The Windows patterns sit in `tools/approval_detection.py`.
- The rest of `hermes_platform/` and `hermes_dir_acl.py`. They hold GPU, host and ACL details that we do not need.
- Windows update, desktop and gateway-service modules, the desktop apps and their `.ps1` scripts. We ship no gateway and no desktop app.
- Most Windows tests, `install-e2e-windows-run.yml` (header only) and the release workflows.
- `scripts/check-case-collisions.py` (grep only). §14.2 runs our own case check.
- `website/docs/user-guide/windows-wsl-quickstart.md`. WSL2 is not the chosen path.

## 1. Six answers in short

| Question | Answer | Section |
|---|---|---|
| How does Hermes find bash? | `pm.shell.bash()` takes a staged Git first, then `HERMES_GIT_BASH_PATH`, the standard Git folders, and `bash` on `PATH`. It rejects `System32` and `WindowsApps` stubs and test-starts each candidate. | §2 |
| How does it start `.sh` and `.py` hooks? | It picks the interpreter by suffix: Git Bash for `.sh`, `sys.executable` for `.py`. It never uses a shell. | §3 |
| What is the encoding policy? | UTF-8 everywhere: UTF-8 mode, code page 65001, reads as `utf-8-sig`, writes as `utf-8` without BOM, and `errors='replace'` on child output. | §6 |
| How does it handle symlinks? | It avoids them on Windows. It uses launchers, junctions, copies or text files instead. Tests that need links skip. | §8 |
| How does it handle long paths? | `\\?\` paths in the package store, `core.longpaths` in the installer, a CI lane with long paths off, and 8.3 name expansion. | §9 |
| How does it clean up processes? | `taskkill /T /F` behind a start-time check, Job Objects for servers it starts, and CI checks for leftover processes. | §10 |

## 2. Shell strategy: how Hermes finds bash

Every terminal command on Windows runs through Git Bash. PowerShell and `cmd`
run only as children of bash (`tests/e2e/core/windows/test_terminal_tool.py:1-10, 32-38`).
`_find_shell` always returns bash on Windows (`tools/environments/local.py:613-622`).

**The resolver.** There is no `pm.shell()` function. The entry point is
`pm.shell.bash()` (`pm/shell.py:106-128`). It tries these candidates in order:

1. A Git that the Hermes package manager staged: `usr/bin/bash.exe`, then `bin/bash.exe` (`pm/shell.py:36-59`).
2. `HERMES_GIT_BASH_PATH` (`pm/shell.py:68-90`).
3. `%ProgramFiles%\Git`, `%ProgramFiles(x86)%\Git`, `%LOCALAPPDATA%\hermes\git` and `%LOCALAPPDATA%\Programs\Git`. Each root gives `bin` first, then `usr\bin`.
4. `bash` on `PATH`, unless it sits in `System32` or `WindowsApps` (`pm/shell.py:62-65`, issue #116818). Those folders hold the WSL launcher and Store alias stubs.

Each candidate must exist and pass `bash -c "exit 0"` within 5 s. The probe
starts with `CREATE_NO_WINDOW` (`pm/shell.py:93-103`).
`tests/pm/test_shell_candidates.py:1-40` fixes the order. The terminal backend
raises `RuntimeError` when no bash works (`local.py:543-555`).

**The environment of the bash child** (`tools/environments/local.py`):

- `PATH` starts with the Git `mingw64/bin`, `mingw32/bin`, `usr/local/bin`, `usr/bin` and `bin` folders (561-581). A non-login `bash -c` never reads `/etc/profile`, so `System32` lookalikes would win otherwise. User tool folders come next (592-603).
- `MSYS_NO_PATHCONV=1` and `MSYS2_ARG_CONV_EXCL=*` are defaults (745-760, issues #56700 and #56147). They stop MSYS from rewriting arguments that look like paths.
- Hermes converts paths between the `C:\` and `/c/` forms itself (136-190, 1150-1165).
- `_path_env_key` finds the `PATH` key in any letter case, because Windows environment keys ignore case (763-766).
- Bash rc files are not sourced on Windows (829-846).
- The temp folder uses forward slashes (1040-1049).
- `_run_bash` runs `[bash, -c, command]`, with an optional `-l`. It uses `encoding='utf-8'`, `errors='replace'` and `CREATE_NO_WINDOW` (1099-1125).

**Other guards:**

- A Windows-only guard protects the running Hermes checkout, because NTFS locks loaded modules (`tools/terminal_tool_guards.py:343-352`).
- Child Python keeps the Windows variables it needs (`tools/code_execution_env.py:48-54`). [DOCS] `windows-quirks.md:23-30` reports WinError 10106 when `SYSTEMROOT` is missing.

## 3. How Hermes starts hooks on Windows

`agent/shell_hooks.py` runs user hook scripts:

- The wire format is JSON on stdin. Exit code 2 blocks the action (1-5).
- The default timeout is 60 s, and the maximum is 300 s (37-38).
- `split_command_line` splits the hook command (24-25). On Windows it uses `shlex` with `posix=False` (`hermes_cli/_subprocess_compat.py:96-117`).
- On Windows the script suffix selects the interpreter (449):

  | Suffix | Interpreter |
  |---|---|
  | `.sh`, `.bash` | the bash from `_find_bash()` |
  | `.py` | `sys.executable` |

- The reason: `CreateProcess` cannot start a script file and fails with WinError 193 (442-448). `_windows_script_argv` builds the command (454-466).
- An unmapped suffix gets a clear error message (451, 500-505).
- `_spawn` uses `shell=False`, UTF-8 with `errors='replace'`, and `CREATE_NO_WINDOW` on Windows (469-520). On POSIX it uses `process_group=0`. A timeout calls `kill_process_tree`.
- The hook allowlist is read as `utf-8-sig` (687).

Our hooks run under Claude Code and Codex, not Hermes. §14.1 says how those
clients start them.

## 4. The footgun checker

`scripts/check-windows-footguns.py` has 970 lines and uses only the standard
library. It has 18 rules, and the old file numbered them correctly:

| # | Rule | Lines | Note |
|---|---|---|---|
| 1 | builtin `open()` in text mode without `encoding` | 144-183 | `Path.open` is not checked (151-154) |
| 2 | `os.fdopen` in text mode without `encoding` | 184-210 | Ruff PLW1514 does not cover it |
| 3 | `os.kill(pid, 0)` | 211-225 | Sends `CTRL_C_EVENT` on Windows (bpo-14484); use `psutil.pid_exists` |
| 4 | `os.setsid` | 226 | |
| 5 | `os.killpg` | 241 | |
| 6 | `getuid`, `geteuid`, `getgid`, `getegid` | 252 | |
| 7 | `os.fork` | 264 | |
| 8 | `signal.SIGKILL` | 273 | |
| 9 | other POSIX-only signals | 282 | |
| 10 | `./script` calls | 296 | |
| 11 | `wmic` | 308 | |
| 12 | a hard-coded `Desktop` path | 329 | |
| 13 | `add_signal_handler` | 345 | |
| 14 | subprocess `text=True` without `encoding` | 360-408 | Fires only when the same line holds a subprocess call (601-630) |
| 15 | `read_text`/`write_text` without `encoding` | 409-440 | Skips calls that do not close on the same line (633-646) |
| 16 | a read with plain `utf-8` | 441-471 | Wants `utf-8-sig`; `/proc` and `/sys` are exempt |
| 17 | a write with `utf-8-sig` | 472-491 | Writes must not add a BOM |
| 18 | a module-level POSIX import | 492-512 | `fcntl`, `pwd`, `grp`, `termios`, `resource`, `pty`, `tty` |

**How it works:**

- The suppression marker is `# windows-footgun: ok`. The regex needs no reason text (47). The docstring example adds one (31).
- Guard hints such as `is_windows` and `shutil.which(` exempt a line (56-70). The match covers the whole line, comments included (805).
- It scans only `.py`, `.pyw` and `.pyi` files (531). An extensionless Python script escapes it.
- `--all` scans 8 roots: `hermes_cli`, `gateway`, `tools`, `cron`, `agent`, `plugins`, `scripts` and `acp_adapter` (907-919). `pm/`, `hermes_platform/` and root modules such as `hermes_bootstrap.py` are outside it.
- The other modes are staged files, explicit paths and `--diff REF` (10-19, 855-880). Exit codes are at 949-966.
- The fix text of rule 14 asks for `encoding` and `errors='replace'` (380-386). Its filter checks `encoding` only.

**A live false negative.** `scripts/check_no_tmp_literals.py:172-175` has a
multi-line `text=True` call without `encoding`. Rule 14 misses it, because the
call spans lines. A line regex cannot see such calls; an `ast` walk can.

## 5. Other Windows lint gates in Hermes CI

- **Ruff PLW1514** (unspecified encoding) blocks CI. It is a preview rule, so `pyproject.toml:717-771` sets `preview = true`.
  - The selection is `PLW1514`, `ASYNC210`, `ASYNC220`, `ASYNC221`, `ASYNC251` and `TID251`.
  - Tests, skills, optional skills and plugins are exempt from PLW1514.
  - The `ruff-blocking` job runs `ruff check .` (`lint.yml:140-178`).
- **The `windows-footguns` job** runs on Ubuntu (`lint.yml:216-316`). Its steps:
  1. the footgun checker with `--all` (237);
  2. `scripts/check_bash_shebangs.py` (239-240);
  3. `scripts/check_no_tmp_literals.py` (247-248);
  4. a check of config writers (252-253);
  5. `check_os_marker_fakes` (258-259) and `check_agents_md_size` (263-264);
  6. two advisory steps and a clean-worktree check.
- **`check_bash_shebangs.py`** rejects `#!/bin/bash` and `#!/usr/bin/bash` (15). It exists for Nix, not for Windows (1-6).
- **`check_no_tmp_literals.py`** finds the token `/tmp` in code:
  - The regex skips `/tmp` inside longer paths and after `:-` (87).
  - It skips comments and docstrings through `tokenize` and `ast` (99-129).
  - The marker is `no-tmp: ok` (58). The baseline holds 1 entry (222-225).
  - The replacement is `hermes_constants.get_scratch_dir()`, under `HERMES_HOME/cache/scratch` (`hermes_constants.py:945-968`). `hermes_bootstrap.py:456-468` exports it as `TMPDIR`, `TMP` and `TEMP`.

## 6. Encoding policy

Hermes uses UTF-8 everywhere. It enforces this in four layers.

**1. Process start.** `hermes_bootstrap.py` applies three fixes at import (475-478):

- `apply_windows_utf8_bootstrap` sets `PYTHONUTF8=1` and `PYTHONIOENCODING=utf-8` with `setdefault`. It reconfigures the standard streams to UTF-8 with `errors='replace'` (227-253).
- `enable_windows_vt` turns on VT escape codes in the console (259-294).
- `suppress_platform_ver_console` handles the console call that `platform` makes for `ver` (297-321).

**2. CLI start.** `configure_windows_stdio` (`hermes_cli/stdio.py:47-82`) runs
from `cli.py:1727`, `hermes_cli/main.py:3495` and `gateway/run.py:5135`. Its
steps, in order:

1. Stop if `HERMES_DISABLE_WINDOWS_UTF8` is set (58).
2. `setdefault` the same two variables (64-65).
3. Set `EDITOR=notepad` only when `EDITOR` and `VISUAL` are both unset (70-72, 85-90).
4. Put Git `cmd`, `bin` and `usr\bin`, the venv `Scripts` and `WinGet\Links` in front of `PATH` (93-120).
5. Set the console code page to 65001 (23-33, 76).
6. Reconfigure the streams (79-80).

**3. Files.** Reads use `utf-8-sig`, and writes use `utf-8` without a BOM
(rules 15-17 in §4).

**4. Child processes.** Calls use `encoding='utf-8'` and `errors='replace'`
(rule 14; `local.py:1099-1125`). `hermes_subprocess_env` sets `PYTHONUTF8` for
child Python (`local.py:358`). The installer starts Python with `-I -B -X utf8`
(`install.ps1:1310`) or `-I -X utf8` (1331).

**PowerShell side:**

- `install.ps1` writes files with `UTF8Encoding($false)`, so without a BOM (710, 796).
- One exception: `Set-Content -Encoding UTF8` at 1500 writes a BOM under PowerShell 5.1. Rule 16 exists because of a BOM'd `install-stamp.json` like this (`check-windows-footguns.py:448-450`).
- `install.ps1` itself has no BOM. Non-ASCII appears only in 5 comment lines (389, 519, 544, 1253, 1647). The printed status glyphs are ASCII (615-620).
- `setup-hermes.ps1:89-98` decodes `uv` output as UTF-8 and then restores the console encoding. `activate.ps1:7-8` sets the session encodings to UTF-8.

## 7. Line endings

- `.gitattributes` has 37 lines. It sets `eol=lf` for `*.sh`, `*.py`, the JS and TS family, `*.json`, `*.yaml`, `*.yml`, `*.toml`, `*.md`, `*.css`, `*.html`, `*.svg`, `Dockerfile` and `uv.lock`.
- `*.ps1` gets `eol=crlf` for Windows PowerShell 5.1 (18-19, 37). The index keeps LF, and the checkout gets CRLF (`git ls-files --eol` shows `i/lf w/crlf`).
- There is no catch-all rule. The extensionless `activate` script has no attribute (`git ls-files --eol` shows an empty `attr/`). A Windows checkout with `core.autocrlf=true` gives it CRLF [EXT].

## 8. Symlinks

Hermes avoids symlinks on Windows. Each feature has its own substitute:

| Feature | Windows behaviour | Source |
|---|---|---|
| Command launchers | distlib `.exe` or `.cmd` launchers; sealed symlink launchers are POSIX only | `hermes_cli/_launchers.py:7, 154-305, 1000-1022` |
| Profiles | NTFS junctions through `_winapi.CreateJunction` | `hermes_cli/profiles.py:1223, 1240, 1261` |
| Worktrees | a `copytree` fallback | `hermes_cli/worktree_ops.py:359-375` |
| Package store | writes the link target as text | `pm/store.py:256-270` |
| Tests | `require_symlinks` probes once and skips | `tests/conftest.py:1228-1232, 1258, 1293-1300` |

Junctions need no privilege, but they link folders only [EXT]. On CPython
3.13+, `mkdir(0o700)` sets a protected DACL. The ACL grants of Hermes refuse to
follow reparse points (`hermes_dir_acl.py:1-26`).

## 9. Long paths and 8.3 names

- `pm/filesystem.py:37-65` builds `\\?\` verbatim roots and a `native()` helper. File locks use `msvcrt.locking` (68-79).
- A live Windows test covers long store paths (`tests/pm/test_long_paths_windows_live.py:1-17`).
- One CI lane sets `LongPathsEnabled` to 0 on purpose (`windows-venv-e2e.yml:88-109`).
- The installer sets `core.longpaths` for Git (`install.ps1:999-1000, 1170-1173`).
- The install-update e2e keeps fake profiles under a short root, because some paths reach 159 characters (`windows-install-update-e2e.yml:80-85`). It avoids long paths; it does not test them.
- GitHub runners report `TEMP` as the 8.3 alias `C:\Users\RUNNER~1\...` (`scripts/tests/test-install-ps1-longpath.ps1:23-27`).
- The installer expands 8.3 names in `TEMP`, `TMP`, `LOCALAPPDATA`, `APPDATA` and `USERPROFILE` with three resolvers (`install.ps1:114-305`, the list at 294).

## 10. Process cleanup

Windows does not re-parent orphans, so Hermes kills whole trees and checks for
leftovers.

- **Tree kill with an identity check.** `terminate_pid` needs a matching process start time before a forced kill. It then runs `taskkill /PID <pid> /T /F`, hidden, with a 10 s timeout (`gateway/status.py:402-441`). The terminal backend calls it (`local.py:996-1004`).
- **Liveness.** `_pid_exists` uses `psutil` (`gateway/status.py:942-972`). Rule 3 bans `os.kill(pid, 0)`.
- **Deadlines.** `agent/deadline.py:422-446` runs `taskkill /F /T` with a 15 s timeout.
- **Hook and probe children** (`hermes_cli/_subprocess_compat.py`):
  - `kill_process_tree` starts at 738 and cites openai/codex#36793 and #37527 (753-754). The legacy `taskkill` call is at 790.
  - `bounded_probe_run` uses a Job Object (798-833). `taskkill /T` misses MSYS grandchildren whose parent already exited (822-825, #73403).
  - The same code records an unbounded `communicate()` hang (#87134).
- **Servers.** `spawn_server` starts the child suspended, assigns it to a Job with `KILL_ON_JOB_CLOSE`, then resumes it (`hermes_cli/local_runtime/processes.py:68, 110-126`).
- **Creation flags** (`_subprocess_compat.py:159-213`). `windows_detach_flags` is `CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW | CREATE_BREAKAWAY_FROM_JOB` (203). `DETACHED_PROCESS` is left out on purpose (162-170).
- **Relaunch.** On Windows the bootstrap relaunches with `subprocess.call`, not `os.execv` (`hermes_bootstrap.py:595-599`).
- **Gateway.** It runs the console `python.exe` with a hidden window, not `pythonw.exe` (`hermes_cli/gateway_windows.py:241-246, 670-690`). `_spawn_detached` leaves out `DETACHED_PROCESS` (760-771).
- [DOCS] `windows-native.md:227-229` still describes `pythonw` with `DETACHED_PROCESS`. The source contradicts it.
- **CI leftovers.** A leftover `python`, `pythonw` or `hermes` process fails the job (`tests-os.yml:277-295`). The comment at 280 says "Windows never re-parents". The install-update e2e also checks `node.exe` (`windows-install-update-e2e.yml:120-141`).

## 11. Dangerous Windows commands (input for H3)

`tools/approval_detection.py:242-286` holds a Windows tier. It flags:

- `cmd /c` with `del` or `rd` (244);
- destructive PowerShell verbs through `powershell` or `pwsh` (247), and `-EncodedCommand` (248);
- a bare `Remove-Item` with `-Recurse` or `-Force` (255);
- `del` or `rd` with `/s` or `/q` (257);
- download-and-run with `iwr | iex` (259-260);
- `taskkill /f` and `Stop-Process -Force`;
- `Format-Volume`, `Clear-Disk`, `diskpart`, `format x:` and `cipher /w`;
- `icacls` with `/grant Everyone` or `/reset`;
- `vssadmin`, `wbadmin` and `bcdedit`;
- `reg delete` and `Remove-ItemProperty`;
- `sc stop` and `sc delete`;
- paths of Windows credential stores (284-285).

Normalization treats backslashes as shell escapes, so `C:\Users\me` loses its
separators. For drive-letter and UNC paths, Hermes also checks a copy with
`\` turned into `/` (1447-1453, #69472).
`tests/tools/test_approval_windows.py:23-110` holds fixtures that must match
and fixtures that must not.

## 12. Tests and CI on Windows

**Test rules:**

- `tests/conftest.py` defines the `platforms` marker (1211-1221) and gates tests by host (1302-1322).
- `pytest-timeout` uses the thread method on Windows (1246-1252).
- Tests must not write the User `PATH` (1489-1503).
- The `real_bash` fixture avoids the WSL `bash.exe` stub (1521-1533).
- Tests must not fake the host OS (`tests/_fixtures/platform_gating.py:7-45`, `tests/AGENTS.md:62-104`). CI checks this with `check_os_marker_fakes` (§5).
- `tests/scripts/test_powershell_script_syntax.py` checks the syntax of the `.ps1` scripts (1-13, 59-63).

**`scripts/run_tests.sh`:**

- It runs tests under `env -i` and forwards the Windows location variables, `PATHEXT` included (86-102, issues #67385 and #70813).
- It reads `ProgramFiles(x86)` through `sed`, because bash cannot name that variable (118-122).
- It sets UTC, `C.UTF-8` and `PYTHONUTF8` (195-199).

**Workflows:**

- `tests-os.yml`:
  - The lanes are Windows Server 2025 plus 2 arm64 slices (95-107).
  - Steps use `shell: bash` (152, 264) and call `python`, not `python3` (160, 193).
  - An empty test selection fails the job (165-168). The selection is `-m "platforms and not integration"` (195-198).
  - The `e2e-windows` job runs with zero retries (229-275).
  - The job ends with the leftover check (277-295) and a clean-worktree check.
- `windows-venv-e2e.yml` runs on push to `wine2e/**` and as a reusable workflow (15-29). It is not on demand only.
- `windows-install-update-e2e.yml` checks a crash manifest (97-109) and leftover processes (120-141).
- `case-collision-check.yml` rejects paths that differ only by letter case (3-17).

## 13. The installer and the PowerShell scripts

`scripts/install.ps1` (read in full):

- It pins `uv` 0.12.3 and PortableGit 2.53.0+3, each with a SHA-256 and a mirror (82-112).
- `Get-Uv` never takes `uv` from `PATH` (521-522).
- `Get-PinnedGit` waits up to 600 s, then kills the tree with `taskkill /T /F` (584-588).
- The installer always uses the pinned Git (`Ensure-Git`, 604-613 and 836-841). [DOCS] `windows-native.md:96` says otherwise.
- All native commands go through one wrapper, `Invoke-Native` (632-655).
- `Set-LauncherUserPath` edits the User `PATH` (1364-1380).
- Under `irm | iex`, `exit` would close the caller's window, so the script avoids it (67-73, 1661-1666). A dot-source guard sits at 58-66 and 1583-1588.
- `UV_NO_CONFIG` keeps user `uv` config out (1596).
- §6 covers its encoding, and §9 covers its long-path and 8.3 handling.

## 14. For this harness

### 14.1 How our clients start hooks on Windows

**Claude Code 2.1.302 [BIN]:**

- It looks for Git Bash in this order:
  1. `CLAUDE_CODE_GIT_BASH_PATH`. The file must exist, and its name must be `bash.exe`, `sh.exe`, `bash` or `sh`.
  2. `C:\Program Files\Git\bin\bash.exe`.
  3. `C:\Program Files (x86)\Git\bin\bash.exe`.
  4. `bin\bash.exe` two folders above the `git` on `PATH`.
- Without Git Bash, the Bash tool is unavailable.
- A command hook runs as a non-login `bash -c` under Git Bash. The bash folder goes first on `PATH`. The window is hidden, and the process is not detached.
- A first token that ends in `.sh` gets `bash ` in front. Path variables use forward slashes. Hook stdin and stdout are UTF-8.
- A hook can set `"shell": "powershell"` or use the exec form (`command` plus `args`, no shell).
- Without Git Bash, a bash hook fails with an error that suggests `"shell": "powershell"`.
- The PowerShell tool is named `PowerShell`. On Windows, `CLAUDE_CODE_USE_POWERSHELL_TOOL` decides when it is set.
- When the variable is unset, the tool is on if Git Bash is missing. Otherwise a feature flag decides, and its default is off.
- The binary also states that a deny of Bash turns off the PowerShell tool.

Result: the five hook commands in `claude/settings.json:142-174` work as
written when Git Bash is found. They are `$HOME/.claude/hooks/*.sh` paths. The
statusline commands (184-189) were not checked.

**Codex 0.158.0 [BIN].** The strings show `hooks.windows_managed_dir` and the
hook event names. They do not show which shell runs a hook `command` on
Windows. This stays unverified.

**Our Codex hook on Windows.** `codex/hooks.json:5, 9, 13` run
`python3 "$HOME/.codex/hooks/policy.py"`. Four things can break:

1. `python3` can be missing, or the Store alias [EXT].
2. `$HOME` expands in bash and PowerShell, but not in `cmd.exe` [EXT].
3. `policy.py:36` starts a bare `bash`. `CreateProcess` searches `System32` before `PATH` [EXT], so it can start the WSL `bash.exe`. Hermes guards against this stub (`pm/shell.py:62-65`, `tests/conftest.py:1521-1533`).
4. Without UTF-8 mode, `json.load(sys.stdin)` decodes with the ANSI code page [EXT].

`policy.py` fails closed. Any `OSError`, `ValueError` or `SubprocessError`
becomes a deny (`policy.py:239-254`). So these faults block work; they do not
open a bypass.

### 14.2 Scan of our repo (reproducible)

Scope: tracked files in `dotfiles/` at HEAD `504215e`. That is 31 `*.py`
files, 1 extensionless Python file (`codex/bin/codex-worktree`) and 25 `*.sh`
files. The repo has no `.ps1` files and no binary files. The other
extensionless files are 3 `LICENSE` files. The script only reads, and it runs
from any folder.

```bash
#!/usr/bin/env bash
# Windows-readiness scan of the harness. Read-only: git grep on a commit.
set -u
cd /var/www/html/personal/setup_scripts || exit 1
REV=HEAD                                               # 504215e for the numbers below
PY=('dotfiles/*.py' dotfiles/codex/bin/codex-worktree) # 31 *.py files + 1 extensionless Python file
SH=('dotfiles/*.sh')                                   # 25 files
NC='^(?!\s*#)'                                         # skip whole-line comments
TESTS='(^|/)tests/|/test_[^/]*$'                       # test files; the rest is product code
hits()    { git grep -n -P "$1" "$REV" -- "${@:2}"; }  # prints REV:path:line:text
count()   { echo "$(hits "$@" | wc -l) lines, $(hits "$@" | cut -d: -f2 | sort -u | wc -l) files," \
                 "$(hits "$@" | cut -d: -f2 | grep -c -v -E "$TESTS") in product code"; }

E1="$NC(?!.*encoding).*\.(read|write)_text\s*\("                     # read_text/write_text, no encoding=
E2="$NC(?!.*encoding).*\b(text|universal_newlines)\s*=\s*True"      # subprocess text mode, no encoding=
E3="$NC(?!.*encoding)(?!.*[\"'][rwax+]*b[rwax+]*[\"']).*(?<![\w])(?<!os\.)open\s*\("  # open()/Path.open, text mode
E4="$NC(?!.*encoding)(?!.*[\"'][rwax+]*b[rwax+]*[\"']).*\bfdopen\s*\(" # os.fdopen, text mode
P1='^(import|from)\s+(fcntl|pwd|grp|termios|resource|pty|tty)\b'    # Hermes rule 18 module list
P2='\bos\.(setsid|killpg|fork|getuid|geteuid|getgid|getegid|O_NOFOLLOW)\b|\bos\.kill\s*\([^,]+,\s*0\s*\)|\bsignal\.SIG(KILL|HUP|USR1|USR2|ALRM|CHLD|PIPE|QUIT)\b|\bfcntl\.'
T1="$NC.*(?<![\w./~\\\\-])(?<!:-)/tmp(?![\w-])"                     # /tmp token (check_no_tmp_literals.py:87)
L1="$NC.*\bln\s+-[A-Za-z]*s\b"                                       # ln -s
L2='\.symlink_to\(|os\.symlink\('                                    # Python symlink creation
B1="$NC.*\bjq\b"                                                     # jq: Git for Windows has none
B2="$NC.*\bpython3\b"                                                # python3: name risk on Windows
B3="$NC(?:.*[;&|({]|.*\\\$\()?\s*(?:if\s+!?\s*)?(find|timeout)\s"   # find/timeout at command position
B4='\[\s*["'"'"']bash["'"'"']'                                       # bare "bash" spawned from Python
B5='\bps\s+-o'                                                       # procps-only ps option

for v in E1 E2 E3 E4 P1 P2 T1 L2 B4; do printf '%-3s py  %s\n' "$v" "$(count "${!v}" "${PY[@]}")"; done
for v in T1 L1 B1 B2 B3 B5;          do printf '%-3s sh  %s\n' "$v" "$(count "${!v}" "${SH[@]}")"; done
echo "python3 in hook configs: $(hits python3 dotfiles/codex/hooks.json dotfiles/claude/settings.json | wc -l)"
echo ".gitattributes files: $(git ls-files ':(glob)**/.gitattributes' | wc -l)"
echo "line endings in the index:"; git ls-files --eol -- dotfiles | awk '{print $1}' | sort | uniq -c
paths() { git ls-tree -r --name-only "$REV" -- dotfiles; }
echo "case collisions:"; paths | awk -F/ '{p=$1; print p; for (i=2; i<=NF; i++) {p=p "/" $i; print p}}' |
  sort -u | tr 'A-Z' 'a-z' | sort | uniq -d
echo "reserved names:"; paths | grep -i -E '(^|/)(con|prn|aux|nul|com[1-9]|lpt[1-9])(\.[^/]*)?(/|$)'
echo "bad characters, trailing dot or space:"; paths | grep -E '[<>:"|?*\\]|[. ](/|$)'
echo "longest path:"; paths | awk '{print length, $0}' | sort -rn | head -1
echo "top 10 files by rule hits:"
{ for v in E1 E2 E3 E4 P1 P2 T1 L2 B4; do hits "${!v}" "${PY[@]}"; done
  for v in T1 L1 B1 B2 B3 B5;          do hits "${!v}" "${SH[@]}"; done; } |
  cut -d: -f2 | sort | uniq -c | sort -k1,1nr -k2,2 | head -10
```

Ruff comparison (ruff 0.14.10). Ruff reads the working tree. One tracked file
has local changes (`tools/agent_sessions_mcp.py`), and ruff reports nothing in it.

```bash
cd /var/www/html/personal/setup_scripts
git ls-files -z 'dotfiles/*.py' | xargs -0 ruff check --preview --select PLW1514 --no-cache --output-format concise --exit-zero
```

Result: 3 findings (`spec-eval/run.py:377, 487`, `test-codex-worktree.py:123`).
So ruff finds 3 of the 157 encoding lines below, because it needs a known
`Path` type.

**Results.** "Product" means outside `tests/` folders and `test_*` files.

| Id | Check | Lines | Files | Product | Sites |
|---|---|---|---|---|---|
| E1 | `read_text`/`write_text` without `encoding` | 129 | 19 | 33 | product: `spec-eval/run.py` 15, `workflow/run.py` 6, `install-config.py` 3, 5 more files |
| E2 | `text=True` without `encoding` | 24 | 13 | 14 | `workflow/run.py` 4, `spec-eval/run.py` 4, `policy.py:37`, `codex-worktree:117` |
| E3 | `open()` or `Path.open` in text mode | 3 | 3 | 2 | `workflow/run.py:623` (two calls), `codex-worktree:180`; the test hit sits in a generated script |
| E4 | `os.fdopen` in text mode | 1 | 1 | 1 | `codex-worktree:164` |
| P1 | POSIX-only import | 1 | 1 | 1 | `codex-worktree:8` (`import fcntl`) |
| P2 | POSIX-only API | 2 | 1 | 2 | `codex-worktree:163` (`O_NOFOLLOW`), `:166` (`fcntl.flock`) |
| T1 | `/tmp` in Python | 2 | 2 | 1 | `policy.py:138` (run time); `test-codex-worktree.py:150` |
| T1 | `/tmp` in shell | 6 | 2 | 0 | `test-hooks.sh:81, 87, 90, 91, 113`; `test-handoff-hook.sh:34` |
| L1 | `ln -s` | 16 | 4 | 4 | `link_dotfiles.sh:105-107, 147`; 12 test lines |
| L2 | Python symlink creation | 9 | 5 | 4 | `install-skills.py:69`; `spec-eval/run.py:109, 113, 146` |
| B1 | `jq` | 117 | 17 | 52 | 8 hooks, 2 statuslines, `run-metrics.sh` |
| B2 | `python3` in shell | 13 | 5 | 9 | `link_dotfiles.sh` 5, `require-worktree-for-writers.sh` 3, `batch-spec.sh:212` |
| — | `python3` in hook configs | 3 | 1 | 3 | `codex/hooks.json:5, 9, 13` |
| B3 | `find` or `timeout` as a command | 7 | 4 | 4 | `warn-stale-base.sh:111, 113`, `worktree-readiness.sh:34`, `link_dotfiles.sh:202` |
| B4 | bare `"bash"` spawn | 4 | 3 | 2 | `policy.py:36`, `codex-worktree:115`; `test-codex-harness.py:207, 234` |
| B5 | `ps -o` | 1 | 1 | 0 | `test-batch-spec.sh:208` |
| — | `.gitattributes` files | 0 | | | none |
| — | line endings in the index | 321 `i/lf` | | | no CRLF |
| — | case collisions, reserved names, bad characters | 0 | | | none |
| — | longest tracked path | 99 characters | | | `docs/adr/0017-…` |

Other Linux-only commands give no hits in the shell files. This command
prints 0:

```bash
cd /var/www/html/personal/setup_scripts
git grep -n -P '^(?!\s*#).*(\benv\s+-i\b|/proc/|\bflock\b|\bsetsid\b|\btmux\b|\bpgrep\b|\bpkill\b|\blsof\b|\bsudo\b|\bkill\s+-0\b|\breadlink\s+-f\b|\brealpath\b|\bsed\s+-i\b|\bstat\s+-|\bdate\s+-d\b|\bsystemctl\b|\bcrontab\b|\bOSTYPE\b|\bstty\b|\btput\b)' HEAD -- 'dotfiles/*.sh' | wc -l
```

**Line regexes are approximate.** A stdlib `ast` cross-check in the session
scratchpad counted 130 `read_text`/`write_text` calls without `encoding`. It
differs by one call in three test files. That script is not part of this file.

### 14.3 Hotspots

Top 10 files by rule hits, from the last command of the script. A line can hit
two rules.

| File | Hits | Rules | Kind |
|---|---|---|---|
| `tools/tests/test-worktree-hooks.sh` | 37 | jq 32, `ln -s` 4, `python3` 1 | test |
| `tools/tests/test-codex-worktree.py` | 33 | encoding 30, links 2, `/tmp` 1 | test |
| `tools/evals/spec-eval/test_produce.py` | 25 | encoding 25 | test |
| `tools/evals/spec-eval/run.py` | 22 | encoding 19, links 3 | product |
| `tools/evals/plan-recall/test_recall.py` | 15 | encoding 15 | test |
| `tools/tests/check-references-test.py` | 15 | encoding 15 | test |
| `tools/tests/test-codex-harness.py` | 15 | encoding 12, bare `bash` 2, links 1 | test |
| `tools/tests/test-hooks.sh` | 15 | jq 9, `/tmp` 5, `ln -s` 1 | test |
| `tools/evals/workflow/run.py` | 11 | encoding 11 | product |
| `tools/run/run-metrics.sh` | 10 | jq 10 | product |

Three more files tie at 10 hits: `tools/setup/link_dotfiles.sh` (links 4,
`python3` and `find` 6), `tools/tests/test-handoff-hook.sh` and
`tools/tests/test-run-metrics.sh`. `codex/bin/codex-worktree` has 7 hits, and
it cannot import on Windows.

### 14.4 What the numbers mean

- **Encoding.** E1-E4 give 157 lines, and 50 of them are in product code. Without UTF-8 mode, Python 3.14 and older use the ANSI code page for these calls [EXT].
- Our Markdown holds non-ASCII characters such as em dashes, so those reads and writes can fail. PEP 686 makes UTF-8 mode the default in Python 3.15 [EXT].
- **`codex-worktree`** cannot start on Windows. It imports `fcntl` at module level (P1).
- **`/tmp`.** Only `policy.py:138` matters at run time. Native Python reads `/tmp` as `\tmp` on the current drive; Git Bash maps it to the user temp folder [EXT]. Use `tempfile.gettempdir()`.
- **Links.** The linker makes 19 links: 9 folders and 10 files. It also runs `install-skills.py`, which creates links in Python (`link_dotfiles.sh:167, 269`; `install-skills.py:69`).
- Without Developer Mode, symlink creation fails on Windows [EXT].
- **jq.** 52 product lines in 11 files need `jq`. Git for Windows ships none (ADR 0087). H1 removes the need.
- **`find` and `timeout`.** `System32` holds `find.exe` and `timeout.exe` [EXT]. They win when `System32` comes before `/usr/bin` on `PATH` (`local.py:561-581`). The order inside a Claude Code hook is unverified.
- **`ps -o`.** The Git Bash `ps` has no `-o` option [EXT]. Only one test uses it.
- **Long paths and names.** No action. The longest tracked path has 99 characters. A checkout root of up to 150 characters keeps all paths below 260.

### 14.5 Porting checklist (W1), re-judged

| Old step | Verdict | Reason |
|---|---|---|
| 1. Line endings | Changed | Add a catch-all. `codex-worktree` has no suffix, and the `activate` file of Hermes shows that gap. |
| 2. Encoding lint and fixes | Changed | Lint product code only, with `ast`. Line regexes miss multi-line calls; ruff finds 3 of 157 lines. |
| 3. UTF-8 for hooks | Changed | The places are now known: `env` in `claude/settings.json` and `-X utf8` in `codex/hooks.json`. |
| 4. `jq` until H1 | Kept | 52 product lines. The `winget` id is unverified. |
| 5. How clients start hooks | Resolved for Claude Code | Git Bash runs our hooks as written. Codex stays unverified. |
| 6. PowerShell tool | Changed | The tool name is confirmed. Turn the tool off and port the tested Hermes patterns (§14.6). |
| 7. Linker | Changed | Also cover `install-skills.py`. Hermes has link handling (§8), but its copies do not fit us. |
| 8. Windows CI | Changed | Add the `python` name, an explicit bash, the 8.3 `TEMP` alias and a symlink probe. |
| 9. Leftover processes | Kept, deferred | Add a decision on `codex-worktree`. |
| 10. Installer | Kept, deferred | §13 records the facts for later. |
| — | New | Resolve Git Bash explicitly in Python (B4). |
| — | New | Probe `find`, `timeout` and `python3` on the host (B2, B3). |

**The new checklist.** Each step lists its check. Native Windows stays the
user's decision; this list only orders the work for it.

1. **Line endings.** Add a root `.gitattributes` with `* text=auto eol=lf`.
   - It covers the `*.sh` and `*.py` lines of the plan and the extensionless `codex-worktree`.
   - Add `*.ps1 text eol=crlf` only when a `.ps1` file arrives.
   - Why: Git for Windows usually sets `core.autocrlf=true` [EXT]. Without attributes, bash then fails on `\r`.
   - Check: `git add --renormalize .` changes nothing, and `git ls-files --eol` shows `eol=lf` on every text file.
2. **Explicit Git Bash in Python.** Replace the bare `bash` in `policy.py:36` and `codex-worktree:115` with one resolver:
   1. `CLAUDE_CODE_GIT_BASH_PATH`, when it is set;
   2. `%ProgramFiles%\Git\bin\bash.exe`, then the `(x86)` path;
   3. never a path under `System32` or `WindowsApps`.
   - Keep plain `bash` on POSIX. Fail closed when no candidate exists; `policy.py` already turns errors into a deny.
   - Check: a test in `test-codex-harness.py` pins the order, like `tests/pm/test_shell_candidates.py`.
3. **One Python name.** Probe `python3` in Git Bash on the host first. If it fails, use one resolver for the linker, the hooks and `codex/hooks.json`.
   - Check: `python3 -c "import sys; print(sys.executable)"` prints a real interpreter.
4. **UTF-8 mode at every entry point.**
   - Claude Code: add `PYTHONUTF8=1` to the `env` block of `claude/settings.json` (line 3).
   - Codex: add `-X utf8` to the three `python3` commands in `codex/hooks.json`.
   - README prerequisite: a User variable `PYTHONUTF8=1` for scripts that you run by hand.
   - Hermes sets UTF-8 mode at its entry points in the same way (§6).
   - Check: a hook fixture with a non-ASCII command passes in the Windows CI job.
5. **Explicit encodings in product code, then a lint.**
   - Fix the 50 product lines (E1-E4). Read with `utf-8-sig` where a Windows tool can write the file. Write with `utf-8`. Give child output `encoding='utf-8', errors='replace'`.
   - Run test code with `PYTHONUTF8=1` instead, as Hermes does (`run_tests.sh:195-199`). Hermes also exempts tests from PLW1514.
   - Add a stdlib `ast` lint for E1-E4 and `/tmp` to `ci.yml`. Require a reason on each suppression marker; Hermes does not (47).
   - Do not copy the whole-line guard hints of Hermes (56-70, 805).
   - Phase the lint inside W1. It is a CI check, not a pipeline gate.
   - Check: the lint passes on product code and fails on a planted fixture.
6. **`jq` until H1.** Keep this step. Add `jq` to the README prerequisites. ADR 0087 already fails closed without `jq`. The id `jqlang.jq` is unverified.
7. **H3.** See §14.6.
8. **Links: probe, then stop.**
   - Probe once with `ln -s` in `link_dotfiles.sh`, before the first link and before `install-skills.py` runs.
   - On failure, stop and print the fix: Developer Mode plus `MSYS=winsymlinks:nativestrict`.
   - Use no copies and no junctions. Copies go stale without warning. Junctions link folders only, and 10 of our 19 links are files.
   - Hermes copies worktrees on Windows (`worktree_ops.py:359-375`). We refuse, because our links are live config.
   - Check on the host: a second linker run reports no change. This proves the `readlink` compare.
9. **`find` and `timeout`.** Probe `command -v find timeout` inside a hook on the host.
   - If either resolves to `System32`, call `/usr/bin/find` and `/usr/bin/timeout`. Or put `/usr/bin` first in the hook prelude, as Hermes does (`local.py:561-603`).
   - Sites: `warn-stale-base.sh:111, 113`, `worktree-readiness.sh:34`, `link_dotfiles.sh:202`.
10. **Windows CI.** Add a `windows-latest` job to `.github/workflows/ci.yml` with `shell: bash`:
    - Call `python`, or prove that `python3` works. Hermes calls `python` (`tests-os.yml:160, 193`).
    - Fail on an empty test selection (`tests-os.yml:165-168`).
    - Set `PYTHONUTF8=1` for test code.
    - Expect the 8.3 `TEMP` alias `RUNNER~1` in path compares.
    - Probe symlinks first, and fail with a clear message.
    - End with a clean-worktree check.
    - The `python3`, `jq` and symlink rights of the runner are unverified.

**Deferred, with the facts:**

- **Leftover processes.** The harness starts no background process on Windows. `agent_deck.py` needs tmux, so it stays on Linux or WSL2.
- **`codex-worktree`.** Decide whether to port it or keep it on Linux and WSL2. A port needs:
  - `msvcrt.locking` instead of `fcntl.flock`, as in `pm/filesystem.py:68-79`;
  - a guard for `O_NOFOLLOW`;
  - a `.cmd` or `.py` launcher, because Windows cannot start an extensionless script [EXT].
  - On CPython 3.13+, its `mkdir(mode=0o700)` sets a protected DACL (`hermes_dir_acl.py:1-26`).
- **Watch item.** `policy.py:36-38` sets a 15 s timeout, but `subprocess.run` kills only the direct child [EXT]. A bash grandchild can keep the pipe open and stall the hook. Hermes records the same problem (#73403, #87134).
- **Installer.** We do not need one while `link_dotfiles.sh` runs under Git Bash. If we need one, reuse §13:
  - one wrapper for native commands;
  - UTF-8 without BOM, so no PowerShell 5.1 `Set-Content -Encoding UTF8`;
  - no `exit` under `iex`;
  - `core.longpaths`.

### 14.6 H3: PowerShell coverage

**Facts [BIN].** The tool name is `PowerShell`. Assume that Git Bash is missing
and that `CLAUDE_CODE_USE_POWERSHELL_TOOL` is unset. Then the Bash tool goes
away and the PowerShell tool turns on. Our guards match only `Bash`
(`claude/settings.json:142`), so every PowerShell call would run unguarded.

With Git Bash present, the agent can still run `powershell -Command ...` or
`cmd /c ...` through the Bash tool. Our bash guard does not know Windows verbs.

**Recommendation:**

1. Set `CLAUDE_CODE_USE_POWERSHELL_TOOL=0` in the `env` block of `claude/settings.json`.
   - This is config, not a new gate.
   - Without Git Bash, Claude Code then has no shell tool, so it fails closed.
   - Check on the host: the tool list shows no `PowerShell`.
2. Add a narrow Windows tier to `claude/hooks/block-destructive-bash.sh` for `powershell`, `pwsh` and `cmd /c` children.
   - Port the patterns from `tools/approval_detection.py:242-286` and the path variant at 1447-1453.
   - Port both fixture sets from `tests/tools/test_approval_windows.py:23-110` into `test-hooks.sh`.
   - This changes an existing gate. Phase it inside W1 and record it in the W1 ADR.
3. Codex: unverified. The binary does not show its Windows hook shell.

The old file said to write our own patterns. Hermes now has tested patterns,
so port them. A `PowerShell` matcher would need PowerShell parsing in bash, so
turn the tool off instead.

### 14.7 Verify on a Windows host

- The shell that Codex uses for hook commands.
- `python3` in Git Bash: a real interpreter or the Store alias.
- The default of MSYS `ln -s` without `MSYS=winsymlinks:nativestrict`.
- The `find` and `timeout` that a Claude Code hook resolves.
- Whether a bash hook that fails for lack of Git Bash blocks the tool call.
- Whether the `env` block of `claude/settings.json` reaches hook processes.
- How Claude Code runs the statusline commands.
- The `winget` id for `jq`.
- The `python3`, `jq` and symlink rights of the GitHub `windows-latest` runner.
- The `readlink` compare in the linker with native links.

## Sources

Hermes commit `5fea5a7a4bf6d02b3427fc0bcae95502222cea2e` (2026-10-17). Paths
are relative to the Hermes repo root.

**Scripts and config:** `.gitattributes`, `pyproject.toml`,
`scripts/check-windows-footguns.py`, `scripts/check_no_tmp_literals.py`,
`scripts/check_bash_shebangs.py`, `scripts/run_tests.sh`,
`scripts/install.ps1`, `setup-hermes.ps1`, `activate.ps1`

**Core modules:** `hermes_bootstrap.py`, `hermes_constants.py`,
`hermes_dir_acl.py`, `hermes_cli/stdio.py`, `hermes_cli/_subprocess_compat.py`,
`hermes_cli/_launchers.py`, `hermes_cli/profiles.py`,
`hermes_cli/worktree_ops.py`, `hermes_cli/gateway_windows.py`,
`hermes_cli/local_runtime/processes.py`, `hermes_platform/AGENTS.md`,
`hermes_platform/resolver/core.py`, `pm/shell.py`, `pm/filesystem.py`,
`pm/store.py`, `agent/shell_hooks.py`, `agent/deadline.py`, `gateway/status.py`,
`tools/environments/local.py`, `tools/approval_detection.py`,
`tools/terminal_tool_guards.py`, `tools/code_execution_env.py`

**Tests:** `tests/conftest.py`, `tests/AGENTS.md`,
`tests/_fixtures/platform_gating.py`, `tests/pm/test_shell_candidates.py`,
`tests/pm/test_long_paths_windows_live.py`,
`tests/tools/test_approval_windows.py`,
`tests/e2e/core/windows/test_terminal_tool.py`,
`tests/scripts/test_powershell_script_syntax.py`,
`scripts/tests/test-install-ps1-longpath.ps1`

**Workflows** (`.github/workflows/`): `lint.yml`, `tests-os.yml`,
`windows-venv-e2e.yml`, `windows-install-update-e2e.yml`,
`case-collision-check.yml`, `install-e2e-windows-run.yml` (header only)

**Docs:** `website/docs/user-guide/windows-native.md`,
`skills/autonomous-ai-agents/hermes-agent/references/windows-quirks.md`

**Callers, cited for line numbers only:** `cli.py`, `hermes_cli/main.py`,
`gateway/run.py`

**Outside Hermes:** strings of the local Claude Code 2.1.302 and Codex 0.158.0
binaries, and our repo at HEAD `504215e`.
