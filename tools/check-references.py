#!/usr/bin/env python3
"""Resolve every cross-reference between harness files and fail on a broken one.

The pipeline is held together by relative links: `/plan` reads
`../references/plan-quality-gates.md`, a skill reads `../../references/
definition-of-done.md`, a reference points at `templates/task.md`. They resolve
from the physical directory of the file that names them, symlink or not
(ARCHITECTURE.md, "Installation and reads"). Nothing checked that the target on
the other end exists.

The failure this guards against is quiet. A stage that cannot read its own
reference does not crash -- it proceeds from the skill body alone and produces
an artifact that was never shaped by the template or checked against the quality
gates. Observed on 2026-09-14: `/plan` ran a full precondition check with
plan-quality-gates.md, templates/plan.md and templates/task.md all unread, and
disclosed it in a footnote (docs/observation-log.md).

Scope, deliberately narrow: markdown links and backticked paths that begin with
`./`, `../` or `templates/` -- the cross-reference class. Artifact paths carrying
a `[TICKET]` placeholder belong to tools/validate-artifact-paths.py and are
skipped here; so are URLs and bare filenames, which are prose more often than
links.

This is the static half. A reference that resolves but is refused at runtime --
a permission denial on a path outside the session's working directory -- is not
visible from here.

Exit 0 when every reference resolves, 1 otherwise.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / 'dotfiles/claude'

# [text](target) and `target`
LINK = re.compile(r'\[[^\]]*\]\(([^)\s]+)\)')
CODE = re.compile(r'`([^`\s]+\.md(?:#[^`\s]*)?)`')

PLACEHOLDER = re.compile(r'\[TICKET\]|<module|\{|\$')


def candidates(text):
    """Relative reference targets named in one file, anchors stripped."""
    for match in list(LINK.finditer(text)) + list(CODE.finditer(text)):
        target = match.group(1).split('#', 1)[0].strip()
        if not target or PLACEHOLDER.search(target):
            continue
        if target.startswith(('http://', 'https://', 'mailto:', '/')):
            continue
        if not target.startswith(('./', '../', 'templates/')):
            continue
        yield target


def broken(path, text):
    """Targets named by `path` that do not resolve to an existing file."""
    base = path.resolve().parent
    out = []
    for target in candidates(text):
        if not (base / target).exists():
            out.append(target)
    return out


def main():
    if not HARNESS.is_dir():
        print(f'check-references: no harness tree at {HARNESS}', file=sys.stderr)
        return 1

    print('Resolving harness cross-references...\n')
    problems = []
    checked = 0
    for path in sorted(HARNESS.rglob('*.md')):
        found = broken(path, path.read_text())
        checked += 1
        if found:
            rel = path.relative_to(ROOT)
            for target in found:
                problems.append(f'{rel} -> {target}')

    for problem in problems:
        print(f'  BROKEN  {problem}')
    print(f'\n{checked} files scanned -- {len(problems)} broken reference(s) -- '
          f'{"FAILED" if problems else "PASSED"}')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
