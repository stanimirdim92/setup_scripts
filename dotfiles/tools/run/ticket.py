#!/usr/bin/env python3
"""Take one ticket from Jira to /ship, stopping for a person only where the risk needs one (ADR 0115).

Run it in the ticket's checkout. Each run moves the ticket as far as it can,
then stops; run it again (by hand or on a schedule) after you answer:

    intake + /spec <TICKET> unattended   Draft spec. Questions on Low and Medium
                                         risk take the recommended option as a
                                         DEC "decided by default"; High-risk
                                         questions stay open.
    ask on Slack                         one message per ticket: the open
                                         questions and the defaults taken.
    your reply in its thread             starts with "TICKET ANSWERS:" (other
                                         replies are talk, say with the PO);
                                         "1A 2B" answers; the ticket id ("AB-11"
                                         or "AB11"), "approved", "go" or "ok"
                                         approves the spec.
    /plan <TICKET>                       a clean plan (check-plan passes, no
                                         SPEC CONFLICT) is approved by the
                                         runner and goes on; any other plan is
                                         posted and stops.
    pipeline.py <TICKET>                 /build, /test, /review, fix rounds.
    /ship <TICKET>                       GO, NO-GO or SHIP BLOCKED, posted.

It commits the spec and plan files as it goes. It never pushes: you push.

Slack goes through `claude -p` and your Slack connector, so it needs no
token. Set the channel and the person whose replies count:

    export HARNESS_SLACK_CHANNEL=C0123456789
    export HARNESS_SLACK_OWNER=you@example.com     # matched against the reply's author
    export HARNESS_SLACK_MENTION=U0123456789       # optional: your Slack user id, so every
                                                   # message @-mentions you and notifies you

Without them, questions and results go to the terminal and to
`<git-common-dir>/handoff/<TICKET>-ticket.md`, and you answer with
`ticket.py <TICKET> --reply "1A, approve"`.

Usage (from the ticket's checkout):
    ticket.py LD-1
    ticket.py LD-1 --reply "1A 2B LD-1"
    ticket.py LD-1 --budget 15

Exit: 0 the ticket reached a /ship result · 1 stopped on a problem · 2 not a
ticket checkout · 3 waiting for your answer.
"""
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('pipeline', HERE / 'pipeline.py')
pl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pl)

DONE, STOPPED, NOT_CHECKOUT, WAITING = 0, 1, 2, 3
# A headless session may use a tool only when it is allowed up front. Claude Code
# names a claude.ai connector mcp__claude_ai_<Name>__…, a configured server mcp__<Name>__….
# What intake and /spec may read without a prompt: Jira, Confluence and Figma, read
# tools only, under the names a configured server ("jira", "atlassian", "figma") and
# a claude.ai connector use. Nothing here writes to Jira. HARNESS_ALLOWED_TOOLS
# (comma-separated) replaces the list.
_ATLASSIAN_READ = ('getAccessibleAtlassianResources', 'atlassianUserInfo', 'getJiraIssue', 'searchJiraIssuesUsingJql',
                   'getJiraIssueRemoteIssueLinks', 'getVisibleJiraProjects', 'getJiraProjectIssueTypesMetadata',
                   'lookupJiraAccountId', 'getConfluencePage', 'getConfluenceContent', 'searchConfluence',
                   'searchConfluenceUsingCql', 'getConfluencePageFooterComments', 'getConfluencePageInlineComments',
                   'getConfluenceCommentChildren', 'getConfluencePageDescendants', 'getPagesInConfluenceSpace',
                   'getConfluenceSpaces', 'search', 'fetch', 'discover', 'executeRead', 'getTeamworkGraphContext',
                   'getTeamworkGraphObject', 'getGraphContext', 'getGraphObject')
_FIGMA_READ = ('create_session', 'whoami', 'get_figjam', 'get_metadata', 'get_screenshot', 'get_design_context', 'get_variable_defs', 'get_code_connect_map')
READ_TOOLS = tuple(f'mcp__{server}__{tool}'
                   for server in ('jira', 'atlassian', 'claude_ai_Atlassian', 'claude_ai_Atlassian_MCP',
                                  'claude_ai_Atlassian_Rovo')
                   for tool in _ATLASSIAN_READ) + tuple(
    f'mcp__{server}__{tool}' for server in ('figma', 'claude_ai_Figma') for tool in _FIGMA_READ)
SLACK_TOOLS = ('mcp__claude_ai_Slack__slack_send_message', 'mcp__claude_ai_Slack__slack_read_thread',
               'mcp__Slack__slack_send_message', 'mcp__Slack__slack_read_thread')
CHECK_PLAN = HERE.parents[1] / 'claude/skills/planning-and-task-breakdown/scripts/check-plan.py'


