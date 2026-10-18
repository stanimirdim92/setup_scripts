#!/usr/bin/env python3
"""Fixture tests for ticket-stats.py (ADR 0112): decisions, open items,
approvals counted from git history, review rounds and finding endings."""
import importlib.util
import io
import json
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

SCRIPT = (Path(__file__).resolve().parents[2] / 'claude' / 'skills' / 'spec-driven-development'
          / 'scripts' / 'ticket-stats.py')
spec = importlib.util.spec_from_file_location('ts', SCRIPT)
ts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ts)

SPEC = '''# Spec: X

Status: {status}
Approved by: me
Approved at: {at}

### DEC-001 — Export format
### DEC-002 — Soft deletes
'''


class TicketStats(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = os.getcwd()
        os.chdir(self.tmp.name)
        self.git('init', '-q', '-b', 'main')
        Path('docs/specs').mkdir(parents=True)
        Path('docs/tasks').mkdir(parents=True)
        self.save('docs/specs/AB-1-SPEC.md', SPEC.format(status='Draft', at='—'), 'draft')
        self.save('docs/specs/AB-1-SPEC.md', SPEC.format(status='Approved', at='2026-10-01'), 'approve')
        self.save('docs/tasks/AB-1-plan.md', 'Approved at: 2026-10-02\n', 'plan approve')
        self.save('docs/specs/AB-1-SPEC.md', SPEC.format(status='Approved', at='2026-10-05'), 'reapprove')
        self.save('docs/tasks/AB-1-open.md', '- OPEN-001 a\n- OPEN-002 b\n- see OPEN-001\n', 'open')
        self.reviews = Path(self.tmp.name) / 'review'
        self.reviews.mkdir()
        res = lambda *ends: json.dumps({'runs': [{'results': [{'properties': {'resolution': e}} for e in ends]}]})
        (self.reviews / 'AB-1-abc1234.sarif').write_text(res('fixed', 'refuted', 'open'))
        (self.reviews / 'AB-1-def5678.sarif').write_text(res('fixed'))
        (self.reviews / 'AB-12-0a1b2c3.sarif').write_text(res('fixed'))

    def tearDown(self):
        os.chdir(self.cwd)
        self.tmp.cleanup()

    def git(self, *args):
        subprocess.run(['git', '-c', 'user.email=t@t', '-c', 'user.name=t', *args], check=True, capture_output=True)

    def save(self, path, text, message):
        Path(path).write_text(text)
        self.git('add', path)
        self.git('commit', '-q', '-m', message)

    def test_counts(self):
        s = ts.stats('AB-1', self.reviews)
        self.assertEqual((s['decisions'], s['open_items'], s['approvals'], s['review_rounds']), (2, 2, 3, 2))
        self.assertEqual(s['findings'], {'fixed': 2, 'refuted': 1, 'other': 1})
        self.assertEqual(ts.row(s, '2026-10-18'),
                         '| 2026-10-18 | AB-1 | 2 | 2 | 3 | 2 | 2 fixed, 1 refuted, 1 other | 0 |')

    def test_missing_spec(self):
        with redirect_stderr(io.StringIO()):
            self.assertEqual(ts.main(['AB-9', '--review-dir', str(self.reviews)]), 1)
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(ts.main(['AB-1', '--review-dir', str(self.reviews), '--json']), 0)
        self.assertEqual(json.loads(out.getvalue())['approvals'], 3)


if __name__ == '__main__':
    unittest.main(verbosity=1)
