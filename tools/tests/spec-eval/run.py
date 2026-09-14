#!/usr/bin/env python3
"""Re-run /spec against a ticket whose right answer is known, and check it still finds it.

Every other check in this repo tests the harness's *shape*: that a persona
declares its tools, that a path is spelled one way, that a hook denies a push.
None of them can tell you whether a change made specs better or worse. That
question only has an answer where the correct output is known independently,
and it is known in exactly one place -- a ticket that shipped, whose spec a
human has read against the implementation and judged.

LD-380 is the first such fixture. Its 0056-harness spec caught three
contradictions buried in linked tickets' comment threads; the approver
confirmed the open questions were valid, that most had not been caught during
the implementation two weeks earlier, and that the spec named work missing from
what went to production (docs/observation-log.md, 2026-09-14). Those specific
findings are the expectations. A later harness that stops producing them has
regressed, whatever its other checks say.

Fixtures hold real ticket content and live outside the repository, under
`fixtures/`, which is gitignored. `fixtures/example/` shows the format with
invented tickets. See README.md.

Two modes, deliberately separable:

    run.py --fixture LD-380            # produce a spec, then judge it (costs tokens)
    run.py --fixture LD-380 --spec P   # judge an existing spec (free)

The second is what makes the expectations themselves testable, and what lets
you re-judge yesterday's spec under today's expectations.
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HARNESS = ROOT / 'dotfiles/claude'
HERE = Path(__file__).resolve().parent


# ---------------------------------------------------------------- judging

def window(text, terms, lines):
    """True when every term appears inside some `lines`-line window.

    Co-occurrence, not presence. A spec that merely says "email" somewhere has
    not noticed that LD-238 promises one and LD-380 forbids it; a spec that
    says both within a few lines of each other has.
    """
    rows = text.splitlines()
    lowered = [r.lower() for r in rows]
    needles = [t.lower() for t in terms]
    for start in range(len(rows)):
        chunk = '\n'.join(lowered[start:start + lines])
        if all(n in chunk for n in needles):
            return True
    return False


def evaluate(expectation, spec):
    """(met, detail) for one expectation. Semantic ones are never auto-met."""
    kind = expectation.get('kind', 'deterministic')
    if kind == 'semantic':
        return None, 'needs human review'

    if 'near' in expectation:
        terms = expectation['near']
        span = expectation.get('within_lines', 4)
        return window(spec, terms, span), f'terms {terms} within {span} lines'
    if 'regex' in expectation:
        return bool(re.search(expectation['regex'], spec, re.M | re.I)), f"/{expectation['regex']}/"
    if 'absent_regex' in expectation:
        hit = re.search(expectation['absent_regex'], spec, re.M | re.I)
        return not hit, f"/{expectation['absent_regex']}/ must not match" + (f' -- found {hit.group(0)!r}' if hit else '')
    raise ValueError(f"expectation {expectation['id']}: no predicate (near / regex / absent_regex)")


def judge(fixture, spec):
    """Apply every expectation. Returns (rows, failed_must)."""
    rows, failed = [], 0
    for expectation in fixture['expectations']:
        met, detail = evaluate(expectation, spec)
        must = expectation.get('severity', 'must') == 'must'
        if met is False and must:
            failed += 1
        rows.append((expectation, met, detail, must))
    return rows, failed


# ---------------------------------------------------------------- producing

def produce(fixture, fixture_dir, budget):
    """Run /spec against the fixture's intake in a throwaway project."""
    intake = (fixture_dir / fixture['intake']).read_text()
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / 'project'
        (project / 'docs/specs').mkdir(parents=True)
        (project / '.claude').mkdir()
        for name in ('commands', 'agents', 'skills', 'references', 'docs', 'hooks'):
            (project / '.claude' / name).symlink_to(HARNESS / name)
        (project / '.claude/CLAUDE.md').symlink_to(HARNESS / 'CLAUDE.md')
        settings = json.loads((HARNESS / 'settings.json').read_text())
        (project / '.claude/settings.json').write_text(json.dumps({
            'model': settings['model'],
            'effortLevel': settings.get('effortLevel'),
            'env': {k: v for k, v in settings['env'].items() if k.startswith('CLAUDE_CODE_MAX_SUBAGENT')
                    or k.startswith('CLAUDE_CODE_EXPERIMENTAL') or k.startswith('CLAUDE_CODE_FORK')},
            'worktree': settings.get('worktree', {}),
            'permissions': {'defaultMode': 'acceptEdits'},
        }, indent=2))
        # No application source on purpose: this fixture measures what the spec
        # does with the tickets, and a stand-in repository would measure the
        # stand-in. Expectations assert the spec says so rather than inventing.
        (project / 'README.md').write_text('Empty project fixture. No application source is available in this run.\n')
        for command in (['git', 'init', '-q', '-b', 'main', '.'], ['git', 'add', '-A'],
                        ['git', '-c', 'user.email=f@f', '-c', 'user.name=f', 'commit', '-qm', 'Fixture baseline']):
            subprocess.run(command, cwd=project, check=True)

        prompt = (f"/spec {fixture['ticket']}\n\n"
                  "The complete jira-ticket intake output is supplied below, verbatim, produced by the "
                  "jira-ticket skill against offline Jira snapshots. There is no live Jira connection in "
                  "this session, so treat this as the user-supplied intake and do not attempt to refetch it.\n\n"
                  f"--- BEGIN SUPPLIED INTAKE ---\n{intake}\n--- END SUPPLIED INTAKE ---")
        result = subprocess.run(
            ['claude', '-p', prompt, '--setting-sources', 'project',
             '--add-dir', str(HARNESS), '--permission-mode', 'acceptEdits',
             '--allowedTools', 'Read', 'Glob', 'Grep', 'Write', 'Edit', 'Task', 'Agent', 'TodoWrite', 'Skill',
             '--max-budget-usd', str(budget), '--output-format', 'json'],
            cwd=project, capture_output=True, text=True, timeout=1800)
        if result.returncode != 0:
            raise RuntimeError(f'claude exited {result.returncode}: {result.stderr[-600:]}')
        meta = json.loads(result.stdout)
        written = sorted((project / 'docs/specs').glob('*.md'))
        if not written:
            raise RuntimeError('no spec written; model said: ' + meta.get('result', '')[:400])
        return written[0].read_text(), meta


