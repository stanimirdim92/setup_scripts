#!/usr/bin/env python3
"""Fixture tests for ticket-stats.py (ADR 0112, ADR 0113): decisions, open items,
approvals counted from git history, review rounds and finding endings, and the
active time, tokens and cost read from fixture transcripts."""
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
                         '| 2026-10-18 | AB-1 | 2 | 2 | 3 | 2 | 2 fixed, 1 refuted, 1 other | '
                         'no transcript found | no transcript found | no transcript found | 0 |')

    def test_missing_spec(self):
        with redirect_stderr(io.StringIO()):
            self.assertEqual(ts.main(['AB-9', '--review-dir', str(self.reviews)]), 1)
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(ts.main(['AB-1', '--review-dir', str(self.reviews), '--json']), 0)
        self.assertEqual(json.loads(out.getvalue())['approvals'], 3)


def at(minutes):
    return f'2026-10-18T09:{minutes:02d}:00Z' if minutes < 60 else f'2026-10-18T10:{minutes - 60:02d}:00Z'


def prompt(minutes, text):
    return {'type': 'user', 'timestamp': at(minutes), 'message': {'role': 'user', 'content': text}}


def reply(minutes, mid, model='claude-opus-5-5', out=1000, **usage):
    u = {'input_tokens': 1000, 'output_tokens': out, 'cache_read_input_tokens': 0, 'cache_creation_input_tokens': 0}
    u.update(usage)
    return {'type': 'assistant', 'timestamp': at(minutes), 'message': {'id': mid, 'model': model, 'usage': u}}


def tool_result(minutes):
    return {'type': 'user', 'timestamp': at(minutes),
            'message': {'content': [{'type': 'tool_result', 'tool_use_id': 't', 'content': 'ok'}]}}


class Spend(unittest.TestCase):
    """Sessions found by worktree and by prompt, capped gaps, one usage per reply, list prices."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.main = root / 'work' / 'proj'
        self.projects = root / 'projects'
        base = self.projects / ts.slug(self.main)
        tree = self.projects / f'{ts.slug(self.main)}--claude-worktrees-AB-1'
        other = self.projects / ts.slug(root / 'work' / 'proj2')
        for d in (base, tree, other):
            d.mkdir(parents=True)
        self.write(base / 'a.jsonl', [
            prompt(0, '/spec AB-1 please'),                   # first prompt: nothing before it to measure
            reply(1, 'm1'), reply(1, 'm1'),                  # one reply written as two records
            tool_result(2),                                  # not a person
            reply(2, 'm2', cache_read_input_tokens=100000,
                  cache_creation_input_tokens=20000, cache_creation={'ephemeral_1h_input_tokens': 20000}),
            prompt(5, 'looks right'),                        # 3 minutes after the reply
            reply(6, 'm3'),
            {'type': 'user', 'timestamp': at(8), 'message': {'content': '<task-notification>x</task-notification>'}},
            prompt(70, 'approved'),                          # 62-minute gap: capped at 10
            reply(71, 'm4', model='claude-haiku-9'),
        ])
        sub = base / 'a' / 'subagents'
        sub.mkdir(parents=True)
        self.write(sub / 'agent-1.jsonl', [dict(reply(3, 's1', model='claude-sonnet-5-5'), isSidechain=True)])
        self.write(base / 'b.jsonl', [prompt(0, 'start AB-12'), reply(1, 'n1')])
        self.write(tree / 'c.jsonl', [prompt(0, 'build it'), reply(1, 'w1'), prompt(3, 'go on'), reply(4, 'w2')])
        self.write(other / 'd.jsonl', [prompt(0, 'AB-1 in another project'), reply(1, 'x1')])

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def write(path, recs):
        path.write_text(''.join(json.dumps(r) + '\n' for r in recs))

    def test_spend(self):
        sp = ts.spend('AB-1', self.main, self.projects)
        self.assertEqual(sp['sessions'], 2)                  # a.jsonl and the worktree's c.jsonl
        self.assertEqual(sp['prompts'], 5)
        self.assertEqual(sp['active_minutes'], 3 + 10 + 2)
        # opus m1, m3, w1, w2: 1000 in + 1000 out each; m2 adds 100k cache read and 20k 1h writes;
        # the sonnet subagent reply; the haiku reply is unpriced.
        opus = 5 * (1000 * 4 + 1000 * 20) + 100000 * 0.2 + 20000 * 8
        sonnet = 1000 * 2 + 1000 * 10
        self.assertAlmostEqual(sp['cost_usd'], round((opus + sonnet) / 1e6, 2))
        self.assertEqual(sp['tokens'], 7 * 2000 + 120000)
        self.assertEqual((sp['unpriced_tokens'], sp['unpriced_models']), (2000, ['claude-haiku-9']))

    def test_row_and_fast(self):
        s = {'ticket': 'AB-1', 'decisions': 0, 'open_items': 0, 'approvals': 1, 'review_rounds': 1,
             'findings': {'fixed': 0, 'refuted': 0, 'other': 0},
             'spend': ts.spend('AB-1', self.main, self.projects, idle_cap_min=5)}
        self.assertEqual(s['spend']['active_minutes'], 3 + 5 + 2)
        self.assertEqual(ts.row(s, '2026-10-18'),
                         '| 2026-10-18 | AB-1 | 0 | 0 | 1 | 1 | 0 fixed, 0 refuted, 0 other | 10 min, 5 prompts | '
                         '134k in 2 sessions | $0.31 (prices 2026-10-06) + 2k unpriced (claude-haiku-9) | 0 |')
        prices = json.loads(ts.PRICES.read_text())['models']
        u = {'input_tokens': 1000000, 'output_tokens': 0, 'speed': 'fast'}
        self.assertEqual(ts.cost_of('claude-opus-5-5', u, prices), 8.0)
        self.assertIsNone(ts.cost_of('claude-sonnet-5-5', u, prices))


if __name__ == '__main__':
    unittest.main(verbosity=1)
