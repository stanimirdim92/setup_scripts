#!/usr/bin/env python3
"""Fixture tests for dotfiles/claude/skills/spec-driven-development/scripts/check-spec.py.

The clean spec must pass with no warning: /spec runs this on every spec, and a
check that flags a correct spec teaches the model to ignore it. Each other
case breaks exactly one rule.
"""
import importlib.util
import unittest
from pathlib import Path

SCRIPT = (Path(__file__).resolve().parents[2] / 'claude' / 'skills' / 'spec-driven-development'
          / 'scripts' / 'check-spec.py')
spec = importlib.util.spec_from_file_location('cs', SCRIPT)
cs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cs)

CLEAN = """# Spec: Invoice reminders

Status: Draft
Ticket: AB-12
Change kind: New

## Requirements

### Requirement: REQ-001 — Overdue invoices get one reminder
Source: AB-12 AC-1

- When an invoice is 7 days overdue, the system MUST send one reminder to the billing contact.
- If the billing contact has no email address, then the system MUST NOT send a reminder.
- The system SHOULD send reminders between 08:00 and 18:00, unless the customer opted into any-time delivery.

#### Scenario: Seven days overdue
- GIVEN an invoice due 7 days ago
- WHEN the daily job runs
- THEN one reminder is sent

### Requirement: REQ-002 — Withdrawn: SMS reminders
Withdrawn on review; no SMS provider.

## Open Questions

None.
"""


def run(text, rfc=True):
    fail, warn = cs.check(text, rfc)
    return [m for _, m in fail], [m for _, m in warn]


class CheckSpec(unittest.TestCase):
    def test_clean_spec_passes_without_warnings(self):
        self.assertEqual(run(CLEAN), ([], []))

    def test_header_fields_and_status(self):
        fail, _ = run(CLEAN.replace('Change kind: New\n', '').replace('Status: Draft', 'Status: Done'))
        self.assertIn('no `Change kind:` line in the header', fail)
        self.assertTrue(any("Status 'Done'" in m for m in fail))

    def test_heading_form_and_duplicate_ids(self):
        fail, _ = run(CLEAN.replace('### Requirement: REQ-001 — Overdue', '### Requirement: REQ-001 - Overdue'))
        self.assertTrue(any('heading must read' in m for m in fail))
        fail, _ = run(CLEAN.replace('REQ-002 — Withdrawn', 'REQ-001 — Withdrawn'))
        self.assertTrue(any('REQ-001 repeats' in m for m in fail))

    def test_source_line_required(self):
        fail, _ = run(CLEAN.replace('Source: AB-12 AC-1\n', ''))
        self.assertIn('REQ-001: the line under the heading must be `Source: …`', fail)

    def test_scenario_required_and_complete(self):
        fail, _ = run(CLEAN.replace('- THEN one reminder is sent\n', ''))
        self.assertTrue(any('scenario lacks THEN' in m for m in fail))
        no_scenario = CLEAN.split('#### Scenario')[0] + '### Requirement: REQ-002 — Withdrawn: SMS\nWithdrawn.\n'
        fail, _ = run(no_scenario)
        self.assertIn('REQ-001: no `#### Scenario:`', fail)

    def test_rfc_keyword_required_unless_disabled(self):
        lower = CLEAN.replace('MUST NOT', 'must not').replace('MUST', 'must').replace('SHOULD', 'should')
        fail, _ = run(lower)
        self.assertTrue(any('no uppercase MUST' in m for m in fail))
        self.assertEqual(run(lower, rfc=False)[0], [])

    def test_open_question_blocks_approval_only(self):
        with_question = CLEAN.replace('None.\n', '```\nOPEN QUESTION 1: Which channel?\n```\n')
        self.assertEqual(run(with_question)[0], [])
        fail, _ = run(with_question.replace('Status: Draft', 'Status: Approved'))
        self.assertIn('the spec is Approved but still holds an OPEN QUESTION', fail)

    def test_warnings_for_ears_slips(self):
        _, warn = run(CLEAN.replace(
            'When an invoice is 7 days overdue, the system MUST send one reminder to the billing contact.',
            'The system MUST send one reminder when an invoice is 7 days overdue.'))
        self.assertTrue(any('condition after the keyword' in m for m in warn))
        _, warn = run(CLEAN.replace(', then the system MUST NOT', ', the system MUST NOT'))
        self.assertTrue(any('`If <condition>, then' in m for m in warn))
        _, warn = run(CLEAN.replace(', unless the customer opted into any-time delivery', ''))
        self.assertTrue(any('SHOULD names the exception' in m for m in warn))

    def test_cli_exit_codes(self):
        import tempfile, io
        from contextlib import redirect_stdout, redirect_stderr
        with tempfile.TemporaryDirectory() as tmp:
            good, bad = Path(tmp) / 'good.md', Path(tmp) / 'bad.md'
            good.write_text(CLEAN)
            bad.write_text(CLEAN.replace('Source: AB-12 AC-1\n', ''))
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(cs.main([str(good)]), 0)
                self.assertEqual(cs.main([str(bad)]), 1)
                self.assertEqual(cs.main([str(Path(tmp) / 'missing.md')]), 2)


if __name__ == '__main__':
    unittest.main(verbosity=1)
