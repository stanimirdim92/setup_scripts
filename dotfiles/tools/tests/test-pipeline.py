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
import json
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

BUILD = '**BUILD COMPLETE**\nHEAD: h\n- task done\nHANDOFF: result=COMPLETE route=none ids=- decide=0'
VERIFY = '**VERIFY PASS**\n- REQ-001: ran it\nHANDOFF: result=PASS route=none ids=- decide=0'
CLEAN = '**Findings: 0 BLOCKER · 0 REQUIRED · 1 ADVISORY**\nmore\nHANDOFF: result=CLEAN route=none ids=- decide=0'
OPEN = '**Findings: 0 BLOCKER · 1 REQUIRED · 0 ADVISORY**\n- CODE-1\nHANDOFF: result=FINDINGS route=/build ids=CODE-1 decide=0'

STUB = '''#!/usr/bin/env bash
prompt="$(cat)"
first="${prompt%%$'\\n'*}"
case "$first" in "Your previous turn"*) first="$(tail -1 "$STUB_CALLS")" ;; esac     # a resumed stage
n=$(( $(wc -l < "$STUB_CALLS") + 1 ))
echo "$first" >> "$STUB_CALLS"
echo "$*" >> "$STUB_PROMPTS/args.txt"
printf '%s' "$prompt" > "$STUB_PROMPTS/$n.txt"
reply() { python3 -c 'import json,sys; print(json.dumps({"result": sys.argv[1], "total_cost_usd": 1}))' "$1"; }
if [ -n "$STUB_SLOW" ] && [ "$n" = 1 ]; then          # a stage that works for a while
  echo '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Bash","input":{"command":"php artisan test --filter=Export"}}]}}'
  sleep 2.5
fi
if [ -n "$STUB_FLAKY" ] && [ "$n" = 1 ]; then          # the first call fails for a passing reason
  echo '{"type":"system","subtype":"init","session_id":"s1"}'
  case "$STUB_FLAKY" in
    stall) exec sleep 30 ;;
    auth)  echo 'Not logged in. Please run /login' >&2; exit 1 ;;
    *)     echo 'API Error: 429 rate limit reached' >&2; exit 1 ;;
  esac
fi
case "$first" in
  "/build "*) echo "$n" >> work.txt; git add work.txt; git -c user.email=t@t -c user.name=t commit -qm "build $n"
              case "${STUB_BUILD:-complete}" in
                blocked) reply '**BUILD BLOCKED** — needs a decision
HANDOFF: result=BLOCKED route=owner ids=- decide=1' ;;
                error)   echo '{"is_error":true,"subtype":"error_max_budget_usd","result":"**BUILD COMPLETE**","total_cost_usd":1}' ;;
                nofooter) reply '**BUILD COMPLETE**
done, no handoff line' ;;
                disagree) reply '**BUILD COMPLETE**
HANDOFF: result=BLOCKED route=/spec ids=REQ-001 decide=0' ;;
                tospec)  reply '**BUILD BLOCKED** — REQ-001 contradicts the code
HANDOFF: result=BLOCKED route=/spec ids=REQ-001 decide=2' ;;
                *)       reply "$STUB_BUILD_TEXT" ;;
              esac ;;
  "/test "*) kind="${STUB_VERIFY:-pass}"
             if [ -n "$STUB_VERIFIES" ]; then round=$(( $(grep -c '^/test' "$STUB_CALLS") )); kind=$(echo $STUB_VERIFIES | cut -d' ' -f"$round"); fi
             case "$kind" in
               fail) reply '**VERIFY FAIL**
- REQ-001 broken
HANDOFF: result=FAIL route=/build ids=REQ-001 decide=0' ;;
               blocked) reply '**VERIFY BLOCKED** — no browser
HANDOFF: result=BLOCKED route=owner ids=- decide=1' ;;
               *)    reply "$STUB_VERIFY_TEXT" ;;
             esac ;;
  "/review "*) round=$(( $(grep -c '^/review' "$STUB_CALLS") ))
               kind=$(echo $STUB_REVIEWS | cut -d' ' -f"$round")
               dir="$(git rev-parse --git-common-dir)/review"; mkdir -p "$dir"
               [ "$kind" = nosarif ] || echo '{"version":"2.1.0","runs":[]}' > "$dir/AB-1-$(git rev-parse --short HEAD).sarif"
               case "$kind" in
                 blocked)  reply '**REVIEW BLOCKED** — VERIFY PASS missing
HANDOFF: result=BLOCKED route=owner ids=- decide=0' ;;
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

    def test_every_stage_is_told_it_runs_headless(self):
        self.run_pipeline()
        for n in (1, 2, 3):
            self.assertIn('Dispatch every agent in the foreground (run_in_background: false)', self.prompt(n))
        self.assertTrue(self.prompt(2).rstrip().endswith('this command requires.'))   # after the handed-on messages
        self.assertIn('never call AskUserQuestion', self.prompt(2))

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

    def test_owner_inbox_note_and_stop(self):
        inbox = Path(self.prompts) / 'inbox.json'
        inbox.write_text('{"after_step": 99, "stop": false, "notes": ["use Select"]}')
        os.environ['HARNESS_INBOX'] = str(inbox)
        try:
            rc, out = self.run_pipeline()
            self.assertIn('TICKET NOTE', self.prompt(2))
            self.assertIn('use Select', self.prompt(2))
            inbox.write_text('{"after_step": 99, "stop": true, "notes": []}')
            rc, out = self.run_pipeline()
            self.assertEqual(rc, 1)
            self.assertIn('stopped by the owner', out)
        finally:
            del os.environ['HARNESS_INBOX']

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

    def test_verify_fail_routed_to_build_starts_a_fix_round_then_tests_again(self):
        os.environ['STUB_VERIFIES'] = 'fail pass'
        rc, out = self.run_pipeline()
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.stages(), ['/build AB-1', '/test AB-1', '/build AB-1 verify fixes', '/test AB-1', '/review AB-1'])
        self.assertIn('VERIFY result', self.prompt(3))
        self.assertIn('REQ-001 broken', self.prompt(3))

    def test_verify_fail_twice_more_stops_at_the_cap(self):
        os.environ['STUB_VERIFIES'] = 'fail fail fail'
        rc, out = self.run_pipeline()
        self.assertEqual(rc, 1)
        self.assertEqual(self.stages().count('/build AB-1 verify fixes'), 2)
        self.assertIn('verify round cap', out)

    def test_verify_blocked_stops_with_its_route(self):
        os.environ['STUB_VERIFY'] = 'blocked'
        rc, out = self.run_pipeline()
        self.assertEqual(rc, 1)
        self.assertIn('VERIFY BLOCKED', out)
        self.assertEqual(json.loads((self.handoff / 'AB-1-pipeline-stop.json').read_text())['handoff']['route'], 'owner')

    def test_no_handoff_line_stops_naming_the_stage(self):
        os.environ['STUB_BUILD'] = 'nofooter'
        rc, out = self.run_pipeline()
        self.assertEqual(rc, 1)
        self.assertEqual(self.stages(), ['/build AB-1'])
        self.assertIn('/build gave no HANDOFF line', out)

    def test_handoff_disagreeing_with_the_result_line_stops(self):
        os.environ['STUB_BUILD'] = 'disagree'
        rc, out = self.run_pipeline()
        self.assertEqual(rc, 1)
        self.assertIn('HANDOFF disagrees with the result line', out)

    def test_build_routed_to_spec_stops_with_the_route_in_the_stop_file(self):
        os.environ['STUB_BUILD'] = 'tospec'
        rc, out = self.run_pipeline()
        self.assertEqual(rc, 1)
        stop = json.loads((self.handoff / 'AB-1-pipeline-stop.json').read_text())
        self.assertEqual((stop['handoff']['route'], stop['handoff']['ids'], stop['handoff']['decide']), ('/spec', ['REQ-001'], 2))

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

    def test_refuses_master_and_a_dirty_tree(self):
        (self.wt / 'stray.txt').write_text('x')
        rc, out = self.run_pipeline()
        self.assertEqual(rc, 2)
        self.assertIn('uncommitted changes', out)
        os.chdir(self.repo)
        subprocess.run(['git', 'checkout', '-q', '-b', 'master'], check=True)
        rc, out = self.run_pipeline()
        self.assertEqual(rc, 2)
        self.assertIn('master', out)
        self.assertEqual(self.stages(), [])

    def test_runs_on_main(self):
        os.chdir(self.repo)                    # this repository works in main directly
        rc, out = self.run_pipeline()
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.stages(), ['/build AB-1', '/test AB-1', '/review AB-1'])

    def test_dry_run_starts_nothing(self):
        rc, out = self.run_pipeline('--dry-run')
        self.assertEqual(rc, 0)
        self.assertEqual(self.stages(), [])
        self.assertIn('Worst case $90', out)

    def args(self, n):
        return (self.prompts / 'args.txt').read_text().splitlines()[n - 1]

    def waits(self):
        """pipeline's backoff sleeps, recorded instead of slept."""
        waited = []
        pl.sleep = waited.append
        self.addCleanup(setattr, pl, 'sleep', __import__('time').sleep)
        return waited

    def test_transient_failure_is_retried_resuming_the_session(self):
        os.environ['STUB_FLAKY'] = 'rate-limit'
        waited = self.waits()
        rc, out = self.run_pipeline()
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.stages(), ['/build AB-1', '/build AB-1', '/test AB-1', '/review AB-1'])
        self.assertIn('--resume s1', self.args(2))
        self.assertNotIn('--resume', self.args(1))
        self.assertTrue(self.prompt(2).startswith('Your previous turn on this task was cut off (exited 1)'))
        self.assertEqual(waited, [10])
        self.assertIn('retry 2/5 in 10s: exited 1 (resuming the session)', out)
        self.assertIn('--verbose', self.args(1))                   # stream-json needs it

    def test_stalled_stage_is_killed_and_retried(self):
        os.environ.update(STUB_FLAKY='stall', HARNESS_STALL_MIN='0.01')
        waited = self.waits()
        rc, out = self.run_pipeline()
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.stages()[:2], ['/build AB-1', '/build AB-1'])
        self.assertIn('--resume s1', self.args(2))
        self.assertIn('retry 2/5 in 10s: no event for 0.01 min', out)
        self.assertEqual(waited, [10])

    def test_auth_error_is_not_retried(self):
        os.environ['STUB_FLAKY'] = 'auth'
        waited = self.waits()
        rc, out = self.run_pipeline()
        self.assertEqual(rc, 1)
        self.assertEqual(self.stages(), ['/build AB-1'])
        self.assertEqual(waited, [])
        self.assertIn('/build exited 1', out)

    def test_retries_stop_at_the_cap(self):
        os.environ.update(STUB_FLAKY='rate-limit', HARNESS_RETRIES='1')
        self.waits()
        rc, out = self.run_pipeline()
        self.assertEqual(rc, 1)
        self.assertEqual(self.stages(), ['/build AB-1'])

    def test_heartbeat_shows_the_stage_is_alive(self):
        os.environ.update(STUB_SLOW='1', HARNESS_HEARTBEAT_S='1')
        rc, out = self.run_pipeline()
        self.assertEqual(rc, 0, out)
        self.assertRegex(out, r'… 0m0[1-3]s · 1 events · last \ds ago · Bash php artisan test --filter=Export')
        os.environ['HARNESS_HEARTBEAT_S'] = '0'
        self.calls.write_text('')
        rc, out = self.run_pipeline()
        self.assertNotIn('events ·', out)

    def test_handoff_line_parses(self):
        self.assertEqual(pl.handoff('report\nBUILD BLOCKED\nHANDOFF: result=BLOCKED route=/spec ids=REQ-008 decide=2\n'),
                         {'result': 'BLOCKED', 'route': '/spec', 'ids': ['REQ-008'], 'decide': 2})
        self.assertEqual(pl.handoff('HANDOFF: result=COMPLETE route=/test ids=T007,T008 decide=0')['ids'], ['T007', 'T008'])
        self.assertEqual(pl.handoff('HANDOFF: result=COMPLETE route=none ids=- decide=0')['ids'], [])
        self.assertEqual(pl.handoff('HANDOFF: result=BLOCKED route=owner ids=- decide=1')['route'], 'owner')
        self.assertEqual(pl.handoff('HANDOFF: result=FAIL route=/build ids=REQ-017,REQ-009 decide=1')['result'], 'FAIL')
        self.assertIsNone(pl.handoff('The verifier is running in its own worktree. I am waiting for its report.'))
        with self.assertRaises(ValueError) as err:
            pl.handoff('HANDOFF: result=BLOCKED route=/ship ids=- decide=0')
        self.assertIn('route=/ship is not one of', str(err.exception))
        with self.assertRaises(ValueError):
            pl.handoff('HANDOFF: result=DONE route=none ids=- decide=0')
        with self.assertRaises(ValueError):
            pl.handoff('HANDOFF: result=PASS route=none ids=- decide=many')

    def test_stop_file_carries_the_parsed_handoff(self):
        os.environ.update(STUB_BUILD='blocked')
        self.run_pipeline()
        stop = json.loads((self.handoff / 'AB-1-pipeline-stop.json').read_text())
        self.assertEqual(stop['handoff'], {'result': 'BLOCKED', 'route': 'owner', 'ids': [], 'decide': 1})
        os.environ.update(STUB_BUILD='nofooter')
        self.calls.write_text('')
        self.run_pipeline()
        stop = json.loads((self.handoff / 'AB-1-pipeline-stop.json').read_text())
        self.assertIsNone(stop['handoff'])                                      # a report without the line

    def test_commands_name_the_handoff_line(self):
        root = SCRIPT.parents[2] / 'claude'
        for name in ('plan', 'build', 'test', 'review'):
            text = (root / 'commands' / f'{name}.md').read_text()
            self.assertIn('HANDOFF: result=', text, name)
            self.assertIn('references/stage-handoff.md', text, name)
        self.assertTrue((root / 'references' / 'stage-handoff.md').exists())

    def test_backoff_doubles_up_to_the_cap(self):
        self.assertEqual([min(pl.BACKOFF[0] * 2 ** (a - 1), pl.BACKOFF[1]) for a in range(1, 7)],
                         [10, 20, 40, 80, 160, 300])

    def test_started_again_on_the_same_head_goes_on_after_the_finished_stages(self):
        os.environ['STUB_VERIFY'] = 'blocked'
        rc, out = self.run_pipeline()
        self.assertEqual(rc, 1)
        del os.environ['STUB_VERIFY']
        rc, out = self.run_pipeline()                                 # same HEAD: no second /build
        self.assertEqual(rc, 0, out)
        self.assertIn('going on after BUILD (stage 1)', out)
        self.assertEqual(self.stages(), ['/build AB-1', '/test AB-1', '/test AB-1', '/review AB-1'])
        self.assertIn(BUILD, self.prompt(3))                          # the kept BUILD message is handed on
        self.assertIn('· stage 3', out)
        self.assertEqual(sorted(p.name for p in self.handoff.glob('AB-1-*-*.md')),
                         ['AB-1-1-BUILD.md', 'AB-1-2-VERIFY.md', 'AB-1-3-VERIFY.md', 'AB-1-4-REVIEW.md'])
        self.assertFalse((self.handoff / 'AB-1-pipeline.json').exists())   # a clean run leaves no state

    def test_stop_file_survives_a_start_and_goes_with_a_clean_run(self):
        os.environ['STUB_BUILD'] = 'blocked'
        self.run_pipeline()
        stop = self.handoff / 'AB-1-pipeline-stop.json'
        self.assertIn('BUILD BLOCKED', stop.read_text())
        del os.environ['STUB_BUILD']
        os.environ['STUB_VERIFY'] = 'blocked'                                 # another stop replaces it
        self.run_pipeline()
        self.assertIn('VERIFY BLOCKED', stop.read_text())                     # replaced, never removed on start
        del os.environ['STUB_VERIFY']
        subprocess.run(['git', '-c', 'user.email=t@t', '-c', 'user.name=t', 'commit', '-q', '--allow-empty', '-m', 'x'], check=True)
        rc, out = self.run_pipeline()
        self.assertEqual(rc, 0, out)
        self.assertFalse(stop.exists())

    def test_another_head_starts_a_fresh_round(self):
        os.environ['STUB_VERIFY'] = 'blocked'
        self.run_pipeline()
        del os.environ['STUB_VERIFY']
        subprocess.run(['git', '-c', 'user.email=t@t', '-c', 'user.name=t', 'commit', '-q', '--allow-empty',
                        '-m', 'owner fix'], check=True)
        rc, out = self.run_pipeline()
        self.assertEqual(rc, 0, out)
        self.assertNotIn('going on after', out)
        self.assertEqual(self.stages(), ['/build AB-1', '/test AB-1', '/build AB-1', '/test AB-1', '/review AB-1'])


if __name__ == '__main__':
    unittest.main()
