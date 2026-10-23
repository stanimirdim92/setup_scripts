#!/usr/bin/env python3
"""How much person-time and money did a ticket take? (ADR 0112, ADR 0113)

Automation should be loosened only while it holds up: fewer stops for a
person, and no more bugs after merge. This counts the stops for one ticket
from what the pipeline already records, and prints the row for the
"Per ticket" table in the harness's observation-log.md:

- decisions: `### DEC-###` headings in the spec, each one a choice a person made;
- open items: `OPEN-###` ids in docs/tasks/<TICKET>-open.md, raised after the plan;
- approvals: commits that set an `Approved at:` line in the spec or plan,
  so a reapproval counts again;
- review rounds: the ticket's review SARIF files;
- findings: how review findings ended (fixed, refuted, other).

It also reads the ticket's Claude Code transcripts (ADR 0113), the main
sessions and their subagents. A person's record is a typed prompt (also one
queued while the agent worked), an answer to AskUserQuestion or
ExitPlanMode, or a refused tool call. An agent record is a model reply or a
tool result. Four times come from them:

- Elapsed: first to last record across the ticket's sessions. Calendar
  time, nights and other work included.
- Agent: the spans the agent was working. Each runs from a person's record
  (or the session's start) to the last agent record before the next one;
  each subagent runs from its first record to its last. Overlaps between
  sessions count once.
- Waiting: from the end of each agent turn to the next person's record,
  uncapped: the time the work waited for a person. A stretch where any
  session or subagent was working counts as Agent, not Waiting.
- You: for each person's record, the gap since the session's previous
  record, capped at --idle-cap minutes (default 30); a longer gap was a
  break, so it counts as the cap. The last session's final review counts in
  full: from its last agent record to the person's records after it.
  Work outside Claude (reading code, Slack, talking to the PO) leaves no
  record and is not counted. Add it with --extra MIN; it is shown apart.

Tokens and cost: every model reply in those sessions and their subagents,
once per reply (message id), priced from model-prices.json next to this
script. A model missing from that file is reported as unpriced, never
guessed.

A ticket's sessions are every session in its Claude worktree
(`.claude/worktrees/<TICKET>`), plus any session in the project where a
person's prompt names the ticket. When no session is found, the transcript
columns say so instead of printing 0.

The shipped-bugs column starts at 0. A later bug ticket whose spec names
this ticket under "Escaped From" adds one (ADR 0110).

It prints the table header, its separator and the row, then what "You"
leaves out. --row prints the row alone.

Usage:
    ticket-stats.py LD-123
    ticket-stats.py LD-123 --json
    ticket-stats.py LD-123 --row
    ticket-stats.py LD-123 --extra 45          # 45 min outside Claude, as the owner reports it
    ticket-stats.py LD-123 --idle-cap 15 --projects-dir ~/.claude/projects

Exit: 0 · 1 no spec for the ticket · 2 not in a git repository.
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path

PRICES = Path(__file__).resolve().with_name('model-prices.json')
IDLE_CAP_MIN = 30
# Prompts the harness writes into the user turn, not a person.
NOT_TYPED = ('<task-notification', '<system-reminder', '[SYSTEM NOTIFICATION', '<local-command-stdout',
             'Caveat: The messages below', '<agent-message')
# Tools whose result is a person's answer, and the result text of a tool call a person refused.
ASKS_PERSON = ('AskUserQuestion', 'ExitPlanMode')
REFUSED = "The user doesn't want to proceed"
HEADER = ('| Shipped | Ticket | Decisions | Open items | Approvals | Review rounds | Findings | Elapsed | Agent | '
          'Waiting | You | Tokens | Cost | Shipped bugs |')


def git(*args):
    out = subprocess.run(['git', *args], capture_output=True, text=True)
    return out.returncode, out.stdout


def stats(ticket, review_dir):
    spec = Path(f'docs/specs/{ticket}-SPEC.md')
    plan = Path(f'docs/tasks/{ticket}-plan.md')
    open_items = Path(f'docs/tasks/{ticket}-open.md')
    text = spec.read_text()
    found = {
        'ticket': ticket,
        'decisions': len(re.findall(r'^###\s+DEC-\d{3}\b', text, re.M)),
        'open_items': len(set(re.findall(r'\bOPEN-\d{3}\b', open_items.read_text()))) if open_items.exists() else 0,
    }
    paths = [str(p) for p in (spec, plan) if p.exists()]
    _, out = git('log', '--format=%H', r'-G^Approved at:\s*[0-9]', '--', *paths)
    found['approvals'] = len(out.split())
    rounds, endings = 0, {'fixed': 0, 'refuted': 0, 'other': 0}
    for path in sorted(Path(review_dir).glob(f'{ticket}-*.sarif')):
        if not re.fullmatch(rf'{re.escape(ticket)}-[0-9a-f]{{7,40}}\.sarif', path.name):
            continue
        rounds += 1
        try:
            data = json.loads(path.read_text())
        except ValueError:
            continue
        for run in data.get('runs', []):
            for r in run.get('results', []):
                end = r.get('properties', {}).get('resolution', 'open')
                endings[end if end in ('fixed', 'refuted') else 'other'] += 1
    found['review_rounds'] = rounds
    found['findings'] = endings
    return found


def run_stats(ticket, handoff_dir):
    """What the unattended runner recorded for the ticket (HR-1 REQ-008): owner interventions (replies it
    acted on), its stops by cause class, stage retries, conflicts taken to /spec, and what it spent. None
    when ticket.py never ran the ticket."""
    state_file = Path(handoff_dir) / f'{ticket}-ticket.json'
    if not state_file.exists():
        return None
    st = json.loads(state_file.read_text())
    by_class = {}
    for stop in st.get('stops', []):
        by_class[stop.get('class', 'runner')] = by_class.get(stop.get('class', 'runner'), 0) + 1
    retries = 0
    for name in (f'{ticket}-ticket.log', f'{ticket}-pipeline.log'):
        log = Path(handoff_dir) / name
        if log.exists():
            retries += len(re.findall(r'^retry \d+/\d+ in', log.read_text(), re.M))
    return {'interventions': len(st.get('inbox_seen', [])) + len((st.get('ask') or {}).get('seen', [])),
            'stops': by_class, 'runner_stops': by_class.get('runner', 0), 'retries': retries,
            'conflicts': st.get('conflicts', 0), 'cost_usd': st.get('cost', 0),
            'decisions_asked': len(st.get('decisions', {}))}


def run_line(r):
    stops = ', '.join(f'{n} {c}' for c, n in sorted(r['stops'].items())) or 'none'
    return (f'run: {r["interventions"]} owner interventions · stops: {stops} · {r["retries"]} stage retries · '
            f'{r["conflicts"]} conflicts to /spec · ${r["cost_usd"]:.2f}')


def slug(path):
    """Claude Code's project-dir name: every character that is not a letter or digit becomes '-'."""
    return re.sub(r'[^A-Za-z0-9]', '-', str(path))


