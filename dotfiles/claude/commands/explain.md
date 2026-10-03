---
description: Render a built candidate as one HTML review page — requirement trace, touched modules, findings, rollback — from existing artifacts only
argument-hint: "[ticket, commit range, or candidate; defaults to the current ticket branch]"
---

`/explain` makes one self-contained HTML page that helps a person review a
candidate. It is a reading aid, not a gate.

- It reads artifacts that already exist. It does not dispatch personas.
- It does not judge the change, run tests, or produce new findings.
- It does not change the candidate. The page goes outside the working tree.

Use it after `/build` or `/review`, before a person reads the diff. A page made
before `/review` shows "not reviewed" in the review sections.

## 1. Resolve the candidate

Resolve the target per `../references/target-selection.md`. Announce it
("Using: <target>") before anything else.

Record the repository root, branch, base revision, HEAD, commit range, and
working-tree state. If the tree is dirty, say so on the page. Do not commit,
stash, or clean anything to make it clean.

## 2. Collect the sources

Read each source from disk or from the current conversation. Re-read files even
if they appeared earlier; the user may have edited them.

| Source | Gives the page |
| --- | --- |
| `docs/specs/[TICKET]-SPEC.md` | goal, `REQ-###` list, Change Impact, Capability Map |
| `docs/tasks/[TICKET]-plan.md`, `docs/tasks/[TICKET]-todo.md` | tasks, their `REQ` ids, planned files, status |
| `git log` and `git diff --stat` over the range | commits, changed files, line counts |
| `/build` completion message in this conversation | per-task verification commands and outcomes |
| `/review` completion message in this conversation | findings with dispositions, blind-reviewer's "What this change appears to do", per-requirement evidence |
| `/test` and `/ship` completion messages, if present | VERIFY result, rollback plan, decision |

A completion message counts only per `../references/target-selection.md`
§Gate handoffs: in this conversation, or supplied in full by the user. Never
reconstruct a missing message from memory or from a summary.

A missing source is not an error. Show its section as "not available" and name
the stage that produces it.

## 3. Build the page

Write one HTML file. Inline all CSS and SVG. Load no scripts and no remote
assets, so the page opens offline and from a file URL.

Put these sections in this order:

1. **Header**: ticket, branch, commit range, HEAD, working-tree state, and the
   time the page was made.
2. **Goal next to behavior**: the spec's goal on the left. Blind-reviewer's
   "What this change appears to do" on the right, verbatim. If they disagree,
   show the disagreement. Do not resolve it.
3. **Requirement trace**: one row per `REQ-###`. Columns: requirement, task(s),
   changed files, verification evidence, review evidence. Mark a missing cell
   "missing". Do not fill it with a guess.
4. **Touched modules**: an inline SVG. One box per top-level module or
   directory the diff touches, sized by changed lines. Draw an edge only where
   the spec's Change Impact or the plan's change surface names a dependency.
   Do not infer edges from imports you did not read.
5. **Changed files**: grouped by module, with `+`/`-` counts. Mark a file as
   "unplanned" when no task's `Files/areas likely touched` covers it.
6. **Findings**: every open finding with its disposition (BLOCKER, REQUIRED,
   ADVISORY), id, file, and one-line claim. Resolved findings go in a closed
   `<details>` element.
7. **Rollback and decision**: the `/ship` rollback plan and decision, or
   "not shipped".

Copy text from sources verbatim where the section says so. Elsewhere, write
plain, short sentences (`AGENTS.md` §Writing for humans). Escape every
inserted string as HTML.

Write the file to:

```bash
"$(git rev-parse --git-common-dir)/explain/<TICKET>-<short HEAD>.html"
```

That directory is inside git's own metadata. It survives the session, it is
shared by all worktrees, and it never shows in `git status`.

## 4. Report

Return:

```markdown
## Explain: <path to the HTML file>

- Candidate: <branch> <range> (<clean | dirty>)
- Sources used: <list>
- Not available: <section — the stage that produces it>
- Gaps shown on the page: <REQ ids with a missing cell, unplanned files>
```

Then stop. The page is not evidence for any gate. `/ship` still reads the
`/review` handoff, never the page.
