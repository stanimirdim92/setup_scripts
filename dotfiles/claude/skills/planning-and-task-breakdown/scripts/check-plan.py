#!/usr/bin/env python3
"""Check a plan against its spec: every requirement planned, nothing invented, every packet complete.

/plan's Requirement Coverage section is where planning proves it dropped
nothing and invented nothing, and /build hands each todo packet to an
executor as written. Both were checked only by the model that wrote them. A
requirement with no task is silently never built; a task naming a requirement
the spec does not have is scope nobody asked for; a packet without
Verification gives the executor nothing to prove. This checks those links
without a model.

Failures (exit 1):
  - the plan header lacks `Status:`, `Spec:` or `Spec revision:`;
  - a Task Index line does not read `- [ ] T### (size, ws-name, deps: …) [ids]: outcome`;
  - a task id repeats, names no REQ or TD id, or depends on an id the plan does not define;
  - with --spec: a requirement of the spec has no task (unless the spec marks it
    withdrawn, or the plan lists modules under `Not yet planned:`, which turns
    this into a warning), or a task names a REQ id the spec does not have;
  - with --todo: an index task has no packet or a packet has no index line, or a
    packet lacks `**Status:**` (Pending or Done), `**Requirements:**`,
    `**Acceptance criteria:**` or `**Verification:**`.

Warnings: a packet without `**Files/areas likely touched:**` (plan coverage
cannot score it), a Files path written as shorthand that drops the first
path's root (`Http/Requests/` after `Modules/.../Api/`), and a packet whose
Requirements line names other ids than its index line.

Usage:
    check-plan.py docs/tasks/LD-123-plan.md --todo docs/tasks/LD-123-todo.md --spec docs/specs/LD-123-SPEC.md
"""
import argparse
import re
import sys
from pathlib import Path

INDEX = re.compile(r'^\s*-\s*\[[ xX~-]\]\s*(T\d{3})\s*\(([^)]*)\)\s*\[([^\]]*)\]\s*:\s*\S')
INDEX_START = re.compile(r'^\s*-\s*\[[ xX~-]\]\s*(T\d{3})\b')
SUPERSEDED = re.compile(r'~~\s*T\d{3}\s*~~')
CHECKPOINT = re.compile(r'^#{2,4}\s*(CP-\d{3})\b', re.M)
REQ_HEADING = re.compile(r'^### Requirement: (REQ-\d{3}) — (.*)$')
IDS = re.compile(r'\b(REQ-\d{3}|TD-\d{3})\b')
PACKET = re.compile(r'^##\s*(T\d{3})\s*:', re.M)
FIELDS = ('**Status:**', '**Requirements:**', '**Acceptance criteria:**', '**Verification:**')


def header(text, key):
    m = re.search(rf'^\**{re.escape(key)}:?\**:?\s*(.*)$', text, re.M)
    return m.group(1).strip() if m else None


def spec_requirements(text):
    """{REQ id: withdrawn?} from `### Requirement:` headings and the two lines under each."""
    reqs, lines = {}, text.splitlines()
    for i, line in enumerate(lines):
        m = REQ_HEADING.match(line)
        if m:
            near = ' '.join([m.group(2)] + lines[i + 1:i + 3]).lower()
            reqs[m.group(1)] = 'withdrawn' in near
    return reqs


def shorthand_paths(body):
    """Paths on a Files bullet that drop the first path's root, like `Http/Requests/`
    after `Modules/Advertisers/app/Http/Controllers/Api/`."""
    files = re.search(r'\*\*Files/areas likely touched:\*\*(.*?)(?=\n\*\*[^*\n]+:\*\*|\n#|\Z)', body, re.S)
    short = []
    for bullet in re.findall(r'^\s*[-*]\s+(.*)$', files.group(1) if files else '', re.M):
        paths = re.findall(r'`([^`]+)`', bullet)
        root = paths[0].split('/')[0] if paths else ''
        short += [p for p in paths[1:] if '/' in p and p.split('/')[0] != root]
    return short

