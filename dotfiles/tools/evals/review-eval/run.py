#!/usr/bin/env python3
"""Review eval: does /review catch bugs that really shipped?

A bugfix commit in the project's history holds its own answer key. Blame on
the lines it changed finds the commit that introduced the bug. The eval runs
a standalone `/review` on that commit, on the code as it was before it, and
checks whether a BLOCKER or REQUIRED finding points at those lines.

A clean case is a commit nobody had to fix. There the eval counts the
blocking findings: each one is noise (ADR 0093).

Usage:
    run.py --new fix-feed-order --repo ~/app --fix <sha>       # case from a bugfix
    run.py --new quiet-ui --repo ~/app --clean <sha>           # case from a clean commit
    run.py --fixture fix-feed-order --fixture quiet-ui --repo ~/app --output ./before
    run.py --fixture ... --repo ~/app --output ./after --baseline ./before/results.json
    run.py --fixture fix-feed-order --findings review.sarif    # judge a saved SARIF (free)

Producing drives the real model and costs money: never in CI.
"""
import argparse
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / 'fixtures'
TOLERANCE = 3          # a finding within this many lines of a target line counts
BLOCKING = {'BLOCKER', 'REQUIRED'}

_spec = importlib.util.spec_from_file_location('spec_eval', HERE.parent / 'spec-eval' / 'run.py')
spec_eval = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(spec_eval)


def git(repo, *args, check=True):
    return subprocess.run(['git', '-C', str(repo), *args], capture_output=True, text=True, check=check).stdout


# ---------------------------------------------------------------- building a case

HUNK = re.compile(r'^@@ -(\d+)(?:,(\d+))? \+\d+(?:,\d+)? @@', re.M)


def fix_lines(repo, fix):
    """{path: [line, ...]} in fix^: the lines the fix removed or changed, and the
    line at each insertion point."""
    out = git(repo, 'diff', '-U0', '--no-color', '--no-ext-diff', f'{fix}^', fix)
    lines, path = {}, None
    for line in out.splitlines():
        if line.startswith('--- '):
            path = None if line[4:] == '/dev/null' else line[6:]
        elif path and (m := HUNK.match(line)):
            start, count = int(m.group(1)), int(m.group(2) if m.group(2) is not None else 1)
            span = range(start, start + count) if count else range(max(start, 1), max(start, 1) + 1)
            lines.setdefault(path, []).extend(span)
    return lines


def blame(repo, rev, path, line):
    """(commit, original path, original line) for one line of path at rev."""
    out = git(repo, 'blame', '--porcelain', '-L', f'{line},{line}', rev, '--', path, check=False)
    head = out.splitlines()[0].split() if out else []
    if len(head) < 2:
        return None
    original = next((l[9:] for l in out.splitlines() if l.startswith('filename ')), path)
    return head[0], original, int(head[1])


def bug_case(repo, fix, bug=None):
    """The case for a bugfix: the commit that introduced the bug, and the lines
    of that commit's version the fix later changed."""
    blamed = [b for path, nums in fix_lines(repo, fix).items() for n in nums
              if (b := blame(repo, f'{fix}^', path, n))]
    if not blamed:
        raise SystemExit('review-eval: the fix changes no line that blame can trace')
    bug = bug or Counter(c for c, _, _ in blamed).most_common(1)[0][0]
    bug = git(repo, 'rev-parse', bug).strip()
    targets = {}
    for commit, path, line in blamed:
        if commit == bug:
            targets.setdefault(path, []).append(line)
    if not targets:
        raise SystemExit(f'review-eval: no line the fix changed comes from {bug[:10]}')
    return {'kind': 'bug', 'change': bug, 'fix': git(repo, 'rev-parse', fix).strip(),
            'targets': {p: sorted(set(v)) for p, v in targets.items()}}


def clean_case(repo, commit):
    return {'kind': 'clean', 'change': git(repo, 'rev-parse', commit).strip(), 'targets': {}}


# ---------------------------------------------------------------- judging

def sarif_findings(text):
    """[(path, line or None, disposition)] from a review SARIF file."""
    found = []
    for run in json.loads(text).get('runs', []):
        for result in run.get('results', []):
            disp = result.get('properties', {}).get('disposition') or \
                {'error': 'BLOCKER', 'warning': 'REQUIRED', 'note': 'ADVISORY'}.get(result.get('level'), '?')
            locs = result.get('locations') or [{}]
            for loc in locs:
                phys = loc.get('physicalLocation', {})
                found.append((phys.get('artifactLocation', {}).get('uri'),
                              phys.get('region', {}).get('startLine'), disp))
    return found


MARKDOWN = re.compile(r'^\s*-\s*\[([A-Z]+-\d+)\]\s*\[?`?([\w./-]+\.\w+):(\d+)', re.M)


def markdown_findings(text):
    """Fallback when no SARIF was written: `- [CODE-1] [path:line] ...` lines,
    with the disposition taken from the nearest heading above."""
    found, disp = [], '?'
    for line in text.splitlines():
        heading = re.match(r'^#+\s*(BLOCKER|REQUIRED|ADVISORY)\b', line.strip())
        if heading:
            disp = heading.group(1)
        elif (m := MARKDOWN.match(line)):
            found.append((m.group(2), int(m.group(3)), disp))
    return found


def judge(case, findings):
    """{'caught', 'caught_any', 'blocking', 'findings'} for one case."""
    def hits(path, line):
        targets = case['targets'].get(path) or []
        return line is not None and any(abs(line - t) <= TOLERANCE for t in targets)
    blocking = [f for f in findings if f[2] in BLOCKING]
    return {'caught': any(hits(p, l) for p, l, _ in blocking),
            'caught_any': any(hits(p, l) for p, l, _ in findings),
            'blocking': len(blocking), 'findings': len(findings)}


