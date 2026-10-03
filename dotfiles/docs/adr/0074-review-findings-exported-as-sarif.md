# Review findings exported as SARIF

**Context.** `/review` reports findings in markdown: an id, the reviewer's
native severity, the canonical disposition (ADR 0033), confidence, file:line,
and the requirement it bears on. The report is the gate artifact `/ship`
reads. No tool can read it: findings cannot appear as annotations in an
editor or on GitHub, and they cannot be compared across runs without parsing
prose.

**Decision — keep the dispositions, add a SARIF level.** BLOCKER, REQUIRED and
ADVISORY stay: they carry release rules that SARIF has no words for (a
REQUIRED finding can be accepted as risk; a suspected BLOCKER can be refuted).
Each maps one to one onto a SARIF 2.1.0 `level`: BLOCKER → `error`, REQUIRED →
`warning`, ADVISORY → `note`. The column is in both disposition tables.

**Decision — `/review` writes a SARIF file.** Next to its report, `/review`
writes every finding to
`"$(git rev-parse --git-common-dir)/review/<TICKET>-<short HEAD>.sarif"`:
outside the working tree, never committed, the same place pattern as
`/explain`. One run per reviewer; the finding id is the `ruleId`; native
severity, disposition, confidence, requirement and resolution go in
`properties`, so nothing in the markdown is lost. The shape is in
`component-response-contracts.md` §Review SARIF. The markdown report stays the
gate artifact.

SARIF is the OASIS format that GitHub code scanning, the VS Code SARIF viewer
and most static analysers read and write.

**Rejected.**
- *Replace the dispositions with SARIF levels.* It loses the release rules
  above and changes every reviewer, `/review`, `/ship` and their tests for no
  gain over a mapping.
- *Make the SARIF file the gate artifact.* `/ship` and the human read the
  markdown; JSON is worse for both.
