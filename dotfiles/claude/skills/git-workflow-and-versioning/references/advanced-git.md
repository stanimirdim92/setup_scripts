# Advanced Git

Use this reference for rebase, merge, conflicts, cherry-pick, stash, reflog,
bisect, or recovery.

Preserve existing work before using any history-changing operation.

## Inspect First

Before advanced Git operations:

```bash
git status --short
git branch --show-current
git log --oneline --decorate -15
git remote -v
```

If the worktree contains unknown or unrelated changes, do not destroy, stage,
stash, or rewrite them.

## Merge vs Rebase

### Merge

Merge preserves existing commit identities and branch history.

Use merge when:

- the repository prefers merge commits
- multiple people or agents share the branch
- rewriting published history would be unsafe
- preserving the exact branch topology matters

Typical update:

```bash
git fetch origin
git merge origin/main
```

Use the actual base branch instead of assuming `main`.

### Rebase

Rebase rewrites commits onto a new base.

Use rebase when:

- the repository expects linear history
- the branch is private or safe to rewrite
- nobody else depends on the existing commit IDs

Typical update:

```bash
git fetch origin
git rebase origin/main
```

Do not rebase:

- protected/default branches
- already merged history
- shared branches without explicit approval
- commits other people or agents may have based work on

If a rewritten remote branch must be updated:

```bash
git push --force-with-lease
```

Never use plain `--force`.

## Before Rebase

A clean worktree is strongly preferred.

Do not automatically stash unrelated changes.

If the worktree is dirty, identify ownership first.

The safe sequence for task-owned changes is generally:

```text
finish logical change
→ verify
→ commit
→ fetch
→ rebase
```

Do not create artificial commits merely to make unrelated user work disappear
from `git status`.

## Conflict Resolution

When Git reports conflicts:

```bash
git status
```

For each conflicted file:

1. Read the conflicting sections.
2. Understand the intent of both versions.
3. Resolve deliberately.
4. Remove conflict markers.
5. Stage only the resolved file.
6. Continue the operation.
7. Re-run relevant tests/checks.

For rebase:

```bash
git add -- path/to/resolved-file
git rebase --continue
```

For merge:

```bash
git add -- path/to/resolved-file
git commit
```

Do not use `--ours` or `--theirs` for a whole file unless that result has been
established as correct.

To abandon an in-progress operation without discarding pre-existing work:

```bash
git rebase --abort
git merge --abort
git cherry-pick --abort
```

Use only the command matching the active operation.

## Cherry-Pick

Cherry-pick copies specific commits onto the current branch.

Inspect the commit first:

```bash
git show <commit>
```

Then:

```bash
git cherry-pick <commit>
```

Use cherry-pick when the task explicitly needs a specific existing change,
such as backporting a fix.

Do not cherry-pick merely to avoid understanding branch history.

Resolve conflicts with the same care as merge/rebase conflicts.

## Stash

Stash is useful for intentionally owned temporary work, but should not be used
as an automatic cleanup mechanism.

Inspect first:

```bash
git status --short
```

Create a named stash only for known work:

```bash
git stash push -m "WIP: <description>" -- path/to/file1 path/to/file2
```

Inspect existing stashes before applying:

```bash
git stash list
git stash show --stat stash@{0}
```

Prefer `apply` when preserving the stash is useful:

```bash
git stash apply stash@{0}
```

Do not drop a stash until its contents are known to be safely restored or no
longer needed.

## Reflog

Use reflog to locate recent branch/HEAD positions after accidental history
movement:

```bash
git reflog
```

Reflog is a diagnostic/recovery source. Do not immediately reset to an entry
without understanding what would be lost.

Prefer non-destructive recovery first, such as creating a branch:

```bash
git branch recovery/<description> <reflog-commit>
```

## Revert

For changes already published/shared, prefer `git revert` over rewriting
history.

```bash
git revert <commit>
```

This creates a new commit that reverses the selected commit.

Verify the resulting code before publishing it.

## Reset

Reset changes refs/index/worktree depending on mode.

Do not use destructive reset casually.

`--hard` may destroy uncommitted work:

```bash
git reset --hard <commit>
```

Use only when the discarded changes are known, owned by the current task, and
the destructive action is explicitly authorized.

For undoing a local commit while preserving changes, `--soft` may be
appropriate:

```bash
git reset --soft HEAD~1
```

Still confirm the commit is private and safe to rewrite.

## Clean

`git clean` deletes untracked files.

Never run destructive clean commands against unknown work:

```bash
git clean -fd
```

If cleanup is explicitly required, preview first:

```bash
git clean -nd
```

Then delete only understood paths.

## Bisect

Use bisect when a regression exists between a known-good and known-bad commit:

```bash
git bisect start
git bisect bad HEAD
git bisect good <known-good-commit>
```

Git selects midpoint commits.

Run the relevant reproduction/test at each step and mark:

```bash
git bisect good
git bisect bad
```

When finished:

```bash
git bisect reset
```

Automated bisect is useful when a deterministic test command exists:

```bash
git bisect run <test-command>
```

## Blame and History Search

Find the commit responsible for a line:

```bash
git blame path/to/file
```

Inspect recent history:

```bash
git log --oneline -20
git log -- path/to/file
```

Search commit messages:

```bash
git log --grep="keyword" --oneline
```

Inspect changes across commits:

```bash
git diff <old>..<new> -- path/to/file
```

Use history to understand intent, not to assign blame to people.

## Recovery Rule

When something goes wrong:

1. Stop changing history.
2. Inspect `git status`.
3. Inspect `git reflog`.
4. Identify which work is task-owned versus pre-existing.
5. Prefer creating a recovery branch over destructive reset.
6. Only discard work when the consequences are known.
