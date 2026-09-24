#!/usr/bin/env python3
"""Fixture tests for tools/check-references.py.

Deny cases prove it catches a moved reference. Allow cases matter more: this
check scans every harness markdown file, so one false positive on a
`[TICKET]` placeholder, a URL, or prose naming a file makes it noise and it
gets switched off.
"""
import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('cr', Path(__file__).with_name('check-references.py'))
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


if __name__ == '__main__':
    unittest.main(verbosity=1)
