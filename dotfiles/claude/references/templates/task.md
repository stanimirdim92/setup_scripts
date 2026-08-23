# Task Template

The canonical single-task shape used by `planning-and-task-breakdown` Step 5.
One task should be a bounded outcome that `/build` can hand to an executor
without copying the full spec or plan.

```markdown
## Task [N]: [Short descriptive title]

**Description:** One paragraph explaining the outcome this task delivers.

**Acceptance criteria:**
- [ ] [Specific, testable condition]
- [ ] [Specific, testable condition]

**Verification:**
- [ ] Tests pass: [the repository's focused-test command]
- [ ] Build/static check succeeds: [the repository's relevant command]
- [ ] Manual check: [only when automation cannot prove the behavior]

**Dependencies:** [Task numbers this depends on, or "None"]

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
