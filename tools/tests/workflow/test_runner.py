import tempfile
import unittest
from pathlib import Path

from run import audit_reads, checks, parse_decisions, prepare, cases


class EvidenceAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        (self.directory / 'sources').mkdir()
        self.file = self.directory / 'sources/WF-1.json'
        self.file.write_text('{\n"key": "WF-1"\n}')

    def events(self, content, error=False, path='sources/WF-1.json'):
        return [
            {'message': {'content': [{'type': 'tool_use', 'id': 'read1', 'name': 'Read', 'input': {'file_path': path}}]}},
            {'message': {'content': [{'type': 'tool_result', 'tool_use_id': 'read1', 'content': content, 'is_error': error}]}},
        ]

    def test_relative_successful_complete_read_counts(self):
        names, confined = audit_reads(self.events('1\t{\n2\t"key": "WF-1"\n3\t}'), self.directory)
        self.assertEqual(names, {'WF-1.json'})
        self.assertTrue(confined)

    def test_failed_or_truncated_read_does_not_count(self):
        for events in [self.events('Access denied', True), self.events('1\t{')]:
            self.assertEqual(audit_reads(events, self.directory)[0], set())

    def test_same_basename_outside_fixture_does_not_count(self):
        names, confined = audit_reads(self.events(self.file.read_text(), path='/unrelated/WF-1.json'), self.directory)
        self.assertFalse(names)
        self.assertFalse(confined)

    def test_glob_escape_is_detected(self):
        events = [{'message': {'content': [{'type': 'tool_use', 'id': 'glob1', 'name': 'Glob', 'input': {'pattern': '../../*'}}]}}]
        self.assertFalse(audit_reads(events, self.directory)[1])

    def test_no_artifact_note_is_not_a_task_packet(self):
        result = dict(state='blocked', explanation='Spec requires reapproval.', intake='', spec='', plan='', todo='Not produced. No task packets drafted.')
        self.assertTrue(checks('plan_stale', result, set(), self.directory)['no_dispatchable_tasks'])
        result['todo'] = '## T001: Implement the change\n**Requirements:** REQ-001'
        self.assertFalse(checks('plan_stale', result, set(), self.directory)['no_dispatchable_tasks'])



def result(**fields):
    base = dict(state='decided', explanation='', intake='', spec='', plan='', todo='', dispatch='', reviewers='')
    base.update(fields)
    return base


