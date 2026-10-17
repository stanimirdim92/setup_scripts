#!/usr/bin/env python3
"""Tests for review-eval: a case built from a real bugfix history, and judging.

History: A adds feed.py; B introduces the bug on line 3; C edits another file;
F fixes line 3. The case must name B and the line B wrote, and a finding there
must count as caught. Producing drives the model and is not tested here."""
import importlib.util
import json
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


if __name__ == '__main__':
    unittest.main(verbosity=1)