def records(path):
    out = []
    try:
        lines = path.read_text(errors='replace').splitlines()
    except OSError:
        return out
    for line in lines:
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if isinstance(rec, dict):
            out.append(rec)
    return out


def typed_prompt(rec):
    """The text a person typed, or None for tool results, meta and harness turns."""
    if rec.get('type') != 'user' or rec.get('isMeta') or rec.get('isSidechain'):
        return None
    content = (rec.get('message') or {}).get('content')
    if isinstance(content, list):
        if any(isinstance(b, dict) and b.get('type') == 'tool_result' for b in content):
            return None
        content = '\n'.join(b.get('text', '') for b in content if isinstance(b, dict))
    if not isinstance(content, str) or not content.strip():
        return None
    if content.lstrip().startswith(NOT_TYPED):
        return None
    return content


def when(rec):
    try:
        return datetime.datetime.fromisoformat(rec['timestamp'].replace('Z', '+00:00'))
    except (KeyError, TypeError, ValueError):
        return None


def sessions(ticket, main_checkout, projects_dir):
    """Main transcripts for the ticket: its worktree's sessions, and project sessions whose prompts name it."""
    base = slug(main_checkout)
    worktree = f'{base}--claude-worktrees-{slug(ticket)}'
    names = re.compile(rf'(?<![A-Za-z0-9]){re.escape(ticket)}(?![0-9])')
    found = []
    if not projects_dir.is_dir():
        return found
    for d in sorted(projects_dir.iterdir()):
        if not d.is_dir() or not (d.name == base or d.name.startswith(f'{base}--claude-worktrees-')):
            continue
        for f in sorted(d.glob('*.jsonl')):
            recs = records(f)
            if d.name == worktree or any(names.search(typed_prompt(r) or '') for r in recs):
                found.append((f, recs))
    return found


