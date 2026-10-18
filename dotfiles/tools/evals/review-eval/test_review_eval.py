#!/usr/bin/env python3
"""Tests for review-eval: a case built from a real bugfix history, and judging.

History: A adds feed.py; B introduces the bug on line 3; C edits another file;
F fixes line 3. The case must name B and the line B wrote, and a finding there
must count as caught. Producing drives the model and is not tested here."""
import importlib.util
import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('re_run', HERE / 'run.py')
rev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rev)


def git(repo, *args):
    return subprocess.run(['git', '-C', str(repo), '-c', 'user.email=t@t', '-c', 'user.name=t', *args],
                          capture_output=True, text=True, check=True).stdout.strip()


class History(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        r = self.repo = Path(self.tmp.name)
        git(r, 'init', '-q')
        (r / 'feed.py').write_text('def order(posts):\n    posts = list(posts)\n    return posts\n')
        git(r, 'add', '-A'); git(r, 'commit', '-qm', 'A')
        (r / 'feed.py').write_text('def order(posts):\n    posts = list(posts)\n    return sorted(posts)[1:]\n')
        git(r, 'commit', '-qam', 'B'); self.bug = git(r, 'rev-parse', 'HEAD')
        (r / 'other.py').write_text('x = 1\n')
        git(r, 'add', '-A'); git(r, 'commit', '-qm', 'C')
        (r / 'feed.py').write_text('def order(posts):\n    posts = list(posts)\n    return sorted(posts)\n')
        git(r, 'commit', '-qam', 'F'); self.fix = git(r, 'rev-parse', 'HEAD')

    def tearDown(self):
        self.tmp.cleanup()

    def test_blame_finds_the_bug_and_its_line(self):
        case = rev.bug_case(self.repo, self.fix)
        self.assertEqual(case['change'], self.bug)
        self.assertEqual(case['targets'], {'feed.py': [3]})

    def test_judging(self):
        case = rev.bug_case(self.repo, self.fix)
        sarif = lambda line, disp: json.dumps({'runs': [{'tool': {'driver': {'name': 'code-reviewer'}}, 'results': [
            {'ruleId': 'CODE-1', 'properties': {'disposition': disp},
             'locations': [{'physicalLocation': {'artifactLocation': {'uri': 'feed.py'}, 'region': {'startLine': line}}}]}]}]})
        self.assertTrue(rev.judge(case, rev.sarif_findings(sarif(4, 'BLOCKER')))['caught'])
        far = rev.judge(case, rev.sarif_findings(sarif(40, 'BLOCKER')))
        self.assertFalse(far['caught'])
        advisory = rev.judge(case, rev.sarif_findings(sarif(3, 'ADVISORY')))
        self.assertEqual((advisory['caught'], advisory['caught_any']), (False, True))

    def test_clean_case_counts_blocking_findings_as_noise(self):
        case = rev.clean_case(self.repo, 'HEAD~1')
        result = rev.judge(case, [('other.py', 1, 'REQUIRED'), ('other.py', 1, 'ADVISORY')])
        self.assertEqual(result['blocking'], 1)
        self.assertFalse(rev.item(case, result))
        self.assertTrue(rev.item(case, rev.judge(case, [])))

    def test_markdown_fallback(self):
        text = '### BLOCKER\n- [CODE-1] [feed.py:3] (confidence: high) drops the first post\n### ADVISORY\n- [CODE-2] [feed.py:1] name\n'
        self.assertEqual(rev.markdown_findings(text), [('feed.py', 3, 'BLOCKER'), ('feed.py', 1, 'ADVISORY')])


class Produce(unittest.TestCase):
    """produce() with a stub `claude` on PATH: a review that did not finish is
    an error, never an empty finding list that scores as a quiet review."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.repo = base / 'repo'
        self.repo.mkdir()
        git(self.repo, 'init', '-q')
        (self.repo / 'feed.py').write_text('x = 1\n')
        git(self.repo, 'add', '-A'); git(self.repo, 'commit', '-qm', 'A')
        (self.repo / 'feed.py').write_text('x = 2\n')
        git(self.repo, 'commit', '-qam', 'B')
        self.case = rev.clean_case(self.repo, 'HEAD')
        self.bin = base / 'bin'
        self.bin.mkdir()
        self.path = os.environ['PATH']
        os.environ['PATH'] = f'{self.bin}:{self.path}'

    def tearDown(self):
        os.environ['PATH'] = self.path
        self.tmp.cleanup()

    def stub(self, **meta):
        out = self.bin / 'claude'
        out.write_text(f"#!/bin/sh\ncat <<'EOF'\n{json.dumps(meta)}\nEOF\n")
        out.chmod(out.stat().st_mode | stat.S_IEXEC)

    def test_error_result_is_not_a_quiet_review(self):
        self.stub(is_error=True, result='REVIEW BLOCKED: verification missing')
        with self.assertRaises(RuntimeError):
            rev.produce(self.case, self.repo, '1')

    def test_review_blocked_text_is_not_a_quiet_review(self):
        self.stub(is_error=False, result='**REVIEW BLOCKED** - run /test first')
        with self.assertRaises(RuntimeError):
            rev.produce(self.case, self.repo, '1')

    def test_empty_output_is_not_a_quiet_review(self):
        self.stub(is_error=False, result='')
        with self.assertRaises(RuntimeError):
            rev.produce(self.case, self.repo, '1')

    def test_budget_stop_is_not_a_quiet_review(self):
        self.stub(is_error=False, subtype='error_max_budget_usd', result='**Nothing to fix.**')
        with self.assertRaises(RuntimeError):
            rev.produce(self.case, self.repo, '1')

    def test_count_line_without_parsable_findings_is_not_a_quiet_review(self):
        self.stub(is_error=False, result='**Findings: 1 BLOCKER · 0 REQUIRED · 0 ADVISORY**\n- CODE-1 something odd')
        with self.assertRaises(RuntimeError):
            rev.produce(self.case, self.repo, '1')

    def test_stated_zero_findings_is_a_valid_quiet_review(self):
        self.stub(is_error=False, result='**Findings: 0 BLOCKER · 0 REQUIRED · 0 ADVISORY**\n**Nothing to fix.**')
        findings, _, source = rev.produce(self.case, self.repo, '1')
        self.assertEqual((findings, source), ([], 'markdown'))

    def test_parsed_markdown_findings_are_a_valid_review(self):
        self.stub(is_error=False, result='### REQUIRED\n- [CODE-1] [feed.py:1] wrong\n')
        findings, _, _ = rev.produce(self.case, self.repo, '1')
        self.assertEqual(findings, [('feed.py', 1, 'REQUIRED')])

    def test_errored_case_is_reported_and_not_scored(self):
        fixtures = Path(self.tmp.name) / 'fixtures'
        (fixtures / 'quiet').mkdir(parents=True)
        (fixtures / 'quiet' / 'case.json').write_text(json.dumps({'name': 'quiet', **self.case}))
        saved_fixtures, rev.FIXTURES = rev.FIXTURES, fixtures
        self.addCleanup(setattr, rev, 'FIXTURES', saved_fixtures)
        out = Path(self.tmp.name) / 'out'
        self.stub(is_error=True, result='REVIEW BLOCKED')
        rc = rev.main(['--fixture', 'quiet', '--repo', str(self.repo), '--output', str(out)])
        saved = json.loads((out / 'results.json').read_text())
        self.assertEqual(saved['results'], {})
        self.assertIn('error', saved['detail']['quiet'])
        self.assertEqual(rc, 1)


if __name__ == '__main__':
    unittest.main(verbosity=1)
