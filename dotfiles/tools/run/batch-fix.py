#!/usr/bin/env python3
"""Fix open review findings overnight, then review again (ADR 0108).

Anthropic's reviewers find, and "often an agent fixes overnight". This does
that for the harness. It reads the review SARIF files `/review` writes, finds
every ticket whose newest review left BLOCKER or REQUIRED findings open, and,
in the worktree still sitting at the reviewed commit, runs two headless
sessions:

    /build <TICKET> review fixes      fix test-first, commit locally
    /review <TICKET>                  the next round, on the fix only

It stops there. Nothing is pushed, nothing reaches `/ship`, and GO stays
yours. A ticket is skipped, with the reason, when:

  - its review files already number three: the next review would be round 4,
    which means the approach needs you (ADR 0089);
  - no worktree sits at the reviewed commit: the candidate moved after the
    review, so it must be reviewed again before anything is fixed;
  - nothing open is BLOCKER or REQUIRED, or what is open is pre-existing.

Usage (from the project's main checkout):
    batch-fix.py --dry-run               # what would run, and what is skipped
    batch-fix.py --yes                   # run every eligible ticket
    batch-fix.py --ticket LD-1 --yes     # one ticket
    batch-fix.py --budget 8 --parallel 2 --yes

Overnight, from cron or `at`:
    echo 'cd ~/code/project && batch-fix.py --yes' | at 01:00

Exit: 0 nothing to do, or every job reached a review · 1 declined, or a job
failed · 2 not in a git repository.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

NAME = re.compile(r'^(?P<ticket>.+)-(?P<sha>[0-9a-f]{7,40})\.sarif$')
ROUND_CAP = 3


def git(*args, cwd=None):
    out = subprocess.run(['git', *args], capture_output=True, text=True, cwd=cwd)
    return out.returncode, out.stdout.strip()


def reviews(directory):
    """{ticket: [(mtime, sha, path)]}, oldest first."""
    found = {}
    for path in Path(directory).glob('*.sarif'):
        m = NAME.match(path.name)
        if m:
            found.setdefault(m.group('ticket'), []).append((path.stat().st_mtime, m.group('sha'), path))
    return {t: sorted(v) for t, v in found.items()}


def open_findings(path):
    """Ids of findings still open that block: BLOCKER or REQUIRED, not pre-existing."""
    data = json.loads(Path(path).read_text())
    ids = []
    for run in data.get('runs', []):
        for r in run.get('results', []):
            props = r.get('properties', {})
            if (props.get('disposition') in ('BLOCKER', 'REQUIRED')
                    and props.get('resolution', 'open') == 'open'
                    and r.get('baselineState') != 'unchanged'):
                ids.append(r.get('ruleId', '?'))
    return ids


def worktrees():
    """{HEAD sha: path} for every worktree of this repository."""
    rc, out = git('worktree', 'list', '--porcelain')
    heads, path = {}, None
    for line in out.splitlines():
        if line.startswith('worktree '):
            path = line[9:]
        elif line.startswith('HEAD ') and path:
            heads[line[5:]] = path
    return heads


def plan(directory, only=None):
    """[{ticket, round, sha, open, worktree, skip}] for every reviewed ticket."""
    heads = worktrees()
    jobs = []
    for ticket, files in sorted(reviews(directory).items()):
        if only and ticket not in only:
            continue
        _, sha, path = files[-1]
        job = {'ticket': ticket, 'round': len(files), 'sha': sha, 'sarif': str(path),
               'open': [], 'worktree': None, 'skip': None}
        try:
            job['open'] = open_findings(path)
        except (OSError, ValueError) as err:
            job['skip'] = f'unreadable review file: {err}'
            jobs.append(job)
            continue
        job['worktree'] = next((p for h, p in heads.items() if h.startswith(sha)), None)
        if not job['open']:
            job['skip'] = 'nothing open that blocks'
        elif job['round'] >= ROUND_CAP:
            job['skip'] = f'round cap: {job["round"]} reviews already; the approach needs you (ADR 0089)'
        elif not job['worktree']:
            job['skip'] = f'no worktree at the reviewed commit {sha}; review the current candidate first'
        jobs.append(job)
    return jobs


def outcome(text):
    """The review's first line that says how it ended."""
    for pattern in (r'REVIEW BLOCKED[^\n]*', r'\*\*Findings:[^\n]*', r'\*\*Nothing to fix\.\*\*'):
        m = re.search(pattern, text)
        if m:
            return m.group(0).strip('*').strip()
    return 'no result line'


