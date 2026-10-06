#!/usr/bin/env python3
"""Fixture tests for dotfiles/claude/skills/planning-and-task-breakdown/scripts/check-plan.py.

The clean plan must pass with no warning. Each other case breaks one link
between spec, plan index and todo packets: a dropped requirement, an invented
one, a dangling dependency, a missing packet field.
"""
import importlib.util
import unittest
from pathlib import Path

SCRIPT = (Path(__file__).resolve().parents[2] / 'claude' / 'skills' / 'planning-and-task-breakdown'
          / 'scripts' / 'check-plan.py')
spec = importlib.util.spec_from_file_location('cp', SCRIPT)
cp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cp)

SPEC = """Status: Approved

### Requirement: REQ-001 — Reminders are sent
Source: AB-12

### Requirement: REQ-002 — Reminders are logged
Source: AB-12

### Requirement: REQ-003 — Withdrawn: SMS
Withdrawn on review.
"""

PLAN = """# Implementation Plan: Invoice reminders

Status: Draft
Spec: docs/specs/AB-12-SPEC.md
Spec revision: git-commit:abc123:docs/specs/AB-12-SPEC.md
Not yet planned: None

## Task Index

- [ ] T001 (S, ws-main, deps: —) [REQ-001]: overdue invoices get one reminder

### CP-001 — Checkpoint: reminder contract stable

- [x] T002 (M, ws-main, deps: T001, CP-001) [REQ-002, TD-001]: each reminder is logged
- [~] ~~T003~~ superseded by T002
"""

PACKET = """## {tid}: {title}

**Status:** Pending

**Requirements:** {ids}

**Acceptance criteria:**
- [ ] it works

**Verification:**
- [ ] Tests pass: composer test

**Files/areas likely touched:**
- `app/Reminders.php`
"""

TODO = (PACKET.format(tid='T001', title='Send', ids='REQ-001')
        + PACKET.format(tid='T002', title='Log', ids='REQ-002, TD-001'))


def run(plan=PLAN, spec=SPEC, todo=TODO):
    fail, warn = cp.check(plan, spec, [('todo', todo)] if todo is not None else [])
    return [m for _, _, m in fail], [m for _, _, m in warn]


class CheckPlan(unittest.TestCase):
    def test_clean_plan_passes_without_warnings(self):
        self.assertEqual(run(), ([], []))

    def test_header_fields(self):
        fail, _ = run(PLAN.replace('Spec revision: git-commit:abc123:docs/specs/AB-12-SPEC.md\n', ''))
        self.assertIn('no `Spec revision:` line in the header', fail)

    def test_index_line_form_ids_and_dependencies(self):
        fail, _ = run(PLAN.replace('(S, ws-main, deps: —) ', ''))
        self.assertTrue(any('T001: index line must read' in m for m in fail))
        fail, _ = run(PLAN.replace('[REQ-001]: overdue', '[]: overdue'))
        self.assertIn('T001: names no REQ-### or TD-### id', fail)
        fail, _ = run(PLAN.replace('deps: T001, CP-001', 'deps: T009'))
        self.assertIn('T002 depends on T009, which the plan does not define', fail)

    def test_spec_coverage_both_ways(self):
        fail, _ = run(PLAN.replace('[REQ-002, TD-001]', '[TD-001]'))
        self.assertIn('REQ-002 has no task', fail)
        fail, _ = run(PLAN.replace('[REQ-001]', '[REQ-001, REQ-009]'))
        self.assertIn('T001 names REQ-009, which the spec does not have', fail)
        # REQ-003 is withdrawn: no task needed, as the clean case already shows.

    def test_deferred_modules_turn_a_gap_into_a_warning(self):
        plan = PLAN.replace('Not yet planned: None', 'Not yet planned: reporting').replace('[REQ-002, TD-001]', '[TD-001]')
        fail, warn = run(plan)
        self.assertEqual(fail, [])
        self.assertTrue(any('REQ-002 has no task' in m for m in warn))

    def test_packets_match_the_index(self):
        fail, _ = run(todo=PACKET.format(tid='T001', title='Send', ids='REQ-001'))
        self.assertIn('T002 has no packet in the todo file', fail)
        fail, _ = run(todo=TODO + PACKET.format(tid='T004', title='Extra', ids='REQ-001'))
        self.assertIn('T004 has a packet but no Task Index line', fail)

    def test_packet_fields(self):
        fail, _ = run(todo=TODO.replace('**Verification:**', '**Checks:**', 1))
        self.assertIn('T001: no **Verification:** line', fail)
        fail, _ = run(todo=TODO.replace('**Status:** Pending', '**Status:** Started', 1))
        self.assertIn("T001: Status is 'Started', not Pending or Done", fail)
        _, warn = run(todo=TODO.replace('**Files/areas likely touched:**', '**Files:**', 1))
        self.assertTrue(any('plan coverage cannot score it' in m for m in warn))
        _, warn = run(todo=TODO.replace('**Requirements:** REQ-001', '**Requirements:** REQ-002', 1))
        self.assertTrue(any('T001: packet names REQ-002' in m for m in warn))

    def test_without_spec_or_todo_only_the_plan_is_checked(self):
        fail, warn = cp.check(PLAN, None, [])
        self.assertEqual((fail, warn), ([], []))


if __name__ == '__main__':
    unittest.main(verbosity=1)
