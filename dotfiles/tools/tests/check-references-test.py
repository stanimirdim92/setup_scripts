#!/usr/bin/env python3
"""Fixture tests for dotfiles/tools/check-references.py.

Deny cases prove it catches a moved reference. Allow cases matter more: this
check scans every harness markdown file, so one false positive on a
`[TICKET]` placeholder, a URL, or prose naming a file makes it noise and it
gets switched off.
"""
import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('cr', Path(__file__).resolve().parent.parent / 'checks' / 'check-references.py')
cr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cr)


class Targets(unittest.TestCase):
    def found(self, text):
        return sorted(cr.candidates(text))

    def test_markdown_link_and_backtick_forms(self):
        self.assertEqual(
            self.found('See [gates](../references/plan-quality-gates.md) and `../../references/x.md`.'),
            ['../../references/x.md', '../references/plan-quality-gates.md'])

    def test_anchor_is_stripped(self):
        self.assertEqual(self.found('`../references/documentation-practices.md#project-documentation`'),
                         ['../references/documentation-practices.md'])

    def test_templates_prefix_counts(self):
        self.assertEqual(self.found('`templates/task.md`'), ['templates/task.md'])

    def test_urls_ignored(self):
        self.assertEqual(self.found('[docs](https://code.claude.com/docs/en/hooks)'), [])

    def test_ticket_placeholder_ignored(self):
        self.assertEqual(self.found('`docs/specs/[TICKET]-SPEC.md` and `[TICKET]-SPEC-<module-id>.md`'), [])

    def test_bare_filename_is_prose_not_a_link(self):
        self.assertEqual(self.found('Keep `CLAUDE.md` under 200 lines; see `settings.json`.'), [])

    def test_absolute_and_variable_paths_ignored(self):
        self.assertEqual(self.found('`/etc/x.md` and `$HOME/.claude/y.md` and `{dir}/z.md`'), [])


class TopLevelDocs(unittest.TestCase):
    def found(self, text):
        return sorted(cr.candidates(text, top_level=True))

    def test_repo_relative_link_counts(self):
        self.assertEqual(self.found('| [dotfiles/claude/AGENTS.md](dotfiles/claude/AGENTS.md) |'),
                         ['dotfiles/claude/AGENTS.md'])

    def test_backticked_paths_are_prose_here(self):
        # README names gitignored paths in backticks on purpose.
        self.assertEqual(self.found('- `dotfiles/claude/skills/synced/` (gitignored)'), [])

    def test_urls_ignored(self):
        self.assertEqual(self.found('[ADR](https://example.com/adr.md)'), [])

    def test_deleted_target_is_caught(self):
        with tempfile.TemporaryDirectory() as tmp:
            doc = Path(tmp) / 'ARCHITECTURE.md'
            (Path(tmp) / 'dotfiles').mkdir()
            (Path(tmp) / 'dotfiles' / 'AGENTS.md').write_text('rules\n')
            doc.write_text('[a](dotfiles/AGENTS.md) [b](dotfiles/CLAUDE.md)\n')
            self.assertEqual(cr.broken(doc, doc.read_text(), top_level=True), ['dotfiles/CLAUDE.md'])

    def test_top_level_docs_exclude_adrs(self):
        self.assertFalse(any('adr' in p.parts for p in cr.top_level_docs()))


class Resolution(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / 'commands').mkdir()
        (root / 'references' / 'templates').mkdir(parents=True)
        (root / 'references' / 'plan-quality-gates.md').write_text('gates\n')
        (root / 'references' / 'templates' / 'task.md').write_text('task\n')
        self.cmd = root / 'commands' / 'plan.md'

    def tearDown(self):
        self.tmp.cleanup()

    def test_resolving_reference_passes(self):
        self.cmd.write_text('Follow `../references/plan-quality-gates.md`.\n')
        self.assertEqual(cr.broken(self.cmd, self.cmd.read_text()), [])

    def test_nested_template_resolves(self):
        self.cmd.write_text('Use [task](../references/templates/task.md).\n')
        self.assertEqual(cr.broken(self.cmd, self.cmd.read_text()), [])

    def test_moved_reference_is_caught(self):
        self.cmd.write_text('Follow `../references/plan-quality-gates.md` and `../references/gone.md`.\n')
        self.assertEqual(cr.broken(self.cmd, self.cmd.read_text()), ['../references/gone.md'])

    def test_wrong_depth_is_caught(self):
        # the ../../ form is right from skills/<name>/SKILL.md, wrong from commands/
        self.cmd.write_text('`../../references/plan-quality-gates.md`\n')
        self.assertEqual(cr.broken(self.cmd, self.cmd.read_text()), ['../../references/plan-quality-gates.md'])


class Places(unittest.TestCase):
    """An anchor or a section that no longer exists in a file that does."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / 'commands').mkdir()
        (root / 'references').mkdir()
        (root / 'references' / 'gates.md').write_text(
            '# Gates\n\n## 3. Id spaces\n\n## Gate handoffs\n\n```\n## Not a heading\n```\n'
            '## Gate handoffs\n')
        self.cmd = root / 'commands' / 'plan.md'

    def tearDown(self):
        self.tmp.cleanup()

    def check(self, text):
        self.cmd.write_text(text)
        return cr.broken(self.cmd, text)

    def test_slugs_follow_github(self):
        self.assertEqual(cr.slug('3. Id spaces'), '3-id-spaces')
        self.assertEqual(cr.slug('`/review` → disposition table'), 'review--disposition-table')
        heads = cr.anchors(Path(self.tmp.name) / 'references' / 'gates.md')
        self.assertIn('gate-handoffs-1', heads)  # the repeated heading
        self.assertNotIn('not-a-heading', heads)  # inside a code fence

    def test_anchor(self):
        self.assertEqual(self.check('[g](../references/gates.md#gate-handoffs)\n'), [])
        self.assertEqual(self.check('`../references/gates.md#3-id-spaces`\n'), [])
        self.assertEqual(self.check('[g](../references/gates.md#handoffs)\n'),
                         ['../references/gates.md#handoffs (no such heading)'])

    def test_named_section(self):
        self.assertEqual(self.check('See `../references/gates.md` §Gate handoffs for it.\n'), [])
        self.assertEqual(self.check('See `../references/gates.md` §Stage handoffs for it.\n'),
                         ['../references/gates.md §Stage handoffs for it (no such section)'])

    def test_numbered_section(self):
        self.assertEqual(self.check('Per `../references/gates.md` §3, ids are stable.\n'), [])
        self.assertEqual(self.check('Per `../references/gates.md` §4–5.\n'),
                         ['../references/gates.md §4 (no such section)'])

    def test_missing_file_reported_once(self):
        self.assertEqual(self.check('`../references/gone.md` §Anything\n'), ['../references/gone.md'])

    def test_named_harness_file(self):
        # Resolved against the real harness: persona and skill names.
        self.assertEqual(self.check('(`test-engineer` §6) and `code-review-and-quality` §Step 2\n'), [])
        self.assertEqual(self.check('`test-engineer` §42\n'), ['agents/test-engineer.md §42 (no such section)'])
        self.assertEqual(self.check('`not-a-skill` §Anything\n'), [])

if __name__ == '__main__':
    unittest.main(verbosity=1)
