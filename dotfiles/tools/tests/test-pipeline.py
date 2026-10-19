#!/usr/bin/env python3
"""Fixture tests for dotfiles/tools/run/pipeline.py (ADR 0114).

`claude` is stubbed: these test the runner's decisions, not the model. Each
stage runs in a fresh session and gets the previous stages' messages verbatim
in its prompt (target-selection.md §Gate handoffs). Only a clear result moves
the run on: BUILD COMPLETE, VERIFY PASS, and a review count line with its
SARIF file for HEAD. Anything else stops it. Findings start a fix round up to
the review round cap, and the run always stops before /ship."""
import importlib.util
import io
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'run' / 'pipeline.py'
spec = importlib.util.spec_from_file_location('pipeline', SCRIPT)
pl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pl)

BUILD = '**BUILD COMPLETE**\nHEAD: h\n- task done'
VERIFY = '**VERIFY PASS**\n- REQ-001: ran it'
CLEAN = '**Findings: 0 BLOCKER · 0 REQUIRED · 1 ADVISORY**\nmore'
OPEN = '**Findings: 0 BLOCKER · 1 REQUIRED · 0 ADVISORY**\n- CODE-1'

STUB = '''#!/usr/bin/env bash
prompt="$(cat)"
first="${prompt%%$'\\n'*}"
n=$(( $(wc -l < "$STUB_CALLS") + 1 ))
echo "$first" >> "$STUB_CALLS"
printf '%s' "$prompt" > "$STUB_PROMPTS/$n.txt"
reply() { python3 -c 'import json,sys; print(json.dumps({"result": sys.argv[1], "total_cost_usd": 1}))' "$1"; }
case "$first" in
  "/build "*) echo "$n" >> work.txt; git add work.txt; git -c user.email=t@t -c user.name=t commit -qm "build $n"
              case "${STUB_BUILD:-complete}" in
                blocked) reply '**BUILD BLOCKED** — needs a decision' ;;
                error)   echo '{"is_error":true,"subtype":"error_max_budget_usd","result":"**BUILD COMPLETE**","total_cost_usd":1}' ;;
                *)       reply "$STUB_BUILD_TEXT" ;;
              esac ;;
  "/test "*) case "${STUB_VERIFY:-pass}" in
               fail) reply '**VERIFY FAIL**
- REQ-001 broken' ;;
               *)    reply "$STUB_VERIFY_TEXT" ;;
             esac ;;
  "/review "*) round=$(( $(grep -c '^/review' "$STUB_CALLS") ))
               kind=$(echo $STUB_REVIEWS | cut -d' ' -f"$round")
               dir="$(git rev-parse --git-common-dir)/review"; mkdir -p "$dir"
               [ "$kind" = nosarif ] || echo '{"version":"2.1.0","runs":[]}' > "$dir/AB-1-$(git rev-parse --short HEAD).sarif"
               case "$kind" in
                 blocked)  reply '**REVIEW BLOCKED** — VERIFY PASS missing' ;;
                 required) reply "$STUB_OPEN_TEXT" ;;
                 *)        reply "$STUB_CLEAN_TEXT" ;;
               esac ;;
esac
'''