# ---- reading and writing the spec and plan -------------------------------------------------

def open_questions(text):
    """The spec's OPEN QUESTION blocks, numbered Q1… in spec order (spec.md §report)."""
    out, cur = [], None
    for raw in text.splitlines():
        s = raw.strip().strip('`')
        m = re.match(r'OPEN QUESTION:\s*(.+)', s)
        if m:
            cur = {'n': len(out) + 1, 'title': m.group(1).strip(), 'options': {}, 'risk': '', 'recommended': ''}
            out.append(cur)
            continue
        if cur is None:
            continue
        m = re.match(r'[-*]\s*Option\s+([A-Z]\d?)\b\s*[:—-]?\s*(.+)', s)
        if m:
            cur['options'][m.group(1)] = m.group(2).strip()
            if re.search(r'\(recommended\b', m.group(2), re.I):
                cur['recommended'] = m.group(1)
            continue
        m = re.match(r'(?:[-*]\s*)?Risk:\s*(High|Medium|Low)', s, re.I)
        if m:
            cur['risk'] = m.group(1).capitalize()
            continue
        if s.startswith(('→', '#')):              # blank lines may sit inside a block
            cur = None
    return out


def defaults_taken(text):
    """DEC headings whose body says the runner took the recommended option."""
    found, title = [], None
    for raw in text.splitlines():
        m = re.match(r'^###\s+(DEC-\d{3}\b.*)', raw)
        if m:
            title = m.group(1).strip()
        elif title and re.search(r'decided by:?\s*default', raw, re.I):
            found.append(title)
            title = None
    return found


def header(text, key):
    m = re.search(rf'^{re.escape(key)}:\s*(.*)$', text, re.M)
    return m.group(1).strip() if m else ''


def set_header(path, values):
    """Set header lines; a missing one goes after the previous key's line, or after Status:."""
    text, anchor = path.read_text(), 'Status'
    for key, value in values.items():
        pattern = rf'^{re.escape(key)}:.*$'
        if re.search(pattern, text, re.M):
            text = re.sub(pattern, f'{key}: {value}', text, count=1, flags=re.M)
        else:
            m = re.search(rf'^{re.escape(anchor)}:.*$', text, re.M) or re.search(r'^#.*$', text, re.M)
            if not m:
                raise SystemExit(f'ticket: {path} has no "{key}:" line and no header to put it under')
            text = text[:m.end()] + f'\n{key}: {value}' + text[m.end():]
        anchor = key
    path.write_text(text)


# ---- the reply ------------------------------------------------------------------------------

ANSWERS = re.compile(r'\*?TICKET ANSWERS:\*?', re.I)


def answers_part(text):
    """The text after "TICKET ANSWERS:", or None: any other reply in the thread is conversation."""
    m = ANSWERS.search(text)
    return text[m.end():] if m else None


def parse_reply(text, ticket):
    """(answers {n: option}, approved, defaults) from a reply like "1A 2b1, approve AB-11", "AB11" or "go"."""
    answers = {int(n): letter.upper()
               for n, letter in re.findall(r'(?<![\w-])Q?(\d+)\s*=?\s*([A-Za-z]\d?)(?![\w-])', text, re.I)}
    key = re.sub(r'[^A-Z0-9]', '', ticket.upper())
    ids = {re.sub(r'[^A-Z0-9]', '', t.upper()) for t in re.findall(r'\b[A-Za-z]+-?\d+\b', text)}
    approved = key in ids or bool(re.search(r'\b(approved?|go|ok|okay)\b', text, re.I))
    return answers, approved, bool(re.search(r'\bdefaults?\b', text, re.I))


# ---- where messages go ----------------------------------------------------------------------

