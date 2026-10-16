#!/usr/bin/env python3
"""Check that a ticket's spec, plan, todo and open items still agree after planning.

check-spec and check-plan run once, when /spec and /plan write their files.
Work after that — decisions added in conversation, commits made outside
/build, gaps deferred "for /review" — changed nothing they look at, so the
records drifted with no gate noticing (LD-365, ADR 0088). /review and /ship
run this; any session can run it on request.

Failures (exit 1):
  - the spec has REQ or DEC ids that the plan's pinned spec revision does not,
    and the plan is not `Needs replan`; or the pin does not resolve;
  - a plan or todo line says "known gap", "deferred", "follow-up" or
    "for /review" and names no `OPEN-###` id; or a spec, plan or todo line
    names an `OPEN-###` id the open-items file does not have;
  - an open item has no owner or no disposition;
  - a todo packet has no `**Status:**` line;
  - with --ship: an open item is still `Open`, or a packet is `Pending` and
    the plan index does not mark it superseded.

Warnings:
  - a DEC names a backticked identifier from a `Never:` line, or from an
    earlier DEC that says something stays unchanged ("does not change",
    "untouched", "unchanged", "never"), and has no `Amends:` line;
  - commits that name the ticket have no task id (`Task:` trailer, or the
    older `(LD-123 T002)` subject), change more than the ticket's docs, and
    the open-items file does not name their short sha. One line lists them.

Usage:
    check-ledger.py LD-123 [--ship] [--base origin/main]
Run from the project root. It reads docs/specs/LD-123-SPEC.md and
docs/tasks/LD-123-{plan,todo,open}.md; a missing plan, todo or open file is
treated as empty.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

SPEC_ID = re.compile(r'^###\s+(?:Requirement:\s+)?((?:REQ|DEC)-\d{3})\b', re.M)
DEC_HEADING = re.compile(r'^###\s+(DEC-\d{3})\b.*$', re.M)
NO_CHANGE = re.compile(r'\bdoes not change\b|\buntouched\b|\bunchanged\b|\bnever\b', re.I)
DEFERRAL = re.compile(r'\bknown gap\b|\bdeferred\b|\bfollow-?up\b|\bfor /review\b', re.I)
OPEN_ID = re.compile(r'\bOPEN-\d{3}\b')
OPEN_ROW = re.compile(r'^\|\s*(OPEN-\d{3})\s*\|(.*)$', re.M)
PACKET = re.compile(r'^##\s*(T\d{3})\s*:', re.M)
SUPERSEDED = re.compile(r'~~\s*(T\d{3})\s*~~')
TICKS = re.compile(r'`([^`\s]+)`')
EMPTY = ('', '—', '-', 'n/a')


def header(text, key):
    m = re.search(rf'^\**{re.escape(key)}:?\**:?\s*(.*)$', text or '', re.M)
    return m.group(1).strip() if m else None


def open_items(text):
    """{OPEN id: (line, owner, disposition)} from the register table."""
    items = {}
    for m in OPEN_ROW.finditer(text or ''):
        cells = [c.strip() for c in m.group(2).rstrip().rstrip('|').split('|')]
        cells += [''] * (4 - len(cells))
        items[m.group(1)] = (text[:m.start()].count('\n') + 1, cells[2], cells[3])
    return items


def decisions(spec):
    """[(DEC id, heading and body)] in spec order."""
    heads = list(DEC_HEADING.finditer(spec))
    out = []
    for i, m in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(spec)
        body = re.split(r'^#{2,3}\s', spec[m.end():end], maxsplit=1, flags=re.M)[0]
        out.append((m.group(1), m.group(0) + body))
    return out


def protected(spec):
    """{identifier: what protects it} from Never lines and from every identifier
    of a DEC that says something stays unchanged. A DEC's no-change rule and the
    names it protects are often in different sentences, so the whole DEC counts."""
    keep = {}
    for line in spec.splitlines():
        if re.search(r'\bNever:', line):
            for ident in TICKS.findall(line):
                keep.setdefault(ident, 'a Boundaries Never line')
    for dec, body in decisions(spec):
        if NO_CHANGE.search(body):
            for ident in TICKS.findall(body):
                keep.setdefault(ident, dec)
    return keep


def earlier(rule, dec):
    """True when the rule binds dec: a Never line always, a DEC only an earlier one."""
    return not rule.startswith('DEC-') or int(rule[4:]) < int(dec[4:])


def check(spec, pinned, plan, todo, open_text, commits, ship=False):
    """(failures, warnings), each a list of (file label, line, message).

    pinned is the spec text at the plan's pin, or None when it did not resolve.
    commits is [(sha, subject, task id)] for the ticket's commits that change
    more than its docs.
    """
    fail, warn = [], []
    items = open_items(open_text)

    if plan is not None:
        if pinned is None:
            fail.append(('plan', 1, 'the `Spec revision:` pin does not resolve; re-pin it '
                                    '(plan-quality-gates.md §2)'))
        else:
            added = sorted(set(SPEC_ID.findall(spec)) - set(SPEC_ID.findall(pinned)))
            if added and (header(plan, 'Status') or '') != 'Needs replan':
                fail.append(('plan', 1, f'the spec gained {", ".join(added)} after the plan pin; set the plan '
                                        '`Needs replan` and replan, or re-pin (plan-quality-gates.md §2)'))

    for label, text in (('spec', spec), ('plan', plan), ('todo', todo)):
        for n, line in enumerate((text or '').splitlines(), 1):
            named = OPEN_ID.findall(line)
            if label != 'spec' and DEFERRAL.search(line) and not named:
                fail.append((label, n, 'deferred work names no OPEN-### id; add it to the open-items file '
                                       '(plan-quality-gates.md §6)'))
            for oid in named:
                if oid not in items:
                    fail.append((label, n, f'{oid} is not in the open-items file'))

    for oid, (n, owner, disposition) in sorted(items.items()):
        if owner.lower() in EMPTY or disposition.lower() in EMPTY:
            fail.append(('open', n, f'{oid} needs an owner and a disposition'))
        elif ship and disposition.split()[0].rstrip('—-') == 'Open':
            fail.append(('open', n, f'{oid} is still Open'))

    superseded = set(SUPERSEDED.findall(plan or ''))
    starts = list(PACKET.finditer(todo or ''))
    for i, m in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else len(todo)
        body, tid, n = todo[m.start():end], m.group(1), todo[:m.start()].count('\n') + 1
        status = re.search(r'\*\*Status:\*\*\s*(\w+)', body)
        if not status:
            fail.append(('todo', n, f'{tid} has no **Status:** line'))
        elif ship and status.group(1) == 'Pending' and tid not in superseded:
            fail.append(('todo', n, f'{tid} is Pending; finish it, or mark it superseded in the plan index'))

    keep = protected(spec)
    for dec, body in decisions(spec):
        hits = sorted(i for i in set(TICKS.findall(body)) if i in keep and earlier(keep[i], dec))
        if hits and not re.search(r'\bAmends:', body):
            what = '; '.join(f'`{i}` ({keep[i]})' for i in hits)
            warn.append(('spec', 1, f'{dec} names {what} and has no `Amends:` line saying it changes that rule'))

    loose = [sha[:7] for sha, _, task in commits if not task.strip() and sha[:7] not in (open_text or '')]
    if loose:
        shown = ', '.join(loose[:10]) + (f' and {len(loose) - 10} more' if len(loose) > 10 else '')
        warn.append(('git', 1, f'{len(loose)} commit(s) have no task id and are not in the open-items file: {shown}'))
    return fail, warn


def git(*args):
    return subprocess.run(['git', *args], capture_output=True, text=True, check=True).stdout


def branch_commits(ticket, base):
    """The ticket's commits in base..HEAD (named in the subject or a Refs:
    trailer) that change more than its own docs, with their task id."""
    ours = (f'docs/specs/{ticket}-', f'docs/tasks/{ticket}-')
    out = []
    for row in git('log', '--format=%H%x1f%s%x1f%(trailers:key=Task,valueonly,separator=%x2C)'
                   '%x1f%(trailers:key=Refs,valueonly,separator=%x2C)', f'{base}..HEAD').splitlines():
        sha, subject, task, refs = (row.split('\x1f') + ['', '', ''])[:4]
        if not re.search(rf'\b{re.escape(ticket)}\b', f'{subject} {refs}'):
            continue
        task = task or ' '.join(re.findall(r'\bT\d{3}\b', subject))
        files = git('diff-tree', '--no-commit-id', '--name-only', '-r', sha).split()
        if any(not f.startswith(ours) for f in files):
            out.append((sha, subject, task))
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('ticket')
    parser.add_argument('--ship', action='store_true', help='also fail on Open items and Pending tasks')
    parser.add_argument('--base', help='where the ticket branch starts (default: merge-base with origin/HEAD)')
    args = parser.parse_args(argv)

    t = args.ticket
    paths = {'spec': Path(f'docs/specs/{t}-SPEC.md'), 'plan': Path(f'docs/tasks/{t}-plan.md'),
             'todo': Path(f'docs/tasks/{t}-todo.md'), 'open': Path(f'docs/tasks/{t}-open.md')}
    read = lambda p: p.read_text(encoding='utf-8') if p.exists() else None
    spec = read(paths['spec'])
    if spec is None:
        print(f'check-ledger: {paths["spec"]} not found (run from the project root)', file=sys.stderr)
        return 2
    plan, todo, open_text = read(paths['plan']), read(paths['todo']), read(paths['open'])

    pinned = None
    pin = re.match(r'git-commit:([0-9a-f]+):(\S+)', header(plan, 'Spec revision') or '')
    if pin:
        try:
            pinned = git('show', f'{pin.group(1)}:{pin.group(2)}')
        except (subprocess.CalledProcessError, OSError):
            pinned = None

    notes, commits = [], []
    try:
        remote_head = git('for-each-ref', '--format=%(symref:short)', 'refs/remotes/*/HEAD').split()
        base = args.base or git('merge-base', 'HEAD', (remote_head or ['origin/main'])[0]).strip()
        commits = branch_commits(t, base)
    except (subprocess.CalledProcessError, OSError):
        notes.append(('git', 1, 'cannot find the branch base; commits not checked (pass --base)'))

    fail, warn = check(spec, pinned, plan, todo, open_text, commits, args.ship)
    for label, n, msg in fail:
        print(f'FAIL {paths.get(label, label)}:{n}  {msg}')
    for label, n, msg in warn + notes:
        print(f'warn {paths.get(label, label)}:{n}  {msg}')
    print(f'check-ledger: {len(fail)} failure(s), {len(warn) + len(notes)} warning(s)', file=sys.stderr)
    return 1 if fail else 0


if __name__ == '__main__':
    sys.exit(main())
