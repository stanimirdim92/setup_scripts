#!/usr/bin/env python3
"""Which changed files sit on a path that always needs a person? (ADR 0096)

Some files are expensive to get wrong however small the change: CI and deploy
workflows, migrations, auth and permission code, billing, installers, `.env*`.
A project lists them under an "## Always a person" heading in its REVIEW.md,
one glob per bullet in backticks. This script reads that list from the base
branch (never from the change itself, ADR 0094), including any REVIEW.md in a
directory the change touches, whose globs are relative to that directory, and
prints the changed files that match.

/review then runs every specialist and requires /test; /ship tells the user
plainly to read those files.

Usage:
    always-person.py --base origin/main            # changed files: base...HEAD
    always-person.py --base origin/main --json

Exit: 0 no match (or no list) · 1 at least one match · 2 usage or git error.
"""
import argparse
import fnmatch
import json
import re
import subprocess
import sys
from pathlib import PurePosixPath

HEADING = re.compile(r'^##\s+Always a person\s*$', re.I | re.M)
GLOB = re.compile(r'^\s*[-*]\s+`([^`]+)`', re.M)


def git(*args):
    out = subprocess.run(['git', *args], capture_output=True, text=True)
    return out.returncode, out.stdout


def globs_in(text, directory=''):
    """The globs under the "Always a person" heading, rooted at directory."""
    m = HEADING.search(text)
    if not m:
        return []
    section = text[m.end():]
    nxt = re.search(r'^#{1,2}\s', section, re.M)
    section = section[:nxt.start()] if nxt else section
    prefix = f'{directory}/' if directory else ''
    return [prefix + g.strip().lstrip('/') for g in GLOB.findall(section)]


def matches(path, glob):
    """fnmatch, plus `dir/**` matching everything under dir."""
    if glob.endswith('/**') and path.startswith(glob[:-2]):
        return True
    return fnmatch.fnmatch(path, glob)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--base', required=True)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)

    rc, out = git('diff', '--name-only', f'{args.base}...HEAD')
    if rc:
        print(f'always-person: cannot diff {args.base}...HEAD', file=sys.stderr)
        return 2
    changed = [p for p in out.splitlines() if p]
    rc, base = git('merge-base', args.base, 'HEAD')
    if rc:
        print(f'always-person: no merge base with {args.base}', file=sys.stderr)
        return 2
    base = base.strip()

    dirs = {''} | {str(p) for f in changed for p in PurePosixPath(f).parents if str(p) != '.'}
    globs = []
    for d in sorted(dirs):
        rc, text = git('show', f'{base}:{d + "/" if d else ""}REVIEW.md')
        if rc == 0:
            globs += globs_in(text, d)

    hits = {f: [g for g in globs if matches(f, g)] for f in changed}
    hits = {f: g for f, g in hits.items() if g}
    if args.json:
        print(json.dumps({'globs': globs, 'matches': hits}, indent=2))
    elif not globs:
        print('Always a person: no list in REVIEW.md on the base branch.')
    elif not hits:
        print(f'Always a person: none of {len(changed)} changed file(s) match.')
    else:
        print(f'Always a person: {len(hits)} file(s) need a person to read them:')
        for f, g in sorted(hits.items()):
            print(f'  {f}   (matches {", ".join(g)})')
    return 1 if hits else 0


if __name__ == '__main__':
    sys.exit(main())
