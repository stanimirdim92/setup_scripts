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

It moves on only on a clear result: each stage's HANDOFF line
(references/stage-handoff.md) agreeing with its result line, and the review
file for HEAD. A VERIFY FAIL routed to /build starts a fix round (at most
two), then /test again. A review routed to /test (browser checks it listed, or
a depth above the one /test ran at) runs /test with that review, then /review
again, once per candidate. A CLI error, a missing or disagreeing HANDOFF line,
BLOCKED, or a route elsewhere stops it; the parsed line is in the stop file. It stops before /ship: GO stays yours. It never pushes.
Every message is saved to `<git-common-dir>/handoff/<TICKET>-<n>-<STAGE>.md`.

A stage that fails for a passing reason (rate limit, a dropped connection, a
crash, or no event for HARNESS_STALL_MIN minutes, default 60) is retried up to
HARNESS_RETRIES times (default 5), 10 s · 2ⁿ apart up to 5 min, resuming the
same session when it has one. An auth or budget error stops at once. Each
finished stage is noted in `<TICKET>-pipeline.json`; started again on the same
HEAD, the run goes on from the next stage instead of building again.

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
import selectors
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROUND_CAP = 3                      # reviews per ticket (ADR 0089)
VERIFY_CAP = 2                     # /build fix rounds a VERIFY FAIL may start before a person looks
REVIEW_TEST_CAP = 1                # verifier rounds a review may ask for per candidate (browser checks, a deeper tier)
PROTECTED = ('master',)            # this repository works in main directly
SUPPLIED = 'Supplied verbatim by pipeline.py from the previous session (target-selection.md §Gate handoffs):'
# A -p session ends with the main agent's final message, and a background agent dies with it (LD-503: /test
# ended with "I am waiting for the verifier's report" and no VERIFY line). Every stage is told so.
HEADLESS = ('This is a headless `claude -p` run: the session ends with your final message, and any agent still '
            'running in the background is lost. Dispatch every agent in the foreground (run_in_background: false) '
            'and wait for its report. No person is at this terminal: never call AskUserQuestion or wait for a '
            'reply; a question for the owner goes in the report as numbered options, with `route=owner` and '
            '`decide=<n>` on the HANDOFF line, and the owner answers in Slack. End only with the complete result '
            'line this command requires.')
BACKOFF = (10, 300)                # seconds: first wait, longest wait (Symphony's numbers)
# What a retry can get past: the API or the network, not the task. An auth or billing problem, or a
# budget or turn cap, stops at once.
TRANSIENT = re.compile(r'rate.?limit|overloaded|too many requests|\b(?:429|5\d\d)\b|ECONN|ETIMEDOUT|ENOTFOUND|'
                       r'EAI_AGAIN|EPIPE|socket hang up|fetch failed|network|timed? ?out|connection (?:reset|closed|'
                       r'refused|error)|internal server error|service unavailable', re.I)
FATAL = re.compile(r'not logged in|please (?:log|sign) ?in|authentication|unauthori[sz]ed|invalid api key|'
                   r'\b(?:401|403)\b|credit balance|billing|max_budget|max_turns', re.I)
sleep = time.sleep                 # tests replace it


def git(*args):
    out = subprocess.run(['git', *args], capture_output=True, text=True)
    return out.returncode, out.stdout.strip()


def claude(binary, prompt, budget, mode, log, tools=(), model=None):
    """(error, result text, cost). error is None only for exit 0 and a successful JSON result.
    An empty mode leaves the permission mode to the user's settings; tools are allowed up front.
    A transient failure is retried with backoff, resuming the session when the first attempt opened one;
    the cost adds up over the attempts."""
    retries = int(os.environ.get('HARNESS_RETRIES', '5'))
    stall = float(os.environ.get('HARNESS_STALL_MIN', '60')) * 60
    base = [binary, '-p', '--verbose', *(['--permission-mode', mode] if mode else []), '--max-budget-usd', str(budget),
            '--output-format', 'stream-json', *(['--allowedTools', *tools] if tools else []),
            *(['--model', model] if model else [])]
    cost, session, attempt, send = 0.0, None, 0, prompt
    while True:
        attempt += 1
        cmd = base + (['--resume', session] if session else [])
        error, text, data, why = attempt_once(cmd, send, stall, log, prompt.splitlines()[0])
        cost += data.get('total_cost_usd') or 0
        session = data.get('session_id') or session
        if not error or not is_transient(why) or attempt >= retries:
            return error, text, cost
        wait = min(BACKOFF[0] * 2 ** (attempt - 1), BACKOFF[1])
        print(f'    retry {attempt + 1}/{retries} in {wait}s: {error}' + (' (resuming the session)' if session else ''))
        with open(log, 'a') as fh:
            fh.write(f'retry {attempt + 1}/{retries} in {wait}s: {error}\n')
        sleep(wait)
        send = (f'Your previous turn on this task was cut off ({error}). Carry on from where you stopped; do not '
                f'start over. Finish the task and end with the report it asks for.') if session else prompt


