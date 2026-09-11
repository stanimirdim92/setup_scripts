#!/usr/bin/env python3
"""Guard the spec -> plan -> build -> review -> ship pipeline against artifact-path drift.

`/spec` and `/plan` write artifacts that `/build`, `/test`, `/review`, `/ship`,
the two pipeline skills, and the quality gates read back by path. When one side
renames or moves an artifact and the other keeps the old spelling, the pipeline
breaks silently -- a stage reports "no spec found" against a spec that exists.
This repo already shipped one such drift: the command wrote `[TICKET]-SPEC.md`
while the skill said `[TICKET]-spec.md` (fixed in c4584dd). Nothing checked it.

One canonical set of artifact paths, enforced across every file that defines
the pipeline. Changing the convention means editing ALLOWED and every guarded
file in the same change; this check fails until they agree.

Scope is deliberately narrow: only spec/capability-map/plan/todo artifacts, only
pipeline files. It is not a general markdown path linter; cross-references to
other harness documents (`../references/spec-quality-gates.md`,
`templates/spec.md`) are ignored by construction, see is_artifact_candidate().

Adapted from addyosmani/agent-skills scripts/validate-artifact-paths.js; the
difference is that our paths carry a `[TICKET]` placeholder and a module-id
suffix, so the allowlist is a set of patterns rather than literal strings.

Exit 0 when clean, 1 on any drifted path.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / 'dotfiles/claude'

# Canonical artifact paths. A module-id is kebab-case or the literal placeholder.
MODULE_ID = r'(?:<module-id>|[a-z0-9]+(?:-[a-z0-9]+)*)'
ALLOWED = [re.compile(p + r'\Z') for p in (
    r'docs/specs/\[TICKET\]-SPEC\.md',
    r'docs/specs/\[TICKET\]-CAPABILITY-MAP\.md',
    r'(?:docs/specs/)?\[TICKET\]-SPEC-' + MODULE_ID + r'\.md',
    r'docs/tasks/\[TICKET\]-plan\.md',
    r'docs/tasks/\[TICKET\]-todo\.md',
)]

# Every file that produces, consumes, or describes a pipeline artifact path.
# Absent files are skipped, not failed: this checks consistency, not presence.
GUARDED = [
    'CLAUDE.md',
    'commands/spec.md', 'commands/plan.md', 'commands/build.md',
    'commands/test.md', 'commands/review.md', 'commands/ship.md',
    'skills/spec-driven-development/SKILL.md',
    'skills/planning-and-task-breakdown/SKILL.md',
    'references/spec-quality-gates.md', 'references/plan-quality-gates.md',
    'references/target-selection.md', 'references/verification-triggers.md',
    'references/templates/spec.md', 'references/templates/bugfix-spec.md',
    'references/templates/plan.md', 'references/templates/task.md',
    'agents/executor.md', 'agents/test-engineer.md', 'agents/code-reviewer.md',
    'agents/security-auditor.md', 'agents/distributed-systems-reviewer.md',
    'agents/repo-recon.md',
    'docs/agents.md',
]

# Any path-like token whose basename looks like a pipeline artifact, in any
# casing, with any directory prefix (so docs/spec/, docs/features/[name]/ and
# a bare drifted filename are all candidates).
TOKEN = re.compile(
    r'(?<![\w./-])'
    r'((?:[A-Za-z0-9._\[\]<>-]+/)*'
    r'(?:\[TICKET\]-)?(?:SPEC(?:-[A-Za-z0-9_<>\[\]-]+)?|CAPABILITY-MAP|plan|todo)\.md)'
    r'(?![\w-])',
    re.IGNORECASE,
)


def is_artifact_candidate(token):
    """Decide whether a matched token is an artifact reference or a doc cross-ref.

    Artifact references either live under docs/ or carry the [TICKET]
    placeholder / an uppercase SPEC or CAPABILITY-MAP basename. A bare lowercase
    `spec.md` / `plan.md` names a template or a sibling document, and anything
    with a `..` or `references/` prefix is a cross-reference, never an artifact.
    """
    if token.startswith('..') or '/references/' in f'/{token}' or '/templates/' in f'/{token}':
        return False
    if token.startswith('docs/'):
        return True
    basename = token.rsplit('/', 1)[-1]
    return '[TICKET]' in basename or basename.startswith(('SPEC', 'CAPABILITY-MAP'))


def find_violations(text):
    """Return [(line_number, token)] for every artifact-shaped path not in ALLOWED."""
    violations = []
    for number, line in enumerate(text.splitlines(), 1):
        for match in TOKEN.finditer(line):
            token = match.group(1)
            if not is_artifact_candidate(token):
                continue
            if not any(pattern.match(token) for pattern in ALLOWED):
                violations.append((number, token))
    return violations


def main(argv):
    print('Checking spec/capability-map/plan/todo artifact paths...\n')
    checked = errors = 0
    for rel in GUARDED:
        path = HARNESS / rel
        if not path.is_file():
            continue
        checked += 1
        violations = find_violations(path.read_text())
        if not violations:
            print(f'  ok   {rel}')
            continue
        print(f'  FAIL {rel}')
        for number, token in violations:
            print(f'       L{number}: {token} -- not a canonical artifact path')
            errors += 1
    print(f'\n{checked} files checked -- {errors} error(s) -- {"FAILED" if errors else "PASSED"}')
    if errors:
        print('\nThe pipeline expects one spelling per artifact. Use a path from ALLOWED,')
        print('or change the convention in every guarded file and ALLOWED together.')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
