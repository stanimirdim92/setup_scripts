#!/usr/bin/env python3
"""Take one ticket from Jira to /ship, stopping for a person only where the risk needs one (ADR 0115).

Run it in the ticket's checkout. Each run moves the ticket as far as it can,
then waits for your Slack answer (--wait hours) or stops; run it again to go on:

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
    ticket.py --watch                    from the main checkout: every --poll seconds,
                                         start a run for each open Jira issue with the
                                         label --label (harness-run), --jobs (2) at once.
                                         Put the label on to start; take it off to stop
                                         the run before its next stage. A stopped run
                                         (exit 1 or 2) starts again only after the label
                                         is taken off and put back.

One run per ticket: `<git-common-dir>/handoff/<TICKET>-ticket.lock` names the
process; a second start is refused while it lives, and takes over when it is
gone. A run picks up where the last one stopped: the state file, the spec and
plan status, and pipeline.py's finished stages on the same HEAD. A stage that
hits a rate limit, a dropped connection or a stall is retried by pipeline.py's
`claude` (HARNESS_RETRIES, HARNESS_STALL_MIN).

Between stages the runner also reads the ticket's Jira status: Done, or a
status named in HARNESS_JIRA_STOP (default "Blocked, On Hold, Paused,
Cancelled"), stops the run before the next stage, like TICKET STOP.
HARNESS_JIRA_STOP=0 turns the check off.

Jira mirrors the run (HARNESS_JIRA_WRITE, default on; 0 turns it off): a run
moves the ticket to HARNESS_JIRA_START ("In Progress") when it starts, the
questions it asks in Slack go on the ticket as a comment too, a stop leaves a
one-line comment, and the /ship result is a comment with the branch, HEAD
and what the run spent; GO moves the ticket to HARNESS_JIRA_REVIEW ("Code
Review, In Review": the first its workflow offers). Only the status and
comments are written, nothing else.

Exit: 0 the ticket reached a /ship result · 1 stopped on a problem · 2 not a
ticket checkout · 3 waiting for your answer · 5 another run holds the ticket.
HARNESS_LABEL=<label> makes a run by hand obey the label too.
"""
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('pipeline', HERE / 'pipeline.py')
pl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pl)

DONE, STOPPED, NOT_CHECKOUT, WAITING, PAUSED, BUSY = 0, 1, 2, 3, 4, 5
JIRA_STOP = 'Blocked, On Hold, Paused, Cancelled, Canceled'
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
# What the runner may write to Jira: the ticket's status and a comment on it, nothing else (no field
# edits, no new issues). Used only with HARNESS_JIRA_WRITE on (the default).
_ATLASSIAN_WRITE = ('transitionJiraIssue', 'getTransitionsForJiraIssue', 'addCommentToJiraIssue',
                    'addOrEditJiraIssueComment')
JIRA_WRITE_TOOLS = tuple(f'mcp__{server}__{tool}'
                         for server in ('jira', 'atlassian', 'claude_ai_Atlassian', 'claude_ai_Atlassian_MCP',
                                        'claude_ai_Atlassian_Rovo')
                         for tool in _ATLASSIAN_WRITE)
JIRA_START = 'In Progress'                  # HARNESS_JIRA_START: where a run moves the ticket when it starts
JIRA_REVIEW = 'Code Review, In Review'     # HARNESS_JIRA_REVIEW: where a GO moves it; the first that exists
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
                              'tool. Print only JSON: a list of {"author": "<name, email and Slack user id>", "text": "<reply, verbatim>", '
                              '"ts": "<reply ts>"}, oldest first, without the parent message.')
        data = first_json(out) if not error else None
        if not isinstance(data, list):
            raise RuntimeError(f'Slack read failed: {error or out[:200]}')
        return [{**r, 'text': str(r.get('text', ''))} for r in data
                if isinstance(r, dict) and self.is_owner(str(r.get('author', '')))]

    def is_owner(self, author):
        """The reply's author is the owner: by email, or by Slack user id when the reader gave no email."""
        author = author.lower()
        return self.owner in author or bool(self.mention and self.mention.lower() in author)


