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

A range often carries more than one ticket. `--ticket LD-441` keeps only the
commits whose message names that ticket, so another ticket's files do not read
as misses. Pipeline artifacts and agent configuration (DEFAULT_EXCLUDES) are
never a task's planned location and are dropped unless `--no-default-excludes`.

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

# Files a ticket changes that no task plans: the pipeline's own artifacts and
# agent configuration. fnmatch's `*` crosses `/`, so `docs/specs/*` is recursive.
DEFAULT_EXCLUDES = (
    'docs/specs/*', 'docs/tasks/*',
    'CLAUDE.md', 'AGENTS.md', '*/CLAUDE.md', '*/AGENTS.md',
    '.claude/*', '.codex/*', '.ai/*', '.worktreeinclude',
)


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
    kept = {p: s for p, s in changed.items()
            if not any(fnmatch.fnmatch(p, g) for g in excludes)}
    excluded = len(changed) - len(kept)
    changed = kept
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
        'excluded_files': excluded,
        'recall': ratio(found, changed),
        'recall_existing': ratio(existing_found, existing),
        'precision': ratio(touched, expected),
        'missed': missed,
        'planned_but_untouched': untouched,
    }


def git(repo, *args):
    return subprocess.run(['git', '-C', str(repo), *args],
                          check=True, text=True, capture_output=True).stdout


def parse_name_status(out, changed):
    for line in out.splitlines():
        parts = line.split('\t')
        if len(parts) < 2:
            continue
        status = parts[0][:1]
        # A rename R100\told\tnew: the location the plan had to find is the old path.
        path = parts[1] if status == 'R' else parts[-1]
        status = 'M' if status == 'R' else status
        if path not in changed:
            changed[path] = status
        elif status == 'D' and changed[path] == 'A':
            del changed[path]            # added and removed inside the ticket: no location
    return changed


def changed_files(repo, rev_range, ticket=None):
    """{path: status} over the range, or over only the ticket's own commits."""
    if not ticket:
        return parse_name_status(git(repo, 'diff', '--name-status', '-M', rev_range), {})
    shas = git(repo, 'log', '--no-merges', '--reverse', '--format=%H', '-i', '-F',
               f'--grep={ticket}', rev_range).split()
    changed = {}
    for sha in shas:
        parse_name_status(git(repo, 'show', '--name-status', '-M', '--format=', sha), changed)
    return changed


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--plan', action='append', required=True, type=Path,
                        help='plan or todo file (repeatable); relative to --repo')
    parser.add_argument('--range', required=True, help='git range of the shipped change, e.g. abc123..def456')
    parser.add_argument('--repo', type=Path, default=Path('.'))
    parser.add_argument('--ticket', help='score only commits whose message names this ticket, e.g. LD-441')
    parser.add_argument('--exclude', action='append', default=[],
                        help="glob of changed files to ignore, e.g. 'docs/*' (repeatable)")
    parser.add_argument('--no-default-excludes', action='store_true',
                        help='also score pipeline artifacts and agent config (DEFAULT_EXCLUDES)')
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

    changed = changed_files(args.repo, args.range, args.ticket)
    if args.ticket and not changed:
        print(f'plan-recall: no commits in {args.range} name {args.ticket}', file=sys.stderr)
    excludes = list(args.exclude) + ([] if args.no_default_excludes else list(DEFAULT_EXCLUDES))
    result = score(entries, changed, excludes)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        pct = lambda v: '—' if v is None else f'{v:.0%}'
        print(f"changed files            : {result['changed_files']}"
              f"   ({result['excluded_files']} excluded)")
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
