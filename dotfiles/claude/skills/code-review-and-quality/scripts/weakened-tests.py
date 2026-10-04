#!/usr/bin/env python3
"""List the changes in a diff that make passing easier instead of making the code right.

An agent that cannot get a test green can make the test easier: skip it,
delete it, drop an assertion, silence the checker, or leave a stub. Each is a
small, plausible-looking hunk that a reviewer reading for correctness passes
over. This lists them so `/review` can ask for the reason behind each one.

Adapted from the floor-guard reference in addyosmani/agent-skills
(skills/constraint-driven-development/references/floor-guard.md, MIT): the
same contract, rewritten for this harness, no code copied.

What it reports (category: what it means):
  test-deleted       a test file removed (a rename is not a deletion)
  test-skipped       a skip, todo or focus marker added in a test file
  assertions-removed a test file that stayed lost more assertions than it gained
  suppression        a lint, type or coverage suppression comment added
  checker-config     a line changed in a test, lint, type or coverage config
  stub               a NotImplemented, TODO/FIXME or empty catch added in code

Only moves that lower the bar are listed; tightening is silent. Documentation
files are skipped: a README that shows `@ts-ignore` silences nothing. A hit is a
question, not a verdict: a test deleted with the feature it tested is fine,
and the review says so.

Exit codes: 0 nothing found, 1 something found, 2 could not run (not a git
repository, unknown base). A 2 never reads as clean.

Usage:
    weakened-tests.py --base <ref> [--head <ref>]   # committed range base...head
    weakened-tests.py --base <ref> --worktree       # also uncommitted and untracked files
    weakened-tests.py ... --json
"""
import argparse
import json
import re
import subprocess
import sys

TEST_PATH = re.compile(
    r'(^|/)(tests?|__tests__|spec|specs)/'
    r'|(^|/)test_[^/]+\.py$|_test\.(py|go|rb|exs?)$'
    r'|\.(test|spec)\.[cm]?[jt]sx?$|Test\.php$|_spec\.rb$'
)
SKIP = re.compile(
    r'\b(?:it|test|describe|context|suite)\.(?:skip|todo|only)\b'
    r'|\b(?:xit|xtest|xdescribe|fit|fdescribe)\s*\('
    r'|@pytest\.mark\.(?:skip|skipif|xfail)\b|\bpytest\.(?:skip|xfail)\s*\('
    r'|@unittest\.(?:skip|skipIf|skipUnless|expectedFailure)\b|\bself\.skipTest\s*\('
    r'|\bmarkTest(?:Skipped|Incomplete)\s*\(|->(?:skip|todo)\s*\(|#\[\\?(?:PHPUnit\\Framework\\Attributes\\)?(?:Skip|Group\(.skip)'
    r'|\bt\.Skip(?:f|Now)?\s*\('
)
ASSERTION = re.compile(
    r'\bassert\w*\s*[\(\s]|\bexpect\s*\(|->assert\w*\s*\(|::assert\w*\s*\('
    r'|\.should\b|\bself\.assert\w*\s*\(|\bt\.(?:Error|Fatal)f?\s*\('
)
SUPPRESSION = re.compile(
    r'eslint-disable|@ts-(?:ignore|expect-error|nocheck)|#\s*noqa\b|#\s*type:\s*ignore'
    r'|pragma:\s*no\s*cover|istanbul\s+ignore|c8\s+ignore|v8\s+ignore'
    r'|@phpstan-ignore|phpstan-ignore-(?:line|next-line)|phpcs:(?:ignore|disable)|@psalm-suppress'
    r'|@codeCoverageIgnore|@SuppressWarnings|\bNOLINT\b|//\s*nolint\b|rubocop:disable'
    r'|biome-ignore|prettier-ignore|#\s*pylint:\s*disable|#\s*mypy:\s*ignore'
)
CHECKER_CONFIG = re.compile(
    r'(^|/)(phpstan[^/]*\.neon(\.dist)?|psalm[^/]*\.xml(\.dist)?|phpunit[^/]*\.xml(\.dist)?|pest\.php'
    r'|\.eslintrc[^/]*|eslint\.config\.[cm]?[jt]s|tsconfig[^/]*\.json|\.prettierrc[^/]*|biome\.jsonc?'
    r'|jest\.config\.[cm]?[jt]s|vitest\.config\.[cm]?[jt]s|vitest\.workspace\.[cm]?[jt]s'
    r'|pyproject\.toml|setup\.cfg|\.coveragerc|tox\.ini|pytest\.ini|mypy\.ini|\.golangci\.ya?ml|\.rubocop\.ya?ml)$'
)
STUB = re.compile(
    r'\bNotImplemented(?:Error)?\b|not\s+implemented|\b(?:TODO|FIXME|XXX)\b'
    r'|catch\s*(?:\([^)]*\))?\s*\{\s*\}|except(?:\s+[^:]+)?:\s*pass\b'
)
DOCS = re.compile(r'\.(md|mdx|markdown|rst|txt|adoc)$', re.I)
HUNK = re.compile(r'^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@')