class Jira:
    """The ticket in Jira, through `claude -p` and the Atlassian tools: its status to read, and with
    HARNESS_JIRA_WRITE on, a comment and the status moves the run makes. A failed write is printed and
    the run goes on: Jira mirrors the run, it does not gate it."""

    def __init__(self, run, ticket, write=True):
        self.run, self.ticket, self.write = run, ticket, write

    def status(self):
        """{status, category, labels} of the ticket; RuntimeError when it cannot be read."""
        error, out = self.run(f'Read the Jira issue {self.ticket} with your Jira tool (getJiraIssue; find the '
                              'cloudId with getAccessibleAtlassianResources if it asks for one). Print only JSON: '
                              '{"status": "<status name>", "category": "<its status category: To Do, In Progress or '
                              'Done>", "labels": ["<each label>"]}.', READ_TOOLS)
        data = first_json(out) if not error else None
        if not isinstance(data, dict):
            raise RuntimeError(error or out[:200])
        return data

    def labelled(self, label, jql_extra='statusCategory != Done'):
        """The keys of the issues carrying `label` and not done, most urgent first; RuntimeError on failure."""
        error, out = self.run(f'Search Jira with your Jira tool (searchJiraIssuesUsingJql; find the cloudId with '
                              f'getAccessibleAtlassianResources if it asks for one) for this JQL, exactly:\n'
                              f'labels = "{label}" AND {jql_extra} ORDER BY priority ASC, created ASC\n'
                              f'Print only JSON: a list of the issue keys in that order, e.g. ["AB-1", "AB-2"]; '
                              f'[] when there are none.', READ_TOOLS)
        data = first_json(out) if not error else None
        if not isinstance(data, list):
            raise RuntimeError(error or out[:200])
        return [ticket_key(str(k)) for k in data if ticket_key(str(k))]

    def comment(self, text):
        """Add `text` as a comment on the ticket. Returns True when Jira confirmed it."""
        return self.change(f'Add this comment to the Jira issue {self.ticket} with your Jira tool, as it is, '
                           f'keeping every line break; change nothing in it. Then print only JSON: '
                           f'{{"ok": true}}.\n\n---\n{text}', 'comment')

    def move(self, statuses):
        """Move the ticket to the first status in `statuses` (comma-separated) that its workflow offers."""
        wanted = [s.strip() for s in statuses.split(',') if s.strip()]
        if not wanted:
            return False
        return self.change(f'With your Jira tools, move the issue {self.ticket} to the first of these statuses that '
                           f'its transitions offer: {", ".join(wanted)}. If it is in that status already, or none '
                           f'of them is offered, change nothing. Then print only JSON: {{"ok": true, "status": '
                           f'"<its status now>"}}.', f'move to {wanted[0]}')

    def change(self, prompt, what):
        if not self.write:
            return False
        error, out = self.run(prompt, READ_TOOLS + JIRA_WRITE_TOOLS)
        data = first_json(out) if not error else None
        if not isinstance(data, dict) or not data.get('ok'):
            print(f'ticket: Jira {what} failed: {error or out[:200]}')
            return False
        return True


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
    def __init__(self, ticket, out, claude, pipeline, budget, until=None, jira=None):
        self.ticket, self.out, self.claude, self.pipeline, self.budget = ticket, out, claude, pipeline, budget
        self.until, self.jira = until, jira                 # jira() reads the ticket's status, or None
        rc, common = pl.git('rev-parse', '--path-format=absolute', '--git-common-dir')
        self.dir = Path(common) / 'handoff'
        self.dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.dir / f'{ticket}-ticket.json'
        self.state = json.loads(self.state_file.read_text()) if self.state_file.exists() else {}
        self.spec = Path(f'docs/specs/{ticket}-SPEC.md')
        self.plan = Path(f'docs/tasks/{ticket}-plan.md')
        self.todo = Path(f'docs/tasks/{ticket}-todo.md')
        self.thread = self.state.get('thread')          # one progress thread per ticket, across runs

    def save(self):
        self.state_file.write_text(json.dumps(self.state, indent=2) + '\n')

    def progress(self, text):
        """A reply in this run's thread. Questions, stops and the /ship result stay top-level."""
        if not getattr(self.out, 'chatty', False):
            return
        try:
            if not self.thread:
                self.thread = self.state['thread'] = self.out.post(
                    f':arrow_forward: *{self.ticket} · Run* · `{os.getcwd()}`\nEach stage reports in this thread. '
                    'Write `TICKET STOP` or `TICKET NOTE: …` here between stages.')
                self.save()
            self.out.post(text, thread=self.thread)
        except RuntimeError as err:
            print(f'ticket: could not post progress: {err}')

    def check_inbox(self):
        """The owner's word before the next stage: (stop, notes). TICKET STOP / TICKET NOTE: replies in the
        run thread, the question thread or the latest conflict thread; and the ticket's Jira status, when
        a stopping one means the same as TICKET STOP."""
        stop, notes = False, ''
        if getattr(self.out, 'chatty', False):
            threads = [self.thread, (self.state.get('ask') or {}).get('ts'),
                       *self.state.get('inbox_threads', [])[-1:]]
            new = []
            for ts in dict.fromkeys(t for t in threads if t):
                try:
                    new += [r for r in self.out.owner_replies(ts) if r.get('ts') not in self.state.get('inbox_seen', [])]
                except RuntimeError as err:
                    print(f'ticket: could not read thread {ts}: {err}')
            self.state.setdefault('inbox_seen', []).extend(r.get('ts') for r in new)
            self.save()
            stop = 'TICKET STOP' if any(re.search(r'\bTICKET STOP\b', r['text'], re.I) for r in new) else False
            notes = '\n'.join(m.group(1).strip() for r in new for m in [re.search(r'TICKET NOTE:\s*(.+)', r['text'], re.I | re.S)] if m)
            if stop:
                self.progress(':octagonal_sign: TICKET STOP read: nothing new starts.')
            elif notes:
                self.progress(f':memo: TICKET NOTE read; it goes to the next stage:\n{notes}')
        status = self.jira_stop()
        if status:
            self.progress(f':octagonal_sign: Jira status is *{status}*: nothing new starts. Move the ticket back '
                          'and run ticket.py again to go on.')
            stop = stop or f'Jira status {status}'
        return stop, notes

    def jira_stop(self):
        """What in Jira says to stop: the status (Done, or one named in HARNESS_JIRA_STOP), or the label
        HARNESS_LABEL gone from the ticket (the label is the claim when --watch started the run). Else ''."""
        stopping, label = os.environ.get('HARNESS_JIRA_STOP', JIRA_STOP), os.environ.get('HARNESS_LABEL', '')
        if not self.jira or (stopping.strip() in ('0', '') and not label):
            return ''
        try:
            status = self.jira.status() or {}
        except RuntimeError as err:
            print(f'ticket: could not read the Jira status: {err}')
            return ''
        name, category = str(status.get('status', '')).strip(), str(status.get('category', '')).strip()
        names = {s.strip().lower() for s in stopping.split(',') if s.strip()}
        if stopping.strip() not in ('0', '') and (category.lower() == 'done' or name.lower() in names):
            return name
        labels = status.get('labels')
        if label and isinstance(labels, list) and label.lower() not in {str(l).lower() for l in labels}:
            return f'{name}, label {label} removed'
        return ''

    def stage(self, prompt):
        stop, notes = self.check_inbox()
        if stop:
            return f'stopped by the owner ({stop})', ''
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
        self.state['cost'] = round(self.state.get('cost', 0) + (cost or 0), 2)
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
        return PAUSED

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
        if self.jira:
            self.jira.comment(f'ticket.py stopped: {plain(why)}')
        return STOPPED

    def go(self):
        t = self.ticket
        if self.state.get('ship'):
            print(f'ticket: {t} already reached /ship: {self.state["ship"]}')
            return DONE
        if self.jira and not self.state.get('jira_started'):
            if self.jira.move(os.environ.get('HARNESS_JIRA_START', JIRA_START)):
                self.state['jira_started'] = True
                self.save()
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
        if self.jira:
            self.jira.comment(f'/ship: {result}\nBranch: {pl.git("symbolic-ref", "--short", "-q", "HEAD")[1]} · '
                              f'HEAD: {pl.git("rev-parse", "--short", "HEAD")[1]} · spent: ${self.state.get("cost", 0):.2f}\n'
                              f'Nothing is pushed; the owner pushes. Report: {self.dir}')
            if result.startswith('GO'):
                self.jira.move(os.environ.get('HARNESS_JIRA_REVIEW', JIRA_REVIEW))
        return DONE

    def settle_spec(self):
        t, text = self.ticket, self.spec.read_text()
        digest = hashlib.sha1(text.encode()).hexdigest()
        ask = self.state.get('ask')
        if not ask or ask.get('spec') != digest:
            self.state['ask'] = {'ts': self.ask(text), 'spec': digest, 'seen': []}
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
        self.state['ask'] = {'ts': self.ask(text), 'spec': hashlib.sha1(text.encode()).hexdigest(), 'seen': []}
        self.save()
        return WAITING

    def ask(self, spec_text):
        """Post the questions and defaults; the same text, without Slack markup, goes on the Jira ticket."""
        text = ask_text(self.ticket, spec_text)
        ts = self.out.post(text)
        if self.jira:
            self.jira.comment(plain(text) + ('\n\nAnswers go in the Slack thread.'
                                             if getattr(self.out, 'chatty', False) else ''))
        return ts

    def pipeline_step(self, prompt, cost, step=None):
        """pipeline.py finished a stage: post what its message file says, then hand it the owner's word.
        `step` is pipeline.py's own count, which runs on from an earlier run it picked up."""
        self.pipeline_steps = int(step) if step else getattr(self, 'pipeline_steps', 0) + 1
        self.state['cost'] = round(self.state.get('cost', 0) + float(cost or 0), 2)
        stop, notes = False, ''
        try:
            self.pipeline_progress(prompt, cost)
            stop, notes = self.check_inbox()
        finally:                                        # pipeline.py waits for this file before its next stage
            (self.dir / f'{self.ticket}-inbox.json').write_text(json.dumps(
                {'after_step': self.pipeline_steps, 'stop': bool(stop), 'notes': [notes] if notes else []}))

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
        """plan → spec (component-response-contracts §5): /spec resolves the conflict unattended. A fix it
        decided by default (Low/Medium) keeps the owner's approval and planning goes on (None); a High one
        stays an OPEN QUESTION, the spec goes back to Draft and the owner answers and approves again
        (ADR 0115). Twice at most; then it stops."""
        t = self.ticket
        self.state['conflicts'] = self.state.get('conflicts', 0) + 1
        self.state.pop('ask', None)                     # a fresh ask for the revised spec
        self.save()
        self.commit(f'{t}: plan stopped at a spec conflict')
        try:
            back = self.out.post(f':leftwards_arrow_with_hook: *{t} · Back to spec.* /plan found a conflict:\n```\n'
                                 f'{conflict[:1500]}\n```\n/spec revises the spec now; you approve it again after.')
            self.state.setdefault('inbox_threads', []).append(back)
            self.save()
        except RuntimeError as err:
            print(f'ticket: could not post the conflict: {err}')
        before = self.spec.read_text()
        approved = {k: header(before, k) for k in ('Status', 'Approved by', 'Approved at')}
        error, _ = self.stage(f'/spec {t} unattended\nThe plan stopped at this SPEC CONFLICT. Revise the spec to '
                              f'resolve it, under the unattended rules; keep the decisions the owner made unless the '
                              f'conflict is about them. A fix that changes behavior or is High risk stays an OPEN '
                              f'QUESTION.\n\n{conflict}')
        if error:
            return self.stop(f'/spec after the plan conflict {error}')
        if approved['Status'] == 'Approved' and not open_questions(self.spec.read_text()):
            set_header(self.spec, {'Status': 'Approved', 'Approved by': approved['Approved by'],
                                   'Approved at': approved['Approved at']})
            self.commit(f'{t}: spec fixed for the plan conflict by default; approval kept (ADR 0115)')
            self.progress(':white_check_mark: The conflict was fixed by default (Low/Medium risk); your approval '
                          'stands. Planning again.')
            return None
        set_header(self.spec, {'Status': 'Draft', 'Approved by': '—', 'Approved at': '—'})
        self.commit(f'{t}: spec revised for the plan conflict')
        return self.settle_spec()

    def make_plan(self):
        t = self.ticket
        if (self.plan.exists() and has_conflict(self.plan.read_text()) and not self.plan_stale()
                and self.state.get('conflicts', 0) < 2):             # this spec already has a conflict: no new /plan
            result = self.back_to_spec(conflict_text(self.plan.read_text()))
            if result is not None:
                return result
        error, text = self.stage(f'/plan {t}')
        if error:
            return self.stop(f'/plan {error}')
        if not self.plan.exists():
            return self.stop(f'/plan wrote no {self.plan}')
        plan = self.plan.read_text()
        if has_conflict(plan) and self.state.get('conflicts', 0) < 2:
            result = self.back_to_spec(conflict_text(plan))
            return self.make_plan() if result is None else result
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