def attempt_once(cmd, prompt, stall, log, title):
    """One `claude -p` run: (error, text, result data, why). It reads the event stream so a stage with no
    event for `stall` seconds is killed; `why` holds what a retry decision needs (stderr, the result, a stall)."""
    with tempfile.TemporaryFile(mode='w+') as err:
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=err, text=True)
        proc.stdin.write(prompt)
        proc.stdin.close()
        sel = selectors.DefaultSelector()
        sel.register(proc.stdout, selectors.EVENT_READ)
        result, session, last, stalled, events = {}, None, time.monotonic(), False, 0
        beat = float(os.environ.get('HARNESS_HEARTBEAT_S', '60'))
        started, next_beat, doing = last, last + beat, ''
        while True:
            if sel.select(timeout=1):
                line = proc.stdout.readline()
                if not line:
                    break
                events, last = events + 1, time.monotonic()
                data = parse_event(line)
                session = data.get('session_id') or session
                doing = tool_call(data) or doing
                if data.get('type') == 'result' or ('type' not in data and 'result' in data):
                    result = data
            elif beat > 0 and time.monotonic() >= next_beat:          # a sign of life while a stage runs
                took = int(time.monotonic() - started)
                print(f'    … {took // 60}m{took % 60:02d}s · {events} events · last {int(time.monotonic() - last)}s ago'
                      + (f' · {doing}' if doing else ''), flush=True)
                next_beat = time.monotonic() + beat
            elif stall > 0 and time.monotonic() - last > stall:
                proc.kill()
                stalled = True
                break
        rc = proc.wait()
        proc.stdout.close()
        err.seek(0)
        stderr = err.read()
    if session and 'session_id' not in result:
        result['session_id'] = session
    with open(log, 'a') as fh:
        fh.write(f'$ {title}\n{json.dumps(result) if result else ""}\n{stderr}\n'
                 + (f'stalled: no event for {stall:.0f}s; killed\n' if stalled else ''))
    if not isinstance(result.get('result'), str):
        error, text = 'printed no JSON result', ''
    elif result.get('is_error') or result.get('subtype', 'success') != 'success':
        error, text = f'reported an error ({result.get("subtype") or "is_error"})', result['result']
    else:
        error, text = None, result['result']
    if stalled:
        error = f'no event for {stall / 60:g} min'
    elif rc:
        error = f'exited {rc}'
    why = {'stalled': stalled, 'rc': rc, 'blob': f'{error or ""}\n{stderr}\n{text if error else ""}'}
    return error, text, result, why


def tool_call(data):
    """'Bash php artisan test …' for an assistant event that calls a tool, else ''."""
    if data.get('type') != 'assistant':
        return ''
    for block in (data.get('message') or {}).get('content') or []:
        if isinstance(block, dict) and block.get('type') == 'tool_use':
            inp = block.get('input') or {}
            arg = inp.get('command') or inp.get('file_path') or inp.get('pattern') or inp.get('description') or ''
            return ' '.join(f'{block.get("name", "")} {str(arg)[:70]}'.split())
    return ''


def parse_event(line):
    try:
        data = json.loads(line)
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def is_transient(why):
    """A stall, a crash or an API/network message is worth a retry; auth, billing and caps are not."""
    if why['stalled']:
        return True
    if FATAL.search(why['blob']):
        return False
    return bool(why['rc']) or bool(TRANSIENT.search(why['blob']))


RESULTS = ('COMPLETE', 'BLOCKED', 'PASS', 'FAIL', 'CLEAN', 'FINDINGS', 'GO', 'NO-GO')
ROUTES = ('none', '/spec', '/plan', '/build', '/test', 'owner')