def check(plan, spec=None, todos=()):
    """(failures, warnings), each a list of (file label, line, message)."""
    fail, warn = [], []
    for key in ('Status', 'Spec', 'Spec revision'):
        if header(plan, key) is None:
            fail.append(('plan', 1, f'no `{key}:` line in the header'))

    tasks, defined = {}, set(CHECKPOINT.findall(plan))
    for n, line in enumerate(plan.splitlines(), 1):
        if SUPERSEDED.search(line) or not INDEX_START.match(line):
            continue
        m = INDEX.match(line)
        tid = INDEX_START.match(line).group(1)
        if not m:
            fail.append(('plan', n, f'{tid}: index line must read `- [ ] T### (size, ws-name, deps: …) [REQ-…]: outcome`'))
            continue
        if tid in tasks:
            fail.append(('plan', n, f'{tid} repeats (first at line {tasks[tid]["line"]})'))
            continue
        meta, ids = m.group(2), IDS.findall(m.group(3))
        deps = re.search(r'deps:\s*(.*)$', meta)
        tasks[tid] = {'line': n, 'ids': set(ids),
                      'deps': re.findall(r'\b(T\d{3}|CP-\d{3})\b', deps.group(1)) if deps else []}
        if not ids:
            fail.append(('plan', n, f'{tid}: names no REQ-### or TD-### id'))
    if not tasks:
        fail.append(('plan', 1, 'no Task Index line (`- [ ] T001 (S, ws-main, deps: —) [REQ-001]: …`)'))
    defined |= set(tasks)
    for tid, t in tasks.items():
        for dep in t['deps']:
            if dep not in defined:
                fail.append(('plan', t['line'], f'{tid} depends on {dep}, which the plan does not define'))

    if spec is not None:
        reqs = spec_requirements(spec)
        planned = set().union(*(t['ids'] for t in tasks.values())) if tasks else set()
        deferred = (header(plan, 'Not yet planned') or 'None').strip().rstrip('.').lower() not in ('none', 'n/a', '')
        for rid, withdrawn in sorted(reqs.items()):
            if rid not in planned and not withdrawn:
                (warn if deferred else fail).append(
                    ('plan', 1, f'{rid} has no task' + (' (its module may be under Not yet planned)' if deferred else '')))
        for tid, t in tasks.items():
            for rid in sorted(i for i in t['ids'] if i.startswith('REQ-') and i not in reqs):
                fail.append(('plan', t['line'], f'{tid} names {rid}, which the spec does not have'))

    packets = {}
    for label, todo in todos:
        starts = [(m.group(1), m.start()) for m in PACKET.finditer(todo)]
        for i, (tid, start) in enumerate(starts):
            end = starts[i + 1][1] if i + 1 < len(starts) else len(todo)
            line = todo[:start].count('\n') + 1
            if tid in packets:
                fail.append((label, line, f'{tid}: a second packet'))
                continue
            packets[tid] = (label, line, todo[start:end])
    if todos:
        for tid in sorted(set(tasks) - set(packets)):
            fail.append(('plan', tasks[tid]['line'], f'{tid} has no packet in the todo file'))
        for tid in sorted(set(packets) - set(tasks)):
            label, line, _ = packets[tid]
            fail.append((label, line, f'{tid} has a packet but no Task Index line'))
        for tid, (label, line, body) in sorted(packets.items()):
            for field in FIELDS:
                if field not in body:
                    fail.append((label, line, f'{tid}: no {field} line'))
            status = re.search(r'\*\*Status:\*\*\s*(\w+)', body)
            if status and status.group(1) not in ('Pending', 'Done'):
                fail.append((label, line, f'{tid}: Status is {status.group(1)!r}, not Pending or Done'))
            if '**Files/areas likely touched:**' not in body:
                warn.append((label, line, f'{tid}: no **Files/areas likely touched:**, so plan coverage cannot score it'))
            for short in shorthand_paths(body):
                warn.append((label, line, f'{tid}: `{short}` is shorthand; write the full repository path, '
                                          'or plan coverage cannot match it'))
            req_line = re.search(r'\*\*Requirements:\*\*(.*)', body)
            if req_line and tid in tasks:
                named = set(IDS.findall(req_line.group(1)))
                if named and named != tasks[tid]['ids']:
                    warn.append((label, line, f'{tid}: packet names {", ".join(sorted(named))}; the index names '
                                              f'{", ".join(sorted(tasks[tid]["ids"]))}'))
    return fail, warn


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('plan', type=Path)
    parser.add_argument('--spec', type=Path, help='the approved spec the plan covers')
    parser.add_argument('--todo', type=Path, action='append', default=[], help='todo file with the task packets (repeatable)')
    args = parser.parse_args(argv)
    try:
        plan = args.plan.read_text(encoding='utf-8')
        spec = args.spec.read_text(encoding='utf-8') if args.spec else None
        todos = [(str(t), t.read_text(encoding='utf-8')) for t in args.todo]
    except OSError as err:
        print(f'check-plan: {err}', file=sys.stderr)
        return 2
    fail, warn = check(plan, spec, todos)
    name = lambda label: str(args.plan) if label == 'plan' else label
    for label, n, msg in fail:
        print(f'FAIL {name(label)}:{n}  {msg}')
    for label, n, msg in warn:
        print(f'warn {name(label)}:{n}  {msg}')
    print(f'check-plan: {len(fail)} failure(s), {len(warn)} warning(s)', file=sys.stderr)
    return 1 if fail else 0


if __name__ == '__main__':
    sys.exit(main())
