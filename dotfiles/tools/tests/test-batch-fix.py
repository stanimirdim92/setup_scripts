#!/usr/bin/env python3
"""Fixture tests for dotfiles/tools/run/batch-fix.py (ADR 0108).

`claude` is stubbed: these test the runner's decisions, not the model. The
skips matter most, since each one stops an unattended run from fixing the
wrong thing: the round cap, a candidate that moved after its review, and
findings that are pre-existing or already resolved."""
import importlib.util
import io
import json
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'run' / 'batch-fix.py'
spec = importlib.util.spec_from_file_location('bf', SCRIPT)
bf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bf)

STUB = '''#!/usr/bin/env bash
prompt=""; next=0
for a in "$@"; do [ "$next" = 1 ] && { prompt="$a"; next=0; }; [ "$a" = "-p" ] && next=1; done
echo "$prompt" >> "$STUB_CALLS"
case "$prompt" in
  "/build "*) [ -n "${STUB_NOFIX:-}" ] || { echo fix >> fix.txt; git add fix.txt; git -c user.email=t@t -c user.name=t commit -qm "fix: CODE-1" ; }
              echo '{"result":"BUILD COMPLETE","total_cost_usd":1.5}' ;;
  "/review "*) echo '{"result":"**Findings: 0 BLOCKER \\u00b7 1 REQUIRED \\u00b7 0 ADVISORY**\\nmore","total_cost_usd":2}' ;;
esac
'''


def sarif(*results):
    return json.dumps({'version': '2.1.0', 'runs': [{'tool': {'driver': {'name': 'code-reviewer'}},
                                                    'results': list(results)}]})


def finding(rule, disposition='REQUIRED', resolution='open', baseline='new'):
    return {'ruleId': rule, 'baselineState': baseline,
            'properties': {'disposition': disposition, 'resolution': resolution}}


class BatchFix(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.repo = root / 'repo'
        g = ['git', '-c', 'user.email=t@t', '-c', 'user.name=t', '-c', 'init.defaultBranch=main']
        subprocess.run(g + ['init', '-q', str(self.repo)], check=True)
        subprocess.run(g + ['-C', str(self.repo), 'commit', '-q', '--allow-empty', '-m', 'base'], check=True)
        self.wt = root / 'wt'
        subprocess.run(['git', '-C', str(self.repo), 'worktree', 'add', '-q', '-b', 'feature/a', str(self.wt)], check=True)
        self.sha = subprocess.run(['git', '-C', str(self.wt), 'rev-parse', '--short', 'HEAD'],
                                  capture_output=True, text=True, check=True).stdout.strip()
        self.reviews = root / 'review'
        self.reviews.mkdir()
        (root / 'bin').mkdir()
        stub = root / 'bin' / 'claude'
        stub.write_text(STUB)
        stub.chmod(0o755)
        self.calls = root / 'calls.txt'
        self.env = dict(os.environ, CLAUDE_BIN=str(stub), STUB_CALLS=str(self.calls))
        self.cwd = os.getcwd()
        os.chdir(self.repo)

    def tearDown(self):
        os.chdir(self.cwd)
        self.tmp.cleanup()

    def write(self, name, *results):
        (self.reviews / name).write_text(sarif(*results))

    def test_plan_skips_with_reasons(self):
        self.write(f'AB-1-{self.sha}.sarif', finding('CODE-1'), finding('CODE-2', 'ADVISORY'),
                   finding('CODE-3', baseline='unchanged'), finding('CODE-4', resolution='fixed'))
        self.write('AB-2-0000000.sarif', finding('CODE-1'))
        self.write(f'AB-3-{self.sha}.sarif', finding('CODE-9', 'ADVISORY'))
        for i, sha in enumerate(('1111111', '2222222', self.sha)):
            self.write(f'AB-4-{sha}.sarif', finding('SEC-1', 'BLOCKER'))
            os.utime(self.reviews / f'AB-4-{sha}.sarif', (i, i))
        jobs = {j['ticket']: j for j in bf.plan(self.reviews)}
        self.assertEqual(jobs['AB-1']['open'], ['CODE-1'])
        self.assertIsNone(jobs['AB-1']['skip'])
        self.assertEqual(jobs['AB-1']['worktree'], str(self.wt))
        self.assertIn('no worktree at the reviewed commit', jobs['AB-2']['skip'])
        self.assertEqual(jobs['AB-3']['skip'], 'nothing open that blocks')
        self.assertIn('round cap', jobs['AB-4']['skip'])

    def test_run_fixes_then_reviews(self):
        self.write(f'AB-1-{self.sha}.sarif', finding('CODE-1', 'BLOCKER'))
        os.environ.update(self.env)
        with redirect_stdout(io.StringIO()) as out:
            rc = bf.main(['--dir', str(self.reviews), '--yes', '--out', str(self.reviews.parent / 'out')])
        self.assertEqual(rc, 0, out.getvalue())
        self.assertEqual(self.calls.read_text().splitlines(), ['/build AB-1 review fixes', '/review AB-1'])
        self.assertIn('reviewed  AB-1', out.getvalue())
        self.assertIn('Findings: 0 BLOCKER · 1 REQUIRED · 0 ADVISORY', out.getvalue())
        self.assertIn('measured total: $3.50', out.getvalue())

    def test_no_commit_means_no_review(self):
        self.write(f'AB-1-{self.sha}.sarif', finding('CODE-1'))
        os.environ.update(self.env, STUB_NOFIX='1')
        try:
            with redirect_stdout(io.StringIO()) as out:
                rc = bf.main(['--dir', str(self.reviews), '--yes', '--out', str(self.reviews.parent / 'out')])
        finally:
            os.environ.pop('STUB_NOFIX')
        self.assertEqual(rc, 1)
        self.assertEqual(self.calls.read_text().splitlines(), ['/build AB-1 review fixes'])
        self.assertIn('NO FIX', out.getvalue())

    def test_dry_run_starts_nothing(self):
        self.write(f'AB-1-{self.sha}.sarif', finding('CODE-1'))
        os.environ.update(self.env)
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(bf.main(['--dir', str(self.reviews), '--dry-run']), 0)
        self.assertFalse(self.calls.exists())
        self.assertIn('fix   AB-1', out.getvalue())


if __name__ == '__main__':
    unittest.main(verbosity=1)
