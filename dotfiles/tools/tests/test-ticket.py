#!/usr/bin/env python3
"""Fixture tests for dotfiles/tools/run/ticket.py (ADR 0115).

`claude`, Slack and pipeline.py are stubbed; git and the files are real. These
test the runner's decisions: High-risk questions wait for the owner, defaults
are reported, only the owner's reply naming the ticket approves the spec, a
clean plan goes on by itself, anything else stops, and nothing is pushed."""
import importlib.util
import io
import os
import re
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'run' / 'ticket.py'
spec = importlib.util.spec_from_file_location('ticket', SCRIPT)
tk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tk)

T = 'AB-11'
DRAFT = '''# Spec: Export advertisers

Status: Draft
Approved by: —
Approved at: —

### Requirement: REQ-001 — Export
Source: ticket

## Material Decisions

### DEC-001 — Retries before failed
- Chosen: 3. Lost: 5.
Decided by: default (unattended, ADR 0115)

OPEN QUESTION: Soft-deleted advertisers in the export
- Option A: never (recommended)
- Option B: behind a filter
Risk: High
→ Decision needed before this spec can be approved.
'''
PLAN = '''# Implementation Plan: Export

Status: Draft
Spec: docs/specs/AB-11-SPEC.md
Approved by: —
Approved at: —

Handoff: Awaiting plan approval
'''


class FakeOut:
    def __init__(self):
        self.posts, self.thread = [], {}

    def post(self, text, thread=None):
        ts = f'{len(self.posts) + 1}.0'
        self.posts.append((ts, text, thread))
        return ts

    def replies(self, ts):
        return self.thread.get(ts, [])

    def reply(self, text):
        """The owner answers the newest top-level message."""
        ts = [p[0] for p in self.posts if p[2] is None][-1]
        self.thread.setdefault(ts, []).append({'author': 'Owner <o@x.io>', 'text': text, 'ts': f'r{len(self.posts)}'})