def first_json(text):
    m = re.search(r'(\{.*\}|\[.*\])', text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except ValueError:
        return None


class Slack:
    """Posts and reads one channel through `claude -p` and the Slack connector."""
    chatty = True                                       # each stage reports in the run's thread

    def __init__(self, run, channel, owner, mention=''):
        self.run, self.channel, self.owner, self.mention = run, channel, owner.lower(), mention

    def post(self, text, thread=None):
        if self.mention and not thread:                 # only top-level messages notify you
            text = f'<@{self.mention}> {text}'
        where = f'as a reply in the thread whose ts is {thread} ' if thread else ''
        error, out = self.run(f'Post this exact message to the Slack channel {self.channel} {where}with your Slack '
                              'tool. Change nothing in it and keep every line break. Then print only JSON: {"ts": "<the new message ts>"}.\n\n'
                              f'---\n{text}')
        data = first_json(out) if not error else None
        if not isinstance(data, dict) or not data.get('ts'):
            raise RuntimeError(f'Slack post failed: {error or out[:200]}')
        return str(data['ts'])

    def replies(self, ts):
        """The owner's replies that start with TICKET ANSWERS:, that part only."""
        return [{**r, 'text': answers_part(r['text'])} for r in self.owner_replies(ts)
                if answers_part(r['text']) is not None]

    def owner_replies(self, ts):
        error, out = self.run(f'Read the replies in the Slack thread {ts} of channel {self.channel} with your Slack '
                              'tool. Print only JSON: a list of {"author": "<name and email>", "text": "<reply, verbatim>", '
                              '"ts": "<reply ts>"}, oldest first, without the parent message.')
        data = first_json(out) if not error else None
        if not isinstance(data, list):
            raise RuntimeError(f'Slack read failed: {error or out[:200]}')
        return [{**r, 'text': str(r.get('text', ''))} for r in data
                if isinstance(r, dict) and self.owner in str(r.get('author', '')).lower()]


class Terminal:
    """No Slack configured: print, keep a file, and take the reply from --reply."""

    def __init__(self, path, reply):
        self.path, self.reply = path, reply

    def post(self, text, thread=None):
        print(text)
        with open(self.path, 'a') as fh:
            fh.write(text.rstrip() + '\n\n')
        return f'{datetime.datetime.now().timestamp():.6f}'

    def replies(self, ts):
        # The same --reply given twice counts once: its id is its text.
        return [{'author': 'you', 'text': self.reply, 'ts': hashlib.sha1(self.reply.encode()).hexdigest()}] \
            if self.reply else []


# ---- the run --------------------------------------------------------------------------------

RISK_ICON = {'High': ':red_circle:', 'Medium': ':large_orange_circle:', 'Low': ':large_green_circle:'}
RULE = '───────────────'


def option_line(key, text):
    """'(recommended — why): what' → bold key, what, star and the why in italics."""
    m = re.match(r'\(([^)]*)\)\s*:?\s*(.*)', text, re.S)
    note, what = (m.group(1), m.group(2)) if m else ('', text)
    star = ' :star:' if re.search(r'\(recommended', text, re.I) else ''
    return f'      • *{key}*{star}  {what}' + (f'\n         _{note}_' if note else '')


def ask_text(ticket, spec_text):
    qs = open_questions(spec_text)
    title = f'Spec needs {len(qs)} answer{"s" * (len(qs) != 1)}' if qs else 'Spec ready to approve'
    lines = [f'{":question:" if qs else ":clipboard:"} *{ticket} · {title}*',
             f'`docs/specs/{ticket}-SPEC.md` · {header(spec_text, "Status") or "Draft"}', RULE]
    for q in qs:
        title = re.sub(r'^Q\d+\s*[—:-]\s*', '', q['title'])
        lines.append(f'{RISK_ICON.get(q["risk"], ":white_circle:")} *{q["n"]}. {title}*  '
                     f'_{q["risk"] or "risk not stated"}_')
        lines += [option_line(k, v) for k, v in q['options'].items()]
    taken = defaults_taken(spec_text)
    if taken:
        lines.append(':gear: *Decided by default*  _Low/Medium risk · to change one, edit the spec before you approve_')
        lines += [f'      • {t}' for t in taken]
    lines.append(RULE)
    example = 'TICKET ANSWERS: ' + ' '.join(f'{q["n"]}{q["recommended"] or "A"}' for q in qs) + (' ok' if qs else 'ok')
    lines.append(f':speech_balloon: Reply in this thread:  `{example}`')
    lines.append('_Only replies that start with TICKET ANSWERS: are read; the rest is conversation. '
                 + ('`ok`, `go` or the ticket id approves once nothing is open._' if qs else
                    '`ok`, `go` or the ticket id approves._'))
    return '\n'.join(lines)


class Run:
    def __init__(self, ticket, out, claude, pipeline, budget, until=None):
        self.ticket, self.out, self.claude, self.pipeline, self.budget = ticket, out, claude, pipeline, budget
        self.until = until
        rc, common = pl.git('rev-parse', '--path-format=absolute', '--git-common-dir')
        self.dir = Path(common) / 'handoff'
        self.dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.dir / f'{ticket}-ticket.json'
        self.state = json.loads(self.state_file.read_text()) if self.state_file.exists() else {}
        self.spec = Path(f'docs/specs/{ticket}-SPEC.md')
        self.plan = Path(f'docs/tasks/{ticket}-plan.md')
        self.todo = Path(f'docs/tasks/{ticket}-todo.md')

    def save(self):
        self.state_file.write_text(json.dumps(self.state, indent=2) + '\n')

    def progress(self, text):
        """A reply in this run's thread. Questions, stops and the /ship result stay top-level."""
        if not getattr(self.out, 'chatty', False):
            return
        try:
            if not getattr(self, 'thread', None):
                self.thread = self.out.post(f':arrow_forward: *{self.ticket} · Run* · `{os.getcwd()}`\n'
                                            'Each stage reports in this thread.')
            self.out.post(text, thread=self.thread)
        except RuntimeError as err:
            print(f'ticket: could not post progress: {err}')

    def check_inbox(self):
        """The owner's new TICKET STOP / TICKET NOTE: replies in the run thread: (stop, notes)."""
        if not getattr(self.out, 'chatty', False) or not getattr(self, 'thread', None):
            return False, ''
        try:
            new = [r for r in self.out.owner_replies(self.thread) if r.get('ts') not in self.state.get('inbox_seen', [])]
        except RuntimeError as err:
            print(f'ticket: could not read the run thread: {err}')
            return False, ''
        self.state.setdefault('inbox_seen', []).extend(r.get('ts') for r in new)
        self.save()
        stop = any(re.search(r'\bTICKET STOP\b', r['text'], re.I) for r in new)
        notes = '\n'.join(m.group(1).strip() for r in new for m in [re.search(r'TICKET NOTE:\s*(.+)', r['text'], re.I | re.S)] if m)
        if stop:
            self.progress(':octagonal_sign: TICKET STOP read: nothing new starts.')
        elif notes:
            self.progress(f':memo: TICKET NOTE read; it goes to the next stage:\n{notes}')
        return stop, notes

    def stage(self, prompt):
        stop, notes = self.check_inbox()
        if stop:
            return 'stopped by the owner (TICKET STOP)', ''
        if notes:
            prompt += f'\n\nOwner notes from Slack (TICKET NOTE). Follow them unless they conflict with the approved spec:\n{notes}'
        print(f'  {datetime.datetime.now():%H:%M} {prompt.splitlines()[0][:110]}')
        started = time.monotonic()
        error, text = self.claude(prompt)
        took, cost = int(time.monotonic() - started), getattr(self.claude, 'cost', None)
        self.progress(f'{":x:" if error else ":white_check_mark:"} *{prompt.splitlines()[0][:80]}* · '
                      f'{took // 60}m{took % 60:02d}s' + (f' · ${cost:.2f}' if cost is not None else '')
                      + (f' · {error}' if error else '') + f'\n{digest(text)}')
        saved = self.dir / f'{self.ticket}-ticket-{len(self.state.setdefault("log", [])) + 1}.md'
        saved.write_text(text + '\n')
        self.last_file = saved.name
        print(f'    saved: {saved}')
        self.state['log'].append(prompt.splitlines()[0])
        self.save()
        return error, text

    def commit(self, message):
        paths = [str(p) for p in (Path(f'docs/specs/{self.ticket}-intake.md'), self.spec, self.plan, self.todo)
                 if p.exists()]
        pl.git('add', '--', *paths)
        if pl.git('diff', '--cached', '--quiet')[0]:
            rc, _ = pl.git('commit', '-q', '-m', f'{message}\n\nRefs: {self.ticket}')
            if rc:
                raise RuntimeError(f'git commit failed for "{message}"')

    def stop_at(self, where):
        print(f'ticket: {self.ticket} stops after /{where} (--until {where})')
        self.out.post(f':double_vertical_bar: *{self.ticket} · Paused after /{where}* (--until {where}). '
                      f'Run ticket.py {self.ticket} again to go on.')
        return WAITING

    def stop(self, why, file=''):
        print(f'ticket: {self.ticket} stopped: {why}')
        text = f':octagonal_sign: *{self.ticket} · Stopped*\n*Why:* {why}'
        if file and (self.dir / file).exists():
            body = '\n'.join(l for l in (self.dir / file).read_text().splitlines() if l.strip())
            text += f'\n*{file}:*\n```\n{body[:1800]}{" …" if len(body) > 1800 else ""}\n```'
        try:
            self.out.post(f'{text}\nLog: `{self.dir}`')
        except RuntimeError as err:
            print(f'ticket: could not post the stop: {err}')
        return STOPPED

    def go(self):
        t = self.ticket
        if self.state.get('ship'):
            print(f'ticket: {t} already reached /ship: {self.state["ship"]}')
            return DONE
        if not self.spec.exists():
            intake = Path(f'docs/specs/{t}-intake.md')
            for prompt in (f'/jira-ticket {t}', f'/spec {t} unattended'):
                error, text = self.stage(prompt)
                if error:
                    return self.stop(f'{prompt} {error}')
                if prompt.startswith('/jira-ticket') and not intake.exists():
                    return self.stop(f'intake wrote no {intake}: {first_line(text)}')
            if not self.spec.exists():
                return self.stop(f'/spec wrote no {self.spec}')
            self.commit(f'{t}: draft spec (unattended)')

        if header(self.spec.read_text(), 'Status') != 'Approved':
            result = self.settle_spec()
            if result is not None:
                return result

        if not self.plan.exists() or header(self.plan.read_text(), 'Status') != 'Approved' or self.plan_stale():
            result = self.make_plan()
            if result is not None:
                return result

        if not self.state.get('pipeline_done'):
            print(f'  spec and plan are approved; pipeline.py runs /build, /test and /review')
            if self.until == 'plan':
                return self.stop_at('plan')
            (self.dir / f'{t}-inbox.json').unlink(missing_ok=True)
            rc = self.pipeline(t, self.budget, self.pipeline_step)
            if rc != 0:
                stopped = self.dir / f'{t}-pipeline-stop.json'
                info = json.loads(stopped.read_text()) if stopped.exists() else {}
                return self.stop(f'pipeline.py: {info.get("why") or f"exited {rc}"}', info.get('stage_file', ''))
            self.state['pipeline_done'] = True
            self.save()

        reviews = sorted(self.dir.glob(f'{t}-*-REVIEW.md'), key=lambda p: int(p.name.split('-')[-2]))
        given = f'\n\nREVIEW result — {pl.SUPPLIED}\n\n{reviews[-1].read_text()}' if reviews else ''
        error, text = self.stage(f'/ship {t}{given}')
        if error:
            return self.stop(f'/ship {error}')
        result = pl.line(text, '(?:GO|NO-GO|SHIP BLOCKED)') or 'no GO / NO-GO line'
        icon = ':rocket:' if result.startswith('GO') else ':no_entry:' if result.startswith('NO-GO') else ':construction:'
        self.out.post(f'{icon} *{t} · /ship: {result}*\n:lock: Nothing is pushed; you push. Report: `{self.dir}`')
        self.state['ship'] = result
        self.save()
        return DONE

    def settle_spec(self):
        t, text = self.ticket, self.spec.read_text()
        digest = hashlib.sha1(text.encode()).hexdigest()
        ask = self.state.get('ask')
        if not ask or ask.get('spec') != digest:
            self.state['ask'] = {'ts': self.out.post(ask_text(t, text)), 'spec': digest, 'seen': []}
            self.save()
            return WAITING
        new = [r for r in self.out.replies(ask['ts']) if r.get('ts') not in ask['seen']]
        if not new:
            return WAITING
        ask['seen'] += [r.get('ts') for r in new]
        self.save()
        for r in new:                                   # a question to the runner gets an answer in the thread
            if '?' in str(r.get('text', '')):
                error, answer = self.claude(
                    f'The owner of {t} asks about its spec. Answer from docs/specs/{t}-SPEC.md and '
                    f'docs/specs/{t}-intake.md, in at most 6 short lines for Slack. Read only; change no '
                    f'file.\n\nQuestion: {r["text"].strip()}')
                self.out.post(f':speech_balloon: *Answer*\n{answer.strip() if not error else "could not answer: " + error}',
                              thread=ask['ts'])
        answers, approved, defaults = {}, False, False
        for r in new:
            a, ok, d = parse_reply(str(r.get('text', '')), t)
            answers.update(a)
            approved, defaults = approved or ok, defaults or d
        qs = {q['n']: q for q in open_questions(text)}
        if defaults:
            for n, q in qs.items():
                if n not in answers and q['recommended'] and q['risk'] != 'High':
                    answers[n] = q['recommended']
        bad = [f'{n}{a}' for n, a in answers.items() if n not in qs or a not in qs[n]['options']]
        if bad:
            self.out.post(f':warning: Not a question and option here: {" ".join(bad)}. Nothing changed.',
                          thread=ask['ts'])
            return WAITING
        if answers:
            given = ', '.join(f'Q{n}=Option {a}: {qs[n]["options"][a]}' for n, a in sorted(answers.items()))
            error, _ = self.stage(f'/spec {t} decisions: {given}\nRecord each as a DEC decided by '
                                  f'{self.out_owner()}; do not set Approved.')
            if error:
                return self.stop(f'/spec decisions {error}')
            self.commit(f'{t}: spec decisions from the owner')
            text = self.spec.read_text()
        left = open_questions(text)
        if approved and not left:
            set_header(self.spec, {'Status': 'Approved', 'Approved by': f'{self.out_owner()} (reply in thread '
                                   f'{ask["ts"]})', 'Approved at': datetime.date.today().isoformat()})
            self.commit(f'{t}: spec approved by the owner')
            self.out.post(f':white_check_mark: *{t} · Spec approved.* Planning, then build, test, review and ship.',
                          thread=ask['ts'])
            return None
        if approved:
            still = ', '.join('Q%d' % q['n'] for q in left)
            self.out.post(f':hourglass_flowing_sand: Still open: {still}. Answer them, then approve.', thread=ask['ts'])
        self.state['ask'] = {'ts': self.out.post(ask_text(t, text)), 'spec': hashlib.sha1(text.encode()).hexdigest(),
                             'seen': []}
        self.save()
        return WAITING

    def pipeline_step(self, prompt, cost):
        """pipeline.py finished a stage: post what its message file says, then hand it the owner's word."""
        self.pipeline_steps = getattr(self, 'pipeline_steps', 0) + 1
        stop, notes = False, ''
        try:
            self.pipeline_progress(prompt, cost)
            stop, notes = self.check_inbox()
        finally:                                        # pipeline.py waits for this file before its next stage
            (self.dir / f'{self.ticket}-inbox.json').write_text(json.dumps(
                {'after_step': self.pipeline_steps, 'stop': stop, 'notes': [notes] if notes else []}))

    def pipeline_progress(self, prompt, cost):
        files = sorted(self.dir.glob(f'{self.ticket}-*-*.md'), key=lambda p: p.stat().st_mtime)
        files = [p for p in files if re.fullmatch(rf'{re.escape(self.ticket)}-\d+-[A-Z]+\.md', p.name)]
        icon = {'BUILD': ':hammer_and_wrench:', 'VERIFY': ':test_tube:', 'REVIEW': ':mag:'}
        kind = files[-1].name.rsplit('-', 1)[1][:-3] if files else ''
        self.progress(f'{icon.get(kind, ":gear:")} *{prompt}* · ${cost}\n' + (digest(files[-1].read_text()) if files else ''))

    def plan_stale(self):
        """The spec changed after the plan's last commit, so the plan answers an older spec."""
        spec, plan = (pl.git('log', '-1', '--format=%H', '--', str(p))[1] for p in (self.spec, self.plan))
        stale = not plan or (spec and pl.git('merge-base', '--is-ancestor', spec, plan)[0] != 0)
        if stale:
            print(f'  the plan predates the current spec; /plan runs again')
        return stale

    def back_to_spec(self, conflict):
        """plan → spec (component-response-contracts §5): /spec resolves the conflict unattended, the spec goes
        back to Draft, and the owner answers and approves again. Twice at most; then it stops."""
        t = self.ticket
        self.state['conflicts'] = self.state.get('conflicts', 0) + 1
        self.state.pop('ask', None)                     # a fresh ask for the revised spec
        self.save()
        self.commit(f'{t}: plan stopped at a spec conflict')
        error, _ = self.stage(f'/spec {t} unattended\nThe plan stopped at this SPEC CONFLICT. Revise the spec to '
                              f'resolve it, under the unattended rules; keep the decisions the owner made unless the '
                              f'conflict is about them.\n\n{conflict}')
        if error:
            return self.stop(f'/spec after the plan conflict {error}')
        set_header(self.spec, {'Status': 'Draft', 'Approved by': '—', 'Approved at': '—'})
        self.commit(f'{t}: spec revised for the plan conflict')
        self.out.post(f':leftwards_arrow_with_hook: *{t} · Back to spec.* /plan found a conflict:\n```\n'
                      f'{conflict[:1500]}\n```\nThe spec is revised and needs your approval again.')
        return self.settle_spec()

    def make_plan(self):
        t = self.ticket
        if (self.plan.exists() and has_conflict(self.plan.read_text()) and not self.plan_stale()
                and self.state.get('conflicts', 0) < 2):             # this spec already has a conflict: no new /plan
            return self.back_to_spec(conflict_text(self.plan.read_text()))
        error, text = self.stage(f'/plan {t}')
        if error:
            return self.stop(f'/plan {error}')
        if not self.plan.exists():
            return self.stop(f'/plan wrote no {self.plan}')
        plan = self.plan.read_text()
        if has_conflict(plan) and self.state.get('conflicts', 0) < 2:
            return self.back_to_spec(conflict_text(plan))
        if has_conflict(plan) or open_questions(plan):
            self.commit(f'{t}: plan draft')
            return self.stop(f'the plan raised a SPEC CONFLICT or an open question; read {self.plan}', self.last_file)
        check = subprocess.run([sys.executable, str(CHECK_PLAN), str(self.plan), '--todo', str(self.todo),
                                '--spec', str(self.spec)], capture_output=True, text=True)
        if check.returncode:
            self.commit(f'{t}: plan draft')
            return self.stop('check-plan failed:\n' + (check.stdout + check.stderr)[-1500:])
        set_header(self.plan, {'Status': 'Approved', 'Approved by': 'ticket.py: clean plan under the approved spec '
                               '(ADR 0115)', 'Approved at': datetime.date.today().isoformat(),
                               'Handoff': 'Ready for /build'})
        self.commit(f'{t}: plan approved (clean, ADR 0115)')
        return None

    def out_owner(self):
        return os.environ.get('HARNESS_SLACK_OWNER') or 'the owner'


def ticket_key(arg):
    """The Jira key from "LD-503" or a ticket URL such as https://x.atlassian.net/browse/LD-503."""
    m = re.search(r'(?<![A-Za-z0-9])([A-Z][A-Z0-9]+-\d+)(?![0-9])', arg)
    return m.group(1) if m else None


def digest(text, lines=6, chars=700):
    """The first lines of a stage's answer, for a Slack progress reply."""
    kept = [l.rstrip() for l in text.splitlines() if l.strip() and not l.strip().startswith('```')][:lines]
    out = '\n'.join(kept)
    return out[:chars] + (' …' if len(out) > chars else '')


CONFLICT = re.compile(r'#+\s*SPEC CONFLICT\b')


def has_conflict(plan):
    """An open conflict is a SPEC CONFLICT heading or a blocked handoff, not the words in prose
    ("resolves the earlier SPEC CONFLICT")."""
    return any(CONFLICT.match(l) for l in plan.splitlines()) or \
        bool(re.search(r'SPEC CONFLICT', header(plan, 'Handoff') or ''))


def conflict_text(plan):
    """The plan's SPEC CONFLICT section: from its line to the next heading of the same or a higher level."""
    lines = plan.splitlines()
    start = next((i for i, l in enumerate(lines) if CONFLICT.match(l)), None)
    if start is None:
        return header(plan, 'Handoff') or 'SPEC CONFLICT (see the plan)'
    level = len(lines[start]) - len(lines[start].lstrip('#')) or 7
    end = next((i for i in range(start + 1, len(lines))
                if lines[i].startswith('#') and len(lines[i]) - len(lines[i].lstrip('#')) <= level), len(lines))
    return '\n'.join(lines[start:end]).strip()[:4000]


def default_branch():
    for remote in pl.git('remote')[1].split():
        rc, ref = pl.git('symbolic-ref', '--short', '-q', f'refs/remotes/{remote}/HEAD')
        if not rc and ref:
            return ref.split('/', 1)[1]
    return 'main' if not pl.git('rev-parse', '-q', '--verify', 'refs/heads/main')[0] else 'master'


def copy_worktree_include(main, path):
    """Copy what .worktreeinclude names and git ignores (.env, vendor, node_modules …) from the main
    checkout into a new worktree, as Claude Code does for `claude --worktree`. Plain git does not."""
    include = main / '.worktreeinclude'
    if not include.exists():
        return []
    rc, listed = pl.git('-C', str(main), 'ls-files', '--others', '--ignored', '--directory', '--no-empty-directory',
                        f'--exclude-from={include}')
    copied = []
    for entry in listed.splitlines():
        rel = entry.rstrip('/')
        if not rel or pl.git('-C', str(main), 'check-ignore', '-q', rel)[0]:    # matched but not gitignored
            continue
        target = path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if subprocess.run(['cp', '-a', str(main / rel), str(target.parent) + '/']).returncode == 0:
            copied.append(rel)
    return copied


def ticket_checkout(ticket):
    """On the main checkout's default branch, move into the ticket worktree .claude/worktrees/<ticket>
    on branch worktree-<ticket>, as `claude --worktree <ticket>` makes it (AGENTS.md §Worktrees), creating
    it from HEAD when missing. /build refuses the default branch. Returns the worktree path, or None."""
    git_dir, common = (pl.git('rev-parse', '--path-format=absolute', flag)[1] for flag in ('--git-dir', '--git-common-dir'))
    if git_dir != common or pl.git('symbolic-ref', '--short', '-q', 'HEAD')[1] != default_branch():
        return None
    path = Path(pl.git('rev-parse', '--show-toplevel')[1]) / '.claude' / 'worktrees' / ticket
    if not path.exists():
        branch = f'worktree-{ticket}'
        exists = not pl.git('rev-parse', '-q', '--verify', f'refs/heads/{branch}')[0]
        rc, out = pl.git('worktree', 'add', str(path), *([branch] if exists else ['-b', branch]))
        if rc:
            raise RuntimeError(f'git worktree add {path} failed: {out}')
        copied = copy_worktree_include(Path(pl.git('rev-parse', '--show-toplevel')[1]), path)
        if copied:
            print(f'ticket: copied from .worktreeinclude: {", ".join(copied)}')
    os.chdir(path)
    return path


def first_line(text):
    for raw in text.splitlines():
        line = raw.strip().strip('*#> ').strip()
        if line and not line.startswith('```'):
            return line[:110]
    return '(empty)'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('ticket', help='the Jira key (LD-503) or the ticket URL')
    parser.add_argument('--reply', help='your answer when Slack is not configured, e.g. "1A 2B LD-1"')
    parser.add_argument('--until', choices=('plan',), help='stop after this stage (approved plan, no /build)')
    parser.add_argument('--budget', type=float, default=10, help='--max-budget-usd per stage (default 10)')
    parser.add_argument('--permission-mode', default='',
                        help='claude -p permission mode; empty (the default) uses your settings.json')
    args = parser.parse_args(argv)
    binary = os.environ.get('CLAUDE_BIN', 'claude')
    key = ticket_key(args.ticket)
    if not key:
        print(f'ticket: no Jira key in "{args.ticket}"; give LD-503 or the ticket URL')
        return NOT_CHECKOUT
    args.ticket = key

    rc, _ = pl.git('rev-parse', '--git-dir')
    branch = pl.git('symbolic-ref', '--short', '-q', 'HEAD')[1]
    if rc or not branch or branch in pl.PROTECTED:
        print(f'ticket: run it in the ticket checkout (branch is {branch or "detached"})')
        return NOT_CHECKOUT
    try:
        moved = ticket_checkout(args.ticket)
    except RuntimeError as err:
        print(f'ticket: {err}')
        return NOT_CHECKOUT
    if moved:
        print(f'ticket: the default branch is not for ticket work; using the worktree {moved}')
    dirty = pl.git('status', '--porcelain')[1]          # the checkout the ticket runs in
    if dirty:
        print(f'ticket: {os.getcwd()} has uncommitted changes. Commit or stash them first:')
        print('\n'.join('  ' + line for line in dirty.splitlines()[:20]))
        return NOT_CHECKOUT
    common = pl.git('rev-parse', '--path-format=absolute', '--git-common-dir')[1]
    log = Path(common) / 'handoff' / f'{args.ticket}-ticket.log'
    log.parent.mkdir(parents=True, exist_ok=True)

    slack_model = os.environ.get('HARNESS_SLACK_MODEL', 'haiku')     # posting and reading needs no big model
    allowed = tuple(t.strip() for t in os.environ.get('HARNESS_ALLOWED_TOOLS', '').split(',') if t.strip()) \
        or READ_TOOLS

    def claude(prompt, tools=None):
        started = time.monotonic()
        budget = 1 if tools else args.budget                  # a Slack post or read is small
        error, text, cost = pl.claude(binary, prompt, budget, args.permission_mode, log,
                                      tools if tools else allowed, slack_model if tools else None)
        claude.cost = cost
        took = int(time.monotonic() - started)
        print(f'    {"slack " if tools else ""}{took // 60}m{took % 60:02d}s, ${cost:.2f}: '
              + (f'ERROR {error}' if error else first_line(text)))
        return error, text

    def pipeline(ticket, budget, step=None):
        """pipeline.py, its output passed through; each finished stage line goes to step(prompt, cost)."""
        proc = subprocess.Popen([sys.executable, '-u', str(HERE / 'pipeline.py'), ticket, '--yes', '--budget',
                                 str(budget), '--permission-mode', args.permission_mode],
                                stdout=subprocess.PIPE, text=True,
                                env={**os.environ, **({'HARNESS_INBOX': str(log.parent / f'{ticket}-inbox.json')}
                                                      if step else {})})
        for line in proc.stdout:
            print(line, end='', flush=True)
            m = re.match(r'  (/\w+ \S+.*?)\s+\$(\d+\.\d\d)$', line.rstrip('\n'))
            if m and step:
                step(m.group(1), m.group(2))
        return proc.wait()

    channel, owner = os.environ.get('HARNESS_SLACK_CHANNEL'), os.environ.get('HARNESS_SLACK_OWNER')
    if channel and owner:
        out = Slack(lambda prompt: claude(prompt, SLACK_TOOLS), channel, owner, os.environ.get('HARNESS_SLACK_MENTION', ''))
    else:
        out = Terminal(log.with_suffix('.md'), args.reply)
    print(f'ticket: {args.ticket} in {os.getcwd()}')
    print(f'  messages: {log.parent}/{args.ticket}-ticket-<n>.md · log: {log}')
    print(f'  questions and results: ' + (f'Slack channel {channel}' if channel and owner else f'this terminal and {log.with_suffix(".md")}'))
    try:
        result = Run(args.ticket, out, claude, pipeline, args.budget, args.until).go()
    except RuntimeError as err:
        print(f'ticket: {err}')
        return STOPPED
    print({DONE: 'ticket: reached /ship.', STOPPED: 'ticket: stopped.', WAITING: 'ticket: waiting for your answer.'}
          .get(result, ''))
    return result


if __name__ == '__main__':
    sys.exit(main())
