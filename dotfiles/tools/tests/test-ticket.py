#!/usr/bin/env python3
"""Fixture tests for dotfiles/tools/run/ticket.py (ADR 0115).

`claude`, Slack and pipeline.py are stubbed; git and the files are real. These
test the runner's decisions: High-risk questions wait for the owner, defaults
are reported, only the owner's reply naming the ticket approves the spec, a
clean plan goes on by itself, anything else stops, and nothing is pushed."""
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
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
        self.posts, self.thread, self.raw = [], {}, {}

    def post(self, text, thread=None):
        ts = f'{len(self.posts) + 1}.0'
        self.posts.append((ts, text, thread))
        return ts

    def replies(self, ts):
        return self.thread.get(ts, [])

    def owner_replies(self, ts):
        return self.raw.get(ts, [])

    def say(self, ts, text):
        """The owner writes in a thread, word for word."""
        self.raw.setdefault(ts, []).append({'author': 'Owner <o@x.io>', 'text': text, 'ts': f'n{len(self.posts)}-{text}'})

    def reply(self, text):
        """The owner answers the newest top-level message."""
        ts = [p[0] for p in self.posts if p[2] is None][-1]
        self.thread.setdefault(ts, []).append({'author': 'Owner <o@x.io>', 'text': tk.answers_part('TICKET ANSWERS: ' + text),
                                               'ts': f'r{len(self.posts)}'})


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

    def pipeline(self, ticket, budget, step=None):
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
        self.assertIn(':red_circle: *1. Soft-deleted advertisers in the export*  _High_', ask)
        self.assertIn('*A* :star:  never (recommended)', ask)
        self.assertIn('`TICKET ANSWERS: 1A ok`', ask)
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
        self.assertIn(':clipboard: *AB-11 · Spec ready to approve*', self.out.posts[-1][1])
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
        self.plan_text = PLAN + '\n## SPEC CONFLICT\nREQ-001 cannot be met\n## Tasks\n'
        self.run_once()
        self.out.reply(f'1A {T}')
        self.assertEqual(self.run_once(), tk.WAITING)               # back to /spec, then the owner
        self.assertEqual(sum('unattended' in p for p in self.prompts), 2)
        self.assertEqual(self.header(f'docs/specs/{T}-SPEC.md', 'Status'), 'Draft')
        self.assertIn('Back to spec', ''.join(p[1] for p in self.out.posts))
        self.assertIn('REQ-001 cannot be met', ''.join(p[1] for p in self.out.posts))
        self.assertNotIn('## Tasks', ''.join(p[1] for p in self.out.posts))
        self.assertNotIn('pipeline.py', self.prompts)
        self.assertTrue(self.clean())
        self.plan_text = PLAN                                        # the revised spec plans cleanly
        self.out.reply(f'1A {T}')
        self.assertEqual(self.run_once(), tk.DONE)

    def test_committed_plan_conflict_skips_plan(self):
        self.plan_text = PLAN + '\n## SPEC CONFLICT\nREQ-001 cannot be met\n'
        self.run_once()
        self.out.reply(f'1A {T}')
        with unittest.mock.patch.object(tk.Run, 'back_to_spec', return_value=tk.STOPPED):
            self.run_once()                                          # /plan writes the conflict
            Path(f'docs/tasks/{T}-plan.md').write_text(self.plan_text)
            subprocess.run(['git', 'add', '-A'], check=True)
            subprocess.run(['git', 'commit', '-qm', 'plan with a conflict'], check=True)
            plans = self.prompts.count(f'/plan {T}')
            self.run_once()
        self.assertEqual(self.prompts.count(f'/plan {T}'), plans)   # reused, not planned again

    def test_repeated_plan_conflict_stops(self):
        self.plan_text = PLAN + '\n## SPEC CONFLICT\nREQ-001 cannot be met\n'
        self.run_once()
        for _ in range(2):
            self.out.reply(f'1A {T}')
            self.assertEqual(self.run_once(), tk.WAITING)
        self.out.reply(f'1A {T}')
        self.assertEqual(self.run_once(), tk.STOPPED)
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

    def test_intake_that_writes_nothing_stops_before_spec(self):
        real = self.claude
        self.claude = lambda prompt: (self.prompts.append(prompt.split()[0]), (None, "I couldn't fetch the ticket."))[1] \
            if prompt.startswith('/jira-ticket') else real(prompt)
        self.assertEqual(self.run_once(), tk.STOPPED)
        self.assertEqual(self.prompts, ['/jira-ticket'])
        self.assertIn("couldn't fetch", self.out.posts[-1][1])

    def test_read_tools_never_write(self):
        self.assertIn('mcp__jira__getJiraIssue', tk.READ_TOOLS)
        self.assertIn('mcp__claude_ai_Atlassian_MCP__getAccessibleAtlassianResources', tk.READ_TOOLS)
        for name in tk.READ_TOOLS:
            if name.endswith('__create_session'):     # Figma: opens a read session, writes nothing
                continue
            self.assertNotRegex(name, r'(?i)create|edit|update|transition|add|delete|write|destructive', name)

    def test_pipeline_failure_stops_before_ship(self):
        self.pipeline_rc = 1
        self.run_once()
        self.out.reply(f'1A {T}')
        self.assertEqual(self.run_once(), tk.STOPPED)
        self.assertNotIn(f'/ship {T}', self.prompts)

    def test_spec_changed_after_plan_plans_again(self):
        self.run_once()
        self.out.reply(f'1A {T}')
        self.assertEqual(self.run_once(), tk.DONE)
        self.assertFalse(tk.Run(T, self.out, self.claude, self.pipeline, 5).plan_stale())
        spec = Path(f'docs/specs/{T}-SPEC.md')
        spec.write_text(spec.read_text() + '\nOne more scenario.\n')
        subprocess.run(['git', 'commit', '-qam', 'spec edit'], check=True)
        with redirect_stdout(io.StringIO()):
            self.assertTrue(tk.Run(T, self.out, self.claude, self.pipeline, 5).plan_stale())

    def test_default_branch_moves_into_ticket_worktree(self):
        subprocess.run(['git', 'checkout', '-q', 'main'], check=True)
        path = tk.ticket_checkout(T)
        self.assertEqual(path, self.repo / '.claude' / 'worktrees' / T)
        self.assertEqual(Path(os.getcwd()).resolve(), path.resolve())
        self.assertEqual(subprocess.run(['git', 'branch', '--show-current'], capture_output=True, text=True)
                         .stdout.strip(), f'worktree-{T}')
        self.assertEqual(tk.ticket_checkout(T), None)             # already in it
        os.chdir(self.repo)
        self.assertEqual(tk.ticket_checkout(T), path)             # reused

    def test_chatty_out_reports_each_stage_in_one_thread(self):
        self.out.chatty = True
        self.run_once()
        top = [p for p in self.out.posts if p[2] is None]
        self.assertTrue(top[0][1].startswith(f':arrow_forward: *{T} · Run*'))
        replies = [p[1] for p in self.out.posts if p[2] == top[0][0]]
        self.assertTrue(replies[0].startswith(f':white_check_mark: */jira-ticket {T}* · 0m'))
        self.assertIn('\ndone', replies[0])
        self.assertTrue(top[-1][1].startswith(':question:'))         # the ask stays top-level

    def test_pipeline_step_posts_the_stage_file(self):
        self.out.chatty = True
        r = tk.Run(T, self.out, self.claude, self.pipeline, 5)
        (r.dir / f'{T}-1-BUILD.md').write_text('BUILD COMPLETE: LD\n\nT001 done\n')
        r.pipeline_step(f'/build {T}', '1.20')
        self.assertIn(f':hammer_and_wrench: */build {T}* · $1.20\nBUILD COMPLETE: LD\nT001 done', self.out.posts[-1][1])

    def test_ticket_stop_and_note_in_the_run_thread(self):
        self.out.chatty = True
        r = tk.Run(T, self.out, self.claude, self.pipeline, 5)
        r.progress('started')
        self.out.say(r.thread, 'TICKET NOTE: use the Select component')
        with redirect_stdout(io.StringIO()):
            r.stage('/note-check AB-11')
        self.assertIn('TICKET NOTE read', self.out.posts[-2][1])
        self.out.say(r.thread, 'PO says hi')                                # conversation: ignored
        self.assertEqual(r.check_inbox(), (False, ''))
        self.out.say(r.thread, 'ticket stop')
        with redirect_stdout(io.StringIO()):
            self.assertEqual(r.stage('/note-check AB-11'), ('stopped by the owner (TICKET STOP)', ''))

    def test_note_in_the_question_thread_counts(self):
        self.out.chatty = True
        self.run_once()
        r = tk.Run(T, self.out, self.claude, self.pipeline, 5)
        self.out.say(r.state['ask']['ts'], 'TICKET NOTE: send min and max')
        self.assertEqual(r.check_inbox(), (False, 'send min and max'))

    def test_pipeline_step_hands_the_owner_word_to_pipeline(self):
        self.out.chatty = True
        r = tk.Run(T, self.out, self.claude, self.pipeline, 5)
        r.progress('started')
        self.out.say(r.thread, 'TICKET STOP')
        r.pipeline_step(f'/build {T}', '1.00')
        self.assertEqual(json.loads((r.dir / f'{T}-inbox.json').read_text()),
                         {'after_step': 1, 'stop': True, 'notes': []})

    def test_until_plan_pauses_before_build(self):
        self.run_once()
        self.out.reply(f'1A {T}')
        with redirect_stdout(io.StringIO()):
            self.assertEqual(tk.Run(T, self.out, self.claude, self.pipeline, 5, 'plan').go(), tk.PAUSED)
        self.assertNotIn('pipeline.py', self.prompts)
        self.assertEqual(self.header(f'docs/tasks/{T}-plan.md', 'Status'), 'Approved')
        self.assertIn('Paused after /plan', self.out.posts[-1][1])
        self.assertEqual(self.run_once(), tk.DONE)                           # without --until it goes on

    def test_new_worktree_gets_worktreeinclude_files(self):
        subprocess.run(['git', 'checkout', '-q', 'main'], check=True)
        Path('.gitignore').write_text('.env\nvendor/\nsecret.txt\n')
        Path('.worktreeinclude').write_text('.env\nvendor\nnot-ignored.txt\n')
        Path('not-ignored.txt').write_text('x')
        subprocess.run(['git', 'add', '.gitignore', '.worktreeinclude'], check=True)
        subprocess.run(['git', 'commit', '-qm', 'ignore'], check=True)
        Path('.env').write_text('APP_KEY=1\n')
        Path('vendor/pkg').mkdir(parents=True)
        Path('vendor/pkg/a.php').write_text('<?php\n')
        Path('secret.txt').write_text('no')
        with redirect_stdout(io.StringIO()):
            path = tk.ticket_checkout(T)
        self.assertEqual((path / '.env').read_text(), 'APP_KEY=1\n')
        self.assertTrue((path / 'vendor/pkg/a.php').exists())
        self.assertFalse((path / 'secret.txt').exists())             # ignored, but not in .worktreeinclude
        self.assertFalse((path / 'not-ignored.txt').exists())        # listed, but not ignored

    def test_pipeline_stop_reason_is_posted(self):
        self.pipeline_rc = 1
        self.run_once()
        self.out.reply(f'1A {T}')
        handoff = Path(subprocess.run(['git', 'rev-parse', '--git-common-dir'], capture_output=True,
                                      text=True).stdout.strip()) / 'handoff'
        handoff.mkdir(exist_ok=True)
        (handoff / f'{T}-1-BUILD.md').write_text('BUILD BLOCKED: T002 needs a migration\n\nmore\n')
        (handoff / f'{T}-pipeline-stop.json').write_text(
            '{"why": "BUILD BLOCKED: T002 needs a migration", "stage_file": "%s-1-BUILD.md"}' % T)
        self.assertEqual(self.run_once(), tk.STOPPED)
        post = self.out.posts[-1][1]
        self.assertIn('*Why:* pipeline.py: BUILD BLOCKED: T002 needs a migration', post)
        self.assertIn(f'*{T}-1-BUILD.md:*\n```\nBUILD BLOCKED: T002 needs a migration\nmore\n```', post)

    def test_question_in_reply_is_answered(self):
        self.run_once()
        self.out.reply('why is DEC-001 a default?')
        self.assertEqual(self.run_once(), tk.WAITING)
        self.assertTrue(any(p.startswith(f'The owner of {T} asks') for p in self.prompts))
        self.assertIn(':speech_balloon: *Answer*\ndone', [p[1] for p in self.out.posts if p[2]])


