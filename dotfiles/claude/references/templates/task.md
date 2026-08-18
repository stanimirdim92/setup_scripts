# Task Template

The canonical single-task shape. Used by `planning-and-task-breakdown`'s
Step 4 (Write Tasks) — one of these per item in `tasks/todo.md`.

```markdown
## Task [N]: [Short descriptive title]

**Description:** One paragraph explaining what this task accomplishes.

**Acceptance criteria:**
- [ ] [Specific, testable condition]
- [ ] [Specific, testable condition]

**Verification:**
- [ ] Tests pass: [the repository's focused-test command]
- [ ] Build succeeds: [the repository's build command]
- [ ] Manual check: [description of what to verify]

**Dependencies:** [Task numbers this depends on, or "None"]

**Workstream:** [Short stable name shared by related/dependent tasks —
lets `/build` resume one executor across them instead of a fresh spawn
per task]

**Files likely touched:**
- `src/path/to/file.ts`
- `tests/path/to/test.ts`

**Estimated scope:** [Small: 1-2 files | Medium: 3-5 files | Large: 5+ files]
```
