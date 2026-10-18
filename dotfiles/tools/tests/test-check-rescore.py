#!/usr/bin/env python3
"""Fixture tests for dotfiles/tools/checks/check-rescore.py (ADR 0111)."""
import importlib.util
import io
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'checks' / 'check-rescore.py'
spec = importlib.util.spec_from_file_location('cr', SCRIPT)
cr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cr)


class Rescore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = os.getcwd()
        os.chdir(self.tmp.name)
        self.git('init', '-q', '-b', 'main')
        self.commit('base', 'README.md')

    def tearDown(self):
        os.chdir(self.cwd)
        self.tmp.cleanup()

    def git(self, *args):
        return subprocess.run(['git', '-c', 'user.email=t@t', '-c', 'user.name=t', *args],
                              capture_output=True, text=True, check=True).stdout.strip()

    def commit(self, message, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'a') as fh:
            fh.write(message + '\n')
        self.git('add', path)
        self.git('commit', '-q', '-m', message)
        return self.git('rev-parse', 'HEAD')

    def test_reviewer_change_needs_a_result(self):
        base = self.git('rev-parse', 'HEAD')
        self.commit('docs only', 'dotfiles/docs/x.md')
        self.commit('reviewer tweak', 'dotfiles/claude/agents/code-reviewer.md')
        self.commit('rescored\n\nReview-eval: bugs 5/8 -> 6/8 (BETTER)', 'dotfiles/claude/commands/review.md')
        self.commit('wording\n\nReview-eval: not run - typo only', 'dotfiles/claude/references/risk-tiers.md')
        self.commit('lazy\n\nReview-eval: not run', 'dotfiles/codex/agents/security-auditor.toml')
        bad = cr.missing(f'{base}..HEAD')
        self.assertEqual([b[1] for b in bad], ['lazy', 'reviewer tweak'])

    def test_clean_range_and_new_branch(self):
        base = self.git('rev-parse', 'HEAD')
        self.commit('unrelated', 'dotfiles/claude/agents/executor.md')
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(cr.main(['--range', f'{base}..HEAD']), 0)
            self.assertEqual(cr.main(['--range', '0000000000000000000000000000000000000000..HEAD']), 0)
        self.assertIn('new branch', out.getvalue())


if __name__ == '__main__':
    unittest.main(verbosity=1)