def usage(recs):
    """One usage per model reply: parallel tool calls repeat it on every record of the reply."""
    best = {}
    for i, r in enumerate(recs):
        msg = r.get('message') or {}
        u = msg.get('usage')
        if r.get('type') != 'assistant' or not isinstance(u, dict):
            continue
        key = msg.get('id') or r.get('requestId') or f'rec{i}'
        if key not in best or (u.get('output_tokens') or 0) > (best[key][1].get('output_tokens') or 0):
            best[key] = (msg.get('model') or '?', u)
    return list(best.values())


def cost_of(model, u, prices):
    p = prices.get(model)
    if p is None:
        return None
    created = u.get('cache_creation_input_tokens') or 0
    split = u.get('cache_creation') or {}
    write_1h = split.get('ephemeral_1h_input_tokens') or 0
    write_5m = created - write_1h
    dollars = ((u.get('input_tokens') or 0) * p['input'] + (u.get('output_tokens') or 0) * p['output']
               + (u.get('cache_read_input_tokens') or 0) * p['cache_read']
               + write_5m * p['cache_write_5m'] + write_1h * p['cache_write_1h']) / 1e6
    if u.get('speed') == 'fast':
        if 'fast' not in p:
            return None
        dollars *= p['fast']
    return dollars


def timeline(recs):
    """Walk one main transcript. Returns the agent spans, the waiting spans, the person's records as
    (time, gap since the session's previous record, is a typed prompt), and the last agent record's time."""
    asks, agent, waiting, person = set(), [], [], []
    removed = {r.get('content') for r in recs if r.get('type') == 'queue-operation' and r.get('operation') == 'remove'}
    start = turn_start = last_agent = prev = None
    for r in recs:
        t = when(r)
        if t is None:
            continue
        start = start or t
        msg = r.get('message') or {}
        content = msg.get('content') if isinstance(msg.get('content'), list) else []
        kind = None
        if typed_prompt(r) is not None:
            kind = 'prompt'
        elif (r.get('type') == 'queue-operation' and r.get('operation') == 'enqueue' and r.get('content') in removed
              and isinstance(r.get('content'), str) and r['content'].strip()
              and not r['content'].lstrip().startswith(NOT_TYPED)):
            kind = 'queued'                          # typed while the agent worked; it never became a user record
        elif r.get('type') == 'assistant':
            asks.update(b.get('id') for b in content if isinstance(b, dict) and b.get('type') == 'tool_use'
                        and b.get('name') in ASKS_PERSON)
            kind = 'agent'
        elif r.get('type') == 'user' and any(isinstance(b, dict) and b.get('type') == 'tool_result' for b in content):
            answered = any(isinstance(b, dict) and b.get('tool_use_id') in asks for b in content)
            refused = any(isinstance(b, dict) and str(b.get('content')).startswith(REFUSED) for b in content)
            kind = 'answer' if answered or refused else 'agent'
        if kind == 'agent':
            last_agent = max(last_agent or t, t)
        elif kind in ('prompt', 'answer'):
            end = begin = turn_start or start
            if last_agent and last_agent > begin:
                agent.append((begin, last_agent))
                end = last_agent
            if t > end:
                waiting.append((end, t))
            turn_start, last_agent = t, None
        if kind in ('prompt', 'queued', 'answer'):
            person.append((t, (t - prev).total_seconds() if prev else 0.0, kind != 'answer'))
        if not r.get('isSidechain') and r.get('type') != 'queue-operation':
            prev = t
    if last_agent and last_agent > (turn_start or start):
        agent.append((turn_start or start, last_agent))
    final_agent = max([e for _, e in agent], default=None)
    return agent, waiting, person, final_agent


