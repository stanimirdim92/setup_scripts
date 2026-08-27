# Independent VERIFY made risk-triggered, `/review` owns the decision

**Decision.** `/test` is no longer a mandatory stage. `/build` still owns
implementation-time verification; `/review` now evaluates the candidate against
the new `references/verification-triggers.md` and requires a VERIFY PASS only
when a trigger matches. The pipeline becomes:

```text
/spec -> /plan -> /build -> /review -> /ship
                        \
                         -> /test -> /review   (when required)
```

`/ship` consumes `/review`'s recorded verification status — `NOT REQUIRED` or
`PASS` — instead of hard-requiring `/test` for every change.

This partially supersedes [0020](0020-build-test-review-pipeline-split.md),
which made VERIFY an unconditional gate between BUILD and REVIEW. The separation
0020 established is kept: VERIFY is still independent of BUILD, still dispatches
`test-engineer` rather than the executor, and still cannot be satisfied by the
implementer's own claim. Only its *unconditional* status changes.
[0024](0024-vendored-test-engineer-persona-for-test-verify-gate.md) is unaffected
in substance — `test-engineer` remains the persona `/test` dispatches.

**Why.** The executor already implements test-first and runs the repository's
verification per `executor-development-discipline`. On an ordinary localized
change with green focused tests, `/test` spawned a fresh `test-engineer` that
repaid code and test discovery from zero to re-confirm what `/build` had already
evidenced. That is the most expensive kind of duplication: a fresh subagent
context, not a few extra lines of prompt.

The triggers preserve independent verification exactly where the implementer's
own evidence is least trustworthy: incomplete or blocked `/build` checks,
persistent-data migration or reinterpretation, security trust boundaries,
concurrency/retry/ordering/delivery semantics, shared contracts consumed
elsewhere, critical business flows, and bug fixes without a trustworthy
reproduction. The matrix defaults toward verification — "when uncertain whether a
material trigger matches, require `/test`."

**Rejected — keep VERIFY mandatory.** It is the safer default in the abstract,
but it charged a fresh verifier context to every documentation edit, formatting
change, and green refactor. Paying that on low-risk work does not make
high-risk work safer, and the cost was the single largest avoidable item in a
pipeline run.

**Rejected — let `/build` decide whether VERIFY is needed.** `/build` produced
the evidence in question. An implementer judging whether its own verification
was sufficient is the conflict of interest 0020 split the gates to remove.

**Rejected — let `/test` self-select when invoked.** By then the verifier
subagent has already been created, which is the cost being avoided. The decision
has to sit in a command that runs in the main context.

**Rejected — duplicate the trigger list into `/review`.** `reviewer-triggers.md`
already demonstrates the single-source pattern for dispatch conditions; a second
copy is the drift rule 6 exists to prevent. `/review` evaluates the file and is
explicitly told not to restate it.

**Revisit if** run metrics show triggered VERIFY firing on nearly every candidate
(the triggers are too broad, and the mandatory gate was simpler), or if defects
start reaching `/ship` on candidates recorded as NOT REQUIRED (the triggers are
too narrow). Judge this from `references/agent-run-metrics.md`, not from
prompt-size estimates.
