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
what went to production (dotfiles/docs/observation-log.md, 2026-09-14). Those specific
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

ROOT = Path(__file__).resolve().parents[4]
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

HARNESS_DIRS = ('commands', 'agents', 'skills', 'references', 'docs', 'hooks')


def link_tree(dst, src):
    """Make `src` visible at `dst`: the whole directory when `dst` is absent,
    otherwise each entry the project does not already have. A project's own
    `.claude/agents` and the global harness combine the same way in real use."""
    if not dst.exists():
        dst.symlink_to(src)
        return
    for child in sorted(src.iterdir()):
        if not (dst / child.name).exists():
            (dst / child.name).symlink_to(child)


def build_project(project, repo=None, at=None):
    """Lay out the throwaway project /spec runs in.

    Without a repository: an empty project, so the fixture measures what the
    spec does with the tickets alone. With one: the files of `repo` at commit
    `at`, exported with `git archive` -- no `.git`, no history, so the run can
    see neither the shipped implementation nor the final spec. Gitignored files
    (`.env`, `vendor/`) are absent; specification needs none of them.
    """
    project.mkdir(parents=True)
    if repo:
        archive = subprocess.run(['git', '-C', str(repo), 'archive', '--format=tar', at],
                                 check=True, capture_output=True)
        subprocess.run(['tar', '-x', '-C', str(project)], input=archive.stdout, check=True)
    else:
        # No application source on purpose: a stand-in repository would measure
        # the stand-in. Expectations assert the spec says so rather than inventing.
        (project / 'README.md').write_text('Empty project fixture. No application source is available in this run.\n')
    (project / 'docs/specs').mkdir(parents=True, exist_ok=True)
    (project / '.claude').mkdir(exist_ok=True)
    for name in HARNESS_DIRS:
        link_tree(project / '.claude' / name, HARNESS / name)
    # The harness rules load as project memory. A project keeps its own
    # CLAUDE.md / AGENTS.md; the harness copy goes beside them, not over them.
    for memory in (project / 'AGENTS.md', project / '.claude/CLAUDE.md'):
        if not memory.exists():
            memory.symlink_to(HARNESS / 'AGENTS.md')
            break
    settings = json.loads((HARNESS / 'settings.json').read_text())
    # settings.local.json, so a project's own .claude/settings.json still applies.
    (project / '.claude/settings.local.json').write_text(json.dumps({
        'model': settings['model'],
        'effortLevel': settings.get('effortLevel'),
        'env': {k: v for k, v in settings['env'].items() if k.startswith('CLAUDE_CODE_MAX_SUBAGENT')
                or k.startswith('CLAUDE_CODE_EXPERIMENTAL') or k.startswith('CLAUDE_CODE_FORK')},
        'worktree': settings.get('worktree', {}),
        'permissions': {'defaultMode': 'acceptEdits'},
    }, indent=2))
    for command in (['git', 'init', '-q', '-b', 'main', '.'], ['git', 'add', '-A'],
                    ['git', '-c', 'user.email=f@f', '-c', 'user.name=f', 'commit', '-qm', 'Fixture baseline']):
        subprocess.run(command, cwd=project, check=True, capture_output=True)
    return project


def specs_snapshot(project):
    return {p.name: p.read_text() for p in (project / 'docs/specs').glob('*.md')}


def written_spec(project, before, ticket):
    """The spec this run wrote: new or changed under docs/specs, preferring the
    ticket's own file. A repository checkout already holds other specs."""
    after = specs_snapshot(project)
    touched = sorted(n for n, text in after.items() if before.get(n) != text)
    own = [n for n in touched if ticket.lower() in n.lower()]
    pick = (own or touched)[:1]
    return after[pick[0]] if pick else None


