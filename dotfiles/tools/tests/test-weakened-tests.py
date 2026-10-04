#!/usr/bin/env python3
"""Fixture tests for dotfiles/claude/skills/code-review-and-quality/scripts/weakened-tests.py.

Each deny case is one way an agent makes a test pass without fixing the code.
The allow cases matter as much: a rename, a new assertion or a tightened
setting must stay silent, or /review learns to ignore the list.
"""
import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = (Path(__file__).resolve().parents[2] / 'claude' / 'skills' / 'code-review-and-quality'
          / 'scripts' / 'weakened-tests.py')
spec = importlib.util.spec_from_file_location('wt', SCRIPT)
wt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wt)

TEST_PHP = '''<?php
class FeedTest extends TestCase {
    public function test_ranks() {
        $this->assertSame(1, rank());
        $this->assertCount(3, feed());
    }
}
'''


class Repo:
    def __init__(self, root):
        self.root = Path(root)
        self.git('init', '-q', '-b', 'main')
        self.git('config', 'user.email', 't@example.com')
        self.git('config', 'user.name', 't')

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.root), *args], check=True,
                              capture_output=True, text=True).stdout.strip()

    def write(self, path, text):
        p = self.root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def commit(self, message='c'):
        self.git('add', '-A')
        self.git('commit', '-qm', message)

    def scan(self, *extra):
        return wt.main(['--repo', str(self.root), '--base', 'main', *extra])

    def found(self, worktree=False):
        files = wt.parse_diff(self.git('diff', '--unified=0', '-M', 'main...HEAD') if not worktree
                              else self.git('diff', '--unified=0', '-M', 'main'))
        if worktree:
            files.update(wt.untracked(str(self.root)))
        return sorted((f['category'], f['path']) for f in wt.findings(files))


class WeakenedTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Repo(self.tmp.name)
        self.repo.write('tests/Feature/FeedTest.php', TEST_PHP)
        self.repo.write('src/feed.ts', 'export function rank(a: number) {\n  return a > 0 ? 1 : 0;\n}\n')
        self.repo.write('src/feed.test.ts', "it('ranks', () => {\n  expect(rank(1)).toBe(1);\n});\n")
        self.repo.write('phpstan.neon', 'parameters:\n  level: 8\n')
        self.repo.commit('base')
        self.repo.git('checkout', '-qb', 'candidate')

    def tearDown(self):
        self.tmp.cleanup()

    def test_clean_change_is_silent(self):
        self.repo.write('src/feed.ts', 'export function rank(a: number) {\n  return a >= 1 ? 1 : 0;\n}\n')
        self.repo.write('src/feed.test.ts', "it('ranks', () => {\n  expect(rank(1)).toBe(1);\n"
                                            "  expect(rank(0)).toBe(0);\n});\n")
        self.repo.commit()
        self.assertEqual(self.repo.found(), [])
        self.assertEqual(self.repo.scan(), 0)

    def test_deleted_test_file(self):
        self.repo.git('rm', '-q', 'tests/Feature/FeedTest.php')
        self.repo.commit()
        self.assertEqual(self.repo.found(), [('test-deleted', 'tests/Feature/FeedTest.php')])
        self.assertEqual(self.repo.scan(), 1)

    def test_move_with_edits_is_not_a_deletion(self):
        self.repo.git('rm', '-q', 'tests/Feature/FeedTest.php')
        self.repo.write('tests/Unit/FeedTest.php', '<?php\nclass FeedTest {}\n')
        self.repo.commit()
        self.assertNotIn(('test-deleted', 'tests/Feature/FeedTest.php'), self.repo.found())

    def test_documentation_is_skipped(self):
        self.repo.write('docs/testing.md', 'Use `// @ts-ignore` sparingly. TODO: expand.\n')
        self.repo.write('tests/README.md', 'it.skip marks a pending test\n')
        self.repo.commit()
        self.assertEqual(self.repo.found(), [])

    def test_rename_is_not_a_deletion(self):
        self.repo.git('mv', 'tests/Feature/FeedTest.php', 'tests/Feature/RankTest.php')
        self.repo.commit()
        self.assertEqual(self.repo.found(), [])

    def test_skip_and_focus_markers(self):
        self.repo.write('src/feed.test.ts', "it.skip('ranks', () => {\n  expect(rank(1)).toBe(1);\n});\n")
        self.repo.write('tests/Feature/FeedTest.php', TEST_PHP.replace(
            '$this->assertSame', "$this->markTestSkipped('flaky');\n        $this->assertSame"))
        self.repo.commit()
        self.assertEqual(self.repo.found(), [('test-skipped', 'src/feed.test.ts'),
                                             ('test-skipped', 'tests/Feature/FeedTest.php')])

    def test_assertion_removed_from_a_test_that_stayed(self):
        self.repo.write('tests/Feature/FeedTest.php', TEST_PHP.replace(
            '        $this->assertCount(3, feed());\n', ''))
        self.repo.commit()
        self.assertEqual(self.repo.found(), [('assertions-removed', 'tests/Feature/FeedTest.php')])

    def test_rewritten_assertion_is_silent(self):
        self.repo.write('tests/Feature/FeedTest.php', TEST_PHP.replace('assertCount(3', 'assertCount(4'))
        self.repo.commit()
        self.assertEqual(self.repo.found(), [])

    def test_suppression_comment(self):
        self.repo.write('src/feed.ts', '// @ts-ignore\nexport function rank(a: number) {\n'
                                       '  return a > 0 ? 1 : 0;\n}\n')
        self.repo.commit()
        self.assertEqual(self.repo.found(), [('suppression', 'src/feed.ts')])

    def test_checker_config_change(self):
        self.repo.write('phpstan.neon', 'parameters:\n  level: 5\n')
        self.repo.commit()
        self.assertEqual(self.repo.found(), [('checker-config', 'phpstan.neon')])

    def test_stub_and_empty_catch_in_code_not_tests(self):
        self.repo.write('src/feed.ts', 'export function rank(a: number) {\n'
                                       '  try { return a > 0 ? 1 : 0; } catch (e) {}\n'
                                       "  throw new Error('not implemented');\n}\n")
        self.repo.write('src/feed.test.ts', "// TODO: more cases\nit('ranks', () => {\n"
                                            "  expect(rank(1)).toBe(1);\n});\n")
        self.repo.commit()
        self.assertEqual(self.repo.found(), [('stub', 'src/feed.ts'), ('stub', 'src/feed.ts')])

    def test_worktree_mode_sees_untracked_and_uncommitted(self):
        self.repo.write('src/new.ts', '// eslint-disable-next-line\nexport const x = 1;\n')
        self.repo.write('src/feed.test.ts', "it.only('ranks', () => {\n  expect(rank(1)).toBe(1);\n});\n")
        self.assertEqual(self.repo.found(worktree=True), [('suppression', 'src/new.ts'),
                                                          ('test-skipped', 'src/feed.test.ts')])
        self.assertEqual(self.repo.scan('--worktree'), 1)
        self.assertEqual(self.repo.scan(), 0)  # nothing committed yet

    def test_cannot_run_is_exit_2(self):
        self.assertEqual(wt.main(['--repo', self.tmp.name, '--base', 'no-such-ref']), 2)
        with tempfile.TemporaryDirectory() as empty:
            self.assertEqual(wt.main(['--repo', empty, '--base', 'main']), 2)

    def test_test_path_detection(self):
        for path in ('tests/Unit/A.php', 'app/__tests__/a.js', 'pkg/a_test.go', 'test_a.py',
                     'src/a.spec.tsx', 'src/a.test.mjs', 'spec/a_spec.rb', 'app/FooTest.php'):
            self.assertTrue(wt.is_test(path), path)
        for path in ('src/latest.ts', 'app/Contest.php', 'docs/testing.md', 'src/attestation.py'):
            self.assertFalse(wt.is_test(path), path)


if __name__ == '__main__':
    unittest.main(verbosity=1)
