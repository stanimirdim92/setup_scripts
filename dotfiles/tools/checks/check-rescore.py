#!/usr/bin/env python3
"""Does every reviewer change say how the review eval scored it? (ADR 0111)

A change to a reviewer persona, to `/review`, to the reviewer triggers or
risk tiers, or to a reviewer's model changes what review catches. Measure
that before trusting it, the way Anthropic rescores its reviewer on real
shipped bugs. Each commit in the range that touches one of those files needs
a `Review-eval:` trailer with the result:

    Review-eval: bugs 5/8 -> 6/8, clean 3/3 -> 3/3 (BETTER); ./after/results.json
    Review-eval: not run - wording only, no change to what is reported

"not run" is allowed with a reason, so the owner decides when a run is worth
its cost. A bare "not run", or no trailer, fails.

Usage:
    check-rescore.py --range origin/main..HEAD
    check-rescore.py --range "$BEFORE..$AFTER"

Exit: 0 clean · 1 a reviewer change without a result · 2 git error.
"""
import argparse
import fnmatch
import re
import subprocess
import sys

WATCHED = (
    'dotfiles/claude/agents/code-reviewer.md',
    'dotfiles/claude/agents/blind-reviewer.md',
    'dotfiles/claude/agents/security-auditor.md',
    'dotfiles/claude/agents/distributed-systems-reviewer.md',
    'dotfiles/claude/commands/review.md',
    'dotfiles/claude/references/reviewer-triggers.md',
    'dotfiles/claude/references/risk-tiers.md',
    'dotfiles/codex/agents/code-reviewer*.toml',
    'dotfiles/codex/agents/blind-reviewer*.toml',
    'dotfiles/codex/agents/security-auditor*.toml',
    'dotfiles/codex/agents/distributed-systems-reviewer*.toml',
)
NOT_RUN = re.compile(r'^not run\s*[-—:]\s*\S', re.I)


def git(*args):
    out = subprocess.run(['git', *args], capture_output=True, text=True)
    if out.returncode:
        raise SystemExit(2)
    return out.stdout


def missing(rng):
    """[(short sha, subject, watched files)] for reviewer changes without a result."""
    bad = []
    for sha in git('rev-list', '--no-merges', rng).split():
        files = git('diff-tree', '--no-commit-id', '--name-only', '-r', sha).split()
        hit = [f for f in files if any(fnmatch.fnmatch(f, g) for g in WATCHED)]
        if not hit:
            continue
        trailer = git('log', '-1', '--format=%(trailers:key=Review-eval,valueonly)', sha).strip()
        if trailer and (not trailer.lower().startswith('not run') or NOT_RUN.match(trailer)):
            continue
        bad.append((sha[:7], git('log', '-1', '--format=%s', sha).strip(), hit))
    return bad


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--range', required=True)
    args = parser.parse_args(argv)
    if re.match(r'^0+\.\.', args.range):
        print('Rescore: new branch, no range to check.')
        return 0
    try:
        bad = missing(args.range)
    except SystemExit:
        print(f'check-rescore: cannot read {args.range}', file=sys.stderr)
        return 2
    if not bad:
        print('Rescore: every reviewer change carries a Review-eval result.')
        return 0
    print('Rescore: reviewer changes without a Review-eval trailer (ADR 0111):')
    for sha, subject, files in bad:
        print(f'  {sha} {subject}\n      {", ".join(files)}')
    print('Run dotfiles/tools/evals/review-eval against the baseline, or state why not:\n'
          '  Review-eval: not run - <reason>')
    return 1


if __name__ == '__main__':
    sys.exit(main())