def merged(spans):
    out = []
    for s, e in sorted(spans):
        if out and s <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], e))
        else:
            out.append((s, e))
    return out


def minutes(spans):
    return sum((e - s).total_seconds() for s, e in spans) / 60


def minus(spans, cut):
    """The parts of the merged spans that no span in the merged cut covers."""
    out = []
    for s, e in spans:
        for cs, ce in cut:
            if ce <= s or cs >= e:
                continue
            if cs > s:
                out.append((s, cs))
            s = max(s, ce)
            if s >= e:
                break
        if s < e:
            out.append((s, e))
    return out


def spend(ticket, main_checkout, projects_dir, idle_cap_min=IDLE_CAP_MIN, prices_file=PRICES, extra_min=0.0):
    table = json.loads(prices_file.read_text())
    prices = table['models']
    found = sessions(ticket, main_checkout, projects_dir)
    out = {'sessions': len(found), 'prompts': 0, 'answers': 0, 'elapsed_minutes': 0.0, 'agent_minutes': 0.0,
           'waiting_minutes': 0.0, 'your_minutes': 0.0, 'extra_minutes': extra_min, 'idle_cap_minutes': idle_cap_min,
           'tokens': 0, 'cost_usd': 0.0, 'unpriced_tokens': 0, 'unpriced_models': [], 'prices_as_of': table['as_of']}
    cap = idle_cap_min * 60
    unpriced = set()
    agent, waiting, stamps, last = [], [], [], None
    for path, recs in found:
        a, w, person, final_agent = timeline(recs)
        agent += a
        waiting += w
        times = [t for t in map(when, recs) if t]
        stamps += times
        out['prompts'] += sum(1 for _, _, typed in person if typed)
        out['answers'] += sum(1 for _, _, typed in person if not typed)
        out['your_minutes'] += sum(min(max(gap, 0), cap) for _, gap, _ in person) / 60
        if times and (last is None or max(times) > last[0]):
            last = (max(times), person, final_agent)
        replies = list(recs)
        sub = path.with_suffix('') / 'subagents'
        if sub.is_dir():
            for f in sorted(sub.glob('*.jsonl')):
                sub_recs = records(f)
                replies += sub_recs
                sub_times = [t for t in map(when, sub_recs) if t]
                if sub_times:
                    agent.append((min(sub_times), max(sub_times)))
                    stamps += sub_times
        for model, u in usage(replies):
            n = sum(u.get(k) or 0 for k in ('input_tokens', 'output_tokens', 'cache_read_input_tokens',
                                            'cache_creation_input_tokens'))
            if not n:
                continue
            out['tokens'] += n
            dollars = cost_of(model, u, prices)
            if dollars is None:
                out['unpriced_tokens'] += n
                unpriced.add(model)
            else:
                out['cost_usd'] += dollars
    if last and last[2]:
        # The final review: the person's records after the last agent record count in full, not capped.
        _, person, final_agent = last
        after = [(t, gap) for t, gap, _ in person if t > final_agent]
        if after:
            out['your_minutes'] += ((after[-1][0] - final_agent).total_seconds()
                                    - sum(min(max(gap, 0), cap) for _, gap in after)) / 60
    agent = merged(agent)
    if stamps:
        out['elapsed_minutes'] = (max(stamps) - min(stamps)).total_seconds() / 60
    out['agent_minutes'] = minutes(agent)
    out['waiting_minutes'] = minutes(minus(merged(waiting), agent))
    for k in ('elapsed_minutes', 'agent_minutes', 'waiting_minutes', 'your_minutes'):
        out[k] = round(out[k], 1)
    out['cost_usd'] = round(out['cost_usd'], 2)
    out['unpriced_models'] = sorted(unpriced)
    return out


