#!/usr/bin/env python3
"""Check a spec's shape: the forms /plan, /build, /review and /ship read mechanically.

A spec is prose, and its rules (spec-driven-development, the spec template)
were text only. Text rules drift: a requirement loses its `Source:` line, a
scenario loses its THEN, an obligation is written as "should" in lowercase,
and a spec is marked Approved with an OPEN QUESTION still in it. Nothing
fails; the next stage just reads less than it should. This checks the forms
that can be checked without a model.

Failures (exit 1):
  - the header lacks `Status:`, `Ticket:` or `Change kind:`, or Status is not
    Draft / Approved / Needs reapproval / Superseded;
  - a requirement heading is not `### Requirement: REQ-### — Title`, or an id
    repeats;
  - a requirement has no `Source:` line right under its heading;
  - a requirement has no `#### Scenario:`, or a scenario lacks GIVEN, WHEN or
    THEN;
  - a requirement statement has no uppercase RFC 2119 keyword (MUST, MUST
    NOT, SHOULD, SHOULD NOT, MAY) -- ADR 0075;
  - the spec is Approved and still holds an OPEN QUESTION.
A withdrawn requirement is skipped after its heading.

Warnings (printed, never fail): an EARS condition placed after the keyword
("MUST X when Y"), an `If` clause without `then`, and a SHOULD that names no
exception (ADR 0076). Each is usually a wording slip, and sometimes fine.

Usage:
    check-spec.py docs/specs/LD-123-SPEC.md
    check-spec.py --no-rfc OLD-SPEC.md      # a spec written before ADR 0075
"""
import argparse
import re
import sys
from pathlib import Path

STATUSES = ('Draft', 'Approved', 'Needs reapproval', 'Superseded')
HEADER = re.compile(r'^\**(Status|Ticket|Change kind):?\**:?\s*(.*)$', re.M)
REQ_HEADING = re.compile(r'^### Requirement: (REQ-\d{3}) — \S.*$')
KEYWORD = re.compile(r'\b(MUST NOT|MUST|SHOULD NOT|SHOULD|MAY)\b')
CONDITION_AFTER = re.compile(r'\b(MUST NOT|MUST|SHOULD NOT|SHOULD|MAY)\b[^.]*?,?\s\b(when|while)\b\s')
EXCEPTION = re.compile(r'\b(unless|except|otherwise|exception|other than)\b', re.I)
SENTENCE = re.compile(r'(?<=[.!?])\s+|\n\s*[-*]\s+')


def requirement_blocks(lines):
    """[(line number, heading, body lines)] for every line starting `### Requirement`."""
    blocks, current = [], None
    for n, line in enumerate(lines, 1):
        if line.startswith('### Requirement'):
            current = (n, line.rstrip(), [])
            blocks.append(current)
        elif re.match(r'^#{1,3} ', line) and current:
            current = None
        elif current:
            current[2].append((n, line.rstrip()))
    return blocks


def check(text, rfc=True):
    """(failures, warnings), each a list of (line, message)."""
    lines = text.splitlines()
    fail, warn = [], []

    header = {k: (v.strip(), text[:m.start()].count('\n') + 1)
              for m in HEADER.finditer(text) for k, v in [m.groups()]}
    for key in ('Status', 'Ticket', 'Change kind'):
        if key not in header:
            fail.append((1, f'no `{key}:` line in the header'))
    status = header.get('Status', ('', 1))[0]
    if 'Status' in header and status not in STATUSES:
        fail.append((header['Status'][1], f'Status {status!r} is not one of: {", ".join(STATUSES)}'))

    blocks = requirement_blocks(lines)
    if not blocks:
        fail.append((1, 'no `### Requirement: REQ-### — Title` heading'))
    seen = {}
    for n, heading, body in blocks:
        m = REQ_HEADING.match(heading)
        if not m:
            fail.append((n, f'heading must read `### Requirement: REQ-### — Title`: {heading[:70]}'))
            continue
        rid = m.group(1)
        if rid in seen:
            fail.append((n, f'{rid} repeats (first at line {seen[rid]})'))
        seen.setdefault(rid, n)
        content = [(k, l) for k, l in body if l.strip()]
        if 'withdrawn' in heading.lower() or any('withdrawn' in l.lower() for _, l in content[:2]):
            continue
        if not content or not content[0][1].startswith('Source:'):
            fail.append((n, f'{rid}: the line under the heading must be `Source: …`'))

        scenarios, statement, cur = [], [], None
        for k, l in body:
            if l.startswith('#### Scenario:'):
                cur = [k, l, set()]
                scenarios.append(cur)
            elif cur is not None:
                word = re.match(r'^\s*[-*]?\s*(GIVEN|WHEN|THEN)\b', l)
                if word:
                    cur[2].add(word.group(1))
            elif not l.startswith('Source:'):
                statement.append((k, l))
        if not scenarios:
            fail.append((n, f'{rid}: no `#### Scenario:`'))
        for k, l, words in scenarios:
            missing = [w for w in ('GIVEN', 'WHEN', 'THEN') if w not in words]
            if missing:
                fail.append((k, f'{rid}: scenario lacks {", ".join(missing)}: {l[15:60].strip()}'))

        prose = '\n'.join(l for _, l in statement)
        if rfc and not KEYWORD.search(prose):
            fail.append((n, f'{rid}: no uppercase MUST / SHOULD / MAY in the requirement statement (ADR 0075)'))
        first = statement[0][0] if statement else n
        for sentence in SENTENCE.split(prose):
            s = re.sub(r'^[-*]\s+', '', sentence.strip())
            if not KEYWORD.search(s):
                continue
            if CONDITION_AFTER.search(s):
                warn.append((first, f'{rid}: condition after the keyword; EARS puts the trigger first: {s[:80]}'))
            if re.match(r'^If\b', s) and not re.search(r',\s*then\b', s):
                warn.append((first, f'{rid}: an `If` requirement reads `If <condition>, then …`: {s[:80]}'))
            if re.search(r'\bSHOULD\b', s) and not EXCEPTION.search(s):
                warn.append((first, f'{rid}: a SHOULD names the exception that allows otherwise (ADR 0075): {s[:80]}'))

    if status == 'Approved':
        for n, line in enumerate(lines, 1):
            if line.lstrip().startswith('OPEN QUESTION'):
                fail.append((n, 'the spec is Approved but still holds an OPEN QUESTION'))
    return fail, warn


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('spec', type=Path)
    parser.add_argument('--no-rfc', action='store_true', help='skip the RFC 2119 keyword rule (specs before ADR 0075)')
    args = parser.parse_args(argv)
    try:
        text = args.spec.read_text(encoding='utf-8')
    except OSError as err:
        print(f'check-spec: cannot read {args.spec}: {err}', file=sys.stderr)
        return 2
    fail, warn = check(text, rfc=not args.no_rfc)
    for n, msg in fail:
        print(f'FAIL {args.spec}:{n}  {msg}')
    for n, msg in warn:
        print(f'warn {args.spec}:{n}  {msg}')
    print(f'check-spec: {len(fail)} failure(s), {len(warn)} warning(s)', file=sys.stderr)
    return 1 if fail else 0


if __name__ == '__main__':
    sys.exit(main())
