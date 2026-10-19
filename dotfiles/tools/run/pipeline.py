#!/usr/bin/env python3
"""Run /build, /test and /review for one ticket, a fresh session each (ADR 0114).

Start it in the ticket's worktree, after the plan is approved and committed:

    /build <TICKET>                   implement the plan
    /test <TICKET>                    verify, given the BUILD COMPLETE
    /review <TICKET>                  review, given BUILD and VERIFY

Each stage is a new `claude -p` session, so each starts with a clean context.
The runner puts the previous stages' complete messages, verbatim, into the
prompt (target-selection.md §Gate handoffs); the stage still checks them
against git. When the review leaves BLOCKER or REQUIRED findings, the runner
starts `/build <TICKET> review fixes`, then /test and /review again, until the
review is clean or three review rounds exist (ADR 0089).

It moves on only on a clear result: BUILD COMPLETE, VERIFY PASS, and a review
count line with the review file for HEAD. A CLI error, BLOCKED, FAIL or any
other result stops it. It stops before /ship: GO stays yours. It never pushes.
Every message is saved to `<git-common-dir>/handoff/<TICKET>-<n>-<STAGE>.md`.

Usage (from the ticket's worktree):
    pipeline.py LD-1 --dry-run
    pipeline.py LD-1 --yes
    pipeline.py LD-1 --budget 15 --yes

Exit: 0 the review is clean, ready for /ship · 1 declined or stopped · 2 not a
ticket checkout (not git, master or detached, or uncommitted changes). main is allowed.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROUND_CAP = 3
PROTECTED = ('master',)            # this repository works in main directly
SUPPLIED = 'Supplied verbatim by pipeline.py from the previous session (target-selection.md §Gate handoffs):'


def git(*args):
    out = subprocess.run(['git', *args], capture_output=True, text=True)
    return out.returncode, out.stdout.strip()


def claude(binary, prompt, budget, mode, log, tools=(), model=None):
    """(error, result text, cost). error is None only for exit 0 and a successful JSON result.
    An empty mode leaves the permission mode to the user's settings; tools are allowed up front."""
    cmd = [binary, '-p', *(['--permission-mode', mode] if mode else []), '--max-budget-usd', str(budget),
           '--output-format', 'json', *(['--allowedTools', *tools] if tools else []), *(['--model', model] if model else [])]
    out = subprocess.run(cmd, input=prompt, capture_output=True, text=True)
    with open(log, 'a') as fh:
        fh.write(f'$ {prompt.splitlines()[0]}\n{out.stdout}\n{out.stderr}\n')
    try:
        data = json.loads(out.stdout)
    except ValueError:
        data = None
    if not isinstance(data, dict) or not isinstance(data.get('result'), str):
        data, error = {}, 'printed no JSON result'
    elif data.get('is_error') or data.get('subtype', 'success') != 'success':
        error = f'reported an error ({data.get("subtype") or "is_error"})'
    else:
        error = None
    if out.returncode:
        error = f'exited {out.returncode}'
    return error, data.get('result', out.stdout), data.get('total_cost_usd') or 0


def line(text, pattern):
    m = re.search(rf'^\W*({pattern}[^\n]*)', text, re.M)
    return m.group(1).replace('**', '').strip() if m else None


def review_counts(text):
    """(blocker, required) from the review count line, or None when there is none."""
    if re.search(r'^\W*Nothing to fix\.', text, re.M):
        return 0, 0
    m = re.search(r'Findings: (\d+) BLOCKER · (\d+) REQUIRED', text)
    return (int(m.group(1)), int(m.group(2))) if m else None


def review_files(common, ticket):
    return list((Path(common) / 'review').glob(f'{ticket}-*.sarif'))


