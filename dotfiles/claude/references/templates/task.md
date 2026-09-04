# Task Template

The canonical single-task shape used by `planning-and-task-breakdown` when
drafting behavioral tasks.
One task should be a bounded outcome that `/build` can hand to an executor
without copying the full spec or plan.

For a compact plan, use the same fields but omit empty optional entries and a
Description that merely repeats the title. Keep production changes and the
tests that prove their acceptance criteria in one delivery task; red/green is
an execution sequence, not two plan tasks. A separate test task needs
independently verifiable value before the production task.

```markdown
## T001: [Short descriptive title]

**Requirements:** [A delivery task names one or more `REQ-###` ids from the
approved spec. A spike names the `TD-###` it resolves plus the `REQ-###` ids it
unblocks. A task fitting neither is scope the spec never asked for — remove it,
or return a SPEC CONFLICT if the behavior is genuinely needed. `/build` passes
this line through to the executor verbatim.]

**Description:** [Omit when the title and acceptance criteria already state the
outcome; otherwise one short paragraph.]

**Acceptance criteria:**
[Each criterion traces to one of the requirements above.]
- [ ] [Specific, testable condition]
- [ ] [Specific, testable condition]

**Verification:**
- [ ] Tests pass: [the repository's focused-test command]
- [ ] Build/static check succeeds: [the repository's relevant command]
- [ ] Manual check: [include only when automation cannot prove the behavior]

**Dependencies:** [Stable task ids this depends on, or "None"]

**Workstream:** [Short stable name shared by related/dependent tasks — lets
`/build` resume one executor across later tasks instead of paying fresh
discovery cost for every task]

**Context pointers:** [Only what materially constrains this task; use file
references rather than copied documents]
- Project/module rules: `[path]` or "None"
- Closest precedent: `[path]` or "None"
- Shared contract/invariant: `[path or short named invariant]` or "None"

**Files/areas likely touched:**
- `src/path/to/file.ts`
- `tests/path/to/test.ts`

**Estimated scope:** [XS | S | M | L | XL — heuristic only, not a file-count gate]
```

Do not paste the full spec, full plan, whole rules files, or raw investigation
logs into `Context pointers`. The executor can read the referenced source when
needed.
