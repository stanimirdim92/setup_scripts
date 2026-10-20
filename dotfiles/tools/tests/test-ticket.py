#!/usr/bin/env python3
"""Fixture tests for dotfiles/tools/run/ticket.py (ADR 0115).

`claude`, Slack and pipeline.py are stubbed; git and the files are real. These
test the runner's decisions: High-risk questions wait for the owner, defaults
are reported, only the owner's reply naming the ticket approves the spec, a
clean plan goes on by itself, anything else stops, and nothing is pushed."""
import datetime
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

    def post(self, text, thread=None, notify=False):
        ts = f'{len(self.posts) + 1}.0'
        self.posts.append((ts, text, thread))
        self.notified = getattr(self, 'notified', []) + ([ts] if notify else [])
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


class FakeJira:
    """The ticket in Jira: a status to read, and what the run wrote."""
    def __init__(self, status='Selected for Development', category='To Do'):
        self.set(status, category)
        self.moves, self.comments = [], []

    def set(self, status, category):
        self._status = {'status': status, 'category': category}

    def status(self):
        return self._status

    def move(self, statuses):
        self.moves.append(statuses)
        return True

    def comment(self, text):
        self.comments.append(text)
        return True


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
        self.conflict_fix_by_default = False

    def tearDown(self):
        tk.CHECK_PLAN = self.saved[0]
        os.chdir(self.cwd)
        self.tmp.cleanup()

    def claude(self, prompt):
        self.prompts.append(prompt.splitlines()[0])
        if 'decisions:' in prompt:
            self.spec_prompt = prompt
        first = prompt.split()[0]
        spec = Path(f'docs/specs/{T}-SPEC.md')
        if first == '/jira-ticket':
            spec.parent.mkdir(parents=True, exist_ok=True)
            Path(f'docs/specs/{T}-intake.md').write_text('intake\n')
        elif first == '/spec' and 'SPEC CONFLICT' in prompt and self.conflict_fix_by_default:
            text = spec.read_text().replace('Source: ticket', 'Source: ticket; min and max (DEC-009, default)')
            spec.write_text(text.replace('Status: Approved', 'Status: Draft'))
            self.plan_text = PLAN
        elif first == '/spec' and 'unattended' in prompt:
            spec.write_text(DRAFT)
        elif first == '/spec' and 'decisions:' in prompt:
            text = spec.read_text()
            if 'Q1=' in prompt:
                text = re.sub(r'\nOPEN QUESTION:.*?→[^\n]*\n', '\n### DEC-002 — Soft-deleted\nDecided by: owner\n',
                              text, flags=re.S)
            if 'DEC-001' in prompt:
                text = text.replace('- Chosen: 3. Lost: 5.\nDecided by: default (unattended, ADR 0115)',
                                    '- Chosen: 5. Lost: 3 (the default).\nDecided by: owner')
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

    def test_ask_numbers_the_defaults_and_lists_the_owner_decisions(self):
        self.run_once()
        ask = self.out.posts[-1][1]
        self.assertIn(':gear: *Decided by default*  _Low/Medium risk · to change one, reply `D<n>: what you want instead`_', ask)
        self.assertIn('      • *D1*  DEC-001 — Retries before failed', ask)
        self.assertNotIn('Your decisions', ask)
        self.assertIn('`D<n>: …` changes a default; put those last.', ask)
        self.out.reply('D1: 5 retries, the API is flaky')
        self.assertEqual(self.run_once(), tk.WAITING)
        self.assertIn('- DEC-001 — Retries before failed: the owner decides instead of the default: 5 retries, the API is flaky',
                      self.spec_prompt)
        self.assertIn('"Decided by: owner"', self.spec_prompt)
        ask = self.out.posts[-1][1]
        self.assertNotIn('Decided by default', ask)                   # the default is now the owner's decision
        self.assertIn(':bust_in_silhouette: *Your decisions*\n      • DEC-001 — Retries before failed', ask)
        self.assertIn(':red_circle: *1. Soft-deleted', ask)            # the High question is still open
        self.assertEqual(self.header(f'docs/specs/{T}-SPEC.md', 'Status'), 'Draft')

    def test_unknown_default_number_changes_nothing(self):
        self.run_once()
        self.out.reply('D4: something')
        self.assertEqual(self.run_once(), tk.WAITING)
        self.assertIn(':warning: Not a question and option here: D4. Nothing changed.', self.out.posts[-1][1])
        self.assertEqual([p for p in self.prompts if 'decisions:' in p], [])

    def test_answer_change_and_approval_in_one_reply(self):
        self.run_once()
        self.out.reply(f'1A {T} D1: 5 retries')
        self.assertEqual(self.run_once(), tk.DONE)
        self.assertIn('Q1=Option A', self.spec_prompt)
        self.assertIn('5 retries', self.spec_prompt)
        self.assertEqual(self.header(f'docs/specs/{T}-SPEC.md', 'Status'), 'Approved')

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

    def test_conflict_fixed_by_default_keeps_the_approval(self):
        self.conflict_fix_by_default = True
        self.plan_text = PLAN + '\n## SPEC CONFLICT\nREQ-001 needs min and max\n'
        self.run_once()
        self.out.reply(f'1A {T}')
        self.assertEqual(self.run_once(), tk.DONE)                   # no second approval
        self.assertEqual(self.header(f'docs/specs/{T}-SPEC.md', 'Status'), 'Approved')
        self.assertIn('reply in thread', self.header(f'docs/specs/{T}-SPEC.md', 'Approved by'))
        self.assertIn('DEC-009', Path(f'docs/specs/{T}-SPEC.md').read_text())
        self.assertEqual(self.prompts.count(f'/plan {T}'), 2)
        self.assertTrue(self.clean())

    def test_different_conflicts_in_a_row_each_go_to_spec_the_same_one_stops(self):
        r = tk.Run(T, self.out, self.claude, self.pipeline, 5)
        a = 'Decision needed (routes to `/spec`). REQ-008: the EXPLAIN criterion fails as written.'
        b = 'Spec conflict on REQ-001 (goes to `/spec`): 422 vs 200.'
        self.assertTrue(r.may_resolve(a))
        r.state.setdefault('conflict_digests', []).append(tk.conflict_digest(a))
        self.assertTrue(r.may_resolve(b))                                        # another one: progress
        self.assertFalse(r.may_resolve('REQ-008 again, worded differently, same EXPLAIN criterion'))   # the same ids
        r.state['conflict_digests'] += [tk.conflict_digest(f'something about TD-00{i}') for i in range(4)]
        self.assertFalse(r.may_resolve(b))                                       # the sixth stops

    def test_repeated_plan_conflict_stops(self):
        """The same conflict coming back means the fix did not take: the owner looks, not /spec again."""
        self.plan_text = PLAN + '\n## SPEC CONFLICT\nREQ-001 cannot be met\n'
        self.run_once()
        self.out.reply(f'1A {T}')
        self.assertEqual(self.run_once(), tk.WAITING)                  # once: back to /spec, asked again
        self.out.reply(f'1A {T}')
        self.assertEqual(self.run_once(), tk.STOPPED)                  # the same REQ-001 conflict again: stop
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

    def git_worktree(self, ticket):
        """What `claude --worktree` does, for the tests: the worktree on its branch, without the model."""
        self.made.append(ticket)
        path = self.repo / '.claude' / 'worktrees' / ticket
        out = subprocess.run(['git', 'worktree', 'add', '-q', '-b', f'worktree-{ticket}', str(path)],
                             capture_output=True, text=True)
        return out.returncode, out.stderr

    def test_default_branch_moves_into_ticket_worktree_made_by_claude(self):
        subprocess.run(['git', 'checkout', '-q', 'main'], check=True)
        self.made = []
        with redirect_stdout(io.StringIO()) as out:
            path = tk.ticket_checkout(T, self.git_worktree)
        self.assertEqual(self.made, [T])
        self.assertIn(f'claude --worktree {T} makes the worktree', out.getvalue())
        self.assertEqual(path, self.repo / '.claude' / 'worktrees' / T)
        self.assertEqual(Path(os.getcwd()).resolve(), path.resolve())
        self.assertEqual(subprocess.run(['git', 'branch', '--show-current'], capture_output=True, text=True)
                         .stdout.strip(), f'worktree-{T}')
        self.assertEqual(tk.ticket_checkout(T, self.git_worktree), None)     # already in it
        os.chdir(self.repo)
        self.assertEqual(tk.ticket_checkout(T, self.git_worktree), path)     # reused, not made again
        self.assertEqual(self.made, [T])

    def test_worktree_claude_did_not_make_stops(self):
        subprocess.run(['git', 'checkout', '-q', 'main'], check=True)
        with self.assertRaises(RuntimeError) as err:
            tk.ticket_checkout(T, lambda ticket: (1, 'Not logged in'))
        self.assertIn(f'claude --worktree {T} made no', str(err.exception))
        self.assertIn('Not logged in', str(err.exception))

    def test_claude_worktree_command(self):
        sent = []
        real = tk.subprocess.run
        tk.subprocess.run = lambda cmd, **kw: (sent.append(cmd), type('R', (), {'returncode': 0, 'stdout': '{"result":"ok"}', 'stderr': ''})())[1]
        try:
            self.assertEqual(tk.claude_worktree('claude', 'haiku')(T), (0, '{"result":"ok"}'))
        finally:
            tk.subprocess.run = real
        self.assertEqual(sent[0][:5], ['claude', '--worktree', T, '-p', 'Reply with exactly: ok'])
        self.assertIn('haiku', sent[0])

    def test_help_shows_the_whole_docstring(self):
        with redirect_stdout(io.StringIO()) as out, self.assertRaises(SystemExit):
            tk.main(['--help'])
        self.assertIn('ticket.py --watch', out.getvalue())
        self.assertIn('TICKET ANSWERS:', out.getvalue())
        self.assertIn('Exit: 0 the ticket reached', out.getvalue())

    def test_chatty_out_reports_each_stage_in_one_thread(self):
        self.out.chatty = True
        self.run_once()
        top = [p for p in self.out.posts if p[2] is None]
        self.assertEqual(len(top), 1)                                 # one top-level message per ticket
        self.assertTrue(top[0][1].startswith(f':arrow_forward: *{T} · Run*'))
        replies = [p for p in self.out.posts if p[2] == top[0][0]]
        self.assertTrue(replies[0][1].startswith(f':white_check_mark: */jira-ticket {T}* · 0m'))
        self.assertIn('\ndone', replies[0][1])
        self.assertTrue(replies[-1][1].startswith(':question:'))      # the ask is in the thread, with a mention
        self.assertIn(replies[-1][0], self.out.notified)
        self.assertNotIn(replies[0][0], self.out.notified)            # progress does not notify
        self.assertEqual(tk.Run(T, self.out, self.claude, self.pipeline, 5).state['ask']['ts'], top[0][0])

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

    def test_note_under_the_stop_message_counts_next_run(self):
        self.out.chatty = True
        self.pipeline_rc = 1
        self.run_once()
        self.out.reply(f'1A {T}')
        self.assertEqual(self.run_once(), tk.STOPPED)
        stop = [p for p in self.out.posts if 'Stopped' in p[1]][-1]
        r = tk.Run(T, self.out, self.claude, self.pipeline, 5)
        self.assertEqual(stop[2], r.thread)                                   # the stop is in the ticket's thread
        self.assertIn(stop[0], self.out.notified)                             # and it pings you
        self.assertIn('Reply here with `TICKET NOTE:', stop[1])
        self.out.say(r.thread, 'TICKET NOTE: use 200')
        self.assertEqual(r.check_inbox(), (False, 'use 200'))

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

    BUILD_BLOCKED = """# BUILD BLOCKED — AB-11

Frontend tasks are done and merged. Backend T001 is stuck. You need to make two decisions.

## Decisions you need to make

1. **Spec conflict on REQ-001 (goes to `/spec`).** The spec requires HTTP 422 for an invalid value. These routes return **HTTP 200** with an `errors` body instead.
   - **My recommendation:** change REQ-001 to accept the existing 200 response. Every other key already behaves this way.
   - The alternative is to return 422 for the whole request.
2. **Schema snapshot drift.** The committed fingerprint no longer matches the local DB.
   - Should I refresh and commit it on `main`, or on this branch?

## Status per task

| Task | State |
| --- | --- |
| T001 | Blocked. |
"""

    def test_build_conflict_takes_the_spec_routed_blocker_with_its_lines(self):
        conflict = tk.build_conflict(self.BUILD_BLOCKED)
        self.assertTrue(conflict.startswith('1. **Spec conflict on REQ-001 (goes to `/spec`).**'))
        self.assertIn('My recommendation:', conflict)
        self.assertIn('The alternative is to return 422', conflict)
        self.assertNotIn('Schema snapshot drift', conflict)
        self.assertEqual(tk.build_conflict('# BUILD BLOCKED\n\nT002 needs a migration. Route: human decision.\n'), '')
        self.assertEqual(tk.build_conflict('resolves the earlier SPEC CONFLICT; see /spec history'), '')   # no blocker

    BUILD_BLOCKED_WORDED = """## BUILD BLOCKED: AB-11
I did not dispatch any executor. Your Slack note ("use 200 status code") settles the open 422 conflict. It still contradicts the approved spec, so `/build` cannot act on it yet.
**Why it stopped**
- The spec at `docs/specs/AB-11-SPEC.md:128` (REQ-001) says an invalid value MUST get HTTP 422.
- `ValidationFailedOverride` returns HTTP 200 with an `errors` body for non-Inertia requests. Your note picks that behaviour.
- Changing what the API returns is a behaviour change to the spec. `/build` does not edit the spec.
**Task state at HEAD**

| Task | Status | Note |
|---|---|---|
| T001 | Pending | Blocked by the 422 vs 200 conflict |
**Commits:** none.
"""

    def test_build_conflict_reads_the_meaning_not_the_phrase(self):
        conflict = tk.build_conflict(self.BUILD_BLOCKED_WORDED)
        self.assertIn('contradicts the approved spec', conflict)
        self.assertIn('Changing what the API returns is a behaviour change to the spec', conflict)
        self.assertNotIn('| T001 |', conflict)                                  # the table stays out
        self.assertEqual(tk.build_conflict('## BUILD BLOCKED: AB-11\nThe schema snapshot does not match the local DB. '
                                           'Refresh it on main or on this branch?\n'), '')
        self.assertEqual(tk.build_conflict('**BUILD COMPLETE**\nthe spec conflict from before is resolved'), '')

    def test_build_conflict_goes_back_to_spec_then_plans_and_builds_again(self):
        self.conflict_fix_by_default = True
        handoff = Path(subprocess.run(['git', 'rev-parse', '--git-common-dir'], capture_output=True,
                                      text=True).stdout.strip()) / 'handoff'
        handoff.mkdir(exist_ok=True)
        blocked = [True]

        def pipeline(ticket, budget, step=None):
            self.prompts.append('pipeline.py')
            if blocked.pop() if blocked else False:
                (handoff / f'{T}-1-BUILD.md').write_text(self.BUILD_BLOCKED)
                (handoff / f'{T}-pipeline-stop.json').write_text(json.dumps({'why': 'BUILD BLOCKED — AB-11', 'stage_file': f'{T}-1-BUILD.md'}))
                return 1
            (handoff / f'{T}-3-REVIEW.md').write_text('**Findings: 0 BLOCKER · 0 REQUIRED**\n')
            return 0

        self.pipeline = pipeline
        self.run_once()
        self.out.reply(f'1A {T}')
        self.assertEqual(self.run_once(), tk.DONE)
        tail = self.prompts[self.prompts.index('pipeline.py'):]
        self.assertEqual(tail, ['pipeline.py', f'/spec {T} unattended', f'/plan {T}', 'pipeline.py', f'/ship {T}'])
        back = [p[1] for p in self.out.posts if 'Back to spec' in p[1]]
        self.assertEqual(len(back), 1)
        self.assertIn('/build found a conflict', back[0])
        self.assertIn('Spec conflict on REQ-001', back[0])
        self.assertEqual(self.header(f'docs/specs/{T}-SPEC.md', 'Status'), 'Approved')   # the default kept it
        self.assertTrue(self.clean())

    def test_new_run_after_a_build_conflict_goes_to_spec_first(self):
        """The stop file and BUILD report of an earlier run are read before building again."""
        self.conflict_fix_by_default = True
        handoff = Path(subprocess.run(['git', 'rev-parse', '--git-common-dir'], capture_output=True,
                                      text=True).stdout.strip()) / 'handoff'
        handoff.mkdir(exist_ok=True)
        self.run_once()
        self.out.reply(f'1A {T}')
        with redirect_stdout(io.StringIO()):
            tk.Run(T, self.out, self.claude, self.pipeline, 5, 'plan').go()        # approved plan, no build
        (handoff / f'{T}-1-BUILD.md').write_text(self.BUILD_BLOCKED)                  # left by a run that stopped
        (handoff / f'{T}-pipeline-stop.json').write_text(json.dumps({'why': 'BUILD BLOCKED — AB-11', 'stage_file': f'{T}-1-BUILD.md'}))
        self.prompts.clear()
        self.assertEqual(self.run_once(), tk.DONE)
        self.assertEqual(self.prompts, [f'/spec {T} unattended', f'/plan {T}', 'pipeline.py', f'/ship {T}'])
        self.prompts.clear()                                                          # the same conflict is not re-read
        r = tk.Run(T, self.out, self.claude, self.pipeline, 5)
        self.assertFalse(r.may_resolve(tk.build_conflict(self.BUILD_BLOCKED)))
        # a new conflict in a report with the same file name is read (stage numbers restart on a new HEAD)
        (handoff / f'{T}-1-BUILD.md').write_text(self.BUILD_BLOCKED.replace('REQ-001', 'REQ-008').replace('422', 'EXPLAIN'))
        self.assertTrue(r.may_resolve(r.last_build_conflict()[0]))
        # a report older than the spec's last commit is old news
        self.assertTrue(r.last_build_conflict()[0])
        old = __import__('time').time() - 3600
        os.utime(handoff / f'{T}-1-BUILD.md', (old, old))
        self.assertEqual(r.last_build_conflict(), ('', ''))

    def test_owner_word_reaches_the_first_pipeline_stage(self):
        self.out.chatty = True
        self.run_once()
        self.out.reply(f'1A {T}')
        with redirect_stdout(io.StringIO()):
            tk.Run(T, self.out, self.claude, self.pipeline, 5, 'plan').go()        # stopped after the plan
        r = tk.Run(T, self.out, self.claude, self.pipeline, 5)
        self.out.say(r.thread, 'TICKET NOTE: use 200 http status')                   # written while it was stopped
        with redirect_stdout(io.StringIO()):
            self.assertEqual(r.go(), tk.DONE)
        inbox = json.loads((r.dir / f'{T}-inbox.json').read_text())
        self.assertEqual(inbox['notes'], ['use 200 http status'])                      # written before pipeline.py ran
        self.out.say(r.thread, 'TICKET STOP')
        r2 = tk.Run(T, self.out, self.claude, self.pipeline, 5)
        r2.state['pipeline_done'] = False                                               # as if /build were still ahead
        r2.state.pop('ship')
        with redirect_stdout(io.StringIO()):
            self.assertEqual(r2.go(), tk.STOPPED)
        self.assertNotIn('pipeline.py', self.prompts[-1:])

    def test_note_from_the_command_line_goes_to_the_first_stage_once(self):
        r = tk.Run(T, self.out, self.claude, self.pipeline, 5, note='use 200; leave Google Ads alone')
        self.assertEqual(r.check_inbox(), (False, 'use 200; leave Google Ads alone'))
        self.assertEqual(r.check_inbox(), (False, ''))                         # once
        full = []
        real = self.claude
        self.claude = lambda prompt: (full.append(prompt), real(prompt))[1]
        with redirect_stdout(io.StringIO()):
            tk.Run(T, self.out, self.claude, self.pipeline, 5, note='work in English').go()
        self.assertIn('Owner notes from Slack (TICKET NOTE)', full[0])
        self.assertIn('work in English', full[0])
        self.assertNotIn('work in English', full[1])

    def test_watch_hands_its_note_to_each_child(self):
        args = tk.argparse.Namespace(label='harness-run', jobs=2, poll=7, budget=5, wait=8, permission_mode='',
                                     note='be brief')
        cmd = tk.child_command('AB-9', args)
        self.assertEqual(cmd[-2:], ['--note', 'be brief'])
        self.assertIn('AB-9', cmd)
        args.note = ''
        self.assertNotIn('--note', tk.child_command('AB-9', args))

    def test_read_replies_get_a_reaction(self):
        reacted = []
        self.out.chatty = True
        self.out.react = lambda ts, emoji='eyes': reacted.append((ts, emoji))
        self.run_once()
        self.out.reply(f'1A {T}')                                                       # TICKET ANSWERS
        self.run_once()
        self.assertEqual([e for _, e in reacted], ['eyes'])
        r = tk.Run(T, self.out, self.claude, self.pipeline, 5)
        r.progress('started')
        self.out.say(r.thread, 'TICKET NOTE: x')
        self.out.say(r.thread, 'PO says hi')
        r.check_inbox()
        self.assertEqual(len(reacted), 2)                                               # the note, not the talk

    def test_slack_react_prompt(self):
        sent = []
        slack = tk.Slack(lambda p: (sent.append(p), (None, '{"ok": true}'))[1], 'C1', 'o@x.io')
        slack.react('17.5')
        self.assertIn('Add the :eyes: reaction to the message whose ts is 17.5 in the Slack channel C1', sent[0])
        self.assertIn('mcp__Slack__slack_add_reaction', tk.SLACK_TOOLS)

    def test_commit_takes_every_ticket_document(self):
        real = self.claude

        def claude(prompt):
            out = real(prompt)
            if prompt.startswith('/spec'):
                Path('docs/tasks').mkdir(exist_ok=True)
                Path(f'docs/tasks/{T}-open.md').write_text('- open item from /spec\n')   # a file the stage adds
            return out

        self.claude = claude
        self.run_once()
        self.assertTrue(self.clean())
        self.assertIn(f'docs/tasks/{T}-open.md', subprocess.run(['git', 'show', '--name-only', '--format=', 'HEAD'],
                                                                capture_output=True, text=True).stdout)

    def test_pipeline_dying_before_a_stage_does_not_show_an_old_stop(self):
        self.run_once()
        self.out.reply(f'1A {T}')
        handoff = Path(subprocess.run(['git', 'rev-parse', '--git-common-dir'], capture_output=True,
                                      text=True).stdout.strip()) / 'handoff'
        handoff.mkdir(exist_ok=True)
        (handoff / f'{T}-1-BUILD.md').write_text(self.BUILD_BLOCKED)
        (handoff / f'{T}-pipeline-stop.json').write_text(json.dumps({'why': 'BUILD BLOCKED — AB-11', 'stage_file': f'{T}-1-BUILD.md'}))
        old = __import__('time').time() - 60
        os.utime(handoff / f'{T}-pipeline-stop.json', (old, old))
        os.utime(handoff / f'{T}-1-BUILD.md', (old, old))
        self.tmp_state = tk.Run(T, self.out, self.claude, self.pipeline, 5)
        self.tmp_state.state['conflict_seen'] = f'{T}-1-BUILD.md'                        # handled earlier
        self.tmp_state.save()

        def pipeline(ticket, budget, step=None):
            self.prompts.append('pipeline.py')
            pipeline.last = 'pipeline: uncommitted changes in the checkout'
            return 2

        self.pipeline = pipeline
        self.assertEqual(self.run_once(), tk.STOPPED)
        post = self.out.posts[-1][1]
        self.assertIn('*Why:* pipeline.py: exited 2: pipeline: uncommitted changes in the checkout', post)
        self.assertNotIn('BUILD BLOCKED', post)

    def test_pipeline_stop_reason_is_posted(self):
        self.run_once()
        self.out.reply(f'1A {T}')
        handoff = Path(subprocess.run(['git', 'rev-parse', '--git-common-dir'], capture_output=True,
                                      text=True).stdout.strip()) / 'handoff'
        handoff.mkdir(exist_ok=True)

        def pipeline(ticket, budget, step=None):                 # pipeline.py writes both as it stops
            self.prompts.append('pipeline.py')
            (handoff / f'{T}-1-BUILD.md').write_text('BUILD BLOCKED: T002 needs a migration\n\nmore\n')
            (handoff / f'{T}-pipeline-stop.json').write_text(
                '{"why": "BUILD BLOCKED: T002 needs a migration", "stage_file": "%s-1-BUILD.md"}' % T)
            return 1

        self.pipeline = pipeline
        self.assertEqual(self.run_once(), tk.STOPPED)
        post = self.out.posts[-1][1]
        self.assertIn('*Why:* pipeline.py: BUILD BLOCKED: T002 needs a migration', post)
        self.assertIn(f'*{T}-1-BUILD.md:*\n```\nBUILD BLOCKED: T002 needs a migration\nmore\n```', post)

    def test_second_run_is_refused_while_the_first_lives(self):
        handoff = Path(subprocess.run(['git', 'rev-parse', '--git-common-dir'], capture_output=True,
                                      text=True).stdout.strip()) / 'handoff'
        handoff.mkdir(exist_ok=True)
        lock = handoff / f'{T}-ticket.lock'
        lock.write_text(json.dumps({'pid': os.getpid(), 'host': tk.socket.gethostname(), 'started': 'now', 'cwd': '/w'}))
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(tk.main([T]), tk.BUSY)
        self.assertIn(f'{T} is running already: pid {os.getpid()} since now in /w', out.getvalue())
        self.assertEqual(self.prompts, [])
        self.assertTrue(lock.exists())                                # not ours to remove

    def test_a_dead_holder_is_taken_over_and_the_lock_released_after(self):
        handoff = Path(subprocess.run(['git', 'rev-parse', '--git-common-dir'], capture_output=True,
                                      text=True).stdout.strip()) / 'handoff'
        handoff.mkdir(exist_ok=True)
        lock = handoff / f'{T}-ticket.lock'
        gone = subprocess.Popen(['true'])
        gone.wait()
        lock.write_text(json.dumps({'pid': gone.pid, 'host': tk.socket.gethostname(), 'started': 'earlier'}))
        Path('stray.txt').write_text('x')                             # so the run ends right after the lock
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(tk.main([T]), tk.NOT_CHECKOUT)
        self.assertIn(f'taking over the run of pid {gone.pid}', out.getvalue())
        self.assertFalse(lock.exists())

    def test_jira_status_stops_before_the_next_stage(self):
        jira = FakeJira('In Progress', 'In Progress')
        r = lambda: tk.Run(T, self.out, self.claude, self.pipeline, 5, jira=jira)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(r().go(), tk.WAITING)                    # an active status changes nothing
        self.out.reply(f'1A {T}')
        jira.set('Done', 'Done')
        with redirect_stdout(io.StringIO()):
            self.assertEqual(r().go(), tk.STOPPED)
        self.assertIn('stopped by the owner (Jira status Done)', self.out.posts[-1][1])
        self.assertNotIn(f'/plan {T}', self.prompts)
        jira.set('Blocked', 'To Do')                                  # named in HARNESS_JIRA_STOP
        self.assertEqual(r().jira_stop(), 'Blocked')
        jira.set('Waiting for PO', 'To Do')
        self.assertEqual(r().jira_stop(), '')
        os.environ['HARNESS_JIRA_STOP'] = 'Waiting for PO'
        try:
            self.assertEqual(r().jira_stop(), 'Waiting for PO')
            os.environ['HARNESS_JIRA_STOP'] = '0'
            jira.set('Done', 'Done')
            self.assertEqual(r().jira_stop(), '')                    # the check is off
        finally:
            del os.environ['HARNESS_JIRA_STOP']

    def test_jira_mirrors_the_run(self):
        jira = FakeJira()
        run = lambda: tk.Run(T, self.out, self.claude, self.pipeline, 5, jira=jira)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(run().go(), tk.WAITING)
        self.assertEqual(jira.moves, ['In Progress'])                 # once, when the run starts
        self.assertEqual(len(jira.comments), 1)
        ask = jira.comments[0]
        self.assertIn('1. Soft-deleted advertisers in the export  High', ask)
        self.assertIn('A  never (recommended)', ask)
        self.assertNotIn(':red_circle:', ask)
        self.assertNotIn('*', ask)
        self.out.reply(f'1A {T}')
        with redirect_stdout(io.StringIO()):
            self.assertEqual(run().go(), tk.DONE)
        self.assertEqual(jira.moves, ['In Progress', 'Code Review, In Review'])   # GO: to review
        self.assertTrue(jira.comments[-1].startswith('/ship: GO'), jira.comments[-1])
        self.assertIn('Branch: feature/AB-11 · HEAD: ', jira.comments[-1])
        self.assertIn('Nothing is pushed', jira.comments[-1])

    def test_jira_gets_the_stop_and_no_review_move_on_no_go(self):
        jira = FakeJira()
        real = self.claude
        self.claude = lambda prompt: (None, '**NO-GO** — rollback needed') if prompt.startswith('/ship') else real(prompt)
        with redirect_stdout(io.StringIO()):
            tk.Run(T, self.out, self.claude, self.pipeline, 5, jira=jira).go()
        self.out.reply(f'1A {T}')
        with redirect_stdout(io.StringIO()):
            self.assertEqual(tk.Run(T, self.out, self.claude, self.pipeline, 5, jira=jira).go(), tk.DONE)
        self.assertEqual(jira.moves, ['In Progress'])
        self.assertTrue(jira.comments[-1].startswith('/ship: NO-GO'))
        self.pipeline_rc = 1
        jira2 = FakeJira()
        self.out = FakeOut()
        self.tmp2 = None
        r = tk.Run('AB-12', self.out, lambda p: (None, 'x'), self.pipeline, 5, jira=jira2)
        with redirect_stdout(io.StringIO()):
            r.stop('pipeline.py: *VERIFY FAIL*')
        self.assertEqual(jira2.comments, ['ticket.py stopped: pipeline.py: VERIFY FAIL'])

    def test_jira_writes_are_moves_and_comments_only_and_can_be_off(self):
        for name in tk.JIRA_WRITE_TOOLS:
            self.assertRegex(name, r'(?i)transition|comment')
            self.assertNotRegex(name, r'(?i)create|delete|editJiraIssue$|destructive')
        sent = []
        jira = tk.Jira(lambda p, tools: (sent.append((p, tools)), (None, '{"ok": true, "status": "In Progress"}'))[1], T)
        self.assertTrue(jira.move('In Progress'))
        self.assertIn('move the issue AB-11 to the first of these statuses', sent[0][0])
        self.assertTrue(set(tk.JIRA_WRITE_TOOLS) <= set(sent[0][1]))
        self.assertTrue(jira.comment('hello\nworld'))
        self.assertTrue(sent[1][0].endswith('---\nhello\nworld'))
        self.assertEqual(jira.status(), {'ok': True, 'status': 'In Progress'})
        self.assertNotIn(tk.JIRA_WRITE_TOOLS[0], sent[2][1])         # a read uses the read tools only
        off = tk.Jira(lambda p, tools: (sent.append(p), (None, '{"ok": true}'))[1], T, write=False)
        self.assertFalse(off.move('In Progress'))
        self.assertFalse(off.comment('x'))
        self.assertEqual(len(sent), 3)                                 # nothing ran

    def test_plain(self):
        self.assertEqual(tk.plain(':question: *AB-11 · Spec needs 1 answer*\n`docs/x.md` · Draft\n      • *A* :star:  never'),
                         'AB-11 · Spec needs 1 answer\ndocs/x.md · Draft\n      • A  never')
        self.assertEqual(tk.plain('<@U1> _Low/Medium risk · edit the spec_'), 'Low/Medium risk · edit the spec')
        self.assertEqual(tk.plain('followers_min and followers_max'), 'followers_min and followers_max')

    def test_removed_label_stops_a_watched_run(self):
        jira = FakeJira('In Progress', 'In Progress')
        jira._status['labels'] = ['harness-run', 'be']
        r = tk.Run(T, self.out, self.claude, self.pipeline, 5, jira=jira)
        self.assertEqual(r.jira_stop(), '')                           # a run by hand ignores labels
        os.environ['HARNESS_LABEL'] = 'harness-run'
        try:
            self.assertEqual(r.jira_stop(), '')
            jira._status['labels'] = ['be']
            self.assertEqual(r.jira_stop(), 'In Progress, label harness-run removed')
            os.environ['HARNESS_JIRA_STOP'] = '0'                     # the status check off, the label still counts
            self.assertEqual(r.jira_stop(), 'In Progress, label harness-run removed')
        finally:
            del os.environ['HARNESS_LABEL'], os.environ['HARNESS_JIRA_STOP']

    def test_labelled_search(self):
        sent = []
        jira = tk.Jira(lambda p, tools: (sent.append(p), (None, 'Here: ["LD-7", "https://x.atlassian.net/browse/LD-9", 3]'))[1], '')
        self.assertEqual(jira.labelled('harness-run'), ['LD-7', 'LD-9'])
        self.assertIn('labels = "harness-run" AND statusCategory != Done ORDER BY priority ASC, created ASC', sent[0])

    def test_watch_starts_labelled_tickets_up_to_jobs_and_restarts_only_what_may_run_again(self):
        class Proc:
            def __init__(self, key):
                self.key, self.pid, self.returncode = key, 4242, None

            def poll(self):
                return self.returncode

        subprocess.run(['git', 'checkout', '-q', 'main'], check=True)
        polls = [['AB-1', 'AB-2', 'AB-3'], ['AB-1', 'AB-2', 'AB-3'], ['AB-2', 'AB-3'], ['AB-1', 'AB-2', 'AB-3'],
                 ['AB-1', 'AB-2', 'AB-3']]
        started, procs = [], {}

        def start(key):
            started.append(key)
            procs[key] = Proc(key)
            return procs[key]

        rounds = iter(polls)
        after = {1: lambda: setattr(procs['AB-1'], 'returncode', tk.STOPPED),     # after poll 1: AB-1 stopped
                 3: lambda: setattr(procs['AB-2'], 'returncode', tk.DONE),        # after poll 3: AB-2 done
                 4: lambda: setattr(procs['AB-3'], 'returncode', tk.WAITING)}     # after poll 4: AB-3 waits
        slept = []

        def sleep(seconds):                                            # between polls, the children move on
            slept.append(seconds)
            after.get(len(slept), lambda: None)()

        tk.pl.sleep = sleep
        self.addCleanup(setattr, tk.pl, 'sleep', __import__('time').sleep)
        args = tk.argparse.Namespace(label='harness-run', jobs=2, poll=7, budget=5, wait=8, permission_mode='')
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(tk.watch(args, lambda: next(rounds), start, rounds=5), tk.DONE)
        # poll 1: AB-1, AB-2 start (jobs 2). poll 2: AB-1 stopped → held; AB-3 starts. poll 3: label off AB-1.
        # poll 4: AB-2 done; AB-1 is back and may run. poll 5: AB-3 waited → runs again.
        self.assertEqual(started, ['AB-1', 'AB-2', 'AB-3', 'AB-1', 'AB-3'])
        self.assertEqual(slept, [7, 7, 7, 7])
        self.assertIn('AB-1 exited 1: stopped; change the ticket in Jira (label off and on) to run it again', out.getvalue())

    def test_watch_runs_a_stopped_ticket_again_once_it_changed_in_jira(self):
        class Proc:
            pid, returncode = 1, None

            def poll(self):
                return self.returncode

        subprocess.run(['git', 'checkout', '-q', 'main'], check=True)
        started, procs, when = [], {}, [None]

        def start(key):
            started.append(key)
            procs[key] = Proc()
            return procs[key]

        slept = []

        def sleep(seconds):
            slept.append(seconds)
            if len(slept) == 1:
                procs['AB-1'].returncode = tk.STOPPED
            if len(slept) == 2:                                             # the owner takes the label off and on
                when[0] = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=5)

        tk.pl.sleep = sleep
        self.addCleanup(setattr, tk.pl, 'sleep', __import__('time').sleep)
        args = tk.argparse.Namespace(label='harness-run', jobs=2, poll=7, budget=5, wait=8, permission_mode='')
        asked = []
        with redirect_stdout(io.StringIO()) as out:
            tk.watch(args, lambda: ['AB-1'], start, rounds=4, updated=lambda k: (asked.append(k), when[0])[1])
        # poll 1 starts; poll 2 sees it stopped and not yet changed; poll 3 sees the change and starts it again
        self.assertEqual(started, ['AB-1', 'AB-1'])
        self.assertEqual(asked, ['AB-1', 'AB-1'])                           # asked only while it waits
        self.assertIn('AB-1 changed in Jira at', out.getvalue())
        self.assertIn('stopped, waiting for a change AB-1', out.getvalue())

    def test_first_line_sums_up_json(self):
        self.assertEqual(tk.first_line('[\n {"author": "o", "text": "TICKET NOTE: x", "ts": "1"},\n {"author": "o", "text": "hi", "ts": "2"}\n]'),
                         '2 items (replies)')
        self.assertEqual(tk.first_line('[]'), '0 items')
        self.assertEqual(tk.first_line('{"ok": true, "status": "In Progress"}'), 'ok: True, status: In Progress')
        self.assertEqual(tk.first_line('**BUILD COMPLETE**\nmore'), 'BUILD COMPLETE')

    def test_parse_time(self):
        self.assertEqual(tk.parse_time('2026-10-20T12:51:03.000+0300').utcoffset(), datetime.timedelta(hours=3))
        self.assertEqual(tk.parse_time('2026-10-20T09:51:03Z').hour, 9)
        self.assertIsNone(tk.parse_time('yesterday'))
        self.assertIsNotNone(tk.parse_time('2026-10-20T09:51:03').tzinfo)

    def test_watch_skips_a_ticket_held_by_hand_or_shipped(self):
        subprocess.run(['git', 'checkout', '-q', 'main'], check=True)
        handoff = Path(subprocess.run(['git', 'rev-parse', '--git-common-dir'], capture_output=True,
                                      text=True).stdout.strip()) / 'handoff'
        handoff.mkdir(exist_ok=True)
        (handoff / 'AB-5-ticket.lock').write_text(json.dumps({'pid': os.getpid(), 'host': tk.socket.gethostname()}))
        (handoff / 'AB-6-ticket.json').write_text(json.dumps({'ship': 'GO'}))
        started = []
        args = tk.argparse.Namespace(label='harness-run', jobs=2, poll=7, budget=5, wait=8, permission_mode='')
        with redirect_stdout(io.StringIO()):
            tk.watch(args, lambda: ['AB-5', 'AB-6', 'AB-7'], lambda k: (started.append(k), None)[1] or
                     type('P', (), {'pid': 1, 'poll': lambda self: None})(), rounds=1)
        self.assertEqual(started, ['AB-7'])

    def test_watch_refuses_a_ticket_branch(self):
        args = tk.argparse.Namespace(label='harness-run', jobs=2, poll=7, budget=5, wait=8, permission_mode='')
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(tk.watch(args, lambda: [], lambda k: None, rounds=1), tk.NOT_CHECKOUT)
        self.assertIn('--watch runs in the main checkout on main', out.getvalue())

    def test_unreadable_jira_status_does_not_stop(self):
        class Broken(FakeJira):
            def status(self):
                raise RuntimeError('no tool')
        r = tk.Run(T, self.out, self.claude, self.pipeline, 5, jira=Broken())
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(r.check_inbox(), (False, ''))
        self.assertIn('could not read the Jira status: no tool', out.getvalue())

    def test_pipeline_step_takes_pipeline_own_count(self):
        r = tk.Run(T, self.out, self.claude, self.pipeline, 5)
        r.pipeline_step(f'/test {T}', '1.00', '3')                    # pipeline.py went on after a crash
        self.assertEqual(json.loads((r.dir / f'{T}-inbox.json').read_text())['after_step'], 3)
        r.pipeline_step(f'/review {T}', '1.00')
        self.assertEqual(json.loads((r.dir / f'{T}-inbox.json').read_text())['after_step'], 4)

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

    def test_answers_part_takes_the_singular_too(self):
        self.assertEqual(tk.answers_part('TICKET ANSWER: Use 200'), ' Use 200')
        self.assertEqual(tk.answers_part('*TICKET ANSWERS:* 1A ok'), ' 1A ok')
        self.assertIsNone(tk.answers_part('the PO says use 200'))

    def test_reply(self):
        self.assertEqual(tk.parse_reply('1A 2b, approve AB-11', 'AB-11'), ({1: 'A', 2: 'B'}, True, False))
        self.assertEqual(tk.parse_reply('AB11', 'AB-11'), ({}, True, False))
        self.assertEqual(tk.parse_reply('1A AB-110', 'AB-11')[1], False)
        self.assertEqual(tk.parse_reply('defaults', 'AB-11'), ({}, False, True))
        self.assertEqual(tk.parse_reply('1B1 Q2=b, AB-11', 'AB-11'), ({1: 'B1', 2: 'B'}, True, False))
        for word in ('go', 'OK', 'approved', '1A approve'):
            self.assertTrue(tk.parse_reply(word, 'AB-11')[1], word)
        self.assertFalse(tk.parse_reply('1A good', 'AB-11')[1])

    def test_split_redo(self):
        self.assertEqual(tk.split_redo('1A ok D1: 5 retries, D2 = keep both; and log it'),
                         ('1A ok ', {1: '5 retries', 2: 'keep both; and log it'}))
        self.assertEqual(tk.split_redo('1A ok'), ('1A ok', {}))
        self.assertEqual(tk.split_redo('D1: it is ok as is'), ('', {1: 'it is ok as is'}))
        self.assertEqual(tk.split_redo('see DEC-003: fine'), ('see DEC-003: fine', {}))   # not a D<n>

    def test_decisions(self):
        text = '### DEC-001 — A\n- x\nDecided by: default (unattended)\n\n### DEC-002 — B\nDecided by: owner, 2026\n\n### DEC-003 — C\n- no line\n\n## Next\n'
        self.assertEqual([(d['title'], d['by']) for d in tk.decisions(text)],
                         [('DEC-001 — A', 'default'), ('DEC-002 — B', 'owner'), ('DEC-003 — C', '')])
        self.assertEqual(tk.defaults_taken(text), ['DEC-001 — A'])

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