def claude(binary, prompt, cwd, budget, mode, log):
    cmd = [binary, '-p', prompt, '--permission-mode', mode,
           '--max-budget-usd', str(budget), '--output-format', 'json']
    out = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    with open(log, 'a') as fh:
        fh.write(f'$ {" ".join(cmd[:3])}\n{out.stdout}\n{out.stderr}\n')
    try:
        data = json.loads(out.stdout)
    except ValueError:
        data = {}
    return out.returncode, data.get('result', out.stdout), data.get('total_cost_usd') or 0


def run_job(job, args, out_dir):
    log = out_dir / f'{job["ticket"]}.log'
    log.write_text('')
    cwd = job['worktree']
    before = git('rev-parse', 'HEAD', cwd=cwd)[1]
    rc, text, cost = claude(args.claude, f'/build {job["ticket"]} review fixes', cwd, args.budget, args.permission_mode, log)
    if rc:
        return dict(job, state='FAILED', detail=f'/build exited {rc}', cost=cost, log=str(log))
    after = git('rev-parse', 'HEAD', cwd=cwd)[1]
    if after == before:
        return dict(job, state='NO FIX', detail='no commit; every finding disputed or blocked (see log)', cost=cost, log=str(log))
    rc, text, more = claude(args.claude, f'/review {job["ticket"]}', cwd, args.budget, args.permission_mode, log)
    cost += more
    if rc:
        return dict(job, state='FAILED', detail=f'/review exited {rc}', cost=cost, log=str(log))
    return dict(job, state='reviewed', detail=outcome(text), cost=cost, log=str(log))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--ticket', action='append', help='limit to this ticket (repeatable)')
    parser.add_argument('--dir', type=Path, help='review directory (default: <git-common-dir>/review)')
    parser.add_argument('--budget', type=float, default=5, help='--max-budget-usd per CLI call (default 5)')
    parser.add_argument('--parallel', type=int, default=1, help='concurrent tickets (default 1)')
    parser.add_argument('--permission-mode', default='acceptEdits')
    parser.add_argument('--out', type=Path, help='logs (default: <git-common-dir>/batch-fix)')
    parser.add_argument('-n', '--dry-run', action='store_true')
    parser.add_argument('-y', '--yes', action='store_true')
    args = parser.parse_args(argv)
    args.claude = os.environ.get('CLAUDE_BIN', 'claude')
    if args.parallel < 1:
        parser.error('--parallel must be at least 1')

    rc, common = git('rev-parse', '--path-format=absolute', '--git-common-dir')
    if rc:
        print('batch-fix: not in a git repository', file=sys.stderr)
        return 2
    directory = args.dir or Path(common) / 'review'
    jobs = plan(directory, set(args.ticket or []))
    run = [j for j in jobs if not j['skip']]
    print(f'batch-fix: {len(run)} ticket(s) to fix, {len(jobs) - len(run)} skipped, ${args.budget:g} cap per call')
    for j in jobs:
        what = j['skip'] or f'{len(j["open"])} open: {", ".join(j["open"])} — in {j["worktree"]}'
        print(f'  {"skip" if j["skip"] else "fix ":<5} {j["ticket"]:<14} round {j["round"]}  {what}')
    if not run:
        return 0
    print(f'Each: /build <TICKET> review fixes, then /review <TICKET>. No push, no /ship. Worst case ${len(run) * 2 * args.budget:g}.')
    if args.dry_run:
        print('batch-fix: dry run; nothing started.')
        return 0
    if not args.yes:
        if not sys.stdin.isatty():
            print('batch-fix: stdin is not a terminal. Re-run with --yes, or --dry-run for the plan.', file=sys.stderr)
            return 1
        if input('Start? [y/N] ').strip().lower() not in ('y', 'yes'):
            print('batch-fix: aborted; nothing started.')
            return 1

    out_dir = args.out or Path(common) / 'batch-fix'
    out_dir.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=args.parallel) as pool:
        results = list(pool.map(lambda j: run_job(j, args, out_dir), run))
    print()
    for r in results:
        print(f'  {r["state"]:<9} {r["ticket"]:<14} {r["detail"]}  ({r["log"]})')
    total = sum(r['cost'] for r in results)
    if total:
        print(f'\n  measured total: ${total:.2f}')
    print('\nRead each review in the morning; /ship stays yours.')
    return 0 if all(r['state'] == 'reviewed' for r in results) else 1


if __name__ == '__main__':
    sys.exit(main())
