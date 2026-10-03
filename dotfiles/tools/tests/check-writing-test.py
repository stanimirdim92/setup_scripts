#!/usr/bin/env python3
"""Fixture tests for dotfiles/tools/checks/check-writing.py.

The splitter is the risk. Joining list items without a full stop into one
"sentence" once reported a spec at 28% long sentences when it held 6%; a check
that cries wolf gets switched off.
"""
import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('cw', Path(__file__).resolve().parent.parent / 'checks' / 'check-writing.py')
cw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cw)

LONG = ' '.join(['word'] * 30) + '.'
SHORT = 'This sentence is short enough to pass.'


class Units(unittest.TestCase):
    def test_list_items_without_full_stops_stay_separate(self):
        text = '- first item with several words here\n- second item with several words here\n'
        self.assertEqual([w for _, w, _ in cw.sentences(text)], [6, 6])

    def test_wrapped_lines_join_their_paragraph_and_item(self):
        text = 'One sentence that is\nwrapped over two lines.\n\n- An item that\n  wraps too.\n'
        self.assertEqual([s for _, _, s in cw.sentences(text)],
                         ['One sentence that is wrapped over two lines.', 'An item that wraps too.'])

    def test_code_tables_headings_front_matter_comments_skipped(self):
        text = ('---\ndescription: ' + LONG + '\n---\n# ' + LONG + '\n\n```\n' + LONG + '\n```\n\n'
                '| ' + LONG + ' |\n\n<!-- ' + LONG + ' -->\n' + SHORT + '\n')
        self.assertEqual([s for _, _, s in cw.sentences(text)], [SHORT])

    def test_symbols_are_not_words_and_short_labels_are_not_counted(self):
        self.assertEqual(cw.sentences('A → B — C · .'), [])
        self.assertEqual(cw.sentences('A → B — C · D.')[0][1], 4)
        self.assertEqual(cw.sentences('- Done\n- Pending\n'), [])

    def test_line_numbers_point_at_the_unit_start(self):
        text = 'Intro sentence for the file here.\n\n' + LONG + '\n'
        _, long = cw.measure(text)
        self.assertEqual(long[0][0], 3)


class Verdict(unittest.TestCase):
    def run_on(self, text, *extra):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'doc.md'
            p.write_text(text)
            return cw.main([str(p), *extra])

    def test_share_at_the_limit_passes_over_it_fails(self):
        self.assertEqual(self.run_on(' '.join([LONG] + [SHORT] * 4)), 0)  # 20%
        self.assertEqual(self.run_on(' '.join([LONG] * 2 + [SHORT] * 4)), 1)  # 33%

    def test_limits_are_flags(self):
        self.assertEqual(self.run_on(' '.join([LONG] * 2 + [SHORT] * 4), '--max-share', '0.4'), 0)
        self.assertEqual(self.run_on(' '.join([LONG] + [SHORT] * 4), '--max-words', '40'), 0)

    def test_default_scope_starts_at_first_checked_adr(self):
        numbers = [int(p.name[:4]) for p in cw.default_files()]
        self.assertTrue(numbers)
        self.assertEqual(min(numbers), cw.FIRST_CHECKED_ADR)


if __name__ == '__main__':
    unittest.main(verbosity=1)
