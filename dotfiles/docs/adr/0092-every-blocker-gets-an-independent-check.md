# Every BLOCKER gets an independent check

**Context.** A BLOCKER from one reviewer went straight to `/ship`. A false
BLOCKER cost a fix round or a refutation from the user. A true one marked
low-confidence waited for evidence nobody had gathered. Anthropic's Claude
Code team posts a finding only after independent verifiers vote that it is
real (claude.dev, "Solving code review at Anthropic", 2026-10).

**Decision.**
- `/review` gives each BLOCKER one check by a fresh reviewer that did not raise
  it: `code-reviewer` for a blind finding, `blind-reviewer` for a code-reviewer
  finding, and a fresh instance of the same specialist for a security or
  distributed-systems finding.
- The packet holds the diff and that one finding, nothing from the other
  reviewers. For `blind-reviewer`, any `REQ-###` or goal wording is removed
  first.
- The verdict is CONFIRMED, REFUTED or UNSURE, with `file:line` evidence.
  CONFIRMED sets the confidence to high. REFUTED keeps the BLOCKER, sets the
  confidence to low and attaches the evidence. UNSURE changes nothing.
- `/ship` may accept a REFUTED verdict's evidence as the refutation of a
  low-confidence BLOCKER. A high-confidence BLOCKER still needs a fix.
- In a later review round (ADR 0089), only new BLOCKERs are checked.

**Cost.** One extra reviewer run per BLOCKER, inside the two-concurrent limit.
One verifier is a cheaper check than Anthropic's vote; REQUIRED and ADVISORY
findings are not checked.
