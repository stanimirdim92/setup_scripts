#!/usr/bin/env python3
"""Fixture tests for dotfiles/tools/run/batch-fix.py (ADR 0108).

`claude` is stubbed: these test the runner's decisions, not the model. The
skips matter most, since each one stops an unattended run from fixing the
wrong thing: the round cap, a candidate that moved after its review, and
findings that are pre-existing or already resolved. So do the checkout
rules: one checkout and branch per ticket, clean, locked, and still at the
reviewed commit when the work starts."""
import argparse
import fcntl
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
  "/review "*) ticket="${prompt#/review }"
               case "${STUB_REVIEW:-pass}" in
                 blocked) echo '{"result":"REVIEW BLOCKED: BUILD handoff missing","total_cost_usd":2}' ;;
                 error)   echo '{"is_error":true,"subtype":"error_max_budget_usd","result":"**Findings: 0 BLOCKER \\u00b7 1 REQUIRED \\u00b7 0 ADVISORY**","total_cost_usd":2}' ;;
                 missing) echo '{"result":"I read the diff and it looks fine.","total_cost_usd":2}' ;;
                 nojson)  echo 'Findings: not json' ;;
                 *)       [ "${STUB_REVIEW:-pass}" = nosarif ] || echo '{"version":"2.1.0","runs":[]}' > "$STUB_REVIEWS/$ticket-$(git rev-parse --short HEAD).sarif"
                          echo '{"result":"**Findings: 0 BLOCKER \\u00b7 1 REQUIRED \\u00b7 0 ADVISORY**\\nmore","total_cost_usd":2}' ;;
               esac ;;
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
        self.env = dict(os.environ, CLAUDE_BIN=str(stub), STUB_CALLS=str(self.calls),
                        STUB_REVIEWS=str(self.reviews))
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

    def add_worktree(self, name, branch):
        path = Path(self.tmp.name) / name
        subprocess.run(['git', '-C', str(self.repo), 'worktree', 'add', '-q', '-b', branch, str(path)], check=True)
        return path

    def job(self, ticket='AB-1'):
        return next(j for j in bf.plan(self.reviews) if j['ticket'] == ticket)

    def run_args(self):
        return argparse.Namespace(claude=self.env['CLAUDE_BIN'], budget=1, permission_mode='acceptEdits')

    def run_job(self, job):
        os.environ.update(self.env)
        out = self.reviews.parent / 'out'
        out.mkdir(exist_ok=True)
        return bf.run_job(job, self.run_args(), out)

    def test_two_tickets_at_one_commit_do_not_share_a_checkout(self):
        self.write(f'AB-1-{self.sha}.sarif', finding('CODE-1'))
        self.write(f'AB-2-{self.sha}.sarif', finding('CODE-2'))
        jobs = bf.plan(self.reviews)
        self.assertEqual([j['ticket'] for j in jobs if not j['skip']], [])
        self.assertIn('AB-2', next(j for j in jobs if j['ticket'] == 'AB-1')['skip'])

    def test_branch_name_binds_each_ticket_to_its_own_checkout(self):
        one = self.add_worktree('wt-one', 'feature/AB-1')
        two = self.add_worktree('wt-two', 'feature/AB-2')
        self.write(f'AB-1-{self.sha}.sarif', finding('CODE-1'))
        self.write(f'AB-2-{self.sha}.sarif', finding('CODE-2'))
        jobs = {j['ticket']: j for j in bf.plan(self.reviews)}
        self.assertEqual((jobs['AB-1']['skip'], jobs['AB-1']['worktree'], jobs['AB-1']['branch']),
                         (None, str(one), 'feature/AB-1'))
        self.assertEqual((jobs['AB-2']['skip'], jobs['AB-2']['worktree']), (None, str(two)))

    def test_ambiguous_checkouts_at_one_commit_are_rejected(self):
        self.add_worktree('wt-b', 'feature/b')
        self.write(f'AB-1-{self.sha}.sarif', finding('CODE-1'))
        self.assertIn('more than one worktree', self.job()['skip'])

    def test_dirty_checkout_is_rejected(self):
        (self.wt / 'notes.txt').write_text('mine\n')
        self.write(f'AB-1-{self.sha}.sarif', finding('CODE-1'))
        self.assertIn('uncommitted', self.job()['skip'])

    def test_checkout_that_turns_dirty_after_planning_is_not_touched(self):
        self.write(f'AB-1-{self.sha}.sarif', finding('CODE-1'))
        job = self.job()
        (self.wt / 'notes.txt').write_text('mine\n')
        result = self.run_job(job)
        self.assertEqual(result['state'], 'FAILED')
        self.assertIn('uncommitted', result['detail'])
        self.assertFalse(self.calls.exists())

    def test_held_lock_blocks_a_second_job(self):
        self.write(f'AB-1-{self.sha}.sarif', finding('CODE-1'))
        job = self.job()
        gitdir = subprocess.run(['git', '-C', str(self.wt), 'rev-parse', '--absolute-git-dir'],
                                capture_output=True, text=True, check=True).stdout.strip()
        with open(Path(gitdir) / 'batch-fix.lock', 'w') as held:
            fcntl.flock(held, fcntl.LOCK_EX)
            result = self.run_job(job)
        self.assertEqual(result['state'], 'FAILED')
        self.assertIn('locked', result['detail'])
        self.assertFalse(self.calls.exists())

    def test_head_that_moved_before_start_is_rejected(self):
        self.write(f'AB-1-{self.sha}.sarif', finding('CODE-1'))
        job = self.job()
        subprocess.run(['git', '-C', str(self.wt), '-c', 'user.email=t@t', '-c', 'user.name=t',
                        'commit', '-q', '--allow-empty', '-m', 'moved on'], check=True)
        result = self.run_job(job)
        self.assertEqual(result['state'], 'FAILED')
        self.assertIn('reviewed commit', result['detail'])
        self.assertFalse(self.calls.exists())

    def review_job(self, mode):
        self.write(f'AB-1-{self.sha}.sarif', finding('CODE-1'))
        job = self.job()
        os.environ['STUB_REVIEW'] = mode
        try:
            return self.run_job(job)
        finally:
            os.environ.pop('STUB_REVIEW')

    def test_complete_review_of_the_fix_counts_as_reviewed(self):
        result = self.review_job('pass')
        self.assertEqual(result['state'], 'reviewed')
        self.assertEqual(result['detail'], 'Findings: 0 BLOCKER \u00b7 1 REQUIRED \u00b7 0 ADVISORY')

    def test_review_blocked_is_not_a_review_even_at_exit_zero(self):
        result = self.review_job('blocked')
        self.assertEqual(result['state'], 'BLOCKED')
        self.assertIn('BUILD handoff missing', result['detail'])

    def test_cli_error_result_is_a_failed_job(self):
        result = self.review_job('error')
        self.assertEqual(result['state'], 'FAILED')
        self.assertIn('error_max_budget_usd', result['detail'])

    def test_review_without_a_result_line_is_a_failed_job(self):
        result = self.review_job('missing')
        self.assertEqual(result['state'], 'FAILED')
        self.assertIn('no result line', result['detail'])

    def test_unparseable_cli_output_is_a_failed_job(self):
        result = self.review_job('nojson')
        self.assertEqual(result['state'], 'FAILED')
        self.assertIn('no JSON', result['detail'])

    def test_review_that_wrote_no_sarif_for_the_candidate_is_a_failed_job(self):
        result = self.review_job('nosarif')
        self.assertEqual(result['state'], 'FAILED')
        self.assertIn('no review file for', result['detail'])

    def test_exit_is_non_zero_unless_every_job_was_reviewed(self):
        for mode, rc in (('pass', 0), ('blocked', 1), ('error', 1), ('missing', 1), ('nosarif', 1)):
            with self.subTest(mode):
                self.write(f'AB-1-{self.sha}.sarif', finding('CODE-1'))
                os.environ.update(self.env, STUB_REVIEW=mode)
                try:
                    with redirect_stdout(io.StringIO()):
                        got = bf.main(['--dir', str(self.reviews), '--yes', '--out', str(self.reviews.parent / 'out')])
                finally:
                    os.environ.pop('STUB_REVIEW')
                self.assertEqual(got, rc)
                subprocess.run(['git', '-C', str(self.wt), 'reset', '-q', '--hard', self.sha], check=True)
                for f in self.reviews.glob('*.sarif'):
                    f.unlink()


if __name__ == '__main__':
    unittest.main(verbosity=1)
