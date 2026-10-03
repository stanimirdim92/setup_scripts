# Writing rule checked in CI

**Context.** ADR 0069 added "Writing for humans" to `AGENTS.md`. A
descriptive sentence has 25 words or fewer, and the rule may break about 20%
of the time. Nothing measured it. ADRs written here after the rule still ran
long: 0074 had 38% long sentences and 0075 had 23%.

A first, quick measurement also showed how a check can mislead. It joined list
items without a full stop into one sentence. It reported the LD-380 spec at
28% long sentences, when the spec held 6%.

**Decision — `check-writing.py`.** The check counts the sentences in a
markdown file and fails when more than 20% run over 25 words.
- Prose paragraphs and list items count. Each list item is its own unit.
- Code blocks, tables, headings, front matter and HTML comments do not count.
- A token with no letter or digit is not a word.
- Sentences under four words do not count, so short labels cannot dilute the
  share.

`--max-words` and `--max-share` change the limits. `--show` lists each long
sentence with its line.

**Decision — scope.** CI checks ADRs from 0073 on. 57 of the 76 older ADRs
fail. They are dated records, and the ADR README forbids rewriting them.
Given files, the check measures anything, such as a project spec or plan.

**Rejected.**
- *Check every harness markdown file.* Commands, agents and skills are
  instructions for models, not prose for people. The rule does not cover them.
- *Fail on any sentence over 25 words.* The rule allows breaks on purpose.
- *A readability score (Flesch and similar).* It measures syllables, not the
  rule, and gives no line to fix.
