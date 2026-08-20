---
name: git-workflow-and-versioning
description: "Git workflow safety and version-control discipline. Use when making code changes, creating branches, staging, committing, pushing, rebasing, resolving conflicts, using worktrees, or preparing releases. Follow repository conventions first; preserve existing work; never rewrite or discard unknown work."
---

# Git Workflow and Versioning

Git is the safety boundary around code changes.

Use small, reviewable changes, preserve existing work, and follow the current
repository's conventions before applying global defaults.

## Repository Conventions First

Before creating branches, staging, or committing, inspect the repository.

Check:

- project instructions (`CLAUDE.md`, `AGENTS.md`, etc.)
- current branch
- default/base branch
- existing local and remote branch names
- recent commit messages
- current worktree state
- configured remotes

Useful commands:

```bash
git status --short
git branch --show-current
git branch -a
git log -10 --oneline
git remote -v
```

Project-local conventions override this skill.

Do not introduce a new branch naming, commit message, merge, or release
convention when the repository already has one.

If no clear convention exists, use the defaults in this skill.

## Preserve Existing Work

Treat pre-existing modifications as user-owned or belonging to another agent
unless this task created them.

Before staging, switching branches, rebasing, resetting, cleaning, or removing
a worktree:

```bash
git status --short
git branch --show-current
```

Never discard, overwrite, stage, stash, commit, or otherwise modify unrelated
work.

Do not use destructive recovery commands on unknown changes:

```bash
git reset --hard
git clean -fd
git checkout -- .
git restore .
```

Only discard changes when they are known to belong to the current task and the
user explicitly requested or approved the destructive action.

## Branching

Follow the repository's existing branching model.

For a new repository with no established workflow, prefer trunk-based /
GitHub Flow:

- keep the default branch deployable
- use short-lived feature/fix branches
- merge through the repository's normal review process
- prefer feature flags over long-lived branches

Do not introduce Gitflow, `develop`, release branches, or another branching
model into an existing repository unless the project requires it.

### Branch Naming

Match existing branch names first.

If ticket keys are normally included, preserve them.

Fallback examples only:

```text
feature/LD-329-social-classification
fix/LD-500-profile-image
chore/update-dependencies
refactor/advertiser-service
```

Do not create or switch branches when doing so would risk unrelated
uncommitted work.

For detailed branching models, see `references/branching.md`.

## Atomic Changes

Each commit should contain one logical, independently understandable change.

Prefer:

```text
Implement slice → Verify → Commit → Next slice
```

Avoid:

```text
Implement everything → One giant mixed commit
```

Separate independently reviewable concerns such as:

- behavior changes
- refactors
- formatting-only changes
- dependency/tooling changes
- unrelated fixes

Small cleanup required directly by the change may stay with it.

Size commits by logical responsibility, not arbitrary line count.

Split when changes are independently reviewable or independently revertible.

## Staging

Inspect changes before staging:

```bash
git status --short
git diff
```

Stage only files belonging to the current logical commit:

```bash
git add -- path/to/file1 path/to/file2
```

Then inspect exactly what will be committed:

```bash
git diff --staged
```

Do not use:

```bash
git add .
git add -A
git add --all
```

when unrelated worktree changes may exist.

Never stage changes merely because they are present in the worktree.

## Commit Messages

Follow the repository's existing commit convention.

Inspect recent commits before composing the first message:

```bash
git log -10 --oneline
```

If there is no clear convention, use Conventional Commits:

```text
<type>[scope]: <description>
```

Fallback types:

- `feat`
- `fix`
- `docs`
- `style`
- `refactor`
- `perf`
- `test`
- `build`
- `ci`
- `chore`
- `revert`

Breaking changes may use:

```text
feat!: change public API contract
```

or a:

```text
BREAKING CHANGE:
```

footer.

Commit messages should explain intent and, when useful, why the change exists.

Avoid vague messages such as:

```text
fix
update
misc
changes
```

## Pre-Commit Verification

Before committing:

1. Inspect `git diff --staged`.
2. Verify only intended files are staged.
3. Run the project's required quality gates.
4. Confirm those commands actually passed.
5. Check the staged diff for secrets or sensitive data.

Discover verification commands from project sources such as:

- `CLAUDE.md` / `AGENTS.md`
- package scripts
- `composer.json`
- `pyproject.toml`
- Makefile / Taskfile
- CI configuration
- project documentation