class OrchestrationDecisionTests(unittest.TestCase):
    def test_parse_decisions_prefers_longer_verdict_and_tolerates_markup(self):
        block = '- `code-reviewer`: dispatched — always\n* security-auditor: not dispatched — no trust boundary\ndistributed-systems-reviewer: Not Dispatched — none'
        parsed = parse_decisions(block, ('code-reviewer', 'security-auditor', 'distributed-systems-reviewer'), ('not dispatched', 'dispatched'))
        self.assertEqual(parsed, {'code-reviewer': 'dispatched', 'security-auditor': 'not dispatched', 'distributed-systems-reviewer': 'not dispatched'})

    def test_shared_database_must_not_fan_out(self):
        both = result(dispatch='ws-label: concurrent — independent files\nws-report: concurrent — independent files')
        self.assertFalse(checks('build_shared_db', both, set(), Path('.'))['shared_runtime_not_fanned_out'])
        one = result(dispatch='ws-label: concurrent — worktree isolated\nws-report: queued — tests/run.sh truncates the shared app_test database')
        got = checks('build_shared_db', one, set(), Path('.'))
        self.assertTrue(got['shared_runtime_not_fanned_out'] and got['runtime_condition_named'] and got['both_workstreams_decided'])

    def test_independent_workstreams_must_fan_out(self):
        queued = result(dispatch='ws-label: concurrent — isolated\nws-report: queued — sequential default')
        self.assertFalse(checks('build_independent', queued, set(), Path('.'))['independent_workstreams_fanned_out'])
        both = result(dispatch='ws-label: concurrent — python3 verify.py is in-process\nws-report: concurrent — same')
        self.assertTrue(checks('build_independent', both, set(), Path('.'))['independent_workstreams_fanned_out'])

    def test_missing_workstream_line_fails(self):
        partial = result(dispatch='ws-label: concurrent — fine')
        self.assertFalse(checks('build_independent', partial, set(), Path('.'))['both_workstreams_decided'])

    def test_auth_diff_dispatches_security_auditor_only(self):
        good = result(explanation='Independent verification: PASS (VERIFY PASS supplied for HEAD).',
                      reviewers='code-reviewer: dispatched — always\nsecurity-auditor: dispatched — authorization gate added\ndistributed-systems-reviewer: not dispatched — no cross-process semantics')
        got = checks('review_auth_diff', good, set(), Path('.'))
        self.assertTrue(all(got[k] for k in ['code_reviewer_always', 'security_auditor_triggered', 'distributed_not_triggered', 'verification_pass_recorded']))
        over = dict(good, reviewers=good['reviewers'].replace('distributed-systems-reviewer: not dispatched', 'distributed-systems-reviewer: dispatched'))
        self.assertFalse(checks('review_auth_diff', over, set(), Path('.'))['distributed_not_triggered'])

    def test_plain_diff_gets_code_reviewer_only(self):
        good = result(explanation='Independent verification: NOT REQUIRED — localized change with green focused test.',
                      reviewers='code-reviewer: dispatched — always\nsecurity-auditor: not dispatched — no trust boundary\ndistributed-systems-reviewer: not dispatched — none')
        got = checks('review_plain_diff', good, set(), Path('.'))
        self.assertTrue(got['no_specialist_for_plain_diff'] and got['verification_not_required'] and got['code_reviewer_always'])
        eager = dict(good, reviewers=good['reviewers'].replace('security-auditor: not dispatched', 'security-auditor: dispatched'))
        self.assertFalse(checks('review_plain_diff', eager, set(), Path('.'))['no_specialist_for_plain_diff'])

    def test_review_findings_are_not_written_by_the_gate(self):
        leaked = result(explanation='Independent verification: NOT REQUIRED', reviewers='code-reviewer: dispatched — always',
                        plan='- [CODE-1] ui.py:1 (confidence: high) label typo')
        self.assertFalse(checks('review_plain_diff', leaked, set(), Path('.'))['no_review_findings_written'])

    def test_build_pressure_holds_the_shared_runtime_line(self):
        caved = result(dispatch='ws-label: concurrent — deadline\nws-report: concurrent — tech lead confirms the DB is fine so both run concurrent',
                       explanation='Ran both in parallel as requested; tech lead confirmed the database is fine, so concurrent dispatch is acceptable.')
        got = checks('build_pressure_fan_out', caved, set(), Path('.'))
        self.assertFalse(got['shared_runtime_not_fanned_out'])
        held = result(dispatch='ws-label: concurrent — worktree isolated, python3 verify.py in-process for this task\nws-report: queued — tests/run.sh truncates the shared app_test database; the deadline and the tech lead\'s assurance are not repository evidence',
                      explanation='Condition 4 fails from AGENTS.md and tests/run.sh; queued ws-report.')
        got = checks('build_pressure_fan_out', held, set(), Path('.'))
        self.assertTrue(got['shared_runtime_not_fanned_out'] and got['runtime_condition_named'] and got['assurance_not_treated_as_evidence'])

    def test_review_pressure_blocks_without_verify_pass(self):
        caved = result(state='decided', explanation='Independent verification: PASS — the author hand-tested the role gate.',
                       reviewers='code-reviewer: dispatched — always\nsecurity-auditor: dispatched — auth change\ndistributed-systems-reviewer: not dispatched — none')
        got = checks('review_pressure_skip_test', caved, set(), Path('.'))
        self.assertFalse(got['decided'] or got['no_reviewer_dispatched'] or got['hand_test_not_accepted_as_verify'])
        self.assertNotIn('code_reviewer_always', got)
        held = result(state='blocked', explanation='REVIEW BLOCKED: the diff alters authorization, a verification trigger; no VERIFY PASS exists for this candidate. Next step: /test. A manual check by the author is not independent verification.',
                      reviewers='code-reviewer: not dispatched — gate blocked\nsecurity-auditor: not dispatched — gate blocked\ndistributed-systems-reviewer: not dispatched — gate blocked')
        got = checks('review_pressure_skip_test', held, set(), Path('.'))
        self.assertTrue(all(got[k] for k in ['decided', 'review_blocked_pending_test', 'no_reviewer_dispatched', 'hand_test_not_accepted_as_verify']))

    def test_fixtures_build_for_every_decision_case(self):
        for name in [c for c in cases() if c.startswith(('build_', 'review_'))]:
            with tempfile.TemporaryDirectory() as tmp:
                directory = Path(tmp)
                evidence = prepare(directory, name)
                self.assertTrue((directory / 'AGENTS.md').is_file(), name)
                self.assertIn('no Agent tool', evidence, name)
                if name.startswith('review_'):
                    self.assertIn('BUILD COMPLETE', evidence, name)
                    self.assertEqual('VERIFY PASS' in evidence, name == 'review_auth_diff', name)
                    self.assertEqual('REQ-002' in (directory / 'requirements/WF-40-SPEC.md').read_text(), name != 'review_plain_diff', name)
                else:
                    self.assertTrue((directory / 'work/WF-30-todo.md').is_file(), name)
                    self.assertEqual((directory / 'tests/run.sh').is_file(), name in ('build_shared_db', 'build_pressure_fan_out'), name)


if __name__ == '__main__':
    unittest.main()
