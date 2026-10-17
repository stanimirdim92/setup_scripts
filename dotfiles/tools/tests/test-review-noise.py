#!/usr/bin/env python3
"""Fixture tests for dotfiles/tools/run/review-noise.py: endings per reviewer,
noise as refuted over closed findings, verification verdicts, review rounds."""
import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'run' / 'review-noise.py'
spec = importlib.util.spec_from_file_location('rn', SCRIPT)
rn = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rn)


def sarif(*runs):
    return json.dumps({'version': '2.1.0', 'runs': [
        {'tool': {'driver': {'name': name}},
         'results': [{'ruleId': f'X-{i}', 'properties': props} for i, props in enumerate(results)]}
        for name, results in runs]})


class ReviewNoise(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        (self.dir / 'AB-1-abc1234.sarif').write_text(sarif(
            ('code-reviewer', [{'disposition': 'BLOCKER', 'resolution': 'fixed', 'verification': 'CONFIRMED'},
                               {'disposition': 'REQUIRED', 'resolution': 'refuted'}]),
            ('blind-reviewer', [{'disposition': 'BLOCKER', 'resolution': 'refuted', 'verification': 'REFUTED'}])))
        (self.dir / 'AB-1-def5678.sarif').write_text(sarif(
            ('code-reviewer', [{'disposition': 'ADVISORY', 'resolution': 'declined'},
                               {'disposition': 'REQUIRED'}])))
        (self.dir / 'AB-2-0a1b2c3.sarif').write_text(sarif(('code-reviewer', [])))

    def tearDown(self):
        self.tmp.cleanup()

    def test_endings_and_rounds(self):
        t = rn.tally(sorted(self.dir.glob('*.sarif')))
        code = t['reviewers']['code-reviewer']
        self.assertEqual((code['total'], code['fixed'], code['refuted'], code['declined'], code['open']), (4, 1, 1, 1, 1))
        self.assertEqual(t['rounds'], {'AB-1': 2, 'AB-2': 1})
        self.assertEqual(t['verification'][('REFUTED', 'refuted')], 1)

    def test_report_shows_noise_over_closed_findings(self):
        out = rn.report(rn.tally(sorted(self.dir.glob('*.sarif'))))
        self.assertRegex(out, r'code-reviewer\s+4 .*33%')     # 1 refuted of 3 closed
        self.assertRegex(out, r'blind-reviewer\s+1 .*100%')
        self.assertIn('more than one: AB-1 (2)', out)

    def test_cli_ticket_filter_and_empty_dir(self):
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(rn.main(['--dir', str(self.dir), '--ticket', 'AB-2', '--json']), 0)
        self.assertEqual(json.loads(out.getvalue())['rounds'], {'AB-2': 1})
        with tempfile.TemporaryDirectory() as empty, redirect_stderr(io.StringIO()):
            self.assertEqual(rn.main(['--dir', empty]), 1)


if __name__ == '__main__':
    unittest.main(verbosity=1)
