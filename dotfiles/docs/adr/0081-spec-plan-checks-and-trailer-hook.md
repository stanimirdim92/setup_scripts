# Spec and plan checks, and a commit trailer hook

**Context.** This week added three rules as text only: EARS statements with
RFC 2119 keywords (ADRs 0075, 0076), `Refs:` and `Task:` trailers on ticket
commits (ADR 0073), and the forms /plan already promised (Requirement
Coverage, complete task packets). The writing rule showed what happens to a
text-only rule: ADRs ran at 23–38% long sentences until a check existed
(ADR 0077). A rule nothing checks drifts.

**Decision — /spec runs `check-spec.py` before it presents a spec.** It
fails on a missing header field, a malformed requirement heading, a repeated
id, a requirement without `Source:` or a complete GIVEN/WHEN/THEN scenario,
a requirement statement without an uppercase RFC 2119 keyword, and an
Approved spec with an OPEN QUESTION. EARS ordering, `If … then`, and a
SHOULD without its exception are warnings: they are usually slips, sometimes
fine. `--no-rfc` checks a spec written before ADR 0075.

**Decision — /plan runs `check-plan.py` before it presents a plan.** With
the spec and todo file, it fails when a spec requirement has no task, a task
names a requirement the spec lacks, a dependency names an undefined id, or a
packet lacks Status, Requirements, Acceptance criteria or Verification. A
packet without Files/areas likely touched is a warning: plan coverage cannot
score it.

Both scripts live in their skills, so they reach every project through
`~/.claude`, like the weakened-test guard. Neither runs a model.

**Decision — writers cannot commit without `Refs:`.**
`require-commit-trailers.sh` joins the executor's and test-engineer's
PreToolUse hooks, and the Codex adapter's writer hooks. It denies a commit
whose new message has no `Refs: <TICKET>` trailer. Commits that reuse a
message, or whose message it cannot read, are allowed. `Task:` is not
required, because review fixes have no task id. `validate-frontmatter.py`
now pins all three writer hooks.

This amends ADR 0073 on one point. A repository with its own ticket trailer
adds `Refs:` beside it, rather than using its key instead.

**Evidence the checks do not cry wolf.** `check-spec.py` passes the approved
LD-441 spec (with `--no-rfc`) and the EARS rewrite of LD-380 with no warning.
`check-plan.py` reads the approved LD-442 plan and todo correctly. Its only
failures there are the packet Status lines, a field added after that plan.

**Rejected.**
- *A git commit-msg hook in each project.* It needs installing per
  repository and also blocks human commits. The agent-scoped hook covers
  exactly the commits the harness makes.
- *Failing on EARS wording.* A deterministic check cannot tell a misplaced
  trigger from a relative clause ("the page where …"). A false failure would
  teach /spec to ignore the check.