class Ticket(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.repo = root / 'repo'
        g = ['git', '-c', 'init.defaultBranch=main']
        subprocess.run(g + ['init', '-q', str(self.repo)], check=True)
        self.cwd = os.getcwd()
        os.chdir(self.repo)
        for k, v in (('user.email', 't@t'), ('user.name', 't')):
            subprocess.run(['git', 'config', k, v], check=True)
        subprocess.run(['git', 'commit', '-q', '--allow-empty', '-m', 'base'], check=True)
        subprocess.run(['git', 'checkout', '-q', '-b', 'feature/AB-11'], check=True)
        check = root / 'check-plan'
        check.write_text("import os, sys\nsys.exit(int(os.environ.get('CHECK_PLAN_RC', '0')))\n")
        check.chmod(0o755)
        self.saved = (tk.CHECK_PLAN, sys.executable)
        tk.CHECK_PLAN = check
        os.environ.pop('CHECK_PLAN_RC', None)
        self.out, self.prompts, self.pipeline_rc, self.plan_text = FakeOut(), [], 0, PLAN

    def tearDown(self):
        tk.CHECK_PLAN = self.saved[0]
        os.chdir(self.cwd)
        self.tmp.cleanup()

    def claude(self, prompt):
        self.prompts.append(prompt.splitlines()[0])
        first = prompt.split()[0]
        spec = Path(f'docs/specs/{T}-SPEC.md')
        if first == '/jira-ticket':
            spec.parent.mkdir(parents=True, exist_ok=True)
            Path(f'docs/specs/{T}-intake.md').write_text('intake\n')
        elif first == '/spec' and 'unattended' in prompt:
            spec.write_text(DRAFT)
        elif first == '/spec' and 'decisions:' in prompt:
            text = spec.read_text()
            text = re.sub(r'\nOPEN QUESTION:.*?→[^\n]*\n', '\n### DEC-002 — Soft-deleted\nDecided by: owner\n',
                          text, flags=re.S)
            spec.write_text(text)
        elif first == '/plan':
            Path('docs/tasks').mkdir(exist_ok=True)
            Path(f'docs/tasks/{T}-plan.md').write_text(self.plan_text)
            Path(f'docs/tasks/{T}-todo.md').write_text('- T001\n')
        elif first == '/ship':
            return None, '**GO** — rollback: revert the merge'
        return None, 'done'

    def pipeline(self, ticket, budget):
        self.prompts.append('pipeline.py')
        common = subprocess.run(['git', 'rev-parse', '--git-common-dir'], capture_output=True, text=True).stdout
        (Path(common.strip()) / 'handoff' / f'{T}-3-REVIEW.md').write_text('**Findings: 0 BLOCKER · 0 REQUIRED**\n')
        return self.pipeline_rc

    def run_once(self):
        with redirect_stdout(io.StringIO()):
            return tk.Run(T, self.out, self.claude, self.pipeline, 5).go()

    def header(self, path, key):
        return tk.header(Path(path).read_text(), key)

    def clean(self):
        return subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True).stdout == ''

    def test_end_to_end_with_one_high_question(self):
        self.assertEqual(self.run_once(), tk.WAITING)
        self.assertEqual(self.prompts, [f'/jira-ticket {T}', f'/spec {T} unattended'])
        ask = self.out.posts[-1][1]
        self.assertIn('1. Soft-deleted advertisers in the export [High]', ask)
        self.assertIn('A) never (recommended)', ask)
        self.assertIn('DEC-001 — Retries before failed', ask)       # the default taken is reported
        self.assertTrue(self.clean())                                # the draft is committed

        self.assertEqual(self.run_once(), tk.WAITING)                # no reply: nothing new
        self.assertEqual(len(self.out.posts), 1)

        self.out.reply(f'1A {T.replace("-", "")}')                  # "1A AB11", as the owner writes it
        self.assertEqual(self.run_once(), tk.DONE)
        self.assertIn('Q1=Option A: never (recommended)', [p for p in self.prompts if 'decisions:' in p][0])
        self.assertEqual(self.header(f'docs/specs/{T}-SPEC.md', 'Status'), 'Approved')
        self.assertIn('reply in thread 1.0', self.header(f'docs/specs/{T}-SPEC.md', 'Approved by'))
        self.assertEqual(self.header(f'docs/tasks/{T}-plan.md', 'Status'), 'Approved')
        self.assertEqual(self.header(f'docs/tasks/{T}-plan.md', 'Handoff'), 'Ready for /build')
        self.assertEqual(self.prompts[-3:], [f'/plan {T}', 'pipeline.py', f'/ship {T}'])
        self.assertIn('/ship: GO', self.out.posts[-1][1])
        log = subprocess.run(['git', 'log', '--format=%B'], capture_output=True, text=True).stdout
        self.assertIn(f'Refs: {T}', log)
        self.assertTrue(self.clean())

        before = list(self.prompts)
        self.assertEqual(self.run_once(), tk.DONE)                   # a rerun ships nothing twice
        self.assertEqual(self.prompts, before)

    def test_approval_waits_while_a_question_is_open(self):
        self.run_once()
        self.out.reply(f'approve {T}')
        self.assertEqual(self.run_once(), tk.WAITING)
        self.assertIn('Still open: Q1', [p[1] for p in self.out.posts if p[2]][0])
        self.assertEqual(self.header(f'docs/specs/{T}-SPEC.md', 'Status'), 'Draft')

    def test_answer_without_approval_asks_again(self):
        self.run_once()
        self.out.reply('1B')
        self.assertEqual(self.run_once(), tk.WAITING)
        self.assertIn(f'Nothing open. Reply "{T}" to approve', self.out.posts[-1][1])
        self.out.reply(T)
        self.assertEqual(self.run_once(), tk.DONE)

    def test_unknown_answer_changes_nothing(self):
        self.run_once()
        self.out.reply('3C')
        self.assertEqual(self.run_once(), tk.WAITING)
        self.assertIn('Not a question and option here: 3C', self.out.posts[-1][1])
        self.assertFalse(any('decisions:' in p for p in self.prompts))

    def test_another_ticket_id_does_not_approve(self):
        self.run_once()
        self.out.reply('1A AB-110 AB-1')
        self.assertEqual(self.run_once(), tk.WAITING)
        self.assertEqual(self.header(f'docs/specs/{T}-SPEC.md', 'Status'), 'Draft')

    def test_plan_with_a_conflict_stops_unapproved(self):
        self.plan_text = PLAN + '\n## SPEC CONFLICT\nREQ-001 cannot be met\n'
        self.run_once()
        self.out.reply(f'1A {T}')
        self.assertEqual(self.run_once(), tk.STOPPED)
        self.assertEqual(self.header(f'docs/tasks/{T}-plan.md', 'Status'), 'Draft')
        self.assertNotIn('pipeline.py', self.prompts)

    def test_failing_check_plan_stops(self):
        os.environ['CHECK_PLAN_RC'] = '1'
        self.run_once()
        self.out.reply(f'1A {T}')
        self.assertEqual(self.run_once(), tk.STOPPED)
        self.assertIn('check-plan failed', self.out.posts[-1][1])

    def test_dirty_checkout_is_refused_before_anything_runs(self):
        Path('stray.txt').write_text('x')
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(tk.main([f'https://x.atlassian.net/browse/{T}']), tk.NOT_CHECKOUT)
        self.assertIn('stray.txt', out.getvalue())
        self.assertEqual(self.prompts, [])

    def test_pipeline_failure_stops_before_ship(self):
        self.pipeline_rc = 1
        self.run_once()
        self.out.reply(f'1A {T}')
        self.assertEqual(self.run_once(), tk.STOPPED)
        self.assertNotIn(f'/ship {T}', self.prompts)


