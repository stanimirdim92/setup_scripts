#!/usr/bin/env python3
"""Fixture tests for recall.py. Deterministic; runs in CI."""
import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('pr', Path(__file__).with_name('recall.py'))
pr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pr)

PLAN = """# Tasks

## T001: Totals on invoices

**Requirements:** REQ-001

**Files/areas likely touched:**
- `app/Billing/InvoiceTotals.php`
- `app/Http/Resources/InvoiceResource.php`
- `routes/api.php` — unchanged, route already exists
- `tests/Feature/Billing/`

**Change-surface search:** `rg -n "InvoiceTotals" app/ routes/ tests/`

**Estimated scope:** S

## T002: Export

**Files/areas likely touched:**
- `app/Exports/*.php`

Other prose mentioning `app/Unrelated.php` is not a planned location.
"""


class Parsing(unittest.TestCase):
    def test_reads_only_the_touched_field(self):
        entries = pr.planned_entries(PLAN)
        self.assertEqual([e for e, _ in entries], [
            'app/Billing/InvoiceTotals.php', 'app/Http/Resources/InvoiceResource.php',
            'routes/api.php', 'tests/Feature/Billing/', 'app/Exports/*.php'])

    def test_unchanged_marker(self):
        self.assertIn(('routes/api.php', True), pr.planned_entries(PLAN))
        self.assertIn(('app/Billing/InvoiceTotals.php', False), pr.planned_entries(PLAN))

    def test_field_ends_at_next_field(self):
        self.assertNotIn('rg -n "InvoiceTotals" app/ routes/ tests/', [e for e, _ in pr.planned_entries(PLAN)])


class Scoring(unittest.TestCase):
    def setUp(self):
        self.entries = pr.planned_entries(PLAN)

    def test_missed_cross_module_file_lowers_recall(self):
        # The LoLBench failure: the change reaches a provider binding nobody planned.
        changed = {'app/Billing/InvoiceTotals.php': 'M', 'app/Http/Resources/InvoiceResource.php': 'M',
                   'app/Providers/BillingServiceProvider.php': 'M', 'tests/Feature/Billing/TotalsTest.php': 'A'}
        result = pr.score(self.entries, changed)
        self.assertEqual(result['missed'], ['app/Providers/BillingServiceProvider.php'])
        self.assertEqual(result['recall'], 0.75)
        self.assertEqual(result['recall_existing'], 0.667)   # 2 of 3 pre-existing files

    def test_directory_and_glob_entries_cover_files(self):
        changed = {'tests/Feature/Billing/TotalsTest.php': 'A', 'app/Exports/InvoiceExport.php': 'M'}
        self.assertEqual(pr.score(self.entries, changed)['recall'], 1.0)

    def test_unchanged_entry_is_not_expected_in_the_diff(self):
        changed = {'app/Billing/InvoiceTotals.php': 'M'}
        self.assertNotIn('routes/api.php', pr.score(self.entries, changed)['planned_but_untouched'])

    def test_precision_counts_planned_edits_that_shipped(self):
        changed = {'app/Billing/InvoiceTotals.php': 'M'}
        result = pr.score(self.entries, changed)
        self.assertEqual(result['precision'], 0.25)          # 1 of 4 expected entries touched

    def test_excludes(self):
        changed = {'app/Billing/InvoiceTotals.php': 'M', 'docs/billing.md': 'M'}
        self.assertEqual(pr.score(self.entries, changed, ['docs/*'])['recall'], 1.0)

    def test_default_excludes_drop_pipeline_and_agent_config(self):
        changed = {'app/Billing/InvoiceTotals.php': 'M', 'docs/specs/LD-1-spec.md': 'A',
                   'docs/tasks/LD-1-todo.md': 'M', '.claude/settings.json': 'M', 'CLAUDE.md': 'M',
                   '.ai/rules/php.md': 'M', 'Modules/Socials/CLAUDE.md': 'M'}
        result = pr.score(self.entries, changed, pr.DEFAULT_EXCLUDES)
        self.assertEqual(result['changed_files'], 1)
        self.assertEqual(result['excluded_files'], 6)
        self.assertEqual(result['recall'], 1.0)

    def test_excluded_planned_entry_is_not_an_untouched_edit(self):
        entries = [('app/A.php', False), ('docs/tasks/LD-1-plan.md', False)]
        result = pr.score(entries, {'app/A.php': 'M'}, pr.DEFAULT_EXCLUDES)
        self.assertEqual(result['planned_but_untouched'], [])
        self.assertEqual(result['precision'], 1.0)

    def test_empty_diff_has_no_ratio(self):
        self.assertIsNone(pr.score(self.entries, {})['recall'])


class EndToEnd(unittest.TestCase):
    def test_git_range_and_rename(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            git = lambda *a: subprocess.run(['git', '-C', tmp, '-c', 'user.email=t@t', '-c', 'user.name=t', *a],
                                            check=True, capture_output=True, text=True).stdout.strip()
            git('init', '-q')
            (repo / 'app').mkdir()
            (repo / 'app/Old.php').write_text('<?php\nclass Old { /* long enough to track a rename */ }\n' * 5)
            (repo / 'app/Keep.php').write_text('<?php\n')
            git('add', '-A'); git('commit', '-qm', 'base')
            base = git('rev-parse', 'HEAD')
            git('mv', 'app/Old.php', 'app/New.php')
            (repo / 'app/Keep.php').write_text('<?php\n// changed\n')
            git('commit', '-qam', 'change')
            changed = pr.changed_files(repo, f'{base}..HEAD')
            self.assertEqual(changed, {'app/Old.php': 'M', 'app/Keep.php': 'M'})
            (repo / 'plan.md').write_text('**Files/areas likely touched:**\n- `app/Old.php`\n')
            self.assertEqual(pr.main(['--repo', tmp, '--plan', 'plan.md', '--range', f'{base}..HEAD',
                                      '--min-recall', '0.9']), 1)
            self.assertEqual(pr.main(['--repo', tmp, '--plan', 'plan.md', '--range', f'{base}..HEAD',
                                      '--min-recall', '0.5']), 0)

    def test_ticket_scopes_to_its_own_commits(self):
        # A range carrying two tickets: the other ticket's files are not misses.
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            git = lambda *a: subprocess.run(['git', '-C', tmp, '-c', 'user.email=t@t', '-c', 'user.name=t', *a],
                                            check=True, capture_output=True, text=True).stdout.strip()
            git('init', '-q')
            (repo / 'a.php').write_text('a\n'); (repo / 'b.php').write_text('b\n')
            git('add', '-A'); git('commit', '-qm', 'base')
            base = git('rev-parse', 'HEAD')
            (repo / 'a.php').write_text('a2\n'); git('commit', '-qam', 'LD-441: change a')
            (repo / 'b.php').write_text('b2\n'); git('commit', '-qam', 'LD-442: change b')
            (repo / 'tmp.php').write_text('t\n'); git('add', '-A'); git('commit', '-qm', 'ld-441 scratch')
            git('rm', '-q', 'tmp.php'); git('commit', '-qm', 'LD-441 drop scratch')
            self.assertEqual(pr.changed_files(repo, f'{base}..HEAD', 'LD-441'), {'a.php': 'M'})
            origins = {}
            pr.changed_files(repo, f'{base}..HEAD', 'LD-441', origins)
            self.assertTrue(origins['a.php'].endswith(' LD-441: change a'))
            self.assertEqual(set(pr.changed_files(repo, f'{base}..HEAD')), {'a.php', 'b.php'})


if __name__ == '__main__':
    unittest.main(verbosity=1)
