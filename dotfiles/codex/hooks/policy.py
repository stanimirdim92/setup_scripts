#!/usr/bin/env python3
"""Adapt Codex hook payloads to shared policies; never execute tool input.

Hooks are accident guards on supported tool paths, not a shell sandbox.
Native role configs supply the trusted role argument; user tool input cannot
grant a role. See dotfiles/docs/adr/0059-codex-native-roles-and-hook-adapters.md.
"""

import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

SHARED = Path(__file__).resolve().parents[2] / "claude" / "hooks"
WRITERS = {"executor", "executor-high", "test-engineer"}
READERS = {"repo-recon", "code-reviewer", "blind-reviewer", "security-auditor",
           "distributed-systems-reviewer"}


def deny(reason):
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
            "permissionDecision": "deny", "permissionDecisionReason": reason}}


def shared(name, payload, *arguments):
    env = dict(os.environ)
    # A Claude remote-session flag must not exempt a Codex push from review.
    env.pop("CLAUDE_CODE_REMOTE", None)
    result = subprocess.run(["bash", str(SHARED / name), *arguments],
                            input=json.dumps(payload), text=True,
                            capture_output=True, timeout=15, env=env)
    if result.returncode:
        raise ValueError(f"Shared policy {name} failed; restore the hook before retrying.")
    output = json.loads(result.stdout) if result.stdout.strip() else {}
    if not isinstance(output, dict):
        raise ValueError(f"Shared policy {name} returned an invalid result.")
    return output


def shell_active(command):
    """True when the command holds a character the shell would act on.

    Substitution ($, `) is live outside single quotes; redirection and
    subshells (<, >, (, )) only outside any quotes. Quoted, they are literal
    search text: rg '->save(' or rg '\\$this' in a PHP codebase. Newlines and an
    unterminated quote are refused outright.
    """
    quote = None
    escaped = False
    for char in command:
        if char == "\n":
            return True
        if escaped:
            escaped = False
        elif quote == "'":
            if char == "'":
                quote = None
        elif char == "\\":
            escaped = True
        elif quote == '"':
            if char == '"':
                quote = None
            elif char in "$`":
                return True
        elif char in "'\"":
            quote = char
        elif char in "$`<>()":
            return True
    return quote is not None or escaped


def read_only_shell(command):
    # Keep read-only personas from running tests, project code, interpreters,
    # substitutions, output redirection, or executable git/search options.
    if shell_active(command):
        return False
    lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|")
    lexer.whitespace_split = True
    groups = [[]]
    for token in lexer:
        if token in {";", "&&", "||", "|"}:
            if not groups[-1]:
                return False
            groups.append([])
        elif token in {"&", ";;", "|&"}:
            return False
        else:
            groups[-1].append(token)
    safe = {"pwd", "ls", "cat", "head", "tail", "nl", "wc", "stat", "readlink", "realpath", "true"}
    for args in groups:
        if not args:
            return False
        program, *options = args
        if program in safe:
            continue
        if program == "rg" and not any(x.startswith(("--pre", "--hostname-bin")) for x in options):
            continue
        if program == "sed" and len(options) >= 2 and options[0] == "-n" and re.fullmatch(r"\d+(,\d+|,\$)?p", options[1]):
            # No additional sed scripts/options after the validated expression.
            if not any(x.startswith("-") for x in options[2:]):
                continue
        if program == "git":
            if any(x.startswith(("--output", "--ext-diff", "--textconv", "--exec-path")) for x in options):
                return False
            if "--no-pager" not in options:
                return False
            while options and options[0] in {"-C", "--no-pager", "--no-optional-locks"}:
                flag = options.pop(0)
                if flag == "-C":
                    if not options:
                        return False
                    options.pop(0)
            if options and options[0] in {"status", "diff", "show", "log", "rev-parse", "ls-files", "ls-tree", "show-ref", "check-ignore"}:
                # Disable external diff drivers, textconv, and pagers in calls
                # made by a read-only persona; see the role instructions.
                if options[0] in {"diff", "show", "log"}:
                    if not {"--no-ext-diff", "--no-textconv"}.issubset(options):
                        return False
                continue
        return False
    return True


MAX_HANDOFF_BLOCKS = 2  # the 2-3 automatic continuations the Opus 5.5 guide recommends


def handoff_counter(payload):
    key = payload.get("agent_id") or payload.get("session_id") or payload.get("turn_id") or "unknown"
    key = re.sub(r"[^A-Za-z0-9._-]", "_", str(key))
    base = os.environ.get("HARNESS_HANDOFF_STATE_DIR") or os.path.join(
        os.environ.get("TMPDIR", "/tmp"), "harness-handoff-hook")
    return Path(base) / key