def checkout_problem():
    rc, _ = git('rev-parse', '--git-dir')
    if rc:
        return 'not in a git repository'
    branch = git('symbolic-ref', '--short', '-q', 'HEAD')[1]
    if not branch or branch in PROTECTED:
        return f'branch is {branch or "detached"}; run it in the ticket worktree'
    if git('status', '--porcelain')[1]:
        return 'uncommitted changes in the checkout'
    return None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('ticket')
    parser.add_argument('--budget', type=float, default=10, help='--max-budget-usd per stage (default 10)')
    parser.add_argument('--permission-mode', default='acceptEdits',
                        help='claude -p permission mode; empty uses your settings.json (default acceptEdits)')
    parser.add_argument('-n', '--dry-run', action='store_true')
    parser.add_argument('-y', '--yes', action='store_true')
    args = parser.parse_args(argv)
    binary = os.environ.get('CLAUDE_BIN', 'claude')
    ticket = args.ticket

    problem = checkout_problem()
    if problem:
        print(f'pipeline: {problem}')
        return 2
    common = git('rev-parse', '--path-format=absolute', '--git-common-dir')[1]
    print(f'pipeline: {ticket} in {os.getcwd()}, ${args.budget:g} cap per stage')
    print('Each round: /build, /test, /review, a fresh session each. Findings start another round, '
          f'up to {ROUND_CAP} reviews. No /ship, no push. Worst case ${ROUND_CAP * 3 * args.budget:g}.')
    if args.dry_run:
        print('pipeline: dry run; nothing started.')
        return 0
    if not args.yes:
        if not sys.stdin.isatty():
            print('pipeline: stdin is not a terminal. Re-run with --yes, or --dry-run for the plan.', file=sys.stderr)
            return 1
        if input('Start? [y/N] ').strip().lower() not in ('y', 'yes'):
            print('pipeline: aborted; nothing started.')
            return 1

    out_dir = Path(common) / 'handoff'
    out_dir.mkdir(parents=True, exist_ok=True)
    log = out_dir / f'{ticket}-pipeline.log'
    stop_file = out_dir / f'{ticket}-pipeline-stop.json'      # why it stopped, for ticket.py to post
    stop_file.unlink(missing_ok=True)
    total, step, last = 0.0, 0, ''

    def stage(prompt, name, *given):
        nonlocal total, step, last
        step += 1
        for label, text in given:
            prompt += f'\n\n{label} — {SUPPLIED}\n\n{text}'
        error, text, cost = claude(binary, prompt, args.budget, args.permission_mode, log)
        total += cost
        last = f'{ticket}-{step}-{name}.md'
        (out_dir / last).write_text(text.rstrip('\n') + '\n')
        print(f'  {prompt.splitlines()[0]:<32} ${cost:.2f}')
        return error, text

    def stop(why):
        stop_file.write_text(json.dumps({'why': why, 'stage_file': last}) + '\n')
        print(f'\npipeline: stopped — {why}\n  messages and log: {out_dir}\n  measured total: ${total:.2f}')
        return 1

    build_prompt, review = f'/build {ticket}', []
    while True:
        error, build = stage(build_prompt, 'BUILD', *review)
        if error:
            return stop(f'/build {error}')
        if line(build, 'BUILD BLOCKED') or not line(build, 'BUILD COMPLETE'):
            return stop(line(build, 'BUILD BLOCKED') or '/build gave no BUILD COMPLETE line')

        error, verify = stage(f'/test {ticket}', 'VERIFY', ('BUILD COMPLETE', build))
        if error:
            return stop(f'/test {error}')
        result = line(verify, 'VERIFY (?:PASS|FAIL|BLOCKED)')
        if not result or not result.startswith('VERIFY PASS'):
            return stop(result or '/test gave no VERIFY line')

        error, text = stage(f'/review {ticket}', 'REVIEW', ('BUILD COMPLETE', build), ('VERIFY PASS', verify))
        if error:
            return stop(f'/review {error}')
        if line(text, 'REVIEW BLOCKED'):
            return stop(line(text, 'REVIEW BLOCKED'))
        counts = review_counts(text)
        if counts is None:
            return stop('/review gave no count line')
        head = git('rev-parse', 'HEAD')[1]
        files = review_files(common, ticket)
        if not any(head.startswith(p.name[len(ticket) + 1:-len('.sarif')]) for p in files):
            return stop(f'/review wrote no review file for {head[:7]}')
        if sum(counts) == 0:
            print(f'\npipeline: {ticket} review is clean; ready for /ship. Paste {out_dir}/{ticket}-{step}-REVIEW.md '
                  f'into /ship in a new session.\n  measured total: ${total:.2f}')
            return 0
        if len(files) >= ROUND_CAP:
            return stop(f'round cap: {len(files)} reviews and findings remain; the approach needs you (ADR 0089)')
        build_prompt, review = f'/build {ticket} review fixes', [('REVIEW result', text)]


if __name__ == '__main__':
    sys.exit(main())
