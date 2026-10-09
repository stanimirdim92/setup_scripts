#!/usr/bin/env python3
"""Merge the harness's Codex settings into ~/.codex/config.toml.

`dotfiles/codex/config.toml` holds only what the harness manages: the sandbox,
the model, approvals, features and the MCP servers. The Codex app writes its
own state into ~/.codex/config.toml as well: trusted projects, desktop
preferences, plugins, marketplaces, hook trust hashes. While that file was a
symlink into this public repository, the app's state reached git, including
project paths and chat titles (ADR 0086).

So ~/.codex/config.toml is a local file. This script:
- turns a symlink at that path into a regular file with the same content;
- copies every top-level key and table of the base into it, replacing the
  local version of the same key or table;
- keeps every key and table the base does not name.

Usage:
    install-config.py            # merge, write when something changed
    install-config.py --check    # exit 1 when a merge would change the file
    install-config.py --lint     # exit 1 when the base holds machine state
"""
import argparse
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE / 'config.toml'
HEADER = re.compile(r'^\s*\[\[?[^\]]+\]\]?\s*(#.*)?$')
KEY = re.compile(r'^\s*([A-Za-z0-9_."-]+)\s*=')
# What the Codex app writes. None of it belongs in the committed base.
MACHINE_STATE = re.compile(r'^\[(projects|desktop|hooks\.state|marketplaces|plugins|tui)\b'
                           r'|^\[mcp_servers\.node_repl|/home/|/var/www/|atlassian\.net/browse', re.M)


def parse(text):
    """(preamble lines, {table header: lines}) with tables in file order."""
    preamble, tables, current = [], {}, None
    for line in text.splitlines():
        if HEADER.match(line):
            current = line.split('#')[0].strip()
            tables[current] = [line]
        elif current is None:
            preamble.append(line)
        else:
            tables[current].append(line)
    return preamble, tables


def strip_blank(lines):
    while lines and not lines[-1].strip():
        lines = lines[:-1]
    return lines


def merge(base, local):
    """The local file with every key and table of the base laid over it."""
    base_pre, base_tables = parse(base)
    local_pre, local_tables = parse(local)
    base_keys = {m.group(1) for m in map(KEY.match, base_pre) if m}
    pre = strip_blank(base_pre) + [l for l in strip_blank(local_pre)
                                   if not ((m := KEY.match(l)) and m.group(1) in base_keys)
                                   and l.strip() and not l.lstrip().startswith('#')]
    out = pre
    for name, lines in base_tables.items():
        out += [''] + strip_blank(lines)
    for name, lines in local_tables.items():
        if name not in base_tables:
            out += [''] + strip_blank(lines)
    return '\n'.join(out).lstrip('\n') + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--dest', type=Path, default=Path.home() / '.codex' / 'config.toml')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--lint', action='store_true')
    args = parser.parse_args(argv)
    base = BASE.read_text()

    if args.lint:
        hits = sorted({m.group(0) for m in MACHINE_STATE.finditer(base)})
        for hit in hits:
            print(f'install-config: {BASE.name} holds machine state: {hit}', file=sys.stderr)
        return 1 if hits else 0

    dest = args.dest
    linked = dest.is_symlink()
    local = dest.read_text() if dest.exists() else ''
    merged = merge(base, local)
    if not linked and merged == local:
        print(f'ok      {dest}')
        return 0
    if args.check:
        print(f'install-config: {dest} needs a merge' + (' (still a symlink)' if linked else ''))
        return 1
    if linked:
        dest.unlink()
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + '.tmp')
    tmp.write_text(merged)
    os.replace(tmp, dest)
    print(f'merged  {dest}' + (' (was a symlink into the repository; now a local file)' if linked else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
