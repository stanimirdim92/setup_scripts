#!/usr/bin/env python3
"""Project layout for spec-eval runs, with `claude` never invoked. Runs in CI."""
import importlib.util
import json
import subprocess
import tempfile
import unittest
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
Send `srch_sort=most_relevant` and keep `srch_interval` for Latest.
Score `paid_ads_reactivated` as 9 in `PaidAdsTickerEventGenerator::score()`.
See `docs/specs/LD-6-SPEC.md`, `REQ-002`, `DEC-005` and the word `relevance`.
"""

    def test_reference_terms_keep_code_and_drop_ids_and_prose(self):
        self.assertEqual(run.reference_terms(self.SPEC),
                         ['srch_sort=most_relevant', 'srch_interval', 'paid_ads_reactivated',
                          'PaidAdsTickerEventGenerator::score()'])

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


if __name__ == '__main__':
    unittest.main(verbosity=1)
