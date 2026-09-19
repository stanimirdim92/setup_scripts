#!/usr/bin/env python3
"""Real Git/launcher tests; stub only the interactive Codex process and setup."""

import json
import os
from pathlib import Path
import runpy
import subprocess
import tempfile
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "dotfiles/codex/bin/codex-worktree"


class CodexWorktreeTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="codex-worktree-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / "project with spaces"
        self.bin = self.base / "bin"
        self.bin.mkdir()
        self.log = self.base / "calls.jsonl"
        self.env = {**os.environ, "PATH": str(self.bin) + os.pathsep + os.environ["PATH"],
                    "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                    "LAUNCHER_TEST_LOG": str(self.log)}
        for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR"):
            self.env.pop(key, None)
        self.git("init", "-q", "-b", "main", str(self.repo), cwd=self.base)
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Worktree fixture")
        (self.repo / "bin").mkdir()
        (self.repo / ".gitignore").write_text(".env*\ncache/\nsetup-ran\n*.ready\n")
        (self.repo / ".worktreeinclude").write_text(".env*\n!.env.exclude\ncache/\nuntracked.txt\ntracked.txt\n")
        (self.repo / "tracked.txt").write_text("committed\n")
        (self.repo / "bin/worktree-setup.sh").write_text("#!/bin/sh\nset -eu\ntest -f .env\ntest -f .env.testing\ntest ! -L cache\nprintf 'ready\\n' > setup-ran\n")
        (self.repo / "bin/worktree-setup.sh").chmod(0o755)
        self.git("add", ".")
        self.git("commit", "-qm", "fixture")
        (self.repo / ".env").write_text("fixture env\n")
        (self.repo / ".env.testing").write_text("fixture tests\n")
        (self.repo / ".env.exclude").write_text("excluded\n")
        (self.repo / "untracked.txt").write_text("not ignored\n")
        (self.repo / "cache").mkdir()
        (self.repo / "cache/dependency").write_text("owned copy\n")
        (self.repo / "cache/link").symlink_to("dependency")
        (self.bin / "codex").write_text("""#!/usr/bin/env python3
import json, os, pathlib, sys, time
cwd = pathlib.Path.cwd()
with open(os.environ['LAUNCHER_TEST_LOG'], 'a') as log:
    log.write(json.dumps({'cwd': str(cwd), 'args': sys.argv[1:]}) + '\\n')
(cwd / 'session.ready').write_text('ready')
while os.environ.get('LAUNCHER_TEST_HOLD') and not (cwd / 'release.ready').exists():
    time.sleep(0.02)
sys.exit(int(os.environ.get('LAUNCHER_TEST_EXIT', '0')))
""")
        (self.bin / "codex").chmod(0o755)

    def git(self, *args, cwd=None):
        return subprocess.run(["git", "-C", str(cwd or self.repo), *args], env=self.env,
                              check=True, text=True, capture_output=True).stdout.strip()

    def launch(self, *args, cwd=None, env=None):
        return subprocess.run([str(LAUNCHER), *args], cwd=cwd or self.repo,
                              env=env or self.env, capture_output=True, text=True, timeout=20)

    def target(self, ticket="LD-1"):
        return self.repo / ".codex/worktrees" / ticket

    def ok(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def test_creation_copy_setup_and_argument_forwarding(self):
        (self.repo / "tracked.txt").write_text("local uncommitted\n")
        result = self.launch("LD-1", "--", "-m", "gpt-6-astra", "prompt with spaces")
        self.ok(result)
        target = self.target()
        self.assertEqual(self.git("branch", "--show-current", cwd=target), "codex/LD-1")
        self.assertEqual((target / "tracked.txt").read_text(), "committed\n")
        self.assertEqual((self.repo / "tracked.txt").read_text(), "local uncommitted\n")
        self.assertEqual((target / ".env").read_text(), "fixture env\n")
        self.assertFalse((target / ".env.exclude").exists())
        self.assertFalse((target / "untracked.txt").exists())
        self.assertFalse((target / "cache/link").is_symlink())
        self.assertEqual((target / "cache/dependency").read_text(), "owned copy\n")
        self.assertNotEqual((target / "cache/dependency").stat().st_ino, (self.repo / "cache/dependency").stat().st_ino)
        self.assertTrue((target / "setup-ran").exists())
        self.assertEqual(self.calls(), [{"cwd": str(target), "args": ["-C", str(target), "-m", "gpt-6-astra", "prompt with spaces"]}])
        self.assertEqual(self.git("branch", "--show-current"), "main")
        self.assertNotIn(".codex", self.git("status", "--short"))

    def test_reuse_preserves_edits_and_environment(self):
        self.ok(self.launch("LD-1"))
        target = self.target()
        (target / ".env").write_text("ticket env\n")
        (target / "tracked.txt").write_text("ticket edits\n")
        self.ok(self.launch("LD-1"))
        self.assertEqual((target / ".env").read_text(), "ticket env\n")
        self.assertEqual((target / "tracked.txt").read_text(), "ticket edits\n")
        self.assertEqual(len(self.calls()), 2)
        # Starting inside a ticket reuses its canonical location, not a nested tree.
        self.ok(self.launch("LD-1", cwd=target / "bin"))
        self.assertEqual(self.calls()[-1]["cwd"], str(target))
        self.assertFalse((target / ".codex/worktrees").exists())

    def test_existing_unchecked_branch_is_reused(self):
        self.git("branch", "codex/LD-1")
        self.ok(self.launch("LD-1"))
        self.assertEqual(self.git("branch", "--show-current", cwd=self.target()), "codex/LD-1")

    def test_interrupted_copy_does_not_leave_partial_files(self):
        target = self.target()
        self.git("worktree", "add", "-qb", "codex/LD-1", str(target))
        copy_includes = runpy.run_path(str(LAUNCHER))["copy_includes"]

        def interrupted_copy(source, destination):
            Path(destination).write_text("partial")
            raise OSError("fixture interrupted copy")

        with mock.patch("shutil.copy2", side_effect=interrupted_copy):
            with self.assertRaisesRegex(OSError, "fixture interrupted copy"):
                copy_includes(self.repo, target)
        self.assertFalse((target / ".env").exists())
        self.assertEqual(list(target.rglob(".codex-copy-*")), [])
        self.ok(self.launch("LD-1"))
        self.assertEqual((target / ".env").read_text(), "fixture env\n")

    def test_dry_run_and_help_do_not_mutate(self):
        before = self.git("status", "--porcelain")
        self.ok(self.launch("--dry-run", "LD-1"))
        self.assertFalse((self.repo / ".codex").exists())
        self.assertFalse((self.repo / ".git/codex-worktree-locks").exists())
        self.assertEqual(before, self.git("status", "--porcelain"))
        self.assertEqual(self.calls(), [])
        self.ok(self.launch("--help", cwd=self.base))

    def test_no_setup_is_explicit_and_still_copies_environment(self):
        self.ok(self.launch("--no-setup", "LD-1"))
        self.assertFalse((self.target() / "setup-ran").exists())
        self.assertTrue((self.target() / ".env").exists())

    def test_invalid_ticket_or_directory_override_is_rejected_before_changes(self):
        for args in [("../oops",), ("bad/name",), ("--bad",),
                     ("LD-1", "--", "-C", "/tmp"), ("LD-1", "--", "--remote=unix://")]:
            with self.subTest(args=args):
                self.assertNotEqual(self.launch(*args).returncode, 0)
                self.assertFalse((self.repo / ".codex").exists())

    def test_unregistered_path_and_symlink_are_never_replaced(self):
        target = self.target()
        target.mkdir(parents=True)
        (target / "keep").write_text("keep\n")
        self.assertNotEqual(self.launch("LD-1").returncode, 0)
        self.assertEqual((target / "keep").read_text(), "keep\n")
        other = self.target("LD-2")
        other.symlink_to(self.base, target_is_directory=True)
        self.assertNotEqual(self.launch("LD-2").returncode, 0)
        self.assertTrue(other.is_symlink())

    def test_checked_out_elsewhere_or_detached_ticket_is_rejected(self):
        elsewhere = self.base / "elsewhere"
        self.git("worktree", "add", "-qb", "codex/LD-1", str(elsewhere))
        self.assertNotEqual(self.launch("LD-1").returncode, 0)
        self.ok(self.launch("LD-2"))
        self.git("checkout", "--detach", "-q", cwd=self.target("LD-2"))
        self.assertNotEqual(self.launch("LD-2").returncode, 0)

    def test_setup_failure_retains_checkout_and_never_starts_codex(self):
        (self.repo / "bin/worktree-setup.sh").write_text("#!/bin/sh\nexit 17\n")
        self.git("add", "bin/worktree-setup.sh")
        self.git("commit", "-qm", "failing setup")
        result = self.launch("LD-1")
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue((self.target() / ".git").is_file())
        self.assertEqual(self.calls(), [])
        self.assertIn("retained", result.stderr)

    def test_infrastructure_failure_prevents_setup_and_launch(self):
        doctor = self.repo / "bin/worktree-doctor.sh"
        doctor.write_text("#!/bin/sh\necho 'fixture stale infrastructure'\nexit 1\n")
        doctor.chmod(0o755)
        self.git("add", "bin/worktree-doctor.sh")
        self.git("commit", "-qm", "failing doctor")
        result = self.launch("LD-1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("fixture stale infrastructure", result.stderr)
        self.assertFalse((self.target() / "setup-ran").exists())
        self.assertEqual(self.calls(), [])

    def test_codex_exit_status_propagates(self):
        result = self.launch("LD-1", env={**self.env, "LAUNCHER_TEST_EXIT": "23"})
        self.assertEqual(result.returncode, 23)
        self.assertTrue(self.target().is_dir())

    def test_separate_tickets_run_concurrently_same_ticket_is_busy(self):
        processes = []
        try:
            for ticket in ("LD-1", "LD-2"):
                processes.append(subprocess.Popen([str(LAUNCHER), ticket], cwd=self.repo,
                    env={**self.env, "LAUNCHER_TEST_HOLD": "1"}, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE))
            deadline = time.monotonic() + 15
            while not all((self.target(ticket) / "session.ready").exists() for ticket in ("LD-1", "LD-2")):
                if time.monotonic() > deadline or any(p.poll() is not None for p in processes):
                    self.fail("both independent sessions did not become active")
                time.sleep(0.02)
            busy = self.launch("LD-1")
            self.assertNotEqual(busy.returncode, 0)
            self.assertIn("already has a launcher/session", busy.stderr)
            self.assertEqual(len(self.calls()), 2)
        finally:
            for ticket in ("LD-1", "LD-2"):
                if self.target(ticket).is_dir():
                    (self.target(ticket) / "release.ready").touch()
            results = []
            for process in processes:
                try:
                    _, error = process.communicate(timeout=5)
                    results.append((process.returncode, error))
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.communicate()
                    results.append((-1, "launcher did not exit"))
            for code, error in results:
                self.assertEqual(code, 0, error)


if __name__ == "__main__":
    unittest.main()