def produce(fixture, fixture_dir, budget, repo=None, at=None):
    """Run /spec against the fixture's intake in a throwaway project."""
    intake = (fixture_dir / fixture['intake']).read_text()
    with tempfile.TemporaryDirectory() as tmp:
        project = build_project(Path(tmp) / 'project', repo, at)
        before = specs_snapshot(project)
        prompt = (f"/spec {fixture['ticket']}\n\n"
                  "The complete jira-ticket intake output is supplied below, verbatim, produced by the "
                  "jira-ticket skill against offline Jira snapshots. There is no live Jira connection in "
                  "this session, so treat this as the user-supplied intake and do not attempt to refetch it.\n\n"
                  f"--- BEGIN SUPPLIED INTAKE ---\n{intake}\n--- END SUPPLIED INTAKE ---")
        result = subprocess.run(
            ['claude', '-p', prompt, '--setting-sources', 'project,local',
             '--add-dir', str(HARNESS), '--permission-mode', 'acceptEdits',
             '--allowedTools', 'Read', 'Glob', 'Grep', 'Write', 'Edit', 'Task', 'Agent', 'TodoWrite', 'Skill',
             '--max-budget-usd', str(budget), '--output-format', 'json'],
            cwd=project, capture_output=True, text=True, timeout=1800)
        if result.returncode != 0:
            raise RuntimeError(f'claude exited {result.returncode}: {result.stderr[-600:]}')
        meta = json.loads(result.stdout)
        spec = written_spec(project, before, fixture['ticket'])
        if spec is None:
            raise RuntimeError('no spec written; model said: ' + meta.get('result', '')[:400])
        return spec, meta


# ---------------------------------------------------------------- new fixture

# A backticked span counts as a concrete term when it looks like code: an
# identifier with `_ . / : = ( -` or camelCase. These are what a spec must get
# right for an executor to build the right thing -- a parameter, a column, a
# class -- and they can be checked without a model. Line references, commands,
# rule files and design-node ids are trivia: a fresh spec citing a different
# line is not worse, so they are normalized away or dropped.
CODE_LIKE = re.compile(r'[_./:=()\-]|[a-z][A-Z]')
NOT_A_TERM = re.compile(
    r'^(REQ|DEC|SEC|DIST|BLIND|TD|CP|T)-?\d+$'          # pipeline ids
    r'|^\[TICKET\]|^/\w+$'                               # placeholders, slash commands
    r'|^(composer|yarn|npm|npx|php|git|vendor/bin|(\./)?bin/)'   # commands, project scripts
    r'|^\.ai/|^docs/|^\.claude/'                          # rule and pipeline files
    r'|^\d+:\d+$|^:\d|:$')                                # design nodes, bare line refs
LINE_SUFFIX = re.compile(r'(\.\w+):\d+(?:-\d+)?(?:,\s*\d+(?:-\d+)?)*$')
# A span that reads as prose is a pairing accident or a quotation, not a term:
# it opens on a closing bracket, ends on sentence punctuation, carries markdown
# emphasis, or runs three lowercase words in a row ("and continues to").
PROSE = re.compile(r'^[)\],;]|[.,;:]$|\*\*|\b[a-z]+ [a-z]+ [a-z]+\b')
FENCE = re.compile(r'^\s*(```|~~~).*$', re.M)


def normalize_term(term):
    """`Modules/X/TickerRepository.php:237-238` -> `TickerRepository.php`."""
    term = LINE_SUFFIX.sub(r'\1', term.strip())
    if '/' in term and ' ' not in term and re.search(r'\.\w+$', term):
        term = term.rsplit('/', 1)[1]
    return term


def reference_terms(spec, limit=40):
    """The reference spec's concrete terms, most used first.

    Frequency is the ranking because a term the spec returns to is load-bearing;
    one it names once in passing is not what a regression would lose."""
    counts, first = {}, {}
    # Fence lines carry three backticks each and would shift every pairing after them.
    for i, raw in enumerate(re.findall(r'`([^`\n]+)`', FENCE.sub('', spec))):
        if NOT_A_TERM.search(raw.strip()) or PROSE.search(raw.strip()):
            continue
        term = normalize_term(raw)
        if not (3 <= len(term) <= 60) or term.count(' ') > 6:
            continue
        if not CODE_LIKE.search(term) or NOT_A_TERM.search(term):
            continue
        counts[term] = counts.get(term, 0) + 1
        first.setdefault(term, i)
    ranked = sorted(counts, key=lambda term: (-counts[term], first[term]))
    return ranked[:limit]


APPROVED = re.compile(r'^\**Status:?\**:?\s*Approved', re.M)


def spec_history(repo, spec_path):
    """[(commit, path at that commit, ISO date)] oldest first, following renames."""
    out = subprocess.run(['git', '-C', str(repo), 'log', '--follow', '--reverse', '--name-only',
                          '--format=%x1e%H%x1f%cI', '--', str(spec_path)],
                         capture_output=True, text=True, check=True).stdout
    history = []
    for record in out.split('\x1e')[1:]:
        head, _, names = record.partition('\n')
        commit, date = head.split('\x1f')
        path = next((n for n in names.split('\n') if n.strip()), str(spec_path))
        history.append((commit, path.strip(), date.strip()))
    return history


