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
disclosed it in a footnote (dotfiles/docs/observation-log.md).

Scope, deliberately narrow: markdown links and backticked paths that begin with
`./`, `../` or `templates/` -- the cross-reference class. Artifact paths carrying
a `[TICKET]` placeholder belong to dotfiles/tools/checks/validate-artifact-paths.py and are
skipped here; so are URLs and bare filenames, which are prose more often than
links.

The harness's own docs (dotfiles/ARCHITECTURE.md, dotfiles/README.md,
dotfiles/docs/*.md) are scanned too, but only their markdown links, which there
are relative to the file (`claude/AGENTS.md`) rather than `./`-prefixed.
ARCHITECTURE.md's ownership table pointed at the deleted dotfiles/claude/CLAUDE.md
for a week because nothing outside dotfiles/claude was checked.
dotfiles/docs/adr/ is excluded: an ADR is a dated record, and a path it names
may be gone by design.

A reference can also name a place inside the target: a `#anchor` on a link,
or a `§Section` after a backticked path (`../references/target-selection.md`
§Gate handoffs). The file resolving is not enough then: a renamed heading
leaves the reader at the top of the right file, looking for a section that is
gone. An anchor must match a heading's GitHub slug. A named section must match
the start of a heading, and a numbered one (`§3`) a heading numbered 3.
Idea from addyosmani/agent-skills (scripts/validate-reference-links.js, MIT);
no code copied.

This is the static half. A reference that resolves but is refused at runtime --
a permission denial on a path outside the session's working directory -- is not
visible from here.

Exit 0 when every reference resolves, 1 otherwise.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HARNESS = ROOT / 'dotfiles/claude'

# [text](target) and `target`
LINK = re.compile(r'\[[^\]]*\]\(([^)\s]+)\)')
CODE = re.compile(r'`([^`\s]+\.md(?:#[^`\s]*)?)`')

PLACEHOLDER = re.compile(r'\[TICKET\]|<module|\{|\$')


def candidates(text, top_level=False):
    """Relative reference targets named in one file, anchors stripped.

    `top_level` switches to the repository-doc rule: markdown links only, with
    any relative target.
    """
    matches = LINK.finditer(text) if top_level else \
        list(LINK.finditer(text)) + list(CODE.finditer(text))
    for match in matches:
        target = match.group(1).split('#', 1)[0].strip()
        if not target or PLACEHOLDER.search(target):
            continue
        if target.startswith(('http://', 'https://', 'mailto:', '/')):
            continue
        if not top_level and not target.startswith(('./', '../', 'templates/')):
            continue
        yield target


NAMED = re.compile(r'`/?([a-z0-9][a-z0-9-]*)`(?=\s+§)')
SECTION = re.compile(r'\s+§\s*([^\n]*)')
FENCE = re.compile(r'^\s*(```|~~~)')


def headings(path):
    """Heading texts of a markdown file, code fences skipped."""
    out, fence = [], False
    for line in path.read_text().splitlines():
        if FENCE.match(line):
            fence = not fence
        elif not fence and line.startswith('#'):
            out.append(line.lstrip('#').strip())
    return out


def slug(heading):
    """GitHub's anchor for a heading: lowercase, punctuation dropped, spaces to hyphens."""
    text = re.sub(r'[`*_~]|\[([^\]]*)\]\([^)]*\)', lambda m: m.group(1) or '', heading.lower())
    return re.sub(r'[^\w\- ]', '', text).replace(' ', '-')


def anchors(path):
    """Every anchor GitHub generates for the file, with -1, -2 for repeated headings."""
    seen, out = {}, set()
    for h in headings(path):
        base = slug(h)
        n = seen.get(base, 0)
        out.add(base if n == 0 else f'{base}-{n}')
        seen[base] = n + 1
    return out


def section_found(name, heads):
    """True when `name` (the text after §) starts with or opens a heading."""
    number = re.match(r'(\d+)', name)
    if number:
        return any(re.match(rf'{number.group(1)}[.)\s]', h) for h in heads)
    words = re.findall(r'[\w-]+', name)
    if not words:
        return True
    first = words[0].lower()
    return any(re.findall(r'[\w-]+', h.lower())[:1] == [first] for h in heads)


def named_file(name):
    """The harness file a backticked skill, persona or command name stands for."""
    for path in (HARNESS / 'skills' / name / 'SKILL.md', HARNESS / 'agents' / f'{name}.md',
                 HARNESS / 'commands' / f'{name}.md'):
        if path.is_file():
            return path
    return None


def places(text, top_level=False):
    """(target, kind, name) for each `#anchor` or `§Section` a reference names.

    A target is a path relative to the file, or, for a backticked skill,
    persona or command name (`test-engineer` §6), the absolute path of its file.
    """
    matches = LINK.finditer(text) if top_level else \
        list(LINK.finditer(text)) + list(CODE.finditer(text))
    for match in matches:
        raw = match.group(1)
        target, _, anchor = raw.partition('#')
        target = target.strip()
        if not target or PLACEHOLDER.search(target) or target.startswith(('http://', 'https://', 'mailto:', '/')):
            continue
        if not top_level and not target.startswith(('./', '../', 'templates/')):
            continue
        if anchor:
            yield target, '#', anchor
        if match.re is CODE and not anchor:
            section = SECTION.match(text, match.end())
            if section:
                yield target, '§', section.group(1)
    if not top_level:
        for match in NAMED.finditer(text):
            path = named_file(match.group(1))
            if path:
                yield str(path), '§', SECTION.match(text, match.end()).group(1)


def top_level_docs():
    """Harness docs outside dotfiles/claude; ADRs excluded (see above)."""
    docs = ROOT / 'dotfiles'
    return [p for p in [docs / 'ARCHITECTURE.md', docs / 'README.md',
                        *sorted((docs / 'docs').glob('*.md'))] if p.is_file()]


def broken(path, text, top_level=False):
    """Targets named by `path` that do not resolve to an existing file."""
    base = path.resolve().parent
    out = []
    for target in candidates(text, top_level):
        if not (base / target).exists():
            out.append(target)
    for target, kind, name in places(text, top_level):
        dest = base / target
        if not dest.is_file():
            continue  # reported above
        if kind == '#' and name not in anchors(dest):
            out.append(f'{target}#{name} (no such heading)')
        elif kind == '§' and not section_found(name, headings(dest)):
            shown = re.match(r'[\w -]*', name.strip()).group().strip()
            if Path(target).is_absolute():
                target = Path(target).relative_to(HARNESS)
            out.append(f'{target} §{shown} (no such section)')
    return out


def main():
    if not HARNESS.is_dir():
        print(f'check-references: no harness tree at {HARNESS}', file=sys.stderr)
        return 1

    print('Resolving harness cross-references...\n')
    problems = []
    checked = 0
    scan = [(p, False) for p in sorted(HARNESS.rglob('*.md'))]
    scan += [(p, True) for p in top_level_docs()]
    for path, top_level in scan:
        found = broken(path, path.read_text(), top_level)
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
