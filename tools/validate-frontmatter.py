#!/usr/bin/env python3
"""Guard the persona frontmatter and settings that carry the harness's enforcement.

Every guarantee in docs/adr/0055 lives in a YAML block or a settings key, and
nothing checked that the block still says what the ADR claims:

- Reviewers are read-only **by tool grant**, not by instruction. A persona that
  loses its `tools:` line inherits everything, including `Agent` and `Bash` --
  the exact hole 0055 closed. A reviewer that gains `Write`/`Edit`/`Bash` is
  read-only in prose only.
- The writing personas carry the two agent-scoped hooks (`block-agent-push.sh`,
  `require-handoff-report.sh`). Delete a `hooks:` block by accident and the
  push denial and the handoff gate silently stop existing; tools/test-hooks.sh
  and tools/test-handoff-hook.sh still pass, because the hooks themselves are
  fine -- nobody is calling them.
- The spawn-depth, agent-teams and fork pins in settings.json are single lines
  whose absence restores a default that undoes the design (0055 follow-up).

This is a shape check on the declarations, not a behavioral test: it proves the
frontmatter still says what the ADR says, not that the runtime honours it.
Same reasoning as 0049 -- a guardrail nothing tests is a guardrail nobody has
checked.

Exit 0 when clean, 1 on any violation.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLAUDE = ROOT / 'dotfiles/claude'
AGENTS = CLAUDE / 'agents'
SETTINGS = CLAUDE / 'settings.json'

# Personas that may write. They keep Bash; the hooks are what bound them, and
# 0058 keeps verifier isolation structural and makes concurrent executor
# isolation an explicit dispatch choice; sequential executors reuse the ticket.
WRITERS = {'executor', 'test-engineer'}
WRITER_HOOKS = ('block-agent-push.sh', 'require-handoff-report.sh')

# Models are tiered by role (0056), and pinned rather than floating for the
# reason 0002 gives: delegation should target a version deliberately chosen, not
# whatever `opus` resolves to after the next release. The session itself runs
# the high tier, so the stages that live in it -- /build, /review, /test, /ship
# -- inherit it without each declaring a model.
OPUS = 'claude-opus-5'
SONNET = 'claude-sonnet-5'
SESSION_MODEL = OPUS

REVIEWERS = {'code-reviewer', 'blind-reviewer', 'security-auditor',
             'distributed-systems-reviewer'}
SONNET_PERSONAS = {'repo-recon', 'executor', 'test-engineer'}

# Personas that must never mutate anything. 0055: "reviewers read-only by tool
# grant". Bash counts as a write tool here -- a reviewer with a shell can commit.
READ_ONLY = REVIEWERS | {'repo-recon'}
MUTATING_TOOLS = {'Write', 'Edit', 'NotebookEdit', 'Bash'}

# Tools that would let a persona dispatch or talk to another one. Depth is
# pinned to 1 in settings, but an explicit grant is a second way in.
DISPATCH_TOOLS = {'Agent', 'Task', 'SendMessage'}

REQUIRED_SETTINGS = {
    'CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH': '1',
    'CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS': '0',
    'CLAUDE_CODE_FORK_SUBAGENT': '0',
}


def frontmatter(text):
    """Return the text between the opening and closing --- fences, or None."""
    match = re.match(r'\A---\n(.*?)\n---\n', text, re.DOTALL)
    return match.group(1) if match else None


def scalar(block, key):
    """Value of a top-level `key: value` line, or None. Not a YAML parser: the
    checks below need flat scalars and one list, and adding PyYAML to make CI
    read five keys is not worth the dependency."""
    match = re.search(rf'^{re.escape(key)}:[ \t]*(.*)$', block, re.MULTILINE)
    if not match:
        return None
    return match.group(1).strip().strip('"\'') or None


def tool_list(block):
    """Tools declared on the `tools:` line. None when the line is absent --
    which is the finding, since an absent line inherits every tool."""
    raw = scalar(block, 'tools')
    if raw is None:
        return None
    return [t.strip() for t in re.split(r'[,\s]+', raw) if t.strip()]


def check_agent(name, text):
    """Violations for one persona file. Pure function of its text, so the
    fixture tests can call it without writing files."""
    problems = []
    block = frontmatter(text)
    if block is None:
        return [f'{name}: no YAML frontmatter']

    if scalar(block, 'name') != name:
        problems.append(f'{name}: frontmatter name is {scalar(block, "name")!r}, expected {name!r}')
    if not scalar(block, 'description'):
        problems.append(f'{name}: no description (it is what routes dispatch)')
    model = scalar(block, 'model')
    if not model:
        problems.append(f'{name}: no model')
    else:
        expected = SONNET if name in SONNET_PERSONAS else OPUS
        if model != expected:
            problems.append(f'{name}: model is {model!r}, expected {expected!r} (adr/0056)')

    tools = tool_list(block)
    if tools is None:
        problems.append(f'{name}: no explicit `tools:` -- inherits every tool, including Agent and Bash (adr/0055)')
    else:
        granted_dispatch = sorted(DISPATCH_TOOLS.intersection(tools))
        if granted_dispatch:
            problems.append(f'{name}: grants {", ".join(granted_dispatch)} -- personas never dispatch personas (adr/0055)')
        if name in READ_ONLY:
            mutating = sorted(MUTATING_TOOLS.intersection(tools))
            if mutating:
                problems.append(f'{name}: read-only persona grants {", ".join(mutating)}')

    if name in READ_ONLY and not scalar(block, 'maxTurns'):
        problems.append(f'{name}: no maxTurns -- read-only personas are capped (adr/0055)')

    if name in WRITERS:
        for hook in WRITER_HOOKS:
            if hook not in block:
                problems.append(f'{name}: frontmatter does not reference {hook} -- the gate is not attached (adr/0055)')
        if name == 'test-engineer' and scalar(block, 'isolation') != 'worktree':
            problems.append(f'{name}: no `isolation: worktree` -- verifier checkout isolation is required (adr/0058)')
        if name == 'executor' and scalar(block, 'isolation') is not None:
            problems.append(f'{name}: isolation belongs to concurrent dispatch; sequential executors inherit the ticket checkout (adr/0058)')

    return problems


def check_settings(text):
    problems = []
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return [f'settings.json: invalid JSON -- {exc}']

    env = data.get('env', {})
    for key, expected in REQUIRED_SETTINGS.items():
        actual = env.get(key)
        if actual is None:
            problems.append(f'settings.json: {key} is unset -- the default undoes adr/0055')
        elif str(actual) != expected:
            problems.append(f'settings.json: {key} is {actual!r}, expected {expected!r}')

    # `isolation: worktree` branches from the DEFAULT BRANCH unless baseRef is
    # "head". Executors work on in-progress branches, so the default would hand
    # each one a checkout without the ticket branch or the earlier workstream
    # commits -- silently, since the worktree is created successfully (adr/0056).
    if data.get('worktree', {}).get('baseRef') != 'head':
        problems.append('settings.json: worktree.baseRef is not "head" -- writer worktrees would branch from the default branch and lose in-progress work (adr/0056)')

    if data.get('model') != SESSION_MODEL:
        problems.append(f'settings.json: model is {data.get("model")!r}, expected {SESSION_MODEL!r} -- the session tier the main-session stages inherit (adr/0056)')

    hooks = json.dumps(data.get('hooks', {}))
    for hook in ('block-destructive-bash.sh', 'warn-force-push.sh'):
        if hook not in hooks:
            problems.append(f'settings.json: global PreToolUse does not run {hook}')

    return problems


def main():
    problems = []
    checked = 0

    if not AGENTS.is_dir():
        print(f'validate-frontmatter: no agents directory at {AGENTS}', file=sys.stderr)
        return 1

    print('Checking persona frontmatter and settings pins...\n')

    for path in sorted(AGENTS.glob('*.md')):
        found = check_agent(path.stem, path.read_text())
        checked += 1
        print(f'  {"FAIL" if found else "ok  "} {path.relative_to(ROOT)}')
        problems += found

    found = check_settings(SETTINGS.read_text())
    checked += 1
    print(f'  {"FAIL" if found else "ok  "} {SETTINGS.relative_to(ROOT)}')
    problems += found

    known = WRITERS | READ_ONLY
    present = {p.stem for p in AGENTS.glob('*.md')}
    for missing in sorted(known - present):
        problems.append(f'{missing}: persona named in this check no longer exists -- update the check or restore it')

    print()
    if problems:
        for problem in problems:
            print(f'  {problem}')
        print(f'\n{checked} files checked -- {len(problems)} problem(s) -- FAILED')
        return 1
    print(f'{checked} files checked -- 0 problems -- PASSED')
    return 0


if __name__ == '__main__':
    sys.exit(main())
