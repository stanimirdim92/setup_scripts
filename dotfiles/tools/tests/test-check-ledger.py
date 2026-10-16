#!/usr/bin/env python3
"""Fixture tests for dotfiles/claude/skills/spec-driven-development/scripts/check-ledger.py.

The clean ticket must pass with no warning. Each other case reproduces one way
LD-365's records drifted after planning: decisions added to the spec with no
replan, a deferred gap with no tracked home, a todo that never caught up, and
a decision that broke an older Never rule without saying so.
"""
import importlib.util
import unittest
from pathlib import Path

SCRIPT = (Path(__file__).resolve().parents[2] / 'claude' / 'skills' / 'spec-driven-development'
          / 'scripts' / 'check-ledger.py')
spec = importlib.util.spec_from_file_location('cl', SCRIPT)
cl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cl)

SPEC = """Status: Approved

### Requirement: REQ-001 — Months are stored
Source: AB-12

## Material Decisions

### DEC-001 — Keep the old table
- Decision: this ticket does not change `old_snapshots` or its writer.

## Boundaries
- Never: delete `legacy_total` or other old metric columns.
"""

PLAN = """# Implementation Plan: Months

Status: Approved
Spec: docs/specs/AB-12-SPEC.md
Spec revision: git-commit:abc123:docs/specs/AB-12-SPEC.md

## Task Index

- [x] T001 (S, ws-main, deps: —) [REQ-001]: months are stored
- [~] ~~T002~~ superseded by T001
"""

TODO = """## T001: Months are stored

**Status:** Done

**Acceptance criteria:**
- [x] a month row exists

## T002: Old store

**Status:** Pending

**Acceptance criteria:**
- [ ] rows are insert-only
"""

OPEN = """# Open items: AB-12

| Id | Item | Kind | Owner | Disposition |
|---|---|---|---|---|
| OPEN-001 | Timezone column | deferred gap | owner | Accepted — months are UTC |
"""


def run(spec=SPEC, pinned=SPEC, plan=PLAN, todo=TODO, open_items=OPEN, commits=(), ship=False):
    return cl.check(spec, pinned, plan, todo, open_items, list(commits), ship)


def messages(items):
    return ' | '.join(m for _, _, m in items)


class CheckLedger(unittest.TestCase):
    def test_clean_ticket_passes(self):
        fail, warn = run(ship=True)
        self.assertEqual(fail, [], messages(fail))
        self.assertEqual(warn, [], messages(warn))

    def test_new_decision_after_pin_fails(self):
        fail, _ = run(spec=SPEC + '\n### DEC-002 — One row per crawl\n- Decision: x\n')
        self.assertIn('DEC-002', messages(fail))

    def test_new_decision_is_fine_once_plan_needs_replan(self):
        fail, _ = run(spec=SPEC + '\n### DEC-002 — One row per crawl\n', plan=PLAN.replace('Status: Approved', 'Status: Needs replan'))
        self.assertEqual(fail, [], messages(fail))

    def test_unresolvable_pin_fails(self):
        fail, _ = run(pinned=None)
        self.assertIn('pin', messages(fail))

    def test_deferred_note_without_open_id_fails(self):
        fail, _ = run(plan=PLAN + '\nKnown gap, deferred: no timezone column, for /review to weigh.\n')
        self.assertIn('OPEN-###', messages(fail))

    def test_deferred_note_with_open_id_passes(self):
        fail, _ = run(plan=PLAN + '\nKnown gap, deferred as OPEN-001.\n')
        self.assertEqual(fail, [], messages(fail))

    def test_reference_to_missing_open_item_fails(self):
        fail, _ = run(plan=PLAN + '\nDeferred as OPEN-009.\n')
        self.assertIn('OPEN-009', messages(fail))

    def test_open_item_without_owner_or_disposition_fails(self):
        fail, _ = run(open_items=OPEN + '| OPEN-002 | Replay overwrites | question |  | — |\n')
        self.assertIn('OPEN-002', messages(fail))

    def test_open_item_blocks_ship_only(self):
        rows = OPEN + '| OPEN-002 | Failing test at line 566 | failing test | owner | Open |\n'
        self.assertEqual(run(open_items=rows)[0], [])
        self.assertIn('OPEN-002', messages(run(open_items=rows, ship=True)[0]))

    def test_packet_without_status_fails(self):
        fail, _ = run(todo=TODO.replace('**Status:** Done\n', '', 1))
        self.assertIn('T001', messages(fail))

    def test_pending_task_blocks_ship_unless_superseded(self):
        todo = TODO.replace('**Status:** Done', '**Status:** Pending', 1)
        self.assertEqual(run(todo=todo)[0], [])
        fail = messages(run(todo=todo, ship=True)[0])
        self.assertIn('T001', fail)
        self.assertNotIn('T002', fail)

    def test_decision_touching_never_rule_warns_without_amends(self):
        dec = '\n### DEC-002 — Drop old columns\n- Decision: drop `legacy_total` from `old_snapshots`.\n'
        _, warn = run(spec=SPEC + dec, pinned=SPEC + dec)
        self.assertIn('DEC-002', messages(warn))
        _, warn = run(spec=SPEC + dec + '- Amends: DEC-001, Boundaries Never, by owner decision.\n',
                      pinned=SPEC + dec)
        self.assertEqual(warn, [], messages(warn))

    def test_decision_breaking_earlier_untouched_decision_warns(self):
        spec = SPEC + ('\n### DEC-002 — Calendar months win; the old cycle is untouched\n'
                       '- Context: `old_writer` copies rows into `cycle_table`.\n'
                       '\n### DEC-003 — Drop columns\n- Decision: `old_writer` stops writing them.\n')
        _, warn = run(spec=spec, pinned=spec)
        self.assertIn('DEC-003', messages(warn))
        self.assertNotIn('DEC-002 names', messages(warn))

    def test_rule_from_a_later_decision_does_not_warn(self):
        spec = SPEC + ('\n### DEC-002 — Months table\n- Decision: write `months_table`.\n'
                       '\n### DEC-003 — Months table is never rebuilt\n- Decision: `months_table` is never rebuilt.\n')
        _, warn = run(spec=spec, pinned=spec)
        self.assertEqual(warn, [], messages(warn))

    def test_spec_prose_about_deferral_is_not_scanned(self):
        fail, _ = run(spec=SPEC + '\nA wide read cache is deferred, not rejected.\n')
        self.assertEqual(fail, [], messages(fail))

    def test_unrecorded_unplanned_commit_warns(self):
        commits = [('a1b2c3d4e5', 'Drop old columns', ''), ('f6e5d4c3b2', 'Store months', 'T001')]
        _, warn = run(commits=commits)
        self.assertIn('a1b2c3d', messages(warn))
        self.assertNotIn('f6e5d4c', messages(warn))
        _, warn = run(commits=commits, open_items=OPEN + '| OPEN-002 | a1b2c3d drop old columns | unplanned commit | owner | Done — DEC-002 |\n')
        self.assertEqual(warn, [], messages(warn))

    def test_missing_open_file_is_empty_register(self):
        fail, _ = run(open_items=None)
        self.assertEqual(fail, [], messages(fail))
        fail, _ = run(open_items=None, plan=PLAN + '\nfollow-up: retry the failed jobs\n')
        self.assertIn('OPEN-###', messages(fail))


if __name__ == '__main__':
    unittest.main()