class GitError(Exception):
    pass


def git(repo, *args, ok=(0,)):
    proc = subprocess.run(['git', '-C', repo, *args], capture_output=True, text=True)
    if proc.returncode not in ok:
        raise GitError(proc.stderr.strip() or f'git {" ".join(args)} failed')
    return proc.stdout


def diff_range(repo, base, head, worktree):
    """The working tree against the merge base, or the committed range base...head."""
    if worktree:
        return [git(repo, 'merge-base', base, head).strip()]
    return [f'{base}...{head}']


def is_test(path):
    return bool(TEST_PATH.search(path)) and not DOCS.search(path)


def parse_diff(text):
    """{path: {'status': str, 'added': [(line, text)], 'removed': [(line, text)]}}."""
    files, cur = {}, None
    old_line = new_line = 0
    for line in text.split('\n'):
        if line.startswith('diff --git '):
            cur = None
            continue
        if line.startswith('--- '):
            old = line[4:]
            continue
        if line.startswith('+++ '):
            new = line[4:]
            path = (new if new != '/dev/null' else old)[2:]
            status = 'D' if new == '/dev/null' else 'A' if old == '/dev/null' else 'M'
            cur = files.setdefault(path, {'status': status, 'added': [], 'removed': []})
            continue
        m = HUNK.match(line)
        if m:
            old_line, new_line = int(m.group(1)), int(m.group(2))
            continue
        if cur is None:
            continue
        if line.startswith('+'):
            cur['added'].append((new_line, line[1:]))
            new_line += 1
        elif line.startswith('-'):
            cur['removed'].append((old_line, line[1:]))
            old_line += 1
    return files


def untracked(repo):
    """{path: {...}} for untracked files, every line counted as added."""
    files = {}
    for path in git(repo, 'ls-files', '--others', '--exclude-standard', '-z').split('\0'):
        if not path:
            continue
        try:
            with open(f'{repo}/{path}', encoding='utf-8') as fh:
                lines = fh.read().split('\n')
        except (OSError, UnicodeDecodeError):
            continue
        files[path] = {'status': 'A', 'added': list(enumerate(lines, 1)), 'removed': []}
    return files


def findings(files):
    out = []
    def hit(category, path, line, text):
        out.append({'category': category, 'path': path, 'line': line, 'text': text.strip()[:160]})
    added_names = {p.rsplit('/', 1)[-1] for p, f in files.items() if f['status'] == 'A'}
    for path, f in sorted(files.items()):
        if DOCS.search(path):
            continue
        test = is_test(path)
        if f['status'] == 'D':
            # Moved and edited in one change, so git saw no rename: not a deletion.
            if test and path.rsplit('/', 1)[-1] not in added_names:
                hit('test-deleted', path, 0, f'{len(f["removed"])} lines removed')
            continue
        for n, text in f['added']:
            if test and SKIP.search(text):
                hit('test-skipped', path, n, text)
            if SUPPRESSION.search(text):
                hit('suppression', path, n, text)
            if not test and STUB.search(text):
                hit('stub', path, n, text)
        if test and f['status'] != 'A':
            lost = sum(1 for _, t in f['removed'] if ASSERTION.search(t))
            gained = sum(1 for _, t in f['added'] if ASSERTION.search(t))
            if lost > gained:
                first = next(n for n, t in f['removed'] if ASSERTION.search(t))
                hit('assertions-removed', path, first, f'{lost} assertion lines removed, {gained} added')
        if CHECKER_CONFIG.search(path) and f['status'] != 'A':
            for n, text in f['added'] or f['removed'][:1]:
                if text.strip():
                    hit('checker-config', path, n, text)
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--base', required=True, help='the ref the candidate branched from, e.g. origin/main')
    parser.add_argument('--head', default='HEAD')
    parser.add_argument('--worktree', action='store_true',
                        help='compare the working tree, including untracked files, instead of head')
    parser.add_argument('--repo', default='.')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    repo = args.repo
    try:
        git(repo, 'rev-parse', '--git-dir')
        rng = diff_range(repo, args.base, args.head, args.worktree)
        files = parse_diff(git(repo, 'diff', '--unified=0', '-M', '--no-color', '--no-ext-diff', *rng))
        if args.worktree:
            files.update(untracked(repo))
    except GitError as err:
        print(f'weakened-tests: could not run: {err}', file=sys.stderr)
        return 2
    found = findings(files)
    if args.json:
        print(json.dumps(found, indent=2))
    elif found:
        for f in found:
            where = f'{f["path"]}:{f["line"]}' if f['line'] else f['path']
            print(f'{where}  {f["category"]}: {f["text"]}')
        print(f'weakened-tests: {len(found)} change(s) that make passing easier; each needs a reason',
              file=sys.stderr)
    else:
        print('weakened-tests: nothing found')
    return 1 if found else 0


if __name__ == '__main__':
    sys.exit(main())
