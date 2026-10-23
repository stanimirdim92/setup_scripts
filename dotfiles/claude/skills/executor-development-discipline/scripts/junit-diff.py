#!/usr/bin/env python3
"""Compare two JUnit XML reports by test identity.

Usage: junit-diff.py BASELINE.xml AFTER.xml

A test's identity is its classname and name (file when classname is absent).
The baseline is the run on the unchanged tree; AFTER is the run on the
candidate. The script prints one summary line and lists:

  new failures    failed or errored in AFTER, passed in the baseline or absent
  newly skipped   skipped in AFTER, passed in the baseline
  missing         in the baseline, absent from AFTER
  now passing     failed in the baseline, passed in AFTER

Exit 0 when there is no new failure, no newly skipped test and no missing
test; exit 1 otherwise; exit 2 when a report cannot be read. A missing test
fails because a deleted or renamed test is not proof of anything; name it in
the handoff report.
"""
import sys
import xml.etree.ElementTree as ET

PASS, FAIL, SKIP = 'pass', 'fail', 'skip'
RANK = {PASS: 0, SKIP: 1, FAIL: 2}


def load(path):
    """Map test identity -> worst status seen for it."""
    results = {}
    for case in ET.parse(path).getroot().iter('testcase'):
        ident = '{}::{}'.format(case.get('classname') or case.get('file') or '',
                                case.get('name') or '')
        if case.find('failure') is not None or case.find('error') is not None:
            status = FAIL
        elif case.find('skipped') is not None:
            status = SKIP
        else:
            status = PASS
        if RANK[status] >= RANK[results.get(ident, PASS)]:
            results[ident] = status
    return results


def compare(base, after):
    new_fail = sorted(t for t, s in after.items() if s == FAIL and base.get(t) != FAIL)
    new_skip = sorted(t for t, s in after.items() if s == SKIP and base.get(t) == PASS)
    missing = sorted(t for t in base if t not in after)
    now_pass = sorted(t for t, s in base.items() if s == FAIL and after.get(t) == PASS)
    return {'new failures': new_fail, 'newly skipped': new_skip,
            'missing': missing, 'now passing': now_pass}


def main(argv):
    if len(argv) != 3:
        print(__doc__.strip().splitlines()[2], file=sys.stderr)
        return 2
    try:
        base, after = load(argv[1]), load(argv[2])
    except (OSError, ET.ParseError) as exc:
        print('junit-diff: cannot read report: {}'.format(exc), file=sys.stderr)
        return 2
    diff = compare(base, after)
    failed = sum(1 for s in after.values() if s == FAIL)
    print('total {} failed {} baseline failed {}'.format(
        len(after), failed, sum(1 for s in base.values() if s == FAIL)))
    for label, tests in diff.items():
        print('{}: {}'.format(label, len(tests)))
        for test in tests:
            print('  ' + test)
    bad = diff['new failures'] or diff['newly skipped'] or diff['missing']
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
