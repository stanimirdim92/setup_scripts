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
    text = path.read_text()
    for key, value in values.items():
        pattern = rf'^{re.escape(key)}:.*$'
        if re.search(pattern, text, re.M):
            text = re.sub(pattern, f'{key}: {value}', text, count=1, flags=re.M)
        else:
            raise SystemExit(f'ticket: {path} has no "{key}:" line')
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

    def __init__(self, run, channel, owner, mention=''):
        self.run, self.channel, self.owner, self.mention = run, channel, owner.lower(), mention

    def post(self, text, thread=None):
        if self.mention:
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
        error, out = self.run(f'Read the replies in the Slack thread {ts} of channel {self.channel} with your Slack '
                              'tool. Print only JSON: a list of {"author": "<name and email>", "text": "<reply, verbatim>", '
                              '"ts": "<reply ts>"}, oldest first, without the parent message.')
        data = first_json(out) if not error else None
        if not isinstance(data, list):
            raise RuntimeError(f'Slack read failed: {error or out[:200]}')
        return [{**r, 'text': answers_part(str(r.get('text', '')))} for r in data
                if isinstance(r, dict) and self.owner in str(r.get('author', '')).lower()
                and answers_part(str(r.get('text', ''))) is not None]


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
    def __init__(self, ticket, out, claude, pipeline, budget):
        self.ticket, self.out, self.claude, self.pipeline, self.budget = ticket, out, claude, pipeline, budget
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

    def stage(self, prompt):
        print(f'  {datetime.datetime.now():%H:%M} {prompt.splitlines()[0][:110]}')
        error, text = self.claude(prompt)
        saved = self.dir / f'{self.ticket}-ticket-{len(self.state.setdefault("log", [])) + 1}.md'
        saved.write_text(text + '\n')
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

        if not self.plan.exists() or header(self.plan.read_text(), 'Status') != 'Approved':
            result = self.make_plan()
            if result is not None:
                return result

        if not self.state.get('pipeline_done'):
            print(f'  spec and plan are approved; pipeline.py runs /build, /test and /review')
            rc = self.pipeline(t, self.budget)
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

    def make_plan(self):
        t = self.ticket
        error, text = self.stage(f'/plan {t}')
        if error:
            return self.stop(f'/plan {error}')
        if not self.plan.exists():
            return self.stop(f'/plan wrote no {self.plan}')
        plan = self.plan.read_text()
        if 'SPEC CONFLICT' in plan or open_questions(plan):
            self.commit(f'{t}: plan draft')
            return self.stop('the plan raised a SPEC CONFLICT or an open question; read the plan')
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
    dirty = pl.git('status', '--porcelain')[1]
    if dirty:
        print('ticket: the checkout has uncommitted changes. Commit or stash them first:')
        print('\n'.join('  ' + line for line in dirty.splitlines()[:20]))
        return NOT_CHECKOUT
    common = pl.git('rev-parse', '--path-format=absolute', '--git-common-dir')[1]
    log = Path(common) / 'handoff' / f'{args.ticket}-ticket.log'
    log.parent.mkdir(parents=True, exist_ok=True)

    allowed = tuple(t.strip() for t in os.environ.get('HARNESS_ALLOWED_TOOLS', '').split(',') if t.strip()) \
        or READ_TOOLS

    def claude(prompt, tools=None):
        started = time.monotonic()
        budget = 1 if tools else args.budget                  # a Slack post or read is small
        error, text, cost = pl.claude(binary, prompt, budget, args.permission_mode, log,
                                      tools if tools else allowed)
        took = int(time.monotonic() - started)
        print(f'    {"slack " if tools else ""}{took // 60}m{took % 60:02d}s, ${cost:.2f}: '
              + (f'ERROR {error}' if error else first_line(text)))
        return error, text

    def pipeline(ticket, budget):
        return subprocess.run([sys.executable, str(HERE / 'pipeline.py'), ticket, '--yes', '--budget', str(budget),
                               '--permission-mode', args.permission_mode]).returncode

    channel, owner = os.environ.get('HARNESS_SLACK_CHANNEL'), os.environ.get('HARNESS_SLACK_OWNER')
    if channel and owner:
        out = Slack(lambda prompt: claude(prompt, SLACK_TOOLS), channel, owner, os.environ.get('HARNESS_SLACK_MENTION', ''))
    else:
        out = Terminal(log.with_suffix('.md'), args.reply)
    print(f'ticket: {args.ticket} in {os.getcwd()}')
    print(f'  messages: {log.parent}/{args.ticket}-ticket-<n>.md · log: {log}')
    print(f'  questions and results: ' + (f'Slack channel {channel}' if channel and owner else f'this terminal and {log.with_suffix(".md")}'))
    try:
        result = Run(args.ticket, out, claude, pipeline, args.budget).go()
    except RuntimeError as err:
        print(f'ticket: {err}')
        return STOPPED
    print({DONE: 'ticket: reached /ship.', STOPPED: 'ticket: stopped.', WAITING: 'ticket: waiting for your answer.'}
          .get(result, ''))
    return result


if __name__ == '__main__':
    sys.exit(main())
