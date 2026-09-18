#!/usr/bin/env python3
"""Fixture tests for tools/validate-frontmatter.py.

Each case is a frontmatter block and the violations it must or must not
produce. The allow cases carry the weight: a check that flags the real
executor -- which legitimately holds Bash, Write and Edit -- gets deleted the
first time it blocks a green build.
"""
import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('vf', Path(__file__).with_name('validate-frontmatter.py'))
vf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vf)


def agent(name, body):
    return f'---\n{body.strip()}\n---\n\nBody text.\n'


EXECUTOR = """
name: executor
description: Implements one planned task end-to-end.
tools: Read, Edit, Write, Bash, Grep, Glob, Skill
model: claude-sonnet-5
hooks:
  PreToolUse:
    - matcher: Bash
      hooks:
        - type: command
          command: "$HOME/.claude/hooks/block-agent-push.sh"
  Stop:
    - hooks:
        - type: command
          command: "$HOME/.claude/hooks/require-handoff-report.sh"
"""

RECON = """
name: repo-recon
description: Read-only repository reconnaissance.
tools: Read, Grep, Glob
model: claude-sonnet-5
maxTurns: 40
"""

REVIEWER = """
name: blind-reviewer
description: Reviews a diff with no knowledge of what it was supposed to do.
tools: Read, Grep, Glob
model: claude-opus-5
maxTurns: 60
"""

SETTINGS_OK = """{
  "model": "claude-opus-5",
  "env": {
    "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "1",
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "0",
    "CLAUDE_CODE_FORK_SUBAGENT": "0"
  },
  "worktree": {"baseRef": "head"},
  "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [
    {"type": "command", "command": "$HOME/.claude/hooks/block-destructive-bash.sh"},
    {"type": "command", "command": "$HOME/.claude/hooks/warn-force-push.sh"}
  ]}]}
}"""


class AllowCases(unittest.TestCase):
    def test_real_executor_shape_passes(self):
        self.assertEqual(vf.check_agent('executor', agent('executor', EXECUTOR)), [])

    def test_real_recon_shape_passes(self):
        self.assertEqual(vf.check_agent('repo-recon', agent('repo-recon', RECON)), [])

    def test_writer_may_hold_write_tools(self):
        problems = vf.check_agent('executor', agent('executor', EXECUTOR))
        self.assertFalse([p for p in problems if 'Write' in p or 'Bash' in p])

    def test_settings_pins_present_passes(self):
        self.assertEqual(vf.check_settings(SETTINGS_OK), [])

    def test_reviewer_on_opus_passes(self):
        self.assertEqual(vf.check_agent('blind-reviewer', agent('blind-reviewer', REVIEWER)), [])


