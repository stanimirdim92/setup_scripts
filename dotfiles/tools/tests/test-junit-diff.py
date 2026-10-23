#!/usr/bin/env python3
"""Fixture tests for dotfiles/claude/skills/executor-development-discipline/scripts/junit-diff.py.

A baseline with one known failure is compared with candidate runs: unchanged,
a new failure, a fixed test, a deleted test, a newly skipped test.
"""
import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = (Path(__file__).resolve().parents[2] / 'claude' / 'skills' / 'executor-development-discipline'
          / 'scripts' / 'junit-diff.py')
spec = importlib.util.spec_from_file_location('jd', SCRIPT)
jd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(jd)


def report(cases):
    """cases: (classname, name, status) with status pass|fail|error|skip."""
    body = []
    for cls, name, status in cases:
        child = {'pass': '', 'fail': '<failure message="x"/>', 'error': '<error message="x"/>',
                 'skip': '<skipped/>'}[status]
        body.append('<testcase classname="{}" name="{}">{}</testcase>'.format(cls, name, child))
    return '<testsuites><testsuite name="s">{}</testsuite></testsuites>'.format(''.join(body))


BASE = [('A', 'one', 'pass'), ('A', 'two', 'fail'), ('B', 'three', 'pass')]


class JunitDiffTest(unittest.TestCase):
    def run_diff(self, after_cases):
        with tempfile.TemporaryDirectory() as tmp:
            base, after = Path(tmp, 'base.xml'), Path(tmp, 'after.xml')
            base.write_text(report(BASE))
            after.write_text(report(after_cases))
            code = jd.main(['junit-diff.py', str(base), str(after)])
            return code, jd.compare(jd.load(str(base)), jd.load(str(after)))

    def test_unchanged_passes(self):
        code, diff = self.run_diff(BASE)
        self.assertEqual(code, 0)
        self.assertEqual(diff['new failures'], [])

    def test_new_failure_fails(self):
        code, diff = self.run_diff([('A', 'one', 'error'), ('A', 'two', 'fail'), ('B', 'three', 'pass')])
        self.assertEqual(code, 1)
        self.assertEqual(diff['new failures'], ['A::one'])

    def test_new_failing_test_fails(self):
        code, diff = self.run_diff(BASE + [('C', 'four', 'fail')])
        self.assertEqual(code, 1)
        self.assertEqual(diff['new failures'], ['C::four'])

    def test_fixed_test_is_reported_and_passes(self):
        code, diff = self.run_diff([('A', 'one', 'pass'), ('A', 'two', 'pass'), ('B', 'three', 'pass')])
        self.assertEqual(code, 0)
        self.assertEqual(diff['now passing'], ['A::two'])

    def test_missing_test_fails(self):
        code, diff = self.run_diff([('A', 'one', 'pass'), ('A', 'two', 'fail')])
        self.assertEqual(code, 1)
        self.assertEqual(diff['missing'], ['B::three'])

    def test_newly_skipped_fails(self):
        code, diff = self.run_diff([('A', 'one', 'skip'), ('A', 'two', 'fail'), ('B', 'three', 'pass')])
        self.assertEqual(code, 1)
        self.assertEqual(diff['newly skipped'], ['A::one'])

    def test_unreadable_report_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp, 'bad.xml')
            bad.write_text('not xml')
            self.assertEqual(jd.main(['junit-diff.py', str(bad), str(bad)]), 2)


if __name__ == '__main__':
    unittest.main()