def plain(text):
    """Slack mrkdwn as plain text for a Jira comment: no emoji codes, bold, code or mentions."""
    text = re.sub(r':[a-z0-9_+-]+:\s?', '', text)
    text = re.sub(r'<@[A-Z0-9]+>\s?', '', text)
    text = re.sub(r'(?<!\w)[*_`](.+?)[*_`](?!\w)', r'\1', text)
    return '\n'.join(l.rstrip() for l in text.splitlines()).strip()


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


def alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def claim(path):
    """Take the ticket's lock for this process. Returns the live holder's record instead when another run
    on this host has it; a dead holder's lock is taken over."""
    holder = claim_holder(path)
    if holder:
        return holder
    try:
        gone = json.loads(path.read_text()).get('pid')
    except (OSError, ValueError):
        gone = None
    if gone:
        print(f'ticket: taking over the run of pid {gone}, which is gone')
    path.write_text(json.dumps({'pid': os.getpid(), 'host': socket.gethostname(), 'cwd': os.getcwd(),
                                'started': datetime.datetime.now().isoformat(timespec='seconds')}) + '\n')
    return None


def release(path):
    try:
        if json.loads(path.read_text()).get('pid') == os.getpid():
            path.unlink()
    except (OSError, ValueError):
        pass


def watch(args, search=None, start=None, rounds=None):
    """From the main checkout on its default branch: every --poll seconds, start `ticket.py <KEY>` for each
    open issue with --label, up to --jobs at once, most urgent first. A finished run is not started again:
    done (0) stays done; stopped (1, 2) waits until the label is taken off and put back; waiting (3) and
    paused (4) go again at the next poll. Children log to <git-common-dir>/handoff/<KEY>-ticket.out.
    `search`, `start` and `rounds` are for tests."""
    rc, _ = pl.git('rev-parse', '--git-dir')
    branch = pl.git('symbolic-ref', '--short', '-q', 'HEAD')[1]
    if rc or branch != default_branch():
        print(f'ticket: --watch runs in the main checkout on {default_branch() if not rc else "its default branch"} '
              f'(branch is {branch or "detached"}); each ticket gets its own worktree')
        return NOT_CHECKOUT
    out_dir = Path(pl.git('rev-parse', '--path-format=absolute', '--git-common-dir')[1]) / 'handoff'
    out_dir.mkdir(parents=True, exist_ok=True)
    if search is None or start is None:
        binary, slack_model = os.environ.get('CLAUDE_BIN', 'claude'), os.environ.get('HARNESS_SLACK_MODEL', 'haiku')
        log = out_dir / 'watch.log'

        def search():
            return Jira(lambda prompt, tools: pl.claude(binary, prompt, 1, args.permission_mode, log, tools, slack_model)[:2],
                        '', write=False).labelled(args.label)

        def start(key):
            child = [sys.executable, '-u', str(Path(__file__).resolve()), key, '--budget', str(args.budget), '--wait',
                     str(args.wait), '--poll', str(args.poll), '--permission-mode', args.permission_mode]
            out = open(out_dir / f'{key}-ticket.out', 'a')
            return subprocess.Popen(child, stdout=out, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                    env={**os.environ, 'HARNESS_LABEL': args.label})
    print(f'ticket: watching Jira for label "{args.label}" every {args.poll}s, {args.jobs} at once, from {os.getcwd()}')
    running, finished, held = {}, {}, set()      # key → process; key → exit code; stopped until relabelled
    rounds_left = rounds
    while rounds_left is None or rounds_left > 0:
        rounds_left = None if rounds_left is None else rounds_left - 1
        for key, proc in list(running.items()):
            if proc.poll() is not None:
                finished[key] = running.pop(key).returncode
                print(f'  {datetime.datetime.now():%H:%M} {key} exited {finished[key]}'
                      + (': stopped; take the label off and on to run it again' if finished[key] in (STOPPED, NOT_CHECKOUT) else ''))
                if finished[key] in (STOPPED, NOT_CHECKOUT):
                    held.add(key)
        try:
            keys = search()
        except RuntimeError as err:
            print(f'ticket: could not search Jira: {err}')
            keys = None
        if keys is not None:
            held &= set(keys)                     # the label came off: a later put-back starts it again
            for key in keys:
                if len(running) >= args.jobs:
                    break
                if key in running or key in held or finished.get(key) == DONE:
                    continue
                if claim_holder(out_dir / f'{key}-ticket.lock') or shipped(out_dir / f'{key}-ticket.json'):
                    continue                      # a run started by hand holds it, or an earlier one finished
                running[key] = start(key)
                print(f'  {datetime.datetime.now():%H:%M} {key} started (pid {running[key].pid}); output: {out_dir}/{key}-ticket.out')
        if rounds_left == 0:
            break
        try:
            pl.sleep(args.poll)
        except KeyboardInterrupt:
            print(f'\nticket: watch ends; {len(running)} run(s) go on by themselves: {", ".join(running) or "none"}')
            break
    return DONE