class Parsing(unittest.TestCase):
    def test_reply(self):
        self.assertEqual(tk.parse_reply('1A 2b, approve AB-11', 'AB-11'), ({1: 'A', 2: 'B'}, True, False))
        self.assertEqual(tk.parse_reply('AB11', 'AB-11'), ({}, True, False))
        self.assertEqual(tk.parse_reply('1A AB-110', 'AB-11')[1], False)
        self.assertEqual(tk.parse_reply('defaults', 'AB-11'), ({}, False, True))

    def test_owner_filter(self):
        slack = tk.Slack(lambda p: (None, '[{"author": "Owner <o@x.io>", "text": "1A", "ts": "1"},'
                                         ' {"author": "Other <z@x.io>", "text": "2B", "ts": "2"}]'), 'C1', 'o@x.io')
        self.assertEqual([r['text'] for r in slack.replies('9.9')], ['1A'])

    def test_mention(self):
        sent = []
        slack = tk.Slack(lambda p: (sent.append(p), (None, '{"ts": "1.5"}'))[1], 'C1', 'o@x.io', 'U123')
        self.assertEqual(slack.post('AB-11 waits'), '1.5')
        self.assertIn('---\n<@U123> AB-11 waits', sent[0])

    def test_ticket_key_from_url(self):
        self.assertEqual(tk.ticket_key('https://smartico1.atlassian.net/browse/LD-503'), 'LD-503')
        self.assertEqual(tk.ticket_key('LD-503'), 'LD-503')
        self.assertEqual(tk.ticket_key('https://x.atlassian.net/browse/AB2-7?focusedCommentId=1'), 'AB2-7')
        self.assertIsNone(tk.ticket_key('https://example.com/nothing'))

    def test_no_push(self):
        self.assertNotIn("'push'", SCRIPT.read_text())


if __name__ == '__main__':
    unittest.main()
