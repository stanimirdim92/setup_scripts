#!/usr/bin/env python3
"""Fixture tests for review-noise.py: endings per reviewer, noise as refuted over
judged findings, `answered` counted apart, verification verdicts, review rounds,
repeated classes."""
import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

SCRIPT = (Path(__file__).resolve().parents[2] / 'claude' / 'skills' / 'code-review-and-quality'
          / 'scripts' / 'review-noise.py')
spec = importlib.util.spec_from_file_location('rn', SCRIPT)
rn = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rn)

def sarif(*runs):
    return json.dumps({'version': '2.1.0', 'runs': [
        {'tool': {'driver': {'name': name}},
         'results': [{'ruleId': f'X-{i}', 'message': {'text': props.pop('text', '')}, 'properties': props}
                     for i, props in enumerate(results)]}
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

    def test_answered_is_neither_found_nor_noise(self):
        # LD-507: a question the spec already answers is not a false positive.
        (self.dir / 'AB-3-1a2b3c4.sarif').write_text(sarif(
            ('blind-reviewer', [{'disposition': 'ADVISORY', 'resolution': 'answered'} for _ in range(3)])))
        t = rn.tally(sorted(self.dir.glob('*.sarif')))
        blind = t['reviewers']['blind-reviewer']
        self.assertEqual((blind['total'], blind['answered'], blind['refuted'], blind['open']), (4, 3, 1, 0))
        self.assertEqual(t['dispositions'][('ADVISORY', 'answered')], 3)
        self.assertRegex(rn.report(t), r'blind-reviewer\s+4 .*100%')   # 1 refuted of 1 judged

    def test_cli_ticket_filter_and_empty_dir(self):
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(rn.main(['--dir', str(self.dir), '--ticket', 'AB-2', '--json']), 0)
        self.assertEqual(json.loads(out.getvalue())['rounds'], {'AB-2': 1})
        with tempfile.TemporaryDirectory() as empty, redirect_stderr(io.StringIO()):
            self.assertEqual(rn.main(['--dir', empty]), 1)


class RepeatedClasses(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        scope = {'class': 'missing-tenant-scope', 'resolution': 'fixed', 'text': 'query skips integration scope'}
        noise = {'class': 'Magic-Number', 'resolution': 'refuted'}
        for i, sha in enumerate(('a1b2c3d', 'b2c3d4e', 'c3d4e5f')):
            (self.dir / f'LD-{i}-{sha}.sarif').write_text(sarif(('code-reviewer', [dict(scope), dict(noise)])))
        # Five findings of one class on one ticket are one fix round, not a pattern.
        (self.dir / 'LD-9-d4e5f60.sarif').write_text(sarif(
            ('code-reviewer', [{'class': 'n-plus-one', 'resolution': 'fixed'} for _ in range(5)])))

    def tearDown(self):
        self.tmp.cleanup()

    def test_classes_across_tickets_get_an_action(self):
        found = {r['class']: r for r in rn.repeats(rn.tally(sorted(self.dir.glob('*.sarif'))))}
        self.assertEqual(set(found), {'missing-tenant-scope', 'magic-number'})
        self.assertEqual(found['missing-tenant-scope']['action'], 'fix')
        self.assertEqual(found['missing-tenant-scope']['tickets'], ['LD-0', 'LD-1', 'LD-2'])
        self.assertEqual(found['missing-tenant-scope']['example'], 'query skips integration scope')
        self.assertEqual(found['magic-number']['action'], 'silence')

    def test_open_findings_are_watched_and_threshold_is_adjustable(self):
        t = rn.tally(sorted(self.dir.glob('*.sarif')))
        self.assertEqual(rn.repeats(t, min_tickets=4), [])
        t['classes']['open-one'] = {'A': [('open', '')], 'B': [('open', '')], 'C': [('open', '')]}
        self.assertEqual([r['action'] for r in rn.repeats(t) if r['class'] == 'open-one'], ['watch'])
        t['classes']['spec-said'] = {'A': [('answered', '')], 'B': [('answered', '')], 'C': [('refuted', '')]}
        t['classes']['mostly-real'] = {'A': [('answered', '')], 'B': [('answered', '')],
                                       'C': [('fixed', ''), ('fixed', ''), ('refuted', '')]}
        actions = {r['class']: r['action'] for r in rn.repeats(t)}
        self.assertEqual((actions['spec-said'], actions['mostly-real']), ('silence', 'fix'))

    def test_cli_classes_and_repeats(self):
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(rn.main(['--dir', str(self.dir), '--classes']), 0)
        self.assertIn('n-plus-one  (1 ticket(s))', out.getvalue())
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(rn.main(['--dir', str(self.dir), '--repeats']), 0)
        self.assertIn('missing-tenant-scope  — 3 tickets', out.getvalue())
        self.assertIn('lint rule', out.getvalue())
        self.assertNotIn('n-plus-one', out.getvalue())

if __name__ == '__main__':
    unittest.main()