def shipped(state_file):
    try:
        return bool(json.loads(state_file.read_text()).get('ship'))
    except (OSError, ValueError):
        return False


def claim_holder(path):
    """The live holder of a lock, or None."""
    try:
        held = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    pid = held.get('pid')
    return held if pid and held.get('host') == socket.gethostname() and alive(pid) else None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('ticket', nargs='?', help='the Jira key (LD-503) or the ticket URL')
    parser.add_argument('--watch', action='store_true',
                        help='no ticket: from the main checkout, start a run for every open Jira issue with --label')
    parser.add_argument('--label', default='harness-run', help='the Jira label --watch starts on (default harness-run)')
    parser.add_argument('--jobs', type=int, default=2, help='how many tickets --watch runs at once (default 2)')
    parser.add_argument('--reply', help='your answer when Slack is not configured, e.g. "1A 2B LD-1"')
    parser.add_argument('--wait', type=float, default=8,
                        help='with Slack: keep checking for your answer this many hours instead of exiting (0: exit)')
    parser.add_argument('--poll', type=int, default=90, help='seconds between Slack checks while waiting (default 90)')
    parser.add_argument('--until', choices=('plan',), help='stop after this stage (approved plan, no /build)')
    parser.add_argument('--budget', type=float, default=10, help='--max-budget-usd per stage (default 10)')
    parser.add_argument('--permission-mode', default='',
                        help='claude -p permission mode; empty (the default) uses your settings.json')
    args = parser.parse_args(argv)
    if args.watch:
        return watch(args)
    key = ticket_key(args.ticket or '')
    if not key:
        print(f'ticket: no Jira key in "{args.ticket}"; give LD-503 or the ticket URL, or --watch')
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
    common = pl.git('rev-parse', '--path-format=absolute', '--git-common-dir')[1]
    log = Path(common) / 'handoff' / f'{args.ticket}-ticket.log'
    log.parent.mkdir(parents=True, exist_ok=True)
    lock = log.with_suffix('.lock')
    holder = claim(lock)                                # one run per ticket; a dirty tree is often its /build
    if holder:
        print(f'ticket: {args.ticket} is running already: pid {holder["pid"]} since {holder.get("started")} '
              f'in {holder.get("cwd")}')
        return BUSY
    try:
        return drive(args, log)
    finally:
        release(lock)