def reference_version(repo, spec_path, which='first-approved'):
    """(text, commit, base commit, as-of date) for the reference spec.

    The reference is the spec as a human first approved it, not as it stands
    today. Later revisions carry what review, verification and production
    found after the build; a fresh /spec at the base commit cannot know any of
    it, so scoring against them counts the unknowable as misses. `latest`
    keeps the old behavior. The base is the parent of the commit that first
    added the spec, and the as-of date is that commit's date: the intake must
    not hold anything written after it."""
    history = spec_history(repo, spec_path)
    if not history:
        return None
    show = lambda c, path: subprocess.run(['git', '-C', str(repo), 'show', f'{c}:{path}'],
                                          capture_output=True, text=True, check=True).stdout
    first_commit, _, first_date = history[0]
    pick = history[-1]
    if which == 'first-approved':
        pick = next((h for h in history if APPROVED.search(show(h[0], h[1]))), history[-1])
    return show(pick[0], pick[1]), pick[0], f'{first_commit}^', first_date[:10]


LATER_DATE = re.compile(r'\b(20\d\d-[01]\d-[0-3]\d)\b')


def dates_after(text, as_of):
    """Lines of the intake that name a date later than `as_of` (YYYY-MM-DD).
    The jira-ticket skill is told to stop at the as-of date; this is the check
    that it did. A later comment is how a replay learns a decision it should
    have had to ask for."""
    return [(n, line.strip()) for n, line in enumerate(text.splitlines(), 1)
            if any(d > as_of for d in LATER_DATE.findall(line))]


def fetch_intake(ticket, jira, repo, budget, as_of=None):
    """Run the jira-ticket skill once and freeze its output, as of `as_of`."""
    cutoff = (f' Report the tickets as they stood at the end of {as_of}: leave out every comment, '
              f'status change, link and description edit made after {as_of}, and say in Source '
              'Coverage how many items you left out for that reason.') if as_of else ''
    prompt = (f'Use the jira-ticket skill on {jira or ticket}.{cutoff} Reply with only its complete intake '
              'summary, exactly as the skill formats it, and nothing else.')
    result = subprocess.run(['claude', '-p', prompt, '--allowedTools', 'Skill', 'Read', 'mcp__jira',
                             '--max-budget-usd', str(budget), '--output-format', 'json'],
                            cwd=repo, capture_output=True, text=True, timeout=900)
    if result.returncode != 0:
        raise RuntimeError(f'claude exited {result.returncode}: {result.stderr[-600:]}')
    meta = json.loads(result.stdout)
    return meta.get('result', ''), meta


def new_fixture(ticket, repo, reference, intake=None, jira=None, at=None, budget='3', force=False,
                which='first-approved', as_of=None):
    """fixtures/<ticket>/ with intake.md, reference-spec.md and expectations.json."""
    repo = Path(repo).resolve()
    ref = Path(reference)
    ref = ref if ref.is_absolute() else repo / ref
    if not ref.is_file():
        raise SystemExit(f'spec-eval: no reference spec at {ref}')
    version = reference_version(repo, ref.resolve().relative_to(repo), which)
    if not version:
        raise SystemExit(f'spec-eval: {ref} has no commit that adds it; commit it, or build the fixture by hand')
    spec, ref_commit, base, first_date = version
    at = at or base
    as_of = as_of or first_date
    out = HERE / 'fixtures' / ticket
    if out.exists() and not force:
        raise SystemExit(f'spec-eval: {out} exists; pass --force to rebuild it')
    out.mkdir(parents=True, exist_ok=True)

    (out / 'reference-spec.md').write_text(spec)
    if intake:
        text, cost = Path(intake).read_text(), None
    else:
        text, meta = fetch_intake(ticket, jira, repo, budget, as_of)
        cost = meta.get('total_cost_usd')
    (out / 'intake.md').write_text(text)
    late = dates_after(text, as_of)

    terms = reference_terms(spec)
    expectations = [
        {'id': 'draft-only', 'why': 'Only a human sets Approved.', 'regex': r'^\**Status:?\**:?\s*Draft'},
        {'id': 'requirement-ids', 'why': 'REQ-### ids are what /plan, /build and /ship trace.',
         'regex': r'REQ-\d{3}'},
    ] + [{'id': f'term:{term}', 'severity': 'should', 'reference_term': True,
          'why': 'The deployed spec names this; a fresh spec that does not may have missed it.',
          'regex': re.escape(term)} for term in terms]
    (out / 'expectations.json').write_text(json.dumps({
        'ticket': ticket, 'intake': 'intake.md', 'reference': 'reference-spec.md',
        'repo': {'at': at}, 'reference_commit': ref_commit, 'reference_version': which, 'as_of': as_of,
        'expectations': expectations}, indent=2) + '\n')
    print(f'Fixture {out}: base {at}, reference {which} at {ref_commit[:10]}, intake as of {as_of}, '
          f'{len(terms)} reference terms' + (f', intake ${cost:.2f}' if cost is not None else '') + '.')
    if late:
        print(f'WARNING: intake.md names {len(late)} date(s) after {as_of}. Information written after the '
              'spec can leak a decision the run should have had to ask for. Remove those lines:')
        for n, line in late[:10]:
            print(f'  intake.md:{n}: {line[:110]}')
    print('Read intake.md once: it is frozen, and every run uses it as is.')
    return out


