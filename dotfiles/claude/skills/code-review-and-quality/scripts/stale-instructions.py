#!/usr/bin/env python3
"""Which instruction lines does this change make untrue? (ADR 0098)

Agents follow CLAUDE.md, AGENTS.md, REVIEW.md, `.ai/rules` and the README
literally. A change that renames `bin/worktree-test.sh` leaves "run
`bin/worktree-test.sh`" in CLAUDE.md, and the next session follows a dead
instruction. This finds the mechanical cases, project-agnostic:

- a file the change deletes or renames, still named in an instruction file
  (the full path anywhere, or the file name inside backticks);
- a package.json or composer.json script the change removes, still run in an
  instruction file (`yarn <name>`, `npm run <name>`, `pnpm <name>`,
  `composer <name>`).

Instruction files are read as the candidate leaves them, so a change that
also fixes the line is clean. Changes in meaning ("validation moved to the
FormRequest") are for code-reviewer, not this script.

Usage:
    stale-instructions.py --base origin/main
    stale-instructions.py --base origin/main --json

Exit: 0 nothing stale · 1 at least one stale line · 2 usage or git error.
"""
import argparse
import fnmatch
import json
import re
import subprocess
import sys
from pathlib import PurePosixPath

INSTRUCTIONS = ('CLAUDE.md', '*/CLAUDE.md', 'AGENTS.md', '*/AGENTS.md', 'REVIEW.md', '*/REVIEW.md',
                'README.md', '.ai/rules/*', '.claude/rules/*', '.cursor/rules/*', 'docs/MEMORY.md')
RUNNERS = {'package.json': ('yarn {}', 'yarn run {}', 'npm run {}', 'pnpm {}', 'pnpm run {}'),
           'composer.json': ('composer {}', 'composer run {}', 'composer run-script {}')}


def git(*args):
    out = subprocess.run(['git', *args], capture_output=True, text=True)
    return out.returncode, out.stdout


def moved(base):
    """[(old path, new path or None)] for files the change deletes or renames."""
    rc, out = git('diff', '--name-status', '-M', f'{base}...HEAD')
    if rc:
        raise SystemExit(2)
    gone = []
    for line in out.splitlines():
        parts = line.split('\t')
        if parts[0].startswith('D'):
            gone.append((parts[1], None))
        elif parts[0].startswith('R'):
            gone.append((parts[1], parts[2]))
    return gone


def scripts(rev, path):
    rc, text = git('show', f'{rev}:{path}')
    if rc:
        return set()
    try:
        return set((json.loads(text).get('scripts') or {}).keys())
    except ValueError:
        return set()


def removed_scripts(base):
    """[(manifest, script name)] for scripts the change removes."""
    rc, merge = git('merge-base', base, 'HEAD')
    if rc:
        raise SystemExit(2)
    merge = merge.strip()
    return [(m, name) for m in RUNNERS for name in sorted(scripts(merge, m) - scripts('HEAD', m))]


def instruction_files():
    rc, out = git('ls-files')
    return [p for p in out.splitlines() if p.endswith('.md') and any(fnmatch.fnmatch(p, g) for g in INSTRUCTIONS)]


def needles(old, new):
    """Text that still points at a moved file: the full path, and its name in backticks."""
    name = PurePosixPath(old).name
    found = [(re.compile(re.escape(old)), old)]
    if name != old and '.' in name and len(name) >= 5:
        found.append((re.compile(r'`[^`\s]*' + re.escape(name) + r'`'), name))
    return found


def scan(base):
    files = {p: (git('show', f'HEAD:{p}')[1]) for p in instruction_files()}
    hits = []
    for old, new in moved(base):
        if old in files:
            continue                      # an instruction file itself moved; not a stale mention
        for rx, label in needles(old, new):
            for path, text in files.items():
                for n, line in enumerate(text.splitlines(), 1):
                    if rx.search(line):
                        what = f'renamed to `{new}`' if new else 'deleted'
                        hits.append({'file': path, 'line': n, 'mentions': label,
                                     'reason': f'`{old}` is {what} by this change', 'text': line.strip()[:120]})
    for manifest, name in removed_scripts(base):
        pattern = re.compile(r'(?<![\w-])(' + '|'.join(re.escape(r.format(name)) for r in RUNNERS[manifest]) + r')(?![\w:-])')
        for path, text in files.items():
            for n, line in enumerate(text.splitlines(), 1):
                if pattern.search(line):
                    hits.append({'file': path, 'line': n, 'mentions': name,
                                 'reason': f'the `{name}` script is removed from {manifest} by this change',
                                 'text': line.strip()[:120]})
    unique = {(h['file'], h['line'], h['reason']): h for h in reversed(hits)}
    return sorted(unique.values(), key=lambda h: (h['file'], h['line']))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--base', required=True)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    try:
        hits = scan(args.base)
    except SystemExit:
        print(f'stale-instructions: cannot compare {args.base}...HEAD', file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(hits, indent=2))
    elif not hits:
        print('Stale instructions: none found.')
    else:
        print(f'Stale instructions: {len(hits)} line(s) the change makes untrue:')
        for h in hits:
            print(f"  {h['file']}:{h['line']}  {h['reason']}\n      {h['text']}")
    return 1 if hits else 0


if __name__ == '__main__':
    sys.exit(main())
