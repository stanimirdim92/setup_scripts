#!/usr/bin/env python3
"""Plan-localization recall: did the plan name the files the shipped change touched?

LoLBench (arXiv 2609.37143) found that coding agents on large systems rarely
edit the wrong file; they miss files that needed editing. That is a recall
problem, and the plan is where this harness decides which files a task touches.
This scores a plan against what actually shipped, deterministically and
without spending tokens:

    python3 recall.py --repo ~/code/leadbuster \\
        --plan docs/tasks/LD-380-plan.md --plan docs/tasks/LD-380-todo.md \\
        --range <base>..<merge-commit>

Planned locations come from every task's `Files/areas likely touched` list
(references/templates/task.md). An entry may be a file, a directory (trailing
`/`), or a glob; an entry marked `unchanged — reason` counts as considered, so
it covers a recall miss but is not expected in the diff. Changed files come from
`git diff --name-status` over the range.

Two recall figures are reported: over every changed file, and over changed
files that already existed (the paper's measure — a new file has no location to
find). A pass here means the plan named the places; it says nothing about
whether the changes there were right.

Exit 0 always unless arguments are wrong; `--min-recall` makes it a gate.
"""
import argparse
import fnmatch
import json
import re
import subprocess
import sys
from pathlib import Path

FIELD = re.compile(r'^\*\*Files/areas likely touched:\*\*', re.IGNORECASE)
NEXT_FIELD = re.compile(r'^(\*\*[^*]+:\*\*|#{1,6} )')
BULLET_PATH = re.compile(r'^\s*[-*]\s+`([^`]+)`(.*)$')
UNCHANGED = re.compile(r'unchanged', re.IGNORECASE)


def planned_entries(text):
    """(path, unchanged) for every bullet under a Files/areas likely touched field."""
    entries, inside = [], False
    for line in text.splitlines():
        if FIELD.match(line.strip()):
            inside = True
            continue
        if inside and NEXT_FIELD.match(line.strip()):
            inside = False
        if not inside:
            continue
        match = BULLET_PATH.match(line)
        if match:
            path = match.group(1).strip().removeprefix('./')
            entries.append((path, bool(UNCHANGED.search(match.group(2)))))
    return entries


def covers(entry, path):
    if entry.endswith('/'):
        return path.startswith(entry)
    if any(ch in entry for ch in '*?['):
        return fnmatch.fnmatch(path, entry)
    return path == entry


def score(entries, changed, excludes=()):
    """changed: {path: status letter}. Returns the figures as a dict."""
    changed = {p: s for p, s in changed.items()
               if not any(fnmatch.fnmatch(p, g) for g in excludes)}
    considered = [e for e, _ in entries]
    expected = [e for e, unchanged in entries if not unchanged]

    found = sorted(p for p in changed if any(covers(e, p) for e in considered))
    missed = sorted(p for p in changed if p not in found)
    existing = [p for p, s in changed.items() if s != 'A']
    existing_found = [p for p in existing if p in found]
    touched = sorted(e for e in expected if any(covers(e, p) for p in changed))
    untouched = sorted(e for e in expected if e not in touched)

    def ratio(a, b):
        return round(len(a) / len(b), 3) if b else None

    return {
        'changed_files': len(changed),
        'recall': ratio(found, changed),
        'recall_existing': ratio(existing_found, existing),
        'precision': ratio(touched, expected),
        'missed': missed,
        'planned_but_untouched': untouched,
    }


def changed_files(repo, rev_range):
    out = subprocess.run(['git', '-C', str(repo), 'diff', '--name-status', '-M', rev_range],
                         check=True, text=True, capture_output=True).stdout
    changed = {}
    for line in out.splitlines():
        parts = line.split('\t')
        status = parts[0][:1]
        # A rename R100\told\tnew: the location the plan had to find is the old path.
        path = parts[1] if status == 'R' else parts[-1]
        changed[path] = 'M' if status == 'R' else status
    return changed


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--plan', action='append', required=True, type=Path,
                        help='plan or todo file (repeatable); relative to --repo')
    parser.add_argument('--range', required=True, help='git range of the shipped change, e.g. abc123..def456')
    parser.add_argument('--repo', type=Path, default=Path('.'))
    parser.add_argument('--exclude', action='append', default=[],
                        help="glob of changed files to ignore, e.g. 'docs/**' (repeatable)")
    parser.add_argument('--min-recall', type=float, help='exit 1 when recall_existing is below this')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)

    entries = []
    for plan in args.plan:
        path = plan if plan.is_absolute() else args.repo / plan
        if not path.is_file():
            parser.error(f'no such plan file: {path}')
        entries += planned_entries(path.read_text())
    if not entries:
        print('plan-recall: no "Files/areas likely touched" entries found in the plan files', file=sys.stderr)

    result = score(entries, changed_files(args.repo, args.range), args.exclude)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        pct = lambda v: '—' if v is None else f'{v:.0%}'
        print(f"changed files            : {result['changed_files']}")
        print(f"recall (all changed)     : {pct(result['recall'])}")
        print(f"recall (existing files)  : {pct(result['recall_existing'])}   <- LoLBench's measure")
        print(f"precision (planned edits): {pct(result['precision'])}")
        if result['missed']:
            print('missed (changed, never planned):')
            for p in result['missed']:
                print(f'  {p}')
        if result['planned_but_untouched']:
            print('planned but not in the diff:')
            for p in result['planned_but_untouched']:
                print(f'  {p}')
    if args.min_recall is not None and (result['recall_existing'] or 0) < args.min_recall:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
