# Git Worktrees for Parallel Work

Use this reference when multiple agents or independent workstreams need
isolated branches.

Worktrees allow multiple branches from the same repository to be checked out
at the same time without repeated branch switching.

## Inspect Existing Worktrees

Always start with:

```bash
git worktree list
```

Do not assume a directory is unused.

Each worktree may contain work owned by another human or agent.

## Create a Worktree

First inspect branches and repository status:

```bash
git status --short
git branch -a
git worktree list
```

Create a new branch and worktree:

```bash
git worktree add -b feature/LD-329-social-classification \
  ../project-LD-329 \
  <base-branch>
```

Or attach an existing branch:

```bash
git worktree add ../project-LD-329 feature/LD-329-social-classification
```

Use the repository's actual base branch and naming convention.

## Ownership

Treat each active worktree as independently owned.

Rules:

- do not edit files in another agent's worktree
- do not switch its branch
- do not stage or commit its changes
- do not delete or prune it while work may still be active
- do not reuse a path because its name looks stale

When coordination is needed, identify the branch/path explicitly.

## Branch Isolation

A branch can normally be checked out in only one worktree at a time.

Use a separate branch for each independent task.

Good:

```text
project/
project-LD-329/   → feature/LD-329-social-classification
project-LD-500/   → fix/LD-500-profile-image
```

Avoid multiple agents sharing one branch unless the workflow explicitly
coordinates them.

## Before Working

Inside the worktree:

```bash
git status --short
git branch --show-current
```

Confirm:

- expected branch
- expected path
- no unknown pre-existing changes

Do not "clean up" unexpected changes automatically.

## Synchronizing With Base

Follow repository conventions.

A common private-branch workflow:

```bash
git fetch origin
git rebase origin/main
```

A merge-based workflow may instead use:

```bash
git fetch origin
git merge origin/main
```

Use the actual base branch.

Do not rebase shared branch history without approval.

## Parallel Agents

Worktrees are preferable when multiple build agents operate concurrently
because they isolate:

- index/staging area
- checked-out branch
- uncommitted files
- build/test artifacts in the project directory

Shared external resources may still conflict, including:

- databases
- ports
- Docker container names
- caches
- generated global files

Worktree isolation does not automatically isolate runtime infrastructure.

## Finish a Worktree

Before cleanup:

```bash
cd ../project-LD-329
git status --short
git branch --show-current
```

Confirm there is no uncommitted or untracked work that must be preserved.

Then return to another directory before removing it:

```bash
cd ../project
git worktree remove ../project-LD-329
```

Do not use forced removal to bypass unknown changes.

## Pruning

After worktrees have been intentionally removed, stale metadata may be cleaned
with:

```bash
git worktree prune
```

Inspect `git worktree list` first.

Do not prune as a substitute for understanding active worktrees.

## Branch Cleanup

After a branch is merged and no longer required:

```bash
git branch -d feature/LD-329-social-classification
```

Use safe delete (`-d`) by default.

Do not use `-D` merely because Git says the branch is unmerged.

Remote branch deletion should follow project/user authorization:

```bash
git push origin --delete feature/LD-329-social-classification
```

## Failure Recovery

If a worktree contains unexpected changes:

1. Do not remove it.
2. Inspect `git status --short`.
3. Inspect its branch.
4. Determine ownership.
5. Preserve unknown work.

If a worktree path disappears unexpectedly, inspect:

```bash
git worktree list
git worktree prune --dry-run
```

before changing metadata.

## Multi-Agent Rule

A worktree is an isolation boundary, not disposable scratch space.

Never destroy or repurpose another agent's worktree just to simplify the
current task.
