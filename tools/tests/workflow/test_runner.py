import tempfile
import unittest
from pathlib import Path

from run import audit_reads, checks


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


if __name__ == '__main__':
    unittest.main()