def handoff(payload):
    # Same contract as hooks/require-handoff-report.sh: block at most twice per
    # agent run; a stop_hook_active stop with no counter is another hook's loop.
    counter = handoff_counter(payload)
    try:
        blocks = int(counter.read_text().strip())
    except (OSError, ValueError):
        blocks = 0
    if blocks >= MAX_HANDOFF_BLOCKS or (payload.get("stop_hook_active") is True and blocks == 0):
        counter.unlink(missing_ok=True)
        return {}
    result = handoff_check(payload.get("last_assistant_message"))
    if result:
        try:
            counter.parent.mkdir(parents=True, exist_ok=True)
            counter.write_text(str(blocks + 1))
        except OSError:
            pass
    else:
        counter.unlink(missing_ok=True)
    return result


def handoff_check(report):
    if not isinstance(report, str) or not report.strip():
        return {"decision": "block", "reason": "Provide verification commands/outcomes, commit identity or no-commit reason, and working-tree state."}
    missing = []
    if not (re.search(r"verif|check|test", report, re.I) and re.search(r"pass|fail|exit|outcome|succeed|error|\bok\b|green|red|blocked|not run", report, re.I)):
        missing.append("verification commands with outcomes")
    if not re.search("commit", report, re.I):
        missing.append("commit id or an explicit no-commit reason")
    if not re.search(r"working[- ]tree|tree state|uncommitted|untracked|clean", report, re.I):
        missing.append("working-tree state")
    if (re.search(r"next,? i('ll| will)|i('ll| will) now|now i('ll| will)|let me now|i'm going to|i am going to", report, re.I)
            and not re.search(r"blocker|blocked|cannot proceed|can.t proceed|waiting (on|for)|needs? (your|the user|a human)", report, re.I)):
        missing.append("the step you announced: do it now, or state the blocker that stops it")
    return {"decision": "block", "reason": "Handoff incomplete: " + "; ".join(missing)} if missing else {}


def policy(payload, role=""):
    if not isinstance(payload, dict):
        raise ValueError("Hook input must be an object.")
    event = payload.get("hook_event_name")
    if event == "SessionStart":
        return shared("warn-stale-base.sh", payload, "--report")
    if event in {"Stop", "SubagentStop"}:
        return handoff(payload) if (role or payload.get("agent_type")) in WRITERS else {}
    if event != "PreToolUse":
        return {}
    if role and role not in WRITERS | READERS:
        raise ValueError("Unknown harness role.")
    tool = payload.get("tool_name", "")
    args = payload.get("tool_input")
    if not isinstance(args, dict):
        raise ValueError("Hook tool_input must be an object.")
    if tool in {"Agent", "spawn_agent"}:
        if role:
            return deny("Harness personas may not dispatch other agents.")
        persona = args.get("agent_type", args.get("subagent_type", ""))
        if not isinstance(persona, str):
            raise ValueError("Invalid agent type.")
        if persona not in WRITERS:
            return {}
        return shared("require-worktree-for-writers.sh", {**payload, "tool_input": {"agent_type": "executor" if persona == "executor-high" else persona}})
    shell = tool in {"Bash", "exec_command", "shell", "shell_command"}
    edit = tool in {"apply_patch", "Edit", "Write"}
    if role in READERS:
        if edit or tool in {"js_repl", "python", "notebook", "spawn_agent", "Agent"}:
            return deny("This persona may only read repository evidence; implementation and test execution belong to writers.")
        if shell and not read_only_shell(args.get("command", args.get("cmd", ""))):
            return deny("Read-only persona: use bounded file/search commands and git --no-pager; diff/show/log also require --no-ext-diff --no-textconv. Do not run project code or tests.")
    normalized = {**payload, "tool_input": dict(args)}
    cwd = args.get("workdir", args.get("cwd", payload.get("cwd")))
    if not isinstance(cwd, str) or not Path(cwd).is_dir():
        raise ValueError("Cannot verify the tool working directory.")
    normalized["cwd"] = cwd
    if shell:
        command = args.get("command", args.get("cmd"))
        if not isinstance(command, str) or not command:
            raise ValueError("Shell command must be a nonempty string.")
        normalized["tool_input"]["command"] = command
        for name in ["block-destructive-bash.sh", "require-isolated-test-runner.sh"] + (["block-agent-push.sh", "require-commit-trailers.sh"] if role in WRITERS else ["warn-force-push.sh"]):
            result = shared(name, normalized)
            if result:
                return result
    if role in WRITERS and (shell or edit):
        result = shared("require-worktree-for-writers.sh", {**normalized, "tool_input": {"agent_type": "executor" if role == "executor-high" else role}})
        if result:
            return result
    return {}


if __name__ == "__main__":
    payload = {}
    try:
        payload = json.load(sys.stdin)
        result = policy(payload, sys.argv[1] if len(sys.argv) > 1 else "")
    except (ValueError, TypeError, OSError, subprocess.SubprocessError) as error:
        reason = f"Codex harness policy could not verify this call: {error}"
        event = payload.get("hook_event_name") if isinstance(payload, dict) else None
        if event == "SessionStart":
            result = {"systemMessage": reason, "hookSpecificOutput": {
                "hookEventName": event, "additionalContext": reason}}
        elif event in {"Stop", "SubagentStop"}:
            result = {"decision": "block", "reason": reason}
        else:
            result = deny(reason)
    print(json.dumps(result))