class Parsing(unittest.TestCase):
    def test_set_header_adds_a_missing_line(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 's.md'
            p.write_text('# Spec\n\nStatus: Approved\nTicket: AB-11\n')
            tk.set_header(p, {'Status': 'Draft', 'Approved by': '—', 'Approved at': '—'})
            self.assertEqual(p.read_text(), '# Spec\n\nStatus: Draft\nApproved by: —\nApproved at: —\nTicket: AB-11\n')

    def test_conflict_only_from_a_heading_or_the_handoff(self):
        self.assertFalse(tk.has_conflict('# Plan\nStatus: Draft\n\nResolves the earlier REQ-004 SPEC CONFLICT (DEC-008).\n'))
        self.assertTrue(tk.has_conflict('# Plan\n\n## SPEC CONFLICT\nREQ-1\n'))
        self.assertTrue(tk.has_conflict('# Plan\nHandoff: Blocked — SPEC CONFLICT (REQ-004)\n'))

    def test_reply(self):
        self.assertEqual(tk.parse_reply('1A 2b, approve AB-11', 'AB-11'), ({1: 'A', 2: 'B'}, True, False))
        self.assertEqual(tk.parse_reply('AB11', 'AB-11'), ({}, True, False))
        self.assertEqual(tk.parse_reply('1A AB-110', 'AB-11')[1], False)
        self.assertEqual(tk.parse_reply('defaults', 'AB-11'), ({}, False, True))
        self.assertEqual(tk.parse_reply('1B1 Q2=b, AB-11', 'AB-11'), ({1: 'B1', 2: 'B'}, True, False))
        for word in ('go', 'OK', 'approved', '1A approve'):
            self.assertTrue(tk.parse_reply(word, 'AB-11')[1], word)
        self.assertFalse(tk.parse_reply('1A good', 'AB-11')[1])

    def test_options_with_reason_and_digit(self):
        qs = tk.open_questions('OPEN QUESTION: Q1 — detected\n\n'
                               '- Option B1 (recommended — owner chose it): live profile.\n'
                               '- Option A: a URL.\n- Risk: High\n')
        self.assertEqual(qs[0]['options'], {'B1': '(recommended — owner chose it): live profile.', 'A': 'a URL.'})
        self.assertEqual((qs[0]['recommended'], qs[0]['risk']), ('B1', 'High'))

    def test_owner_filter(self):
        slack = tk.Slack(lambda p: (None, '[{"author": "Owner <o@x.io>", "text": "*TICKET ANSWERS:* 1A", "ts": "1"},'
                                         ' {"author": "Owner <o@x.io>", "text": "PO, is 1A ok? go", "ts": "2"},'
                                         ' {"author": "Other <z@x.io>", "text": "TICKET ANSWERS: 2B", "ts": "3"}]'),
                         'C1', 'o@x.io')
        self.assertEqual([r['text'].strip() for r in slack.replies('9.9')], ['1A'])

    def test_owner_by_slack_id_when_no_email(self):
        slack = tk.Slack(lambda p: (None, '[{"author": "Stanimir (U123)", "text": "TICKET NOTE: x", "ts": "1"},'
                                         ' {"author": "Other (U999)", "text": "TICKET STOP", "ts": "2"}]'),
                         'C1', 'o@x.io', 'U123')
        self.assertEqual([r['ts'] for r in slack.owner_replies('9.9')], ['1'])

    def test_mention(self):
        sent = []
        slack = tk.Slack(lambda p: (sent.append(p), (None, '{"ts": "1.5"}'))[1], 'C1', 'o@x.io', 'U123')
        self.assertEqual(slack.post('AB-11 waits'), '1.5')
        self.assertIn('---\n<@U123> AB-11 waits', sent[0])
        slack.post('progress', thread='1.5')
        self.assertIn('---\nprogress', sent[1])                    # thread replies do not notify

    def test_ticket_key_from_url(self):
        self.assertEqual(tk.ticket_key('https://smartico1.atlassian.net/browse/LD-503'), 'LD-503')
        self.assertEqual(tk.ticket_key('LD-503'), 'LD-503')
        self.assertEqual(tk.ticket_key('https://x.atlassian.net/browse/AB2-7?focusedCommentId=1'), 'AB2-7')
        self.assertIsNone(tk.ticket_key('https://example.com/nothing'))

    def test_no_push(self):
        self.assertNotIn("'push'", SCRIPT.read_text())


if __name__ == '__main__':
    unittest.main()
