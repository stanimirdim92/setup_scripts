#!/usr/bin/env python3
"""Fixture tests for the judging half of run.py.

The judging half is deterministic and runs in CI. The producing half drives the
real model and does not.

These exist because the eval's whole value is discrimination: it must pass the
spec a human validated and fail the one that missed things. An expectation that
passes everything is worse than no expectation, because it reads like coverage.
"""
import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('se', Path(__file__).with_name('run.py'))
se = importlib.util.module_from_spec(spec)
spec.loader.exec_module(se)


class Window(unittest.TestCase):
    def test_terms_in_one_line(self):
        self.assertTrue(se.window('This contradicts LD-238, which promises an email.', ['LD-238', 'email'], 4))

    def test_terms_across_the_window(self):
        text = 'Notification behavior is unsettled.\nLD-238 says one thing.\nThe story says no email is sent.'
        self.assertTrue(se.window(text, ['LD-238', 'email'], 3))

    def test_terms_further_apart_than_the_window(self):
        text = 'LD-238 says one thing.\n' + 'filler\n' * 20 + 'no email is sent'
        self.assertFalse(se.window(text, ['LD-238', 'email'], 4))

    def test_presence_alone_is_not_co_occurrence(self):
        # the failure mode the predicate exists to catch: a spec that mentions
        # email somewhere without noticing the tickets disagree about it
        text = 'The success state sends no email.\n' + 'filler\n' * 30 + 'LD-238 is a linked spike.'
        self.assertFalse(se.window(text, ['LD-238', 'email'], 4))

    def test_case_insensitive(self):
        self.assertTrue(se.window('ld-238 promises an EMAIL', ['LD-238', 'email'], 2))

    def test_missing_term_fails(self):
        self.assertFalse(se.window('LD-238 is linked.', ['LD-238', 'email'], 4))


class Predicates(unittest.TestCase):
    def test_regex_matches_multiline_and_case_insensitively(self):
        met, _ = se.evaluate({'id': 'x', 'why': '', 'regex': r'^Status:\s*Draft\s*$'}, 'Ticket: A\nstatus: draft\n')
        self.assertTrue(met)

    def test_absent_regex_passes_when_missing(self):
        met, detail = se.evaluate({'id': 'x', 'why': '', 'absent_regex': r'^### DEC-\d+'}, '## Objective\n')
        self.assertTrue(met)
        self.assertNotIn('found', detail)

    def test_absent_regex_fails_and_quotes_the_hit(self):
        met, detail = se.evaluate(
            {'id': 'x', 'why': '', 'absent_regex': r'^### DEC-\d+[^\n]*(provider|Outscraper)'},
            '### DEC-001 — Search provider is Google Places, not Outscraper\n')
        self.assertFalse(met)
        self.assertIn('DEC-001', detail)

    def test_semantic_is_never_auto_met(self):
        met, detail = se.evaluate({'id': 'x', 'why': '', 'kind': 'semantic'}, 'anything at all')
        self.assertIsNone(met)
        self.assertIn('human', detail)

    def test_predicateless_expectation_is_an_error(self):
        with self.assertRaises(ValueError):
            se.evaluate({'id': 'typo', 'why': ''}, 'text')


class Judge(unittest.TestCase):
    FIXTURE = {'expectations': [
        {'id': 'must-find', 'why': '', 'near': ['LD-238', 'email'], 'within_lines': 4},
        {'id': 'must-not-decide', 'why': '', 'absent_regex': r'^### DEC-\d+[^\n]*provider'},
        {'id': 'nice-to-have', 'why': '', 'regex': 'What is done well', 'severity': 'should'},
        {'id': 'read-it', 'why': '', 'kind': 'semantic'},
    ]}

    def test_good_spec_passes(self):
        rows, failed = se.judge(self.FIXTURE, 'This contradicts LD-238, which promises an email.\nWhat is done well\n')
        self.assertEqual(failed, 0)
        self.assertEqual(len(rows), 4)

    def test_missing_finding_fails(self):
        _, failed = se.judge(self.FIXTURE, 'A spec that never noticed.\n')
        self.assertEqual(failed, 1)

    def test_self_decided_question_fails(self):
        _, failed = se.judge(self.FIXTURE, 'LD-238 promises an email.\n### DEC-001 — provider is Google Places\n')
        self.assertEqual(failed, 1)

    def test_should_severity_misses_without_failing(self):
        rows, failed = se.judge(self.FIXTURE, 'LD-238 promises an email.\n')
        self.assertEqual(failed, 0)
        self.assertFalse(dict((r[0]['id'], r[1]) for r in rows)['nice-to-have'])

    def test_semantic_never_counts_as_failure(self):
        rows, failed = se.judge({'expectations': [{'id': 's', 'why': '', 'kind': 'semantic'}]}, '')
        self.assertEqual(failed, 0)
        self.assertIsNone(rows[0][1])


class ExampleFixture(unittest.TestCase):
    """The committed example must stay loadable and every predicate valid."""

    def test_example_expectations_are_well_formed(self):
        import json
        fixture = json.loads((Path(__file__).parent / 'fixtures/example/expectations.json').read_text())
        self.assertTrue(fixture['expectations'])
        for expectation in fixture['expectations']:
            self.assertTrue(expectation.get('id'), expectation)
            self.assertTrue(expectation.get('why'), f"{expectation['id']} has no rationale")
            se.evaluate(expectation, 'probe text')   # raises if it carries no predicate


if __name__ == '__main__':
    unittest.main(verbosity=1)
