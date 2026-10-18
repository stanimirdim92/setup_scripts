#!/usr/bin/env python3
"""Fixture tests for skills/code-review-and-quality/scripts/stale-instructions.py
(ADR 0098): renamed and deleted files still named in instruction files, removed
package and composer scripts, a change that also fixes the line, and files
that are not instructions."""
import importlib.util
import io
import json
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

SCRIPT = (Path(__file__).resolve().parents[2] / 'claude' / 'skills' / 'code-review-and-quality'
          / 'scripts' / 'stale-instructions.py')
spec = importlib.util.spec_from_file_location('si', SCRIPT)
si = importlib.util.module_from_spec(spec)
spec.loader.exec_module(si)

CLAUDE = """# Project
Run backend tests with `bin/worktree-test.sh`.
Lint with `yarn lint`; build with `yarn build`.
"""


class StaleInstructions(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        self.cwd = os.getcwd()
        os.chdir(self.repo)
        self.git('init', '-q', '-b', 'main')
        self.write('CLAUDE.md', CLAUDE)
        self.write('.ai/rules/tests.md', 'Never run Pest directly; use bin/worktree-test.sh.\n')
        self.write('notes/todo.md', 'bin/worktree-test.sh is slow\n')       # not an instruction file
        self.write('bin/worktree-test.sh', '#!/bin/sh\n')
        self.write('package.json', json.dumps({'scripts': {'lint': 'eslint .', 'build': 'vite build'}}))
        self.git('add', '-A'); self.git('commit', '-qm', 'base')
        self.git('checkout', '-q', '-b', 'ticket')

    def tearDown(self):
        os.chdir(self.cwd)
        self.tmp.cleanup()

    def git(self, *args):
        subprocess.run(['git', '-c', 'user.email=t@t', '-c', 'user.name=t', *args], check=True, capture_output=True)

    def write(self, path, text):
        p = self.repo / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def commit(self):
        self.git('add', '-A'); self.git('commit', '-qm', 'change')

    def run_script(self):
        with redirect_stdout(io.StringIO()) as out:
            rc = si.main(['--base', 'main', '--json'])
        return rc, json.loads(out.getvalue())

    def test_renamed_script_is_stale_in_instructions_only(self):
        self.git('mv', 'bin/worktree-test.sh', 'bin/test.sh'); self.commit()
        rc, hits = self.run_script()
        self.assertEqual(rc, 1)
        self.assertEqual(sorted((h['file'], h['line']) for h in hits), [('.ai/rules/tests.md', 1), ('CLAUDE.md', 2)])
        self.assertIn('renamed to `bin/test.sh`', hits[0]['reason'])

    def test_change_that_fixes_the_line_is_clean(self):
        self.git('mv', 'bin/worktree-test.sh', 'bin/test.sh')
        self.write('CLAUDE.md', CLAUDE.replace('bin/worktree-test.sh', 'bin/test.sh'))
        self.write('.ai/rules/tests.md', 'Never run Pest directly; use bin/test.sh.\n')
        self.commit()
        self.assertEqual(self.run_script(), (0, []))

    def move(self, old, new):
        (self.repo / new).parent.mkdir(parents=True, exist_ok=True)
        self.git('mv', old, new)

    def test_updated_path_after_a_move_to_another_directory_is_clean(self):
        self.move('bin/worktree-test.sh', 'scripts/worktree-test.sh')
        self.write('CLAUDE.md', CLAUDE.replace('bin/worktree-test.sh', 'scripts/worktree-test.sh'))
        self.write('.ai/rules/tests.md', 'Never run Pest directly; use `scripts/worktree-test.sh`.\n')
        self.commit()
        self.assertEqual(self.run_script(), (0, []))

    def test_updated_path_that_ends_with_the_old_path_is_clean(self):
        self.move('bin/worktree-test.sh', 'app/bin/worktree-test.sh')
        self.write('CLAUDE.md', CLAUDE.replace('`bin/worktree-test.sh`', '`app/bin/worktree-test.sh`'))
        self.write('.ai/rules/tests.md', 'Never run Pest directly.\n')
        self.commit()
        self.assertEqual(self.run_script(), (0, []))

    def test_old_directory_path_after_a_move_is_still_stale(self):
        self.move('bin/worktree-test.sh', 'scripts/worktree-test.sh')
        self.write('CLAUDE.md', CLAUDE.replace('bin/worktree-test.sh', './bin/worktree-test.sh'))
        self.commit()
        rc, hits = self.run_script()
        self.assertEqual(rc, 1)
        self.assertIn(('CLAUDE.md', 2), [(h['file'], h['line']) for h in hits])

    def test_removed_package_script(self):
        self.write('package.json', json.dumps({'scripts': {'build': 'vite build'}})); self.commit()
        rc, hits = self.run_script()
        self.assertEqual(rc, 1)
        self.assertEqual([(h['file'], h['mentions']) for h in hits], [('CLAUDE.md', 'lint')])

    def test_unrelated_change_is_clean(self):
        self.write('app.py', 'x = 1\n'); self.commit()
        self.assertEqual(self.run_script(), (0, []))


if __name__ == '__main__':
    unittest.main(verbosity=1)
