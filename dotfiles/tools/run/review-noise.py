#!/usr/bin/env python3
"""Count how review findings ended, per reviewer, from the review SARIF files.

/review writes one SARIF file per round to $(git rev-parse --git-common-dir)/review/,
and /ship writes each finding's resolution into it (ADR 0093). A finding that
ends `fixed` was worth raising. One that ends `refuted` was noise: the code was
already right. `accepted`, `deferred` and `follow-up` are real but not fixed
now; `declined` is an ADVISORY the author chose not to take.

Usage:
    review-noise.py                     # this repository's review files
    review-noise.py --dir PATH          # another review directory
    review-noise.py --ticket LD-380     # one ticket only
    review-noise.py --json
"""
import argparse
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

ENDINGS = ('fixed', 'refuted', 'accepted', 'deferred', 'follow-up', 'declined', 'open')
NAME = re.compile(r'^(?P<ticket>.+)-(?P<sha>[0-9a-f]{7,40})\.sarif$')


def review_dir():
    out = subprocess.run(['git', 'rev-parse', '--git-common-dir'], capture_output=True, text=True)
    if out.returncode:
        raise SystemExit('review-noise: not in a git repository; pass --dir')
    return Path(out.stdout.strip()).resolve() / 'review'


def tally(files):
    """{'reviewers': {name: Counter}, 'dispositions': Counter of (disposition, ending),
    'verification': Counter of (verdict, ending), 'rounds': {ticket: n}}"""
    reviewers, dispositions, verification = defaultdict(Counter), Counter(), Counter()
    rounds = Counter()
    for path in files:
        m = NAME.match(path.name)
        if m:
            rounds[m.group('ticket')] += 1
        try:
            data = json.loads(path.read_text())
        except (OSError, ValueError) as err:
            print(f'review-noise: skipped {path.name}: {err}', file=sys.stderr)
            continue
        for run in data.get('runs', []):
            name = run.get('tool', {}).get('driver', {}).get('name', '?')
            for result in run.get('results', []):
                props = result.get('properties', {})
                ending = props.get('resolution', 'open')
                ending = ending if ending in ENDINGS else 'open'
                reviewers[name][ending] += 1
                reviewers[name]['total'] += 1
                dispositions[(props.get('disposition', '?'), ending)] += 1
                if props.get('verification'):
                    verification[(props['verification'], ending)] += 1
    return {'reviewers': reviewers, 'dispositions': dispositions,
            'verification': verification, 'rounds': dict(rounds)}


def report(t):
    lines = ['FINDINGS BY REVIEWER (how each ended)',
             f'  {"reviewer":<30} {"total":>5} ' + ' '.join(f'{e:>9}' for e in ENDINGS) + '   noise']
    for name, c in sorted(t['reviewers'].items()):
        closed = c['total'] - c['open']
        noise = f'{c["refuted"] / closed:.0%}' if closed else '—'
        lines.append(f'  {name:<30} {c["total"]:>5} ' + ' '.join(f'{c[e]:>9}' for e in ENDINGS) + f'   {noise:>5}')
    lines += ['', 'BY DISPOSITION']
    for disp in ('BLOCKER', 'REQUIRED', 'ADVISORY'):
        row = {e: t['dispositions'][(disp, e)] for e in ENDINGS}
        if any(row.values()):
            lines.append(f'  {disp:<9} ' + ', '.join(f'{e} {n}' for e, n in row.items() if n))
    if t['verification']:
        lines += ['', 'BLOCKER CHECK VERDICT vs ENDING (ADR 0092)']
        for verdict in ('CONFIRMED', 'REFUTED', 'UNSURE'):
            row = {e: t['verification'][(verdict, e)] for e in ENDINGS}
            if any(row.values()):
                lines.append(f'  {verdict:<9} ' + ', '.join(f'{e} {n}' for e, n in row.items() if n))
    if t['rounds']:
        many = {k: v for k, v in t['rounds'].items() if v > 1}
        lines += ['', f'REVIEW ROUNDS: {len(t["rounds"])} ticket(s), mean {sum(t["rounds"].values()) / len(t["rounds"]):.2f}'
                  + (f'; more than one: {", ".join(f"{k} ({v})" for k, v in sorted(many.items()))}' if many else '')]
    lines += ['', 'noise = refuted / closed findings. A reviewer with high noise is a candidate for a',
              'REVIEW.md rule or a prompt change; measure the change with the review eval.']
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--dir', type=Path)
    parser.add_argument('--ticket')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    directory = args.dir or review_dir()
    files = sorted(directory.glob(f'{args.ticket}-*.sarif' if args.ticket else '*.sarif'))
    if not files:
        print(f'review-noise: no review files in {directory}', file=sys.stderr)
        return 1
    t = tally(files)
    if args.json:
        print(json.dumps({'reviewers': {k: dict(v) for k, v in t['reviewers'].items()},
                          'rounds': t['rounds']}, indent=2))
    else:
        print(report(t))
    return 0


if __name__ == '__main__':
    sys.exit(main())