class DenyCases(unittest.TestCase):
    def test_missing_frontmatter(self):
        problems = vf.check_agent('executor', 'No fences here.\n')
        self.assertTrue(any('no YAML frontmatter' in p for p in problems))

    def test_missing_tools_line_inherits_everything(self):
        body = RECON.replace('tools: Read, Grep, Glob\n', '')
        problems = vf.check_agent('repo-recon', agent('repo-recon', body))
        self.assertTrue(any('no explicit `tools:`' in p for p in problems))

    def test_reviewer_granted_bash(self):
        body = RECON.replace('tools: Read, Grep, Glob', 'tools: Read, Grep, Glob, Bash')
        problems = vf.check_agent('repo-recon', agent('repo-recon', body))
        self.assertTrue(any('read-only persona grants Bash' in p for p in problems))

    def test_reviewer_granted_edit(self):
        body = REVIEWER.replace('tools: Read, Grep, Glob', 'tools: Read, Grep, Glob, Edit, Write')
        problems = vf.check_agent('blind-reviewer', agent('blind-reviewer', body))
        self.assertTrue(any('Edit' in p and 'Write' in p for p in problems))

    def test_persona_granted_agent_tool(self):
        body = RECON.replace('tools: Read, Grep, Glob', 'tools: Read, Grep, Glob, Agent')
        problems = vf.check_agent('repo-recon', agent('repo-recon', body))
        self.assertTrue(any('personas never dispatch personas' in p for p in problems))

    def test_writer_missing_push_hook(self):
        body = EXECUTOR.replace('block-agent-push.sh', 'some-other-hook.sh')
        problems = vf.check_agent('executor', agent('executor', body))
        self.assertTrue(any('block-agent-push.sh' in p for p in problems))

    def test_writer_missing_handoff_gate(self):
        body = EXECUTOR.replace('require-handoff-report.sh', 'some-other-hook.sh')
        problems = vf.check_agent('executor', agent('executor', body))
        self.assertTrue(any('require-handoff-report.sh' in p for p in problems))

    def test_read_only_persona_missing_max_turns(self):
        body = RECON.replace('maxTurns: 40\n', '')
        problems = vf.check_agent('repo-recon', agent('repo-recon', body))
        self.assertTrue(any('no maxTurns' in p for p in problems))

    def test_name_mismatch(self):
        problems = vf.check_agent('test-engineer', agent('test-engineer', EXECUTOR))
        self.assertTrue(any('expected' in p and 'name' in p for p in problems))

    def test_settings_spawn_depth_unset(self):
        problems = vf.check_settings(SETTINGS_OK.replace('"CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "1",\n    ', ''))
        self.assertTrue(any('SPAWN_DEPTH is unset' in p for p in problems))

    def test_settings_fork_re_enabled(self):
        problems = vf.check_settings(SETTINGS_OK.replace('"CLAUDE_CODE_FORK_SUBAGENT": "0"', '"CLAUDE_CODE_FORK_SUBAGENT": "1"'))
        self.assertTrue(any('FORK_SUBAGENT' in p for p in problems))

    def test_persona_drifted_off_the_model(self):
        body = REVIEWER.replace('model: claude-opus-5', 'model: claude-sonnet-5')
        problems = vf.check_agent('blind-reviewer', agent('blind-reviewer', body))
        self.assertTrue(any("expected 'claude-opus-5'" in p for p in problems))

    def test_floating_alias_is_not_the_pinned_model(self):
        body = REVIEWER.replace('model: claude-opus-5', 'model: opus')
        problems = vf.check_agent('blind-reviewer', agent('blind-reviewer', body))
        self.assertTrue(any("expected 'claude-opus-5'" in p for p in problems))

    def test_sonnet_persona_escalated_to_opus(self):
        body = RECON.replace('model: claude-sonnet-5', 'model: claude-opus-5')
        problems = vf.check_agent('repo-recon', agent('repo-recon', body))
        self.assertTrue(any("expected 'claude-sonnet-5'" in p for p in problems))

    def test_settings_session_model_drifted(self):
        problems = vf.check_settings(SETTINGS_OK.replace('"model": "claude-opus-5"', '"model": "sonnet"'))
        self.assertTrue(any('settings.json: model' in p for p in problems))

    def test_executor_must_inherit_ticket_checkout(self):
        body = EXECUTOR + 'isolation: worktree\n'
        problems = vf.check_agent('executor', agent('executor', body))
        self.assertTrue(any('isolation belongs to concurrent dispatch' in p for p in problems))

    def test_verifier_still_requires_worktree_isolation(self):
        body = EXECUTOR.replace('name: executor', 'name: test-engineer')
        problems = vf.check_agent('test-engineer', agent('test-engineer', body))
        self.assertTrue(any('isolation: worktree' in p for p in problems))
        body += 'isolation: worktree\n'
        self.assertEqual(vf.check_agent('test-engineer', agent('test-engineer', body)), [])

    def test_settings_worktree_base_ref_missing(self):
        problems = vf.check_settings(SETTINGS_OK.replace('"worktree": {"baseRef": "head"},\n  ', ''))
        self.assertTrue(any('baseRef' in p for p in problems))

    def test_settings_worktree_base_ref_fresh(self):
        problems = vf.check_settings(SETTINGS_OK.replace('"baseRef": "head"', '"baseRef": "fresh"'))
        self.assertTrue(any('baseRef' in p for p in problems))

    def test_settings_invalid_json(self):
        problems = vf.check_settings('{"env": ')
        self.assertTrue(any('invalid JSON' in p for p in problems))

    def test_settings_global_hook_dropped(self):
        problems = vf.check_settings(SETTINGS_OK.replace('block-destructive-bash.sh', 'nothing.sh'))
        self.assertTrue(any('block-destructive-bash.sh' in p for p in problems))


if __name__ == '__main__':
    unittest.main(verbosity=1)
