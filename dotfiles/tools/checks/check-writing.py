#!/usr/bin/env python3
"""Fail when too many prose sentences in a file are longer than the writing rule allows.

dotfiles/claude/AGENTS.md "Writing for humans" keeps a descriptive sentence
to 25 words or fewer, and allows a break about 20% of the time. Nothing checked
it: ADRs written in this repository after the rule landed still ran from 23% to
38% long sentences (ADRs 0074, 0075). ADR 0077.

What counts as a sentence: prose and list items. Code blocks, tables,
headings, front matter and HTML comments are skipped. A list item is its own
unit even when it has no full stop, and a wrapped line joins the item or
paragraph it continues. Words are whitespace-separated tokens; a token with no
letter or digit (an arrow, a dash, a middot) is not a word. Sentences under
four words are left out of the count, so a list of short labels cannot dilute
the share.

Default scope: ADRs numbered FIRST_CHECKED_ADR and later. Older ADRs are dated
records written before the rule, and the ADR README forbids rewriting them.
Pass paths to check anything else, such as a project spec or plan.

Usage:
    python3 dotfiles/tools/checks/check-writing.py            # the checked ADRs
    python3 dotfiles/tools/checks/check-writing.py FILE...    # any markdown files
    python3 dotfiles/tools/checks/check-writing.py --show FILE  # list the long sentences
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADR_DIR = ROOT / 'docs' / 'adr'
FIRST_CHECKED_ADR = 73
MAX_WORDS = 25
MAX_SHARE = 0.20
MIN_WORDS = 4

LIST_ITEM = re.compile(r'^(?:[-*+]|\d+[.)])\s+')
SENTENCE_END = re.compile(r'(?<=[.!?])["\')\]*_`]*\s+')
WORD = re.compile(r'[A-Za-z0-9]')


def units(text):
    """[(line, text)]: each paragraph and list item, wrapped lines joined."""
    text = re.sub(r'<!--.*?-->', lambda m: '\n' * m.group().count('\n'), text, flags=re.S)
    lines = text.split('\n')
    if lines and lines[0].strip() == '---':
        end = next((i for i, l in enumerate(lines[1:], 1) if l.strip() == '---'), 0)
        lines = [''] * (end + 1) + lines[end + 1:]
    out, cur, start, fence = [], [], 0, None
    def flush():
        if cur:
            out.append((start, ' '.join(cur)))
            cur.clear()
    for n, raw in enumerate(lines, 1):
        s = raw.strip()
        if fence:
            if s.startswith(fence):
                fence = None
            continue
        m = re.match(r'(`{3,}|~{3,})', s)
        if m:
            flush()
            fence = m.group(1)
            continue
        s = re.sub(r'^(?:>\s?)+', '', s)
        if not s or s.startswith(('|', '#')) or re.fullmatch(r'[-*_=\s]{3,}', s):
            flush()
            continue
        if LIST_ITEM.match(s):
            flush()
            s = LIST_ITEM.sub('', s)
        if not cur:
            start = n
        cur.append(s)
    flush()
    return out


def sentences(text):
    """[(line, word count, sentence)] for every sentence of MIN_WORDS words or more."""
    found = []
    for line, unit in units(text):
        for s in SENTENCE_END.split(unit):
            words = sum(1 for t in s.split() if WORD.search(t))
            if words >= MIN_WORDS:
                found.append((line, words, s.strip()))
    return found


def measure(text, max_words=MAX_WORDS):
    """(sentences, long sentences)."""
    all_ = sentences(text)
    return all_, [s for s in all_ if s[1] > max_words]


def default_files():
    files = []
    for path in sorted(ADR_DIR.glob('[0-9][0-9][0-9][0-9]-*.md')):
        if int(path.name[:4]) >= FIRST_CHECKED_ADR:
            files.append(path)
    return files


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('files', nargs='*', type=Path)
    parser.add_argument('--max-words', type=int, default=MAX_WORDS)
    parser.add_argument('--max-share', type=float, default=MAX_SHARE,
                        help='largest allowed share of long sentences, 0-1 (default %(default)s)')
    parser.add_argument('--show', action='store_true', help='list every long sentence, also in passing files')
    args = parser.parse_args(argv)

    files = args.files or default_files()
    failed = 0
    for path in files:
        all_, long = measure(path.read_text(encoding='utf-8'), args.max_words)
        share = len(long) / len(all_) if all_ else 0.0
        bad = share > args.max_share
        failed += bad
        try:
            name = path.resolve().relative_to(ROOT.parent)
        except ValueError:
            name = path
        if bad or args.show:
            print(f'{"FAIL" if bad else "ok  "} {name}: {len(long)} of {len(all_)} sentences over '
                  f'{args.max_words} words ({share:.0%}, limit {args.max_share:.0%})')
            for line, words, s in long:
                print(f'       {name}:{line} ({words} words) {s[:100]}{"…" if len(s) > 100 else ""}')
    if failed:
        print(f'check-writing: {failed} file(s) over the limit. Split the sentences, or put '
              'parallel items in a list (dotfiles/claude/AGENTS.md "Writing for humans").', file=sys.stderr)
        return 1
    if not args.show:
        print(f'check-writing: {len(files)} file(s) within the limit')
    return 0


if __name__ == '__main__':
    sys.exit(main())