# ---------------------------------------------------------------- paired comparison

def results_of(rows):
    """{expectation id: met} for every machine-checked expectation."""
    return {e['id']: met for e, met, _, _ in rows if met is not None}


def paired(baseline, current, must_ids=()):
    """Per-item comparison of two runs on the same fixture (SAGE, arXiv 2609.36043).

    An aggregate can rise while items the baseline got right are lost. Pairing
    by item shows each loss. Returns {'wins', 'regressions', 'unchanged',
    'not_compared', 'must_regressions'}."""
    shared = sorted(set(baseline) & set(current))
    wins = [i for i in shared if not baseline[i] and current[i]]
    regressions = [i for i in shared if baseline[i] and not current[i]]
    return {'wins': wins, 'regressions': regressions,
            'unchanged': len(shared) - len(wins) - len(regressions),
            'not_compared': sorted(set(baseline) ^ set(current)),
            'must_regressions': [i for i in regressions if i in must_ids]}


def verdict(pair):
    """Accept only with no lost must item and more wins than losses."""
    if pair['must_regressions']:
        return 'WORSE', 'a must item the baseline met is now missed'
    if len(pair['wins']) > len(pair['regressions']):
        return 'BETTER', 'more items gained than lost'
    if not pair['wins'] and not pair['regressions']:
        return 'SAME', 'no item changed'
    return 'NOT BETTER', 'as many or more items lost than gained'


