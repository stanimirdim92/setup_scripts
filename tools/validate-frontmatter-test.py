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
effort: medium
maxTurns: 40
"""

SETTINGS_OK = """{
  "env": {
    "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "1",
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "0",
    "CLAUDE_CODE_FORK_SUBAGENT": "0"
  },
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
        body = RECON.replace('tools: Read, Grep, Glob', 'tools: Read, Grep, Glob, Edit, Write')
        problems = vf.check_agent('code-reviewer', agent('code-reviewer', body).replace('repo-recon', 'code-reviewer'))
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

    def test_settings_invalid_json(self):
        problems = vf.check_settings('{"env": ')
        self.assertTrue(any('invalid JSON' in p for p in problems))

    def test_settings_global_hook_dropped(self):
        problems = vf.check_settings(SETTINGS_OK.replace('block-destructive-bash.sh', 'nothing.sh'))
        self.assertTrue(any('block-destructive-bash.sh' in p for p in problems))


if __name__ == '__main__':
    unittest.main(verbosity=1)