class Pipeline(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.repo = root / 'repo'
        g = ['git', '-c', 'user.email=t@t', '-c', 'user.name=t', '-c', 'init.defaultBranch=main']
        subprocess.run(g + ['init', '-q', str(self.repo)], check=True)
        subprocess.run(g + ['-C', str(self.repo), 'commit', '-q', '--allow-empty', '-m', 'base'], check=True)
        self.wt = root / 'wt'
        subprocess.run(['git', '-C', str(self.repo), 'worktree', 'add', '-q', '-b', 'feature/AB-1', str(self.wt)],
                       check=True)
        (root / 'bin').mkdir()
        stub = root / 'bin' / 'claude'
        stub.write_text(STUB)
        stub.chmod(0o755)
        self.calls = root / 'calls.txt'
        self.calls.write_text('')
        self.prompts = root / 'prompts'
        self.prompts.mkdir()
        self.handoff = self.repo / '.git' / 'handoff'
        self.saved_env = dict(os.environ)
        os.environ.update(CLAUDE_BIN=str(stub), STUB_CALLS=str(self.calls), STUB_PROMPTS=str(self.prompts),
                          STUB_BUILD_TEXT=BUILD, STUB_VERIFY_TEXT=VERIFY, STUB_CLEAN_TEXT=CLEAN,
                          STUB_OPEN_TEXT=OPEN, STUB_REVIEWS='clean')
        self.cwd = os.getcwd()
        os.chdir(self.wt)

    def tearDown(self):
        os.chdir(self.cwd)
        os.environ.clear()
        os.environ.update(self.saved_env)
        self.tmp.cleanup()

    def run_pipeline(self, *args):
        with redirect_stdout(io.StringIO()) as out:
            rc = pl.main(['AB-1', '--yes', *args])
        return rc, out.getvalue()

    def stages(self):
        return self.calls.read_text().splitlines()

    def prompt(self, n):
        return (self.prompts / f'{n}.txt').read_text()

    def test_clean_run_builds_tests_reviews_and_stops_before_ship(self):
        rc, out = self.run_pipeline()
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.stages(), ['/build AB-1', '/test AB-1', '/review AB-1'])
        self.assertIn('ready for /ship', out)
        self.assertIn('measured total: $3.00', out)

    def test_each_stage_gets_the_previous_messages_verbatim(self):
        self.run_pipeline()
        self.assertNotIn(BUILD, self.prompt(1))
        self.assertIn(BUILD, self.prompt(2))
        self.assertIn('pipeline.py', self.prompt(2))
        self.assertIn(BUILD, self.prompt(3))
        self.assertIn(VERIFY, self.prompt(3))

    def test_every_message_is_saved_for_the_owner(self):
        self.run_pipeline()
        saved = sorted(p.name for p in self.handoff.iterdir())
        self.assertEqual(saved[:3], ['AB-1-1-BUILD.md', 'AB-1-2-VERIFY.md', 'AB-1-3-REVIEW.md'])
        self.assertEqual((self.handoff / 'AB-1-1-BUILD.md').read_text(), BUILD + '\n')
        self.assertEqual((self.handoff / 'AB-1-3-REVIEW.md').read_text(), CLEAN + '\n')

    def test_open_findings_start_a_fix_round_with_the_review_in_the_prompt(self):
        os.environ['STUB_REVIEWS'] = 'required clean'
        rc, out = self.run_pipeline()
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.stages(), ['/build AB-1', '/test AB-1', '/review AB-1',
                                         '/build AB-1 review fixes', '/test AB-1', '/review AB-1'])
        self.assertIn(OPEN, self.prompt(4))

    def test_round_cap_stops_without_a_fourth_review(self):
        os.environ['STUB_REVIEWS'] = 'required required required'
        rc, out = self.run_pipeline()
        self.assertEqual(rc, 1)
        self.assertEqual(self.stages().count('/review AB-1'), 3)
        self.assertEqual(len(self.stages()), 9)
        self.assertIn('round cap', out)

    def test_build_blocked_stops(self):
        os.environ['STUB_BUILD'] = 'blocked'
        rc, out = self.run_pipeline()
        self.assertEqual(rc, 1)
        self.assertEqual(self.stages(), ['/build AB-1'])
        self.assertIn('BUILD BLOCKED', out)

    def test_cli_error_stops_even_with_a_complete_line(self):
        os.environ['STUB_BUILD'] = 'error'
        rc, out = self.run_pipeline()
        self.assertEqual(rc, 1)
        self.assertEqual(self.stages(), ['/build AB-1'])
        self.assertIn('error_max_budget_usd', out)

    def test_verify_fail_stops(self):
        os.environ['STUB_VERIFY'] = 'fail'
        rc, out = self.run_pipeline()
        self.assertEqual(rc, 1)
        self.assertEqual(self.stages(), ['/build AB-1', '/test AB-1'])
        self.assertIn('VERIFY FAIL', out)

    def test_review_blocked_stops(self):
        os.environ['STUB_REVIEWS'] = 'blocked'
        rc, out = self.run_pipeline()
        self.assertEqual(rc, 1)
        self.assertIn('REVIEW BLOCKED', out)

    def test_review_without_a_sarif_file_for_head_stops(self):
        os.environ['STUB_REVIEWS'] = 'nosarif'
        rc, out = self.run_pipeline()
        self.assertEqual(rc, 1)
        self.assertIn('no review file', out)

    def test_refuses_main_and_a_dirty_tree(self):
        (self.wt / 'stray.txt').write_text('x')
        rc, out = self.run_pipeline()
        self.assertEqual(rc, 2)
        self.assertIn('uncommitted changes', out)
        os.chdir(self.repo)
        rc, out = self.run_pipeline()
        self.assertEqual(rc, 2)
        self.assertIn('main', out)
        self.assertEqual(self.stages(), [])

    def test_dry_run_starts_nothing(self):
        rc, out = self.run_pipeline('--dry-run')
        self.assertEqual(rc, 0)
        self.assertEqual(self.stages(), [])
        self.assertIn('Worst case $90', out)


if __name__ == '__main__':
    unittest.main()