# ---------------------------------------------------------------- cli

def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--fixture', required=True, help='directory name under fixtures/')
    parser.add_argument('--spec', help='judge this spec file instead of producing one (free)')
    parser.add_argument('--output', help='directory to save the produced spec and run metadata')
    parser.add_argument('--budget', default='15', help='--max-budget-usd for the run (default 15)')
    args = parser.parse_args()

    fixture_dir = HERE / 'fixtures' / args.fixture
    definition = fixture_dir / 'expectations.json'
    if not definition.is_file():
        print(f'spec-eval: no fixture at {definition}', file=sys.stderr)
        print('spec-eval: fixtures hold real ticket content and are gitignored; see README.md', file=sys.stderr)
        return 2
    fixture = json.loads(definition.read_text())

    if args.spec:
        spec, meta = Path(args.spec).read_text(), None
        print(f"Judging {args.spec} against {fixture['ticket']} expectations.\n")
    else:
        spec, meta = produce(fixture, fixture_dir, args.budget)
        print(f"Produced a spec for {fixture['ticket']}: {len(spec)} chars, "
              f"${meta.get('total_cost_usd', 0):.2f}, {meta.get('duration_ms', 0) / 1000:.0f}s.\n")

    if args.output:
        out = Path(args.output); out.mkdir(parents=True, exist_ok=True)
        (out / f"{fixture['ticket']}-SPEC.md").write_text(spec)
        if meta:
            (out / 'run.json').write_text(json.dumps(meta, indent=2))

    rows, failed = judge(fixture, spec)
    semantic = [r for r in rows if r[1] is None]

    for expectation, met, detail, must in rows:
        if met is None:
            continue
        mark = 'PASS' if met else ('FAIL' if must else 'miss')
        print(f"  {mark}  {expectation['id']:<34} {detail}")
        if not met:
            print(f"        why it matters: {expectation['why']}")

    if semantic:
        print('\nFor human review — not machine-checkable:')
        for expectation, _, _, _ in semantic:
            print(f"  ?     {expectation['id']:<34} {expectation['why']}")

    checked = len(rows) - len(semantic)
    print(f'\n{checked} checked, {failed} failed, {len(semantic)} for review — '
          f'{"FAILED" if failed else "PASSED"}')
    print('A pass means the known findings survived. It does not mean the spec is good; '
          'read it (README.md).')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
