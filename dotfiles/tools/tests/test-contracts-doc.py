#!/usr/bin/env python3
"""component-response-contracts.md says of itself that nothing checks it against its sources. This does
the cheap half: every file in hooks/, agents/ and commands/ is named in the section that catalogues it,
so a new hook or persona cannot go uncatalogued and a renamed one cannot stay."""
import re
import unittest
from pathlib import Path

CLAUDE = Path(__file__).resolve().parents[2] / 'claude'
DOC = (CLAUDE / 'references' / 'component-response-contracts.md').read_text()


def section(title):
    m = re.search(rf'^## \d+\. {re.escape(title)}\n(.*?)(?=^## \d+\. |\Z)', DOC, re.M | re.S)
    return m.group(1)


class ContractsDoc(unittest.TestCase):
    def test_every_hook_is_in_the_hook_table(self):
        hooks = section('Claude hooks')
        for path in sorted((CLAUDE / 'hooks').glob('*.sh')):
            self.assertIn(f'| `{path.name}` |', hooks, path.name)

    def test_every_persona_is_in_the_report_table(self):
        personas = section('Claude agent report contracts')
        for path in sorted((CLAUDE / 'agents').glob('*.md')):
            self.assertIn(f'| `{path.stem}` |', personas, path.stem)

    def test_every_command_is_in_the_stage_table(self):
        commands = section('Command stage-gate contracts')
        for path in sorted((CLAUDE / 'commands').glob('*.md')):
            self.assertIn(f'| `/{path.stem}` |', commands, path.stem)

    def test_the_counts_in_the_prose_match(self):
        self.assertEqual(len(list((CLAUDE / 'hooks').glob('*.sh'))), 10)
        self.assertIn('Ten files live in `../hooks/`', DOC)
        self.assertEqual(len(list((CLAUDE / 'agents').glob('*.md'))), 7)
        self.assertIn('Seven personas live in', DOC)
        self.assertEqual(len(list((CLAUDE / 'commands').glob('*.md'))), 7)
        self.assertIn('Seven commands live in', DOC)


if __name__ == '__main__':
    unittest.main()