def handoff(text):
    """The report's HANDOFF line (references/stage-handoff.md) as {result, route, ids, decide}, or None
    when there is none. A value outside the closed sets raises ValueError naming it."""
    lines = [l.strip() for l in text.splitlines() if l.strip().startswith('HANDOFF:')]
    if not lines:
        return None
    fields = dict(re.findall(r'(\w+)=(\S+)', lines[-1]))
    out = {'result': fields.get('result', ''), 'route': fields.get('route', ''),
           'ids': [i for i in fields.get('ids', '-').split(',') if i and i != '-'], 'decide': fields.get('decide', '0')}
    if out['result'] not in RESULTS:
        raise ValueError(f'HANDOFF result={out["result"] or "?"} is not one of {", ".join(RESULTS)}')
    if out['route'] not in ROUTES:
        raise ValueError(f'HANDOFF route={out["route"] or "?"} is not one of {", ".join(ROUTES)}')
    if not out['decide'].isdigit():
        raise ValueError(f'HANDOFF decide={out["decide"]} is not a number')
    out['decide'] = int(out['decide'])
    return out


OK_RESULTS = ('COMPLETE', 'PASS', 'CLEAN', 'GO')


def verdict(text, stage_name, said_ok):
    """The stage's HANDOFF line as a dict, or the reason it cannot be used: missing, a bad value, or a
    verdict that disagrees with the result line the command wrote above it (HR-1 REQ-002)."""
    try:
        h = handoff(text)
    except ValueError as err:
        return None, str(err)
    if h is None:
        return None, f'{stage_name} gave no HANDOFF line'
    if (h['result'] in OK_RESULTS) != bool(said_ok):
        return None, f'{stage_name}: HANDOFF disagrees with the result line (result={h["result"]})'
    return h, None


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
    stop_file = out_dir / f'{ticket}-pipeline-stop.json'      # why it stopped, for ticket.py to post; a clean
                                                              # run removes it, a start keeps the last one
    state_file = out_dir / f'{ticket}-pipeline.json'          # the finished stages, to go on after a crash
    total, step, last = 0.0, 0, ''
    state = resume_state(state_file)
    if state:
        total, step = state['total'], state['step']
        print(f'pipeline: going on after {state["done"]} (stage {step}) on this HEAD; ${total:.2f} spent before')
        step = max(step, *saved_steps(out_dir, ticket))   # a failed stage's message keeps its number

    def note(done, **kept):
        """Stage `done` passed its check on this HEAD; a run started again here goes on after it."""
        state_file.write_text(json.dumps({'head': git('rev-parse', 'HEAD')[1], 'done': done, 'step': step,
                                          'total': total, **kept}) + '\n')

    def inbox(done):
        """ticket.py's word after stage `done`: (stop, notes). It writes HARNESS_INBOX once it has read Slack."""
        path = os.environ.get('HARNESS_INBOX')
        deadline = time.monotonic() + 300
        while path and time.monotonic() < deadline:
            try:
                data = json.loads(Path(path).read_text())
            except (OSError, ValueError):
                data = {}
            if data.get('after_step', -1) >= done:
                return bool(data.get('stop')), '\n'.join(data.get('notes', []))
            time.sleep(1)
        return False, ''

    def stage(prompt, name, *given):
        nonlocal total, step, last
        if step or os.environ.get('HARNESS_INBOX'):    # ticket.py's word, before the first stage too
            stop_now, notes = inbox(step)
            if stop_now:
                return 'stopped by the owner (TICKET STOP)', ''
            if notes:
                prompt += f'\n\nOwner notes from Slack (TICKET NOTE). Follow them unless they conflict with the approved spec:\n{notes}'
        step += 1
        for label, text in given:
            prompt += f'\n\n{label} — {SUPPLIED}\n\n{text}'
        prompt += f'\n\n{HEADLESS}'
        error, text, cost = claude(binary, prompt, args.budget, args.permission_mode, log)
        total += cost
        last = f'{ticket}-{step}-{name}.md'
        (out_dir / last).write_text(text.rstrip('\n') + '\n')
        print(f'  {prompt.splitlines()[0]:<32} ${cost:.2f} · stage {step}')
        return error, text

    def stop(why):
        """Why it stopped, the last stage's file, and that report's HANDOFF line parsed (None without one)."""
        try:
            parsed = handoff((out_dir / last).read_text()) if last else None
        except (OSError, ValueError):
            parsed = None
        stop_file.write_text(json.dumps({'why': why, 'stage_file': last, 'handoff': parsed}) + '\n')
        print(f'\npipeline: stopped — {why}\n  messages and log: {out_dir}\n  measured total: ${total:.2f}')
        return 1

    build_prompt = state.get('build_prompt', f'/build {ticket}')
    review = [('REVIEW result', state['review'])] if state.get('review') else []
    build, verify, done = state.get('build', ''), state.get('verify', ''), state.get('done', '')
    verify_rounds = state.get('verify_rounds', 0)
    verify_review, review_tests = state.get('verify_review', ''), state.get('review_tests', 0)
    while True:
        if done not in ('BUILD', 'VERIFY'):
            error, build = stage(build_prompt, 'BUILD', *review)
            if error:
                return stop(f'/build {error}')
            h, problem = verdict(build, '/build', line(build, 'BUILD COMPLETE') and not line(build, 'BUILD BLOCKED'))
            if problem:
                return stop(problem)
            if h['result'] == 'BLOCKED':                     # its route is in the stop file for ticket.py
                return stop(line(build, 'BUILD BLOCKED') or f'BUILD BLOCKED → {h["route"]}')
            review_tests = 0
            note('BUILD', build=build)

        if done != 'VERIFY':
            error, verify = stage(f'/test {ticket}', 'VERIFY', ('BUILD COMPLETE', build),
                                  *([('REVIEW result', verify_review)] if verify_review else []))
            if error:
                return stop(f'/test {error}')
            said = line(verify, 'VERIFY (?:PASS|FAIL|BLOCKED)') or ''
            h, problem = verdict(verify, '/test', said.startswith('VERIFY PASS'))
            if problem:
                return stop(problem)
            if h['result'] == 'FAIL' and h['route'] == '/build':  # a production defect: fix, then test again
                verify_rounds += 1
                if verify_rounds > VERIFY_CAP:
                    return stop(f'verify round cap: {VERIFY_CAP} fix rounds and /test still fails; a person looks')
                build_prompt, review, done = f'/build {ticket} verify fixes', [('VERIFY result', verify)], ''
                note('REVIEW', build_prompt=build_prompt, review=verify, verify_rounds=verify_rounds,
                     verify_review=verify_review, review_tests=review_tests)
                continue
            if h['result'] != 'PASS':
                return stop(said or f'VERIFY {h["result"]} → {h["route"]}')
            verify_review = ''
            note('VERIFY', build=build, verify=verify, review_tests=review_tests)
        done = ''

        error, text = stage(f'/review {ticket}', 'REVIEW', ('BUILD COMPLETE', build), ('VERIFY PASS', verify))
        if error:
            return stop(f'/review {error}')
        counts = review_counts(text)
        h, problem = verdict(text, '/review', counts is not None and sum(counts) == 0 and not line(text, 'REVIEW BLOCKED'))
        if problem:
            return stop(problem)
        if h['route'] == '/test':                       # browser checks remain, or the depth rose (review.md §2, §4):
            review_tests += 1                           # the verifier runs with this review, then /review again
            if review_tests > REVIEW_TEST_CAP:
                return stop(f'/review routes to /test again on this candidate after {REVIEW_TEST_CAP} verifier '
                            'round; the check did not settle it; a person looks')
            verify_review, done = text, 'BUILD'
            note('BUILD', build=build, verify_review=verify_review, review_tests=review_tests)
            continue
        if h['result'] == 'BLOCKED':
            return stop(line(text, 'REVIEW BLOCKED') or f'REVIEW BLOCKED → {h["route"]}')
        if counts is None:
            return stop('/review gave no count line')
        head = git('rev-parse', 'HEAD')[1]
        files = review_files(common, ticket)
        if not any(head.startswith(p.name[len(ticket) + 1:-len('.sarif')]) for p in files):
            return stop(f'/review wrote no review file for {head[:7]}')
        if h['result'] == 'CLEAN':
            state_file.unlink(missing_ok=True)
            stop_file.unlink(missing_ok=True)
            print(f'\npipeline: {ticket} review is clean; ready for /ship. Paste {out_dir}/{ticket}-{step}-REVIEW.md '
                  f'into /ship in a new session.\n  measured total: ${total:.2f}')
            return 0
        if len(files) >= ROUND_CAP:
            return stop(f'round cap: {len(files)} reviews and findings remain; the approach needs you (ADR 0089)')
        build_prompt, review = f'/build {ticket} review fixes', [('REVIEW result', text)]
        note('REVIEW', build_prompt=build_prompt, review=text, verify_rounds=verify_rounds, review_tests=review_tests)


def saved_steps(out_dir, ticket):
    """The numbers of the stage messages saved for the ticket, and 0."""
    return [0] + [int(m.group(1)) for p in out_dir.glob(f'{ticket}-*-*.md')
                  for m in [re.fullmatch(rf'{re.escape(ticket)}-(\d+)-[A-Z]+\.md', p.name)] if m]


def resume_state(path):
    """The finished stages of an earlier run on this HEAD, or {} (another HEAD means the work moved on)."""
    try:
        state = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    return state if isinstance(state, dict) and state.get('head') == git('rev-parse', 'HEAD')[1] else {}


if __name__ == '__main__':
    sys.exit(main())
