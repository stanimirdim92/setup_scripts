#!/usr/bin/env python3
"""Fixture tests for tools/validate-artifact-paths.py.

Each case is (text, expected drifted tokens). The allow cases matter as much as
the deny cases: a validator that flags `../references/spec-quality-gates.md`
or the `spec.md` template would be switched off within a week.
"""
import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('vap', Path(__file__).with_name('validate-artifact-paths.py'))
vap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vap)


def drifted(text):
    return [token for _, token in vap.find_violations(text)]


class CanonicalPathsPass(unittest.TestCase):
    def test_every_canonical_form_is_allowed(self):
        text = '\n'.join([
            'Save the spec as docs/specs/[TICKET]-SPEC.md.',
            'The map lives at `docs/specs/[TICKET]-CAPABILITY-MAP.md`.',
            'Module specs: `[TICKET]-SPEC-identity.md`, `[TICKET]-SPEC-billing.md`.',
            'Pattern: docs/specs/[TICKET]-SPEC-<module-id>.md and [TICKET]-SPEC-<module-id>.md',
            'Plan: docs/tasks/[TICKET]-plan.md; tasks: docs/tasks/[TICKET]-todo.md.',
        ])
        self.assertEqual(drifted(text), [])

    def test_cross_references_and_templates_are_ignored(self):
        text = '\n'.join([
            'See ../references/spec-quality-gates.md and ../../references/plan-quality-gates.md.',
            'Template: ../../references/templates/spec.md, sibling bugfix-spec.md, and spec.md.',
            'git show <sha>:<spec path> > tmp/spec-pinned.md',
            'Source: `../commands/spec.md`, `../commands/plan.md`.',
            'docs/adr/0049-durable-spec-pin-and-hook-bypasses.md explains the pin.',
            'the plan/todo artifacts, the spec, a plan',
        ])
        self.assertEqual(drifted(text), [])


class DriftIsCaught(unittest.TestCase):
    def test_lowercase_spec_drift_the_bug_we_shipped(self):
        self.assertEqual(drifted('Single-capability spec: `docs/specs/[TICKET]-spec.md`'), ['docs/specs/[TICKET]-spec.md'])

    def test_bare_ticket_drift(self):
        self.assertEqual(drifted('write [TICKET]-spec.md next to it'), ['[TICKET]-spec.md'])

    def test_module_spec_without_ticket_prefix(self):
        self.assertEqual(drifted('named by module id (`SPEC-identity.md`, `SPEC-billing.md`)'), ['SPEC-identity.md', 'SPEC-billing.md'])

    def test_moved_directory(self):
        self.assertEqual(drifted('docs/spec/[TICKET]-SPEC.md and docs/features/[name]/spec.md'),
                         ['docs/spec/[TICKET]-SPEC.md', 'docs/features/[name]/spec.md'])

    def test_plan_and_todo_drift(self):
        self.assertEqual(drifted('docs/tasks/[TICKET]-PLAN.md, docs/plans/[TICKET]-plan.md, docs/tasks/[TICKET]-tasks-todo.md'),
                         ['docs/tasks/[TICKET]-PLAN.md', 'docs/plans/[TICKET]-plan.md'])

    def test_root_level_upstream_convention_is_not_ours(self):
        self.assertEqual(drifted('Save as SPEC.md in the project root'), ['SPEC.md'])

    def test_line_numbers_are_reported(self):
        self.assertEqual(vap.find_violations('fine\n\ndocs/specs/[TICKET]-spec.md\n'), [(3, 'docs/specs/[TICKET]-spec.md')])


class GuardedFilesExist(unittest.TestCase):
    def test_every_guarded_file_currently_exists(self):
        missing = [rel for rel in vap.GUARDED if not (vap.HARNESS / rel).is_file()]
        self.assertEqual(missing, [], 'guarded list names files that do not exist; remove or fix them')

    def test_harness_is_currently_clean(self):
        dirty = {rel: vap.find_violations((vap.HARNESS / rel).read_text()) for rel in vap.GUARDED if (vap.HARNESS / rel).is_file()}
        self.assertEqual({k: v for k, v in dirty.items() if v}, {})


if __name__ == '__main__':
    unittest.main()
