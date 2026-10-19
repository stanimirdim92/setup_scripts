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
    your reply in its thread             "1A 2B" answers; the ticket id
                                         ("AB-11" or "AB11") approves the spec.
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
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('pipeline', HERE / 'pipeline.py')
pl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pl)

DONE, STOPPED, NOT_CHECKOUT, WAITING = 0, 1, 2, 3
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
        m = re.match(r'[-*]\s*Option\s+([A-Z])\s*[:—-]\s*(.+)', s)
        if m:
            cur['options'][m.group(1)] = m.group(2).strip()
            if re.search(r'\(recommended\)', m.group(2), re.I):
                cur['recommended'] = m.group(1)
            continue
        m = re.match(r'Risk:\s*(High|Medium|Low)', s, re.I)
        if m:
            cur['risk'] = m.group(1).capitalize()
            continue
        if s.startswith('→') or not s:
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

def parse_reply(text, ticket):
    """(answers {n: letter}, approved, defaults) from a reply like "1A 2b, approve AB-11" or "AB11"."""
    answers = {int(n): letter.upper() for n, letter in re.findall(r'(?<![\w-])(\d+)\s*([A-Za-z])\b', text)}
    key = re.sub(r'[^A-Z0-9]', '', ticket.upper())
    ids = {re.sub(r'[^A-Z0-9]', '', t.upper()) for t in re.findall(r'\b[A-Za-z]+-?\d+\b', text)}
    return answers, key in ids, bool(re.search(r'\bdefaults?\b', text, re.I))


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

    def __init__(self, run, channel, owner):
        self.run, self.channel, self.owner = run, channel, owner.lower()

    def post(self, text, thread=None):
        where = f'as a reply in the thread whose ts is {thread} ' if thread else ''
        error, out = self.run(f'Post this exact message to the Slack channel {self.channel} {where}with your Slack '
                              'tool. Change nothing in it. Then print only JSON: {"ts": "<the new message ts>"}.\n\n'
                              f'---\n{text}')
        data = first_json(out) if not error else None
        if not isinstance(data, dict) or not data.get('ts'):
            raise RuntimeError(f'Slack post failed: {error or out[:200]}')
        return str(data['ts'])

    def replies(self, ts):
        error, out = self.run(f'Read the replies in the Slack thread {ts} of channel {self.channel} with your Slack '
                              'tool. Print only JSON: a list of {"author": "<name and email>", "text": "<reply>", '
                              '"ts": "<reply ts>"}, oldest first, without the parent message.')
        data = first_json(out) if not error else None
        if not isinstance(data, list):
            raise RuntimeError(f'Slack read failed: {error or out[:200]}')
        return [r for r in data if isinstance(r, dict) and self.owner in str(r.get('author', '')).lower()]


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

def ask_text(ticket, spec_text):
    qs = open_questions(spec_text)
    lines = [f'*{ticket}* · {header(spec_text, "Status") or "Draft"} spec · `docs/specs/{ticket}-SPEC.md`']
    for q in qs:
        opts = '  '.join(f'{k}) {v}' for k, v in q['options'].items())
        lines.append(f'{q["n"]}. {q["title"]} [{q["risk"] or "risk not stated"}]  {opts}')
    taken = defaults_taken(spec_text)
    if taken:
        lines.append('Decided by default (Low/Medium risk; reply to change one):')
        lines += [f'• {t}' for t in taken]
    if qs:
        lines.append(f'Reply in this thread: "1A 2B", and "{ticket}" to approve once nothing is open.')
    else:
        lines.append(f'Nothing open. Reply "{ticket}" to approve the spec.')
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
        print(f'  {prompt.splitlines()[0]}')
        error, text = self.claude(prompt)
        (self.dir / f'{self.ticket}-ticket-{len(self.state.setdefault("log", [])) + 1}.md').write_text(text + '\n')
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

    def stop(self, why):
        self.out.post(f'*{self.ticket}* stopped: {why}\nLog: {self.dir}')
        return STOPPED

    def go(self):
        t = self.ticket
        if self.state.get('ship'):
            print(f'ticket: {t} already reached /ship: {self.state["ship"]}')
            return DONE
        if not self.spec.exists():
            for prompt in (f'/jira-ticket {t}', f'/spec {t} unattended'):
                error, text = self.stage(prompt)
                if error:
                    return self.stop(f'{prompt} {error}')
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
            rc = self.pipeline(t, self.budget)
            if rc != 0:
                return self.stop(f'pipeline.py exited {rc}; the review files and messages are in the log')
            self.state['pipeline_done'] = True
            self.save()

        reviews = sorted(self.dir.glob(f'{t}-*-REVIEW.md'), key=lambda p: int(p.name.split('-')[-2]))
        given = f'\n\nREVIEW result — {pl.SUPPLIED}\n\n{reviews[-1].read_text()}' if reviews else ''
        error, text = self.stage(f'/ship {t}{given}')
        if error:
            return self.stop(f'/ship {error}')
        result = pl.line(text, '(?:GO|NO-GO|SHIP BLOCKED)') or 'no GO / NO-GO line'
        self.out.post(f'*{t}* /ship: {result}\nNothing is pushed. Read the report: {self.dir}')
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
            self.out.post(f'Not a question and option here: {" ".join(bad)}. Nothing changed.', thread=ask['ts'])
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
            self.out.post(f'*{t}* spec approved. Planning next.', thread=ask['ts'])
            return None
        if approved:
            still = ', '.join('Q%d' % q['n'] for q in left)
            self.out.post(f'Still open: {still}. Answer them, then approve.', thread=ask['ts'])
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


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('ticket')
    parser.add_argument('--reply', help='your answer when Slack is not configured, e.g. "1A 2B LD-1"')
    parser.add_argument('--budget', type=float, default=10, help='--max-budget-usd per stage (default 10)')
    parser.add_argument('--permission-mode', default='acceptEdits')
    args = parser.parse_args(argv)
    binary = os.environ.get('CLAUDE_BIN', 'claude')

    rc, _ = pl.git('rev-parse', '--git-dir')
    branch = pl.git('symbolic-ref', '--short', '-q', 'HEAD')[1]
    if rc or not branch or branch in pl.PROTECTED:
        print(f'ticket: run it in the ticket checkout (branch is {branch or "detached"})')
        return NOT_CHECKOUT
    common = pl.git('rev-parse', '--path-format=absolute', '--git-common-dir')[1]
    log = Path(common) / 'handoff' / f'{args.ticket}-ticket.log'
    log.parent.mkdir(parents=True, exist_ok=True)

    def claude(prompt):
        error, text, _ = pl.claude(binary, prompt, args.budget, args.permission_mode, log)
        return error, text

    def pipeline(ticket, budget):
        return subprocess.run([sys.executable, str(HERE / 'pipeline.py'), ticket, '--yes', '--budget', str(budget),
                               '--permission-mode', args.permission_mode]).returncode

    channel, owner = os.environ.get('HARNESS_SLACK_CHANNEL'), os.environ.get('HARNESS_SLACK_OWNER')
    if channel and owner:
        out = Slack(claude, channel, owner)
    else:
        out = Terminal(log.with_suffix('.md'), args.reply)
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
