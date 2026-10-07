#!/usr/bin/env python3
"""Project layout for spec-eval runs, with `claude` never invoked. Runs in CI."""
import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

spec = importlib.util.spec_from_file_location('run', Path(__file__).with_name('run.py'))
run = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run)


def git(cwd, *args):
    return subprocess.run(['git', '-C', str(cwd), '-c', 'user.email=t@t', '-c', 'user.name=t', *args],
                          check=True, capture_output=True, text=True).stdout.strip()


class RepoProject(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / 'app'
        (self.repo / 'docs/specs').mkdir(parents=True)
        (self.repo / '.claude/agents').mkdir(parents=True)
        (self.repo / 'docs/specs/LD-1-SPEC.md').write_text('old spec\n')
        (self.repo / '.claude/agents/local-helper.md').write_text('project agent\n')
        (self.repo / 'CLAUDE.md').write_text('project rules\n')
        (self.repo / 'Ticker.php').write_text('<?php // before\n')
        git(self.repo, 'init', '-q'); git(self.repo, 'add', '-A'); git(self.repo, 'commit', '-qm', 'base')
        self.base = git(self.repo, 'rev-parse', 'HEAD')
        (self.repo / 'Shipped.php').write_text('<?php // the implementation\n')
        (self.repo / 'docs/specs/LD-2-SPEC.md').write_text('the final spec\n')
        git(self.repo, 'add', '-A'); git(self.repo, 'commit', '-qm', 'LD-2: shipped')
        self.project = run.build_project(Path(self.tmp.name) / 'project', self.repo, self.base)

    def tearDown(self):
        self.tmp.cleanup()

    def test_files_at_the_commit_without_the_future(self):
        self.assertTrue((self.project / 'Ticker.php').is_file())
        self.assertFalse((self.project / 'Shipped.php').exists())
        self.assertFalse((self.project / 'docs/specs/LD-2-SPEC.md').exists())

    def test_no_history_reaches_the_run(self):
        self.assertEqual(git(self.project, 'rev-list', '--count', 'HEAD'), '1')
        self.assertNotIn('shipped', git(self.project, 'log', '--all', '--format=%s'))

    def test_project_config_kept_and_harness_merged(self):
        agents = self.project / '.claude/agents'
        self.assertTrue((agents / 'local-helper.md').is_file())
        self.assertTrue((agents / 'executor.md').exists())
        self.assertEqual((self.project / 'CLAUDE.md').read_text(), 'project rules\n')
        self.assertEqual((self.project / 'AGENTS.md').resolve(), (run.HARNESS / 'AGENTS.md').resolve())
        self.assertTrue((self.project / '.claude/settings.local.json').is_file())

    def test_written_spec_is_the_new_one_for_the_ticket(self):
        before = run.specs_snapshot(self.project)
        (self.project / 'docs/specs/LD-3-SPEC.md').write_text('fresh\n')
        self.assertEqual(run.written_spec(self.project, before, 'LD-3'), 'fresh\n')
        self.assertIsNone(run.written_spec(self.project, run.specs_snapshot(self.project), 'LD-3'))


class EmptyProject(unittest.TestCase):
    def test_empty_project_still_builds(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = run.build_project(Path(tmp) / 'project')
            self.assertIn('Empty project fixture', (project / 'README.md').read_text())
            self.assertTrue((project / '.claude/skills').is_symlink())


class Arguments(unittest.TestCase):
    def test_repo_fixture_needs_repo_unless_judging(self):
        with tempfile.TemporaryDirectory() as tmp:
            here = Path(tmp)
            fixture = here / 'fixtures/LD-9'
            fixture.mkdir(parents=True)
            (fixture / 'intake.md').write_text('intake\n')
            (fixture / 'expectations.json').write_text(json.dumps({
                'ticket': 'LD-9', 'intake': 'intake.md', 'repo': {'at': 'abc123'},
                'expectations': [{'id': 'draft', 'why': 'w', 'regex': 'Draft'}]}))
            (here / 'spec.md').write_text('Status: Draft\n')
            saved, run.HERE = run.HERE, here
            try:
                with self.assertRaises(SystemExit) as stop:
                    run.main(['--fixture', 'LD-9'])
                self.assertEqual(stop.exception.code, 2)
                self.assertEqual(run.main(['--fixture', 'LD-9', '--spec', str(here / 'spec.md')]), 0)
            finally:
                run.HERE = saved


class NewFixture(unittest.TestCase):
    SPEC = """# LD-7 Spec

**Status:** Approved

### Requirement: REQ-001 Sort
Send `sort_mode=most_relevant` and keep `date_window` for Latest.
Score `invoice_reissued` as 9 in `InvoiceTotalsCalculator::total()`.
See `docs/specs/LD-6-SPEC.md`, `REQ-002`, `DEC-005` and the word `relevance`.
"""

    def test_reference_terms_keep_code_and_drop_ids_and_prose(self):
        self.assertEqual(run.reference_terms(self.SPEC),
                         ['sort_mode=most_relevant', 'date_window', 'invoice_reissued',
                          'InvoiceTotalsCalculator::total()'])

    def test_reference_terms_drop_trivia_seen_in_real_specs(self):
        # Shapes from a real deployed spec: a span longer than 60 characters
        # (it once broke backtick pairing), line references, commands, rule
        # files, design-node ids and slash commands.
        spec = ("Edit `Modules/Billing/app/Services/InvoiceTotalsCalculator.php:735-756` and "
                "`OrderRepository.php:237-238`, then `OrderRepository.php:79, 222-224`. Run "
                "`composer test -- --filter=Order`, `bin/worktree-setup.sh --build`, `./bin/schema-refresh.sh`. "
                "Per `.ai/rules/repositories.md:9`, Figma `2:3075`, `:180-186`, `/plan`, `Tests:`. "
                "Uses `sort_mode` and `sort_mode` and `order_lines`.")
        self.assertEqual(run.reference_terms(spec),
                         ['OrderRepository.php', 'sort_mode', 'InvoiceTotalsCalculator.php', 'order_lines'])

    def test_new_fixture_finds_base_and_writes_expectations(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / 'app'
            (repo / 'docs/specs').mkdir(parents=True)
            (repo / 'a.php').write_text('<?php\n')
            git(repo, 'init', '-q'); git(repo, 'add', '-A'); git(repo, 'commit', '-qm', 'before')
            before = git(repo, 'rev-parse', 'HEAD')
            (repo / 'docs/specs/LD-7-SPEC.md').write_text(self.SPEC)
            git(repo, 'add', '-A'); git(repo, 'commit', '-qm', 'LD-7 spec')
            intake = Path(tmp) / 'intake.md'
            intake.write_text('### LD-7 — Sort\n')
            saved, run.HERE = run.HERE, Path(tmp)
            try:
                out = run.new_fixture('LD-7', repo, 'docs/specs/LD-7-SPEC.md', intake=str(intake))
                fixture = json.loads((out / 'expectations.json').read_text())
                self.assertEqual(run.build_project(Path(tmp) / 'p', repo, fixture['repo']['at'])
                                 .joinpath('a.php').is_file(), True)
                self.assertEqual(git(repo, 'rev-parse', fixture['repo']['at']), before)
                terms = [e for e in fixture['expectations'] if e.get('reference_term')]
                self.assertEqual(len(terms), 4)
                # The deployed spec itself names every term; a draft one is still Draft.
                fresh = self.SPEC.replace('Approved', 'Draft')
                rows, failed = run.judge(fixture, fresh)
                self.assertEqual(failed, 0)
                with self.assertRaises(SystemExit):
                    run.new_fixture('LD-7', repo, 'docs/specs/LD-7-SPEC.md', intake=str(intake))
            finally:
                run.HERE = saved


class EvaluatorIntegrity(unittest.TestCase):
    """The eval's own defects, found on LD-441: a reference holding what review
    found after the build, an intake holding comments written after the spec,
    and prose fragments counted as terms."""

    def test_reference_is_the_first_approved_version_and_base_precedes_the_draft(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / 'docs/specs').mkdir(parents=True)
            (repo / 'a.php').write_text('<?php\n')
            git(repo, 'init', '-q'); git(repo, 'add', '-A'); git(repo, 'commit', '-qm', 'before')
            before = git(repo, 'rev-parse', 'HEAD')
            spec = repo / 'docs/specs/LD-8-SPEC.md'
            for status, body in (('Draft', 'first draft'), ('Approved', 'as approved'),
                                 ('Approved', 'review found `UnexpectedValueException`')):
                spec.write_text(f'Status: {status}\n\n{body}\n')
                git(repo, 'add', '-A'); git(repo, 'commit', '-qm', f'spec {status}')
            text, commit, base, as_of = run.reference_version(repo, 'docs/specs/LD-8-SPEC.md')
            self.assertIn('as approved', text)
            self.assertNotIn('UnexpectedValueException', text)
            self.assertEqual(git(repo, 'rev-parse', base), before)
            self.assertRegex(as_of, r'^\d{4}-\d\d-\d\d$')
            latest = run.reference_version(repo, 'docs/specs/LD-8-SPEC.md', 'latest')[0]
            self.assertIn('UnexpectedValueException', latest)

    def test_reference_follows_a_rename(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / 'docs').mkdir()
            (repo / 'docs/old.md').write_text('Status: Approved\n\nfirst\n')
            git(repo, 'init', '-q'); git(repo, 'add', '-A'); git(repo, 'commit', '-qm', 'add')
            git(repo, 'mv', 'docs/old.md', 'docs/LD-9-SPEC.md'); git(repo, 'commit', '-qm', 'rename')
            self.assertIn('first', run.reference_version(repo, 'docs/LD-9-SPEC.md')[0])

    def test_intake_dates_after_the_spec_are_flagged(self):
        intake = ('Comment by Ann (2026-09-14): use srch_sort.\n'
                  'Comment by Ann (2026-09-23): EVENT_TYPE_SCORES gives reactivated 9.\n'
                  'Resolved 2026-09-30.\n')
        self.assertEqual([n for n, _ in run.dates_after(intake, '2026-09-17')], [2, 3])
        self.assertEqual(run.dates_after(intake, '2026-10-01'), [])

    def test_intake_record_of_what_it_left_out_is_not_flagged(self):
        intake = ('- Snapshot: Jira at the end of 2026-09-06. I fetched the data on 2026-10-07.\n'
                  '- Left out because they were made after 2026-09-06: **2 items**.\n'
                  '  - LD-380: status QA -> Done (2026-09-16).\n'
                  '  - LD-386: description edit (2026-09-16).\n'
                  '- LD-386: I used the description as it stood before the 2026-09-16 edit.\n'
                  '- Comment by Ann (2026-09-20): drop the lock.\n')
        self.assertEqual([n for n, _ in run.dates_after(intake, '2026-09-06')], [6])

    def test_reference_terms_match_the_forms_a_spec_writes(self):
        cases = {
            'BaseAI::googlePlace()': 'calls `BaseAI::googlePlace` once',
            'Modules\\Advertisers\\Jobs\\FillAdvertiserDataFromAI': 'dispatch `FillAdvertiserDataFromAI`',
            'RequestAdvertiserModal.tsx': 'the `RequestAdvertiserModal` stays',
            'POST /v1/advertiser-request': '`POST /api/v1/advertiser-request` stays',
            'Modules/Core/app/Services/AI/BaseAI': 'through `BaseAI`',
        }
        for term, text in cases.items():
            self.assertRegex(text, run.term_pattern(term), term)
        self.assertNotRegex('the row exists today', run.term_pattern('exists()'))
        self.assertNotRegex('a services layer', run.term_pattern('Modules/Core/app/Services'))

    def test_prose_fragments_are_not_terms(self):
        spec = ('Throws `UnexpectedValueException` (REQ-004`). Both ` and `in:` and '
                '`for **newly generated** rows` and `) and continues to strip`, but '
                '`value_score => \'high\'` and `(score, time_posted, id)` stay.\n'
                '```php\n$x = 1;\n```\nUses `srch_sort`.\n')
        terms = run.reference_terms(spec)
        self.assertIn('UnexpectedValueException', terms)
        self.assertIn("value_score => 'high'", terms)
        self.assertIn('(score, time_posted, id)', terms)
        self.assertIn('srch_sort', terms)
        for junk in ('in:', 'for **newly generated** rows', ') and continues to strip'):
            self.assertNotIn(junk, terms)


class Paired(unittest.TestCase):
    """SAGE (arXiv 2609.36043): compare per item, not by the average."""

    def test_wins_regressions_and_must_losses(self):
        base = {'a': True, 'b': True, 'c': False, 'd': False, 'only-old': True}
        new = {'a': True, 'b': False, 'c': True, 'd': True, 'only-new': False}
        pair = run.paired(base, new, must_ids={'b'})
        self.assertEqual(pair['wins'], ['c', 'd'])
        self.assertEqual(pair['regressions'], ['b'])
        self.assertEqual(pair['unchanged'], 1)
        self.assertEqual(pair['not_compared'], ['only-new', 'only-old'])
        self.assertEqual(run.verdict(pair)[0], 'WORSE')  # a must loss outweighs any gain

    def test_verdicts(self):
        self.assertEqual(run.verdict(run.paired({'a': False, 'b': False}, {'a': True, 'b': False}))[0], 'BETTER')
        self.assertEqual(run.verdict(run.paired({'a': True}, {'a': True}))[0], 'SAME')
        # A higher average can still hide an equal trade: one gained, one lost.
        self.assertEqual(run.verdict(run.paired({'a': True, 'b': False}, {'a': False, 'b': True}))[0],
                         'NOT BETTER')

    def test_baseline_gate_through_the_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            fixture = tmp / 'fixtures' / 'LD-5'
            fixture.mkdir(parents=True)
            (fixture / 'expectations.json').write_text(json.dumps({'ticket': 'LD-5', 'expectations': [
                {'id': 'draft', 'regex': 'Draft', 'why': 'w'},
                {'id': 'term:alpha', 'regex': 'alpha', 'severity': 'should', 'reference_term': True, 'why': 'w'},
                {'id': 'term:beta', 'regex': 'beta', 'severity': 'should', 'reference_term': True, 'why': 'w'}]}))
            old, new = tmp / 'old.md', tmp / 'new.md'
            old.write_text('Draft alpha\n'); new.write_text('Draft beta\n')
            saved, run.HERE = run.HERE, tmp
            try:
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(run.main(['--fixture', 'LD-5', '--spec', str(old), '--output', str(tmp / 'o')]), 0)
                    results = tmp / 'o' / 'results.json'
                    self.assertEqual(json.loads(results.read_text())['results']['term:alpha'], True)
                    self.assertEqual(run.main(['--fixture', 'LD-5', '--spec', str(new), '--baseline', str(results)]), 1)
                    self.assertEqual(run.main(['--fixture', 'LD-5', '--spec', str(old), '--baseline', str(results)]), 0)
            finally:
                run.HERE = saved

if __name__ == '__main__':
    unittest.main(verbosity=1)