# ---------------------------------------------------------------- cli

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--fixture', help='directory name under fixtures/')
    parser.add_argument('--new', metavar='TICKET', help='build fixtures/TICKET from a deployed spec (needs --repo, --reference)')
    parser.add_argument('--reference', help='with --new: the deployed spec, relative to --repo or absolute')
    parser.add_argument('--intake', help='with --new: use this intake file instead of fetching from Jira')
    parser.add_argument('--jira', help='with --new: Jira URL or key to fetch (default: the ticket)')
    parser.add_argument('--force', action='store_true', help='with --new: rebuild an existing fixture')
    parser.add_argument('--spec', help='judge this spec file instead of producing one (free)')
    parser.add_argument('--output', help='directory to save the produced spec and run metadata')
    parser.add_argument('--budget', default='15', help='--max-budget-usd for the run (default 15)')
    parser.add_argument('--repo', type=Path,
                        help='project checkout, for a fixture with a "repo" block (its files at the commit, no history)')
    parser.add_argument('--at', help='commit to export; overrides the fixture\'s repo.at')
    parser.add_argument('--reference-version', choices=('first-approved', 'latest'), default='first-approved',
                        help='with --new: which version of the spec is the reference (default: first approved)')
    parser.add_argument('--as-of', help='with --new: intake cutoff date YYYY-MM-DD (default: the date the spec was first committed)')
    parser.add_argument('--baseline', type=Path,
                        help='results.json of an earlier run (from --output): compare item by item, exit 1 unless BETTER or SAME')
    args = parser.parse_args(argv)

    if args.new:
        if not (args.repo and args.reference):
            parser.error('--new needs --repo and --reference')
        new_fixture(args.new, args.repo, args.reference, args.intake, args.jira, args.at, force=args.force,
                    which=args.reference_version, as_of=args.as_of)
        return 0
    if not args.fixture:
        parser.error('pass --fixture NAME, or --new TICKET to build one')

    fixture_dir = HERE / 'fixtures' / args.fixture
    definition = fixture_dir / 'expectations.json'
    if not definition.is_file():
        print(f'spec-eval: no fixture at {definition}', file=sys.stderr)
        print('spec-eval: fixtures hold real ticket content and are gitignored; see README.md', file=sys.stderr)
        return 2
    fixture = json.loads(definition.read_text())
    at = args.at or fixture.get('repo', {}).get('at')
    if args.repo and not at:
        parser.error('--repo needs a commit: set "repo": {"at": ...} in the fixture or pass --at')
    if 'repo' in fixture and not args.repo and not args.spec:
        parser.error(f"fixture {args.fixture} reads the project at {fixture['repo'].get('at')}; pass --repo PATH "
                     '(judging an existing spec with --spec needs no repository)')

    if args.spec:
        spec, meta = Path(args.spec).read_text(), None
        print(f"Judging {args.spec} against {fixture['ticket']} expectations.\n")
    else:
        spec, meta = produce(fixture, fixture_dir, args.budget, args.repo, at)
        if args.repo:
            print(f'Project: {args.repo} at {at} (files only, no history).')
        print(f"Produced a spec for {fixture['ticket']}: {len(spec)} chars, "
              f"${meta.get('total_cost_usd', 0):.2f}, {meta.get('duration_ms', 0) / 1000:.0f}s.\n")

    rows, failed = judge(fixture, spec)

    if args.output:
        out = Path(args.output); out.mkdir(parents=True, exist_ok=True)
        (out / f"{fixture['ticket']}-SPEC.md").write_text(spec)
        if meta:
            (out / 'run.json').write_text(json.dumps(meta, indent=2))
        (out / 'results.json').write_text(json.dumps(
            {'ticket': fixture['ticket'], 'results': results_of(rows)}, indent=2) + '\n')
    semantic = [r for r in rows if r[1] is None]

    for expectation, met, detail, must in rows:
        if met is None or expectation.get('reference_term'):
            continue
        mark = 'PASS' if met else ('FAIL' if must else 'miss')
        print(f"  {mark}  {expectation['id']:<34} {detail}")
        if not met:
            print(f"        why it matters: {expectation['why']}")

    if semantic:
        print('\nFor human review — not machine-checkable:')
        for expectation, _, _, _ in semantic:
            print(f"  ?     {expectation['id']:<34} {expectation['why']}")

    terms = [r for r in rows if r[0].get('reference_term')]
    if terms:
        found = sum(1 for r in terms if r[1])
        print(f"\nReference terms named: {found}/{len(terms)} ({found / len(terms):.0%}) -- "
              f"compare with {fixture.get('reference', 'the reference spec')}")
        missing = [r[0]['id'][len('term:'):] for r in terms if not r[1]]
        if missing:
            print('  not named: ' + ', '.join(f'`{m}`' for m in missing))

    gate = 0
    if args.baseline:
        base = json.loads(args.baseline.read_text())
        must_ids = {e['id'] for e, _, _, must in rows if must}
        pair = paired(base['results'], results_of(rows), must_ids)
        word, why = verdict(pair)
        print(f"\nPaired with {args.baseline}: {len(pair['wins'])} gained, {len(pair['regressions'])} lost, "
              f"{pair['unchanged']} unchanged -- {word} ({why})")
        for label, ids in (('gained', pair['wins']), ('LOST', pair['regressions'])):
            if ids:
                print(f'  {label}: ' + ', '.join(ids))
        if pair['not_compared']:
            print(f"  not compared (in one run only): {len(pair['not_compared'])}")
        gate = 0 if word in ('BETTER', 'SAME') else 1

    checked = len(rows) - len(semantic)
    print(f'\n{checked} checked, {failed} failed, {len(semantic)} for review — '
          f'{"FAILED" if failed else "PASSED"}')
    print('A pass means the known findings survived. It does not mean the spec is good; '
          'read it (README.md).')
    return 1 if failed or gate else 0


if __name__ == '__main__':
    sys.exit(main())
