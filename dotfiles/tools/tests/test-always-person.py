#!/usr/bin/env python3
"""Fixture tests for skills/code-review-and-quality/scripts/always-person.py
(ADR 0096): globs from the base branch's REVIEW.md, directory REVIEW.md files,
`dir/**`, and a change that edits REVIEW.md not exempting itself."""
import io
import importlib.util
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

SCRIPT = (Path(__file__).resolve().parents[2] / 'claude' / 'skills' / 'code-review-and-quality'
          / 'scripts' / 'always-person.py')
spec = importlib.util.spec_from_file_location('ap', SCRIPT)
ap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ap)

ROOT_REVIEW = """# REVIEW.md

## Always a person

- `.github/workflows/**`
- `database/migrations/*.php`

## Cap the nits

Report at most 5 nits.
"""


class AlwaysPerson(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        self.cwd = os.getcwd()
        os.chdir(self.repo)
        self.git('init', '-q', '-b', 'main')
        self.write('REVIEW.md', ROOT_REVIEW)
        self.write('app/Billing/REVIEW.md', '## Always a person\n\n- `*.php`\n')
        self.write('app/Feed.php', '<?php\n')
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

    def run_script(self):
        with redirect_stdout(io.StringIO()) as out:
            rc = ap.main(['--base', 'main'])
        return rc, out.getvalue()

    def commit(self, *files):
        for f in files:
            self.write(f, 'x\n')
        self.git('add', '-A'); self.git('commit', '-qm', 'change')

    def test_ordinary_change_does_not_match(self):
        self.commit('app/Feed.php')
        rc, out = self.run_script()
        self.assertEqual(rc, 0)
        self.assertIn('none of 1 changed file(s) match', out)

    def test_workflow_and_migration_match(self):
        self.commit('.github/workflows/deploy.yml', 'database/migrations/2026_add.php')
        rc, out = self.run_script()
        self.assertEqual(rc, 1)
        self.assertIn('.github/workflows/deploy.yml', out)
        self.assertIn('database/migrations/2026_add.php', out)

    def test_directory_review_md_globs_are_relative(self):
        self.commit('app/Billing/Invoice.php')
        rc, out = self.run_script()
        self.assertEqual(rc, 1)
        self.assertIn('app/Billing/*.php', out)

    def test_change_cannot_remove_its_own_entry(self):
        self.write('REVIEW.md', '# REVIEW.md\n')          # the change deletes the list...
        self.commit('database/migrations/2026_drop.php')    # ...and edits a migration
        rc, out = self.run_script()
        self.assertEqual(rc, 1)                             # the base branch's list still applies

    def test_moving_a_protected_file_out_of_its_directory_still_matches(self):
        self.git('checkout', '-q', 'main')
        self.write('app/Billing/Invoice.php', '<?php\n// invoice\n')
        self.git('add', '-A'); self.git('commit', '-qm', 'invoice')
        self.git('checkout', '-q', '-B', 'ticket')
        self.git('mv', 'app/Billing/Invoice.php', 'app/Invoice.php')
        self.git('commit', '-qm', 'move out of Billing')
        rc, out = self.run_script()
        self.assertEqual(rc, 1)
        self.assertIn('app/Billing/Invoice.php', out)
        self.assertIn('app/Billing/*.php', out)

    def test_rule_added_to_base_after_branching_applies(self):
        self.commit('auth.py')                              # the ticket edits auth.py
        self.git('checkout', '-q', 'main')
        self.write('REVIEW.md', ROOT_REVIEW.replace('- `database/migrations/*.php`',
                                                    '- `database/migrations/*.php`\n- `auth.py`'))
        self.git('add', '-A'); self.git('commit', '-qm', 'main adds an auth rule')
        self.git('checkout', '-q', 'ticket')
        rc, out = self.run_script()
        self.assertEqual(rc, 1)
        self.assertIn('auth.py', out)

    def test_no_list(self):
        self.assertEqual(ap.globs_in('# REVIEW.md\n\n## Cap the nits\n'), [])


if __name__ == '__main__':
    unittest.main(verbosity=1)
