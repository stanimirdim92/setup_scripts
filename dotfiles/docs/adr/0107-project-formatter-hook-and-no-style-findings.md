# The project's formatter formats; reviewers drop style

**Context.** Anthropic drops style, diagnostic and cleanup findings from its
review after A/B testing them (claude.dev, "Solving code review at
Anthropic", 2026-10, layer 2). In the harness, `code-reviewer` could still
raise naming and style as ADVISORY, and nothing ran the project's formatter
on what agents wrote. The owner agreed, with two conditions: "Adhere to
project lint and formatter if any", and it must work for their Python and
Rust projects too, so nothing may assume Laravel.

**Decision.**
- A PostToolUse hook, `format-edited-file.sh`, runs after every Edit or Write.
  It formats the one edited file with the project's own formatter, and only
  when the project declares it and has it installed. That covers Pint or
  PHP-CS-Fixer, Biome or Prettier, ruff or black, rustfmt with the crate's
  edition, and gofmt. It never installs or picks a default. It skips
  `vendor/`, `node_modules/` and `target/`, and a failing formatter leaves the
  file as written.
- The executor runs the project's linter and static analyser on changed files
  when the project defines them. It fixes what the change introduced and
  reports older errors as pre-existing. Where no hook runs (Codex), it runs
  the formatter too.
- Style is not a review finding: formatting, layout, import order, naming
  taste. A reviewer reports one only when the project's linter fails on a
  changed line or `REVIEW.md` asks. A misleading name is still a readability
  finding.

**Rejected — run `eslint --fix` or `ruff check --fix` in the hook.** Fixers
can change behavior. Linting stays an explicit, reported step.

**Cost.** One formatter run per edit, usually under a second. Projects
without a formatter pay nothing.