Do not substitute generic commands such as `npm test` or `pytest` without
first confirming that they are appropriate for the project.

Never say a change is tested, verified, passing, or working unless the relevant
command was actually run successfully in this session.

If verification was not run, say so.

## Commit and Push Authorization

Commits are local but still modify repository history. Pushes publish work to
the remote and may trigger CI, deployments, or collaborator workflows.

### Local IDE session

Ask before every commit and push.

Wait for explicit approval.

### Claude app / Claude Code on the web

Commits and normal pushes may proceed without asking when the surrounding
workflow already authorizes publishing changes.

Do not infer authorization for destructive history rewriting.

### Protected/default branches

Do not directly push to the default or protected branch unless that is the
repository's explicit workflow and the user has authorized it.

Never force-push the default or protected branch as part of normal work.

## Shared History

Before rebasing, amending, or otherwise rewriting commits, determine whether
the history may already be shared.

Rebase is normally safe when:

- the branch is local/private
- no other contributor or agent depends on its commits
- the repository workflow expects rebasing

Do not rewrite shared history without explicit approval.

When updating from the remote:

```bash
git fetch
```

Then use merge or rebase according to the repository's established workflow.

If rewritten remote history must be pushed, use:

```bash
git push --force-with-lease
```

Never use:

```bash
git push --force
```

For rebase, merge, conflict resolution, cherry-pick, stash, reflog, bisect,
and recovery patterns, see `references/advanced-git.md`.

## Conflict Resolution

Do not resolve conflicts mechanically.

For each conflict:

1. Understand both sides.
2. Preserve the intended behavior from each where compatible.
3. Resolve the file deliberately.
4. Inspect the resulting diff.
5. Run relevant verification again.

Do not automatically choose `ours` or `theirs` across a file unless the
correct result is established.

Do not discard unrelated changes while resolving conflicts.

## Worktrees

Use worktrees when parallel agents or independent workstreams need isolated
branches.

Before creating or removing one:

```bash
git worktree list
```

Rules:

- one active branch per worktree
- do not reuse another agent's worktree
- do not remove a worktree with unknown changes
- verify `git status --short` inside the worktree before removal
- never force-remove a worktree to discard unknown work

Prefer worktrees over repeated branch switching when several agents are
working concurrently.

See `references/worktrees.md` for detailed patterns.

## Generated Files

Commit generated files only when the repository expects them.

Examples that may belong in Git:

- lockfiles
- migrations
- generated schemas/contracts explicitly tracked by the project

Do not assume generated build output belongs in Git.

Follow the repository's `.gitignore` and existing tracked-file conventions.

Never commit:

- secrets
- private keys
- environment credentials

unless the repository explicitly contains safe templates/placeholders rather
than real credentials.

## Change Summary

Before asking for commit approval, and at final handoff when relevant, provide
a concise summary:

```text
CHANGES
- what changed

VERIFICATION
- commands actually run and their result

NOT INCLUDED
- relevant nearby work deliberately left out, when useful

CONCERNS
- unresolved risks or follow-up items, if any
```

Do not claim verification that did not occur.

Avoid narrating every intermediate edit.

## Release and Versioning

Release/versioning guidance is not needed for normal code changes.

When the task involves:

- semantic versioning
- version bumps
- tags
- changelogs
- release branches
- release preparation
- breaking-change version decisions

load `references/releases.md`.

## Advanced Topics

Load references only when relevant:

| Reference | Use for |
|---|---|
| `references/branching.md` | trunk-based, GitHub Flow, Gitflow, release/hotfix branch models |
| `references/advanced-git.md` | rebase, merge, conflicts, cherry-pick, stash, reflog, bisect, recovery |
| `references/worktrees.md` | parallel agents, worktree creation, isolation, cleanup |
| `references/releases.md` | SemVer, tags, changelogs, release/versioning workflow |

Do not load advanced references for routine staging or committing.

## Hard Safety Rules

Never:

- discard unknown or unrelated work
- stage unrelated files
- commit secrets knowingly
- use `git add .` as a shortcut around scope inspection
- use `git reset --hard` or `git clean -fd` on unknown work
- rewrite shared history without approval
- use plain `git push --force`
- force-push a protected/default branch as normal workflow
- claim tests or verification passed when they were not run
- invent repository branch or commit conventions without checking existing ones

When uncertain whether a Git action could destroy or publish someone else's
work, stop before performing that action.
