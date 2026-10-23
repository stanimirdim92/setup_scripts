#!/usr/bin/env python3
"""Count how review findings ended, per reviewer, from the review SARIF files.

/review writes one SARIF file per round to $(git rev-parse --git-common-dir)/review/,
and /ship writes each finding's resolution into it (ADR 0093). A finding that
ends `fixed` was worth raising. One that ends `refuted` was noise: the code was
already right. `answered` is a question the approved spec already answers, or
a restatement of the owner's own request: neither a bug found nor a false
positive, so it counts in no noise figure. `accepted`, `deferred` and
`follow-up` are real but not fixed now; `declined` is an ADVISORY the author
chose not to take.

Each finding also carries a `class`, a short slug for the kind of defect
(`missing-tenant-scope`, `n-plus-one`). A class that keeps coming back across
tickets should be fixed at the source, not found again on the next ticket
(ADR 0105): a lint rule when a tool can catch it, a REVIEW.md "Always check"
line when it is a project convention, a CLAUDE.md line when it is how code
gets written. A class that keeps ending `refuted` belongs under REVIEW.md
"Do not report".

Usage:
    review-noise.py                     # this repository's review files
    review-noise.py --dir PATH          # another review directory
    review-noise.py --ticket LD-380     # one ticket only
    review-noise.py --classes           # class names used so far, to reuse
    review-noise.py --repeats [--min-tickets 3]   # classes to fix at the source
    review-noise.py --json
"""
import argparse
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

ENDINGS = ('fixed', 'refuted', 'answered', 'accepted', 'deferred', 'follow-up', 'declined', 'open')
UNJUDGED = ('open', 'answered')    # not judged real or false: outside every noise figure
NAME = re.compile(r'^(?P<ticket>.+)-(?P<sha>[0-9a-f]{7,40})\.sarif$')


def review_dir():
    out = subprocess.run(['git', 'rev-parse', '--git-common-dir'], capture_output=True, text=True)
    if out.returncode:
        raise SystemExit('review-noise: not in a git repository; pass --dir')
    return Path(out.stdout.strip()).resolve() / 'review'


def tally(files):
    """{'reviewers': {name: Counter}, 'dispositions': Counter of (disposition, ending),
    'verification': Counter of (verdict, ending), 'rounds': {ticket: n},
    'classes': {class: {ticket: [(ending, message)]}}}"""
    reviewers, dispositions, verification = defaultdict(Counter), Counter(), Counter()
    rounds, classes = Counter(), defaultdict(lambda: defaultdict(list))
    for path in files:
        m = NAME.match(path.name)
        ticket = m.group('ticket') if m else path.stem
        if m:
            rounds[ticket] += 1
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
                if props.get('class'):
                    text = result.get('message', {}).get('text', '')
                    classes[props['class'].strip().lower()][ticket].append((ending, text))
    return {'reviewers': reviewers, 'dispositions': dispositions,
            'verification': verification, 'rounds': dict(rounds),
            'classes': {k: dict(v) for k, v in classes.items()}}


def repeats(t, min_tickets=3):
    """Classes seen in at least min_tickets tickets, with what to do about each.

    A finding is one per ticket: a class raised five times on one ticket is
    one fix round, not a pattern. 'fix' when most judged findings were real,
    'silence' when most were refuted, 'watch' while none is judged yet.
    `answered` is not judged: the spec settled it, not the code."""
    out = []
    for name, tickets in sorted(t['classes'].items()):
        if len(tickets) < min_tickets:
            continue
        endings = Counter(e for found in tickets.values() for e, _ in found)
        judged = sum(endings.values()) - sum(endings[e] for e in UNJUDGED)
        if not judged:
            action = 'watch'
        elif endings['refuted'] * 2 > judged:
            action = 'silence'
        else:
            action = 'fix'
        example = next((m for found in tickets.values() for _, m in found if m), '')
        out.append({'class': name, 'tickets': sorted(tickets), 'endings': dict(endings),
                    'action': action, 'example': example[:160]})
    return out


ACTIONS = {
    'fix': 'real each time: fix at the source. A lint rule if a tool can catch it; '
           'else a REVIEW.md "Always check" line if it is a project convention; '
           'else a CLAUDE.md line if it is how the code gets written.',
    'silence': 'mostly refuted: add it to REVIEW.md "Do not report", or narrow the reviewer prompt.',
    'watch': 'nothing judged yet (open or answered): decide after /ship resolves them.',
}


def repeats_report(found, min_tickets):
    if not found:
        return f'Repeated classes: none in {min_tickets} or more tickets.'
    lines = [f'REPEATED CLASSES ({min_tickets}+ tickets)']
    for r in found:
        ends = ', '.join(f'{e} {n}' for e, n in r['endings'].items())
        lines += [f'  {r["class"]}  — {len(r["tickets"])} tickets ({", ".join(r["tickets"])}); {ends}',
                  f'    {ACTIONS[r["action"]]}']
        if r['example']:
            lines.append(f'    e.g. {r["example"]}')
    return '\n'.join(lines)


def report(t):
    lines = ['FINDINGS BY REVIEWER (how each ended)',
             f'  {"reviewer":<30} {"total":>5} ' + ' '.join(f'{e:>9}' for e in ENDINGS) + '   noise']
    for name, c in sorted(t['reviewers'].items()):
        judged = c['total'] - sum(c[e] for e in UNJUDGED)
        noise = f'{c["refuted"] / judged:.0%}' if judged else '—'
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
    found = repeats(t)
    if found:
        lines += ['', repeats_report(found, 3)]
    lines += ['', 'noise = refuted / judged findings (all but open and answered). A reviewer with high',
              'noise is a candidate for a REVIEW.md rule or a prompt change; measure the change with',
              'the review eval. answered = the spec or the owner\'s request already settled it.']
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--dir', type=Path)
    parser.add_argument('--ticket')
    parser.add_argument('--classes', action='store_true')
    parser.add_argument('--repeats', action='store_true')
    parser.add_argument('--min-tickets', type=int, default=3)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    directory = args.dir or review_dir()
    files = sorted(directory.glob(f'{args.ticket}-*.sarif' if args.ticket else '*.sarif'))
    if not files:
        print(f'review-noise: no review files in {directory}', file=sys.stderr)
        return 1
    t = tally(files)
    if args.classes:
        print('\n'.join(f'{k}  ({len(v)} ticket(s))' for k, v in sorted(t['classes'].items())))
        return 0
    if args.repeats:
        found = repeats(t, args.min_tickets)
        print(json.dumps(found, indent=2) if args.json else repeats_report(found, args.min_tickets))
        return 0
    if args.json:
        print(json.dumps({'reviewers': {k: dict(v) for k, v in t['reviewers'].items()},
                          'rounds': t['rounds']}, indent=2))
    else:
        print(report(t))
    return 0


if __name__ == '__main__':
    sys.exit(main())