def item(case, result):
    """The pass/fail item a case contributes to a paired comparison."""
    return result['caught'] if case['kind'] == 'bug' else result['blocking'] == 0


# ---------------------------------------------------------------- producing

def produce(case, repo, budget):
    """Run a standalone /review on the case's change, in a throwaway project."""
    with tempfile.TemporaryDirectory() as tmp:
        project = spec_eval.build_project(Path(tmp) / 'project', repo, f'{case["change"]}^')
        patch = git(repo, 'diff', '--binary', '--no-ext-diff', f'{case["change"]}^', case['change'])
        subprocess.run(['git', 'apply', '--index'], input=patch, text=True, cwd=project, check=True)
        subprocess.run(['git', '-c', 'user.email=f@f', '-c', 'user.name=f', 'commit', '-qm', 'Change under review'],
                       cwd=project, check=True, capture_output=True)
        prompt = ('/review HEAD~1..HEAD\n\nThis is a standalone review of the last commit; there is no '
                  'BUILD handoff, spec or ticket. Use REVIEW-EVAL as the ticket id for the SARIF file.')
        result = subprocess.run(
            ['claude', '-p', prompt, '--setting-sources', 'project,local', '--add-dir', str(spec_eval.HARNESS),
             '--permission-mode', 'acceptEdits', '--allowedTools', 'Read', 'Glob', 'Grep', 'Write', 'Task',
             'Agent', 'Skill', 'Bash(git *)', 'Bash(mkdir *)', 'Bash(python3 *)',
             '--max-budget-usd', str(budget), '--output-format', 'json'],
            cwd=project, capture_output=True, text=True, timeout=1800)
        if result.returncode != 0:
            raise RuntimeError(f'claude exited {result.returncode}: {result.stderr[-600:]}')
        meta = json.loads(result.stdout)
        sarifs = sorted((project / '.git' / 'review').glob('*.sarif'))
        if sarifs:
            return [f for s in sarifs for f in sarif_findings(s.read_text())], meta, 'sarif'
        return markdown_findings(meta.get('result', '')), meta, 'markdown'


# ---------------------------------------------------------------- cli

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--new', metavar='NAME')
    parser.add_argument('--fix', help='with --new: the bugfix commit')
    parser.add_argument('--bug', help='with --new --fix: the commit that introduced the bug (default: found by blame)')
    parser.add_argument('--clean', help='with --new: a commit nobody had to fix')
    parser.add_argument('--fixture', action='append', default=[])
    parser.add_argument('--repo', type=Path)
    parser.add_argument('--findings', type=Path, help='judge this SARIF file instead of producing (free; one fixture)')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--budget', default='10')
    args = parser.parse_args(argv)

    if args.new:
        if not args.repo or not (args.fix or args.clean):
            parser.error('--new needs --repo and --fix or --clean')
        case = bug_case(args.repo, args.fix, args.bug) if args.fix else clean_case(args.repo, args.clean)
        out = FIXTURES / args.new
        out.mkdir(parents=True, exist_ok=True)
        (out / 'case.json').write_text(json.dumps({'name': args.new, **case}, indent=2) + '\n')
        where = ', '.join(f'{p} ({len(v)} line(s))' for p, v in case['targets'].items()) or 'none (clean case)'
        print(f'Case {out}: {case["kind"]}, change {case["change"][:10]}, targets: {where}.')
        return 0

    if not args.fixture:
        parser.error('give --new, or one or more --fixture')
    results, items, spent = {}, {}, 0.0
    for name in args.fixture:
        case = json.loads((FIXTURES / name / 'case.json').read_text())
        if args.findings:
            findings, source = sarif_findings(args.findings.read_text()), 'given'
        else:
            if not args.repo:
                parser.error('producing needs --repo')
            findings, meta, source = produce(case, args.repo, args.budget)
            spent += meta.get('total_cost_usd', 0) or 0
        result = judge(case, findings)
        results[name] = {**result, 'kind': case['kind'], 'source': source}
        items[name] = item(case, result)
        mark = ('CAUGHT' if result['caught'] else 'missed') if case['kind'] == 'bug' else \
            ('quiet' if result['blocking'] == 0 else f'{result["blocking"]} blocking finding(s)')
        print(f'  {name:<32} {case["kind"]:<6} {mark:<24} findings {result["findings"]} ({source})')

    bugs = [n for n in results if results[n]['kind'] == 'bug']
    clean = [n for n in results if results[n]['kind'] == 'clean']
    if bugs:
        print(f'Bugs caught: {sum(results[n]["caught"] for n in bugs)}/{len(bugs)}')
    if clean:
        print(f'Clean cases quiet: {sum(results[n]["blocking"] == 0 for n in clean)}/{len(clean)}')
    if spent:
        print(f'Cost: ${spent:.2f}')

    if args.output:
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / 'results.json').write_text(json.dumps({'results': items, 'detail': results}, indent=2) + '\n')
    if args.baseline:
        pair = spec_eval.paired(json.loads(args.baseline.read_text())['results'], items)
        word, why = spec_eval.verdict(pair)
        for n in pair['wins']:
            print(f'  gained {n}')
        for n in pair['regressions']:
            print(f'  lost   {n}')
        print(f'{word}: {why}')
        return 0 if word in ('BETTER', 'SAME') else 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
