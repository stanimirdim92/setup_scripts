#!/usr/bin/env python3
"""How much person-time did a ticket take? (ADR 0112)

Automation should be loosened only while it holds up: fewer stops for a
person, and no more bugs after merge. This counts the stops for one ticket
from what the pipeline already records, and prints the row for the
"Per ticket" table in the harness's observation-log.md:

- decisions: `### DEC-###` headings in the spec, each one a choice a person made;
- open items: `OPEN-###` ids in docs/tasks/<TICKET>-open.md, raised after the plan;
- approvals: commits that set an `Approved at:` line in the spec or plan,
  so a reapproval counts again;
- review rounds: the ticket's review SARIF files;
- findings: how review findings ended (fixed, refuted, other).

The shipped-bugs column starts at 0. A later bug ticket whose spec names
this ticket under "Escaped From" adds one (ADR 0110).

Usage:
    ticket-stats.py LD-123
    ticket-stats.py LD-123 --json

Exit: 0 · 1 no spec for the ticket · 2 not in a git repository.
"""
import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path


def git(*args):
    out = subprocess.run(['git', *args], capture_output=True, text=True)
    return out.returncode, out.stdout


def stats(ticket, review_dir):
    spec = Path(f'docs/specs/{ticket}-SPEC.md')
    plan = Path(f'docs/tasks/{ticket}-plan.md')
    open_items = Path(f'docs/tasks/{ticket}-open.md')
    text = spec.read_text()
    found = {
        'ticket': ticket,
        'decisions': len(re.findall(r'^###\s+DEC-\d{3}\b', text, re.M)),
        'open_items': len(set(re.findall(r'\bOPEN-\d{3}\b', open_items.read_text()))) if open_items.exists() else 0,
    }
    paths = [str(p) for p in (spec, plan) if p.exists()]
    _, out = git('log', '--format=%H', r'-G^Approved at:\s*[0-9]', '--', *paths)
    found['approvals'] = len(out.split())
    rounds, endings = 0, {'fixed': 0, 'refuted': 0, 'other': 0}
    for path in sorted(Path(review_dir).glob(f'{ticket}-*.sarif')):
        if not re.fullmatch(rf'{re.escape(ticket)}-[0-9a-f]{{7,40}}\.sarif', path.name):
            continue
        rounds += 1
        try:
            data = json.loads(path.read_text())
        except ValueError:
            continue
        for run in data.get('runs', []):
            for r in run.get('results', []):
                end = r.get('properties', {}).get('resolution', 'open')
                endings[end if end in ('fixed', 'refuted') else 'other'] += 1
    found['review_rounds'] = rounds
    found['findings'] = endings
    return found


def row(s, today=None):
    f = s['findings']
    return (f'| {today or datetime.date.today().isoformat()} | {s["ticket"]} | {s["decisions"]} | '
            f'{s["open_items"]} | {s["approvals"]} | {s["review_rounds"]} | '
            f'{f["fixed"]} fixed, {f["refuted"]} refuted, {f["other"]} other | 0 |')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('ticket')
    parser.add_argument('--review-dir', type=Path)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    rc, common = git('rev-parse', '--path-format=absolute', '--git-common-dir')
    if rc:
        print('ticket-stats: not in a git repository', file=sys.stderr)
        return 2
    if not Path(f'docs/specs/{args.ticket}-SPEC.md').exists():
        print(f'ticket-stats: no docs/specs/{args.ticket}-SPEC.md', file=sys.stderr)
        return 1
    s = stats(args.ticket, args.review_dir or Path(common.strip()) / 'review')
    print(json.dumps(s, indent=2) if args.json else row(s))
    return 0


if __name__ == '__main__':
    sys.exit(main())
