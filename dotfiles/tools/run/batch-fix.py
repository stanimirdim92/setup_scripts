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
  - the checkout is not one ticket's alone: several worktrees sit at the
    commit and the branch names do not tell them apart, two tickets claim the
    same checkout, it is detached or on main/master, or it has uncommitted
    changes (the job would mix its edits with yours);
  - nothing open is BLOCKER or REQUIRED, or what is open is pre-existing.

Each job holds an exclusive lock (`batch-fix.lock` in the checkout's git dir)
for its whole run. Under that lock it checks again that HEAD is still the
reviewed commit, on the same branch, with a clean tree. A held lock fails the
job at once; it never waits.

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
import fcntl
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path

NAME = re.compile(r'^(?P<ticket>.+)-(?P<sha>[0-9a-f]{7,40})\.sarif$')
ROUND_CAP = 3
PROTECTED = ('main', 'master')
LOCK_NAME = 'batch-fix.lock'


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
    """[{path, head, branch}] for every worktree of this repository; branch is None when detached."""
    rc, out = git('worktree', 'list', '--porcelain')
    found = []
    for block in out.split('\n\n'):
        entry = {'path': None, 'head': None, 'branch': None}
        for line in block.splitlines():
            if line.startswith('worktree '):
                entry['path'] = line[9:]
            elif line.startswith('HEAD '):
                entry['head'] = line[5:]
            elif line.startswith('branch refs/heads/'):
                entry['branch'] = line[18:]
        if entry['path'] and entry['head']:
            found.append(entry)
    return found


def bind(ticket, sha, checkouts):
    """(checkout, why not): the one worktree and branch this ticket's fix may use."""
    at = [w for w in checkouts if w['head'].startswith(sha)]
    if not at:
        return None, f'no worktree at the reviewed commit {sha}; review the current candidate first'
    usable = [w for w in at if w['branch'] and w['branch'] not in PROTECTED]
    if not usable:
        return None, f'worktree at {sha} is detached or on {"/".join(PROTECTED)}; a fix must go on the ticket branch'
    if len(usable) > 1:
        usable = [w for w in usable if ticket.lower() in w['branch'].lower()]
    if len(usable) != 1:
        return None, f'more than one worktree at {sha} and the branch names do not tell them apart; name the ticket branch for {ticket}'
    return usable[0], None


def checkout_problem(job):
    """Why the checkout is not safe to work in right now, or None."""
    cwd = job['worktree']
    head = git('rev-parse', 'HEAD', cwd=cwd)[1]
    if not head.startswith(job['sha']):
        return f'HEAD is {head[:7]}, not the reviewed commit {job["sha"]}'
    branch = git('symbolic-ref', '--short', '-q', 'HEAD', cwd=cwd)[1]
    if branch != job['branch']:
        return f'branch is {branch or "detached"}, not {job["branch"]}'
    rc, status = git('status', '--porcelain', cwd=cwd)
    if rc or status:
        return 'uncommitted changes in the checkout'
    return None


class CheckoutBusy(Exception):
    pass


@contextmanager
def checkout_lock(worktree):
    """Hold an exclusive lock on the checkout. It never waits: a held lock raises CheckoutBusy."""
    rc, gitdir = git('rev-parse', '--absolute-git-dir', cwd=worktree)
    if rc:
        raise CheckoutBusy(f'cannot find the git dir of {worktree}')
    with open(Path(gitdir) / LOCK_NAME, 'w') as fh:
        try:
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise CheckoutBusy(f'checkout is locked by another batch-fix job ({fh.name})') from None
        yield


def plan(directory, only=None):
    """[{ticket, round, sha, open, worktree, branch, skip}] for every reviewed ticket."""
    checkouts = worktrees()
    jobs = []
    for ticket, files in sorted(reviews(directory).items()):
        _, sha, path = files[-1]
        job = {'ticket': ticket, 'round': len(files), 'sha': sha, 'sarif': str(path),
               'open': [], 'worktree': None, 'branch': None, 'skip': None}
        try:
            job['open'] = open_findings(path)
        except (OSError, ValueError) as err:
            job['skip'] = f'unreadable review file: {err}'
            jobs.append(job)
            continue
        found, why = bind(ticket, sha, checkouts)
        if found:
            job['worktree'], job['branch'] = found['path'], found['branch']
        if not job['open']:
            job['skip'] = 'nothing open that blocks'
        elif job['round'] >= ROUND_CAP:
            job['skip'] = f'round cap: {job["round"]} reviews already; the approach needs you (ADR 0089)'
        elif not found:
            job['skip'] = why
        else:
            problem = checkout_problem(job)
            if problem:
                job['skip'] = f'{job["worktree"]}: {problem}'
        jobs.append(job)
    claims = {}
    for job in jobs:
        if not job['skip']:
            claims.setdefault(job['worktree'], []).append(job['ticket'])
    for job in jobs:
        others = [t for t in claims.get(job['worktree'], []) if t != job['ticket']] if not job['skip'] else []
        if others:
            job['skip'] = f'{job["worktree"]} is also the reviewed commit of {", ".join(others)}; one checkout per ticket'
    return [j for j in jobs if not only or j['ticket'] in only]


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
    try:
        with checkout_lock(job['worktree']):
            problem = checkout_problem(job)
            if problem:
                return dict(job, state='FAILED', detail=problem, cost=0, log='-')
            return work(job, args, out_dir)
    except CheckoutBusy as err:
        return dict(job, state='FAILED', detail=str(err), cost=0, log='-')


def work(job, args, out_dir):
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