def drive(args, log):
    """The run itself, under the ticket's lock."""
    binary, key = os.environ.get('CLAUDE_BIN', 'claude'), args.ticket
    dirty = pl.git('status', '--porcelain')[1]          # the checkout the ticket runs in
    if dirty:
        print(f'ticket: {os.getcwd()} has uncommitted changes. Commit or stash them first:')
        print('\n'.join('  ' + line for line in dirty.splitlines()[:20]))
        return NOT_CHECKOUT

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
            m = re.match(r'  (/\w+ \S+.*?)\s+\$(\d+\.\d\d)(?: · stage (\d+))?$', line.rstrip('\n'))
            if m and step:
                step(m.group(1), m.group(2), m.group(3))
        return proc.wait()

    jira = Jira(claude, key, write=os.environ.get('HARNESS_JIRA_WRITE', '1').strip() not in ('0', ''))

    channel, owner = os.environ.get('HARNESS_SLACK_CHANNEL'), os.environ.get('HARNESS_SLACK_OWNER')
    if channel and owner:
        out = Slack(lambda prompt: claude(prompt, SLACK_TOOLS), channel, owner, os.environ.get('HARNESS_SLACK_MENTION', ''))
    else:
        out = Terminal(log.with_suffix('.md'), args.reply)
    print(f'ticket: {args.ticket} in {os.getcwd()}')
    print(f'  messages: {log.parent}/{args.ticket}-ticket-<n>.md · log: {log}')
    print(f'  questions and results: ' + (f'Slack channel {channel}' if channel and owner else f'this terminal and {log.with_suffix(".md")}'))
    waits = isinstance(out, Slack) and args.wait > 0
    deadline = time.monotonic() + args.wait * 3600
    while True:
        try:
            result = Run(args.ticket, out, claude, pipeline, args.budget, args.until, jira).go()
        except RuntimeError as err:
            print(f'ticket: {err}')
            return STOPPED
        if result != WAITING or not waits or time.monotonic() > deadline:
            break
        print(f'ticket: waiting for your answer in Slack; checking every {args.poll}s (Ctrl+C to leave; '
              f'run it again later to go on)')
        try:
            time.sleep(args.poll)
        except KeyboardInterrupt:
            print()
            break
    print({DONE: 'ticket: reached /ship.', STOPPED: 'ticket: stopped.', WAITING: 'ticket: waiting for your answer.',
           PAUSED: f'ticket: paused after /{args.until}; run it again without --until to go on.'}.get(result, ''))
    return result


if __name__ == '__main__':
    sys.exit(main())
