#!/usr/bin/env python3
"""Exercise installed hook shapes against real, disposable Git checkouts."""

import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]
CODEX = ROOT / "dotfiles/codex"
POLICY = CODEX / "hooks/policy.py"
SPEC = importlib.util.spec_from_file_location("policy", POLICY)
POLICIES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(POLICIES)


class CodexHarnessTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="codex-harness-")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.repo = self.home / "main checkout"
        self.ticket = self.home / "ticket checkout"
        self.env = {**os.environ, "HOME": str(self.home), "GIT_CONFIG_NOSYSTEM": "1",
                    "GIT_CONFIG_GLOBAL": os.devnull}
        self.env.pop("GIT_DIR", None)
        self.env.pop("GIT_WORK_TREE", None)
        self.git("init", "-q", "-b", "main", str(self.repo))
        self.git("config", "user.name", "Harness fixture", cwd=self.repo)
        self.git("config", "user.email", "fixture@example.invalid", cwd=self.repo)
        (self.repo / "sample.txt").write_text("sample\n")
        self.git("add", "sample.txt", cwd=self.repo)
        self.git("commit", "-qm", "fixture", cwd=self.repo)
        self.git("worktree", "add", "-qb", "ticket", str(self.ticket), cwd=self.repo)
        (self.home / ".codex").mkdir()
        (self.home / ".codex/hooks").symlink_to(CODEX / "hooks")

    def git(self, *args, cwd=None):
        return subprocess.run(["git", *args], cwd=cwd, env=self.env, check=True,
                              text=True, capture_output=True).stdout.strip()

    def invoke(self, payload, role="", env=None):
        proc = subprocess.run(["python3", str(POLICY), *([role] if role else [])],
                              input=json.dumps(payload), text=True, capture_output=True,
                              env=env or self.env, timeout=25)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    def payload(self, tool="Bash", command="git status --short", cwd=None, **args):
        return {"hook_event_name": "PreToolUse", "cwd": str(cwd or self.ticket),
                "tool_name": tool, "tool_input": {"command": command, **args}}

    def decision(self, result):
        return result.get("hookSpecificOutput", {}).get("permissionDecision")

    def test_global_shell_guards_and_claude_remote_flag(self):
        for command, expected in [("git reset --hard", "deny"),
                                  ("git push origin ticket", "ask"),
                                  ("git status --short", None)]:
            with self.subTest(command=command):
                output = self.invoke(self.payload(command=command),
                                     env={**self.env, "CLAUDE_CODE_REMOTE": "true"})
                self.assertEqual(self.decision(output), expected)

    def test_writer_push_and_publish_denied_local_commit_allowed(self):
        for role in POLICIES.WRITERS:
            for command in ["git push", "git fu", "gh pr create", "gh pr merge", "gh release create v1"]:
                with self.subTest(role=role, command=command):
                    self.assertEqual(self.decision(self.invoke(self.payload(command=command), role)), "deny")
            self.assertEqual(self.invoke(self.payload(command="git commit -m task"), role), {})

    def test_raw_exec_arguments_are_normalized(self):
        payload = {"hook_event_name": "PreToolUse", "cwd": str(self.ticket),
                   "tool_name": "exec_command", "tool_input": {"cmd": "git push"}}
        self.assertEqual(self.decision(self.invoke(payload, "executor")), "deny")
        payload["tool_input"] = {"cmd": "git status --short", "workdir": str(self.repo)}
        self.assertEqual(self.decision(self.invoke(payload, "executor")), "deny")

    def test_writer_actual_tool_directory_checked(self):
        for role in POLICIES.WRITERS:
            self.assertEqual(self.invoke(self.payload(), role), {})
            for payload in [self.payload(cwd=self.repo),
                            self.payload(workdir=str(self.repo)),
                            self.payload(workdir=str(self.home / "missing")),
                            self.payload("apply_patch", "*** Begin Patch\n*** End Patch", cwd=self.repo)]:
                with self.subTest(role=role, payload=payload):
                    self.assertEqual(self.decision(self.invoke(payload, role)), "deny")
        self.git("checkout", "--detach", "-q", cwd=self.ticket)
        self.assertEqual(self.decision(self.invoke(self.payload(), "executor")), "deny")

    def test_dispatch_and_no_nesting(self):
        for role in POLICIES.WRITERS:
            payload = self.payload("spawn_agent", agent_type=role, cwd=self.repo)
            self.assertEqual(self.decision(self.invoke(payload)), "deny")
        # A task_name is not a native role selector.
        self.assertEqual(self.invoke(self.payload("spawn_agent", task_name="executor", cwd=self.repo)), {})
        for role in POLICIES.WRITERS | POLICIES.READERS:
            self.assertEqual(self.decision(self.invoke(self.payload("spawn_agent"), role)), "deny")

    def test_readers_can_inspect_default_branch_but_not_execute(self):
        for command in ["rg -n sample . | head -30", "nl -ba sample.txt", "sed -n '1,20p' sample.txt",
                        "git --no-pager diff --no-ext-diff --no-textconv | head -30"]:
            self.assertEqual(self.invoke(self.payload(command=command, cwd=self.repo), "repo-recon"), {})
        for role in POLICIES.READERS:
            for tool, command in [("Bash", "php artisan test"), ("Bash", "python3 tool.py"),
                                  ("Bash", "sed -i s/a/b/ sample.txt"), ("Bash", "rg --pre script sample"),
                                  ("Bash", "git --no-pager diff --output=result"),
                                  ("Bash", "git show HEAD"), ("Bash", "cat $(touch marker)"),
                                  ("apply_patch", "patch"), ("js_repl", "code")]:
                with self.subTest(role=role, command=command):
                    self.assertEqual(self.decision(self.invoke(self.payload(tool, command), role)), "deny")
        self.assertFalse((self.ticket / "marker").exists())

    def test_failed_doctor_denies_writer_and_surfaces_startup_warning(self):
        (self.ticket / "bin").mkdir()
        doctor = self.ticket / "bin/worktree-doctor.sh"
        doctor.write_text("#!/bin/sh\necho 'fixture infrastructure is stale'\nexit 1\n")
        doctor.chmod(0o755)
        result = self.invoke(self.payload(), "executor")
        self.assertEqual(self.decision(result), "deny")
        self.assertIn("fixture infrastructure is stale", json.dumps(result))
        startup = self.invoke({"hook_event_name": "SessionStart", "cwd": str(self.ticket)})
        self.assertEqual(startup["hookSpecificOutput"]["hookEventName"], "SessionStart")
        self.assertIn("fixture infrastructure is stale", startup["hookSpecificOutput"]["additionalContext"])

    def test_isolated_runner_policy_applies_to_codex_shell(self):
        (self.ticket / "bin").mkdir()
        runner = self.ticket / "bin/worktree-test.sh"
        runner.write_text("#!/bin/sh\nexit 0\n")
        runner.chmod(0o755)
        self.assertEqual(self.decision(self.invoke(self.payload(command="php artisan test"))), "deny")
        self.assertEqual(self.invoke(self.payload(command="bin/worktree-test.sh"), "test-engineer"), {})

    def test_invalid_input_denies_instead_of_crashing(self):
        for payload in [[], None, {"hook_event_name": "PreToolUse", "tool_input": []},
                        self.payload(command=None), self.payload(workdir=[]),
                        self.payload("spawn_agent", agent_type=[]), self.payload(command="unterminated '")]:
            with self.subTest(payload=payload):
                self.assertEqual(self.decision(self.invoke(payload, "repo-recon")), "deny")

    def test_handoff_uses_codex_message_and_stops_after_one_retry(self):
        payload = {"hook_event_name": "SubagentStop", "agent_type": "executor",
                   "last_assistant_message": "Done."}
        self.assertEqual(self.invoke(payload)["decision"], "block")
        self.assertEqual(self.invoke({**payload, "last_assistant_message": ""})["decision"], "block")
        self.assertEqual(self.invoke({**payload, "last_assistant_message":
            "Verification: pytest passed, exit 0. No commit: not authorized. Working tree: uncommitted changes."}), {})
        self.assertEqual(self.invoke({**payload, "stop_hook_active": True}), {})
        self.assertEqual(self.invoke({**payload, "agent_type": "code-reviewer"}), {})

    def test_registered_hooks_execute_from_installed_paths(self):
        manifest = json.loads((CODEX / "hooks.json").read_text())["hooks"]
        scenarios = {
            "SessionStart": ("startup", {"hook_event_name": "SessionStart", "cwd": str(self.ticket)}),
            "PreToolUse": ("Bash", self.payload(command="git reset --hard")),
            "SubagentStop": ("executor", {"hook_event_name": "SubagentStop", "agent_type": "executor", "last_assistant_message": "Done."}),
        }
        for event, (match, payload) in scenarios.items():
            group, = manifest[event]
            self.assertRegex(match, group["matcher"])
            handler, = group["hooks"]
            result = subprocess.run(["bash", "-c", handler["command"]], input=json.dumps(payload),
                                    env=self.env, text=True, capture_output=True, timeout=handler["timeout"])
            self.assertEqual(result.returncode, 0, result.stderr)
            output = json.loads(result.stdout)
            if event == "PreToolUse":
                self.assertEqual(self.decision(output), "deny")
            elif event == "SubagentStop":
                self.assertEqual(output["decision"], "block")
            else:
                self.assertEqual(output["hookSpecificOutput"]["hookEventName"], event)

    def test_native_roles_resolve_shared_bodies_and_scope_policies(self):
        files = list((CODEX / "agents").glob("*.toml"))
        self.assertEqual({p.stem for p in files}, POLICIES.READERS | POLICIES.WRITERS)
        for path in files:
            role = tomllib.loads(path.read_text())
            name = role["name"]
            writer = name in POLICIES.WRITERS
            self.assertEqual(role["agents"]["enabled"], False)
            self.assertEqual(role["sandbox_mode"], "workspace-write" if writer else "read-only")
            terra = name in {"executor", "test-engineer", "repo-recon"}
            self.assertEqual(role["model"], "gpt-5.6-terra" if terra else "gpt-6-astra")
            self.assertEqual(role["model_reasoning_effort"], "xhigh" if terra else "high")
            persona, = re.findall(r"~/\.claude/agents/([\w-]+)\.md", role["developer_instructions"])
            self.assertTrue((ROOT / "dotfiles/claude/agents" / f"{persona}.md").is_file())
            group, = role["hooks"]["PreToolUse"]
            handler, = group["hooks"]
            result = subprocess.run(["bash", "-c", handler["command"]],
                                    input=json.dumps(self.payload(command="git push" if writer else "php artisan test")),
                                    env=self.env, text=True, capture_output=True, timeout=handler["timeout"])
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(self.decision(json.loads(result.stdout)), "deny")


if __name__ == "__main__":
    unittest.main()