def human(n):
    if n >= 1_000_000:
        return f'{n / 1_000_000:.1f}M'
    if n >= 1000:
        return f'{round(n / 1000)}k'
    return str(n)


def duration(minutes):
    m = round(minutes)
    return f'{m}m' if m < 60 else f'{m // 60}h{m % 60:02d}m'


def row(s, today=None):
    f = s['findings']
    sp = s.get('spend')
    if not sp or not sp['sessions']:
        times = ['no transcript found'] * 4
        tokens_col = cost_col = 'no transcript found'
    else:
        you = f'{duration(sp["your_minutes"])}, {sp["prompts"]} prompts'
        if sp['answers']:
            you += f', {sp["answers"]} answers'
        if sp.get('extra_minutes'):
            you += f' + {duration(sp["extra_minutes"])} reported'
        times = [duration(sp['elapsed_minutes']), duration(sp['agent_minutes']), duration(sp['waiting_minutes']), you]
        tokens_col = f'{human(sp["tokens"])} in {sp["sessions"]} sessions'
        cost_col = f'${sp["cost_usd"]:.2f} (prices {sp["prices_as_of"]})'
        if sp['unpriced_tokens']:
            cost_col += f' + {human(sp["unpriced_tokens"])} unpriced ({", ".join(sp["unpriced_models"])})'
    return (f'| {today or datetime.date.today().isoformat()} | {s["ticket"]} | {s["decisions"]} | '
            f'{s["open_items"]} | {s["approvals"]} | {s["review_rounds"]} | '
            f'{f["fixed"]} fixed, {f["refuted"]} refuted, {f["other"]} other | '
            f'{" | ".join(times)} | {tokens_col} | {cost_col} | 0 |')


def table(s, today=None):
    """The "Per ticket" header, its separator, the row, and what the You column cannot see."""
    cap = (s.get('spend') or {}).get('idle_cap_minutes', IDLE_CAP_MIN)
    return '\n'.join([HEADER, '|' + '---|' * HEADER.count(' | ') + '---|', row(s, today), '',
                      f'Elapsed: first to last record. Agent: the agent working. Waiting: turns waiting for you. '
                      f'You: each prompt or answer counts the gap before it, up to {cap:g} min. Work outside Claude '
                      f'(reading code, Slack, the PO) is not in the transcripts; add it with --extra MIN.'])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('ticket')
    parser.add_argument('--review-dir', type=Path)
    parser.add_argument('--projects-dir', type=Path,
                        default=Path(os.environ.get('CLAUDE_PROJECTS_DIR', Path.home() / '.claude' / 'projects')))
    parser.add_argument('--idle-cap', type=float, default=IDLE_CAP_MIN,
                        help=f'minutes; a longer gap before a prompt counts as this much (default {IDLE_CAP_MIN})')
    parser.add_argument('--extra', type=float, default=0.0, metavar='MIN',
                        help='minutes the owner reports outside Claude; shown apart in the You column')
    parser.add_argument('--row', action='store_true', help='print the table row alone, without header or notes')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    rc, common = git('rev-parse', '--path-format=absolute', '--git-common-dir')
    if rc:
        print('ticket-stats: not in a git repository', file=sys.stderr)
        return 2
    if not Path(f'docs/specs/{args.ticket}-SPEC.md').exists():
        print(f'ticket-stats: no docs/specs/{args.ticket}-SPEC.md', file=sys.stderr)
        return 1
    common = Path(common.strip())
    s = stats(args.ticket, args.review_dir or common / 'review')
    s['spend'] = spend(args.ticket, common.parent, args.projects_dir, args.idle_cap, extra_min=args.extra)
    s['run'] = run_stats(args.ticket, common / 'handoff')
    if args.json:
        print(json.dumps(s, indent=2))
    else:
        print((row(s) if args.row else table(s)) + (f'\n{run_line(s["run"])}' if s['run'] else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
