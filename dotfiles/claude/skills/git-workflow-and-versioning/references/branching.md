# Branching Workflows

Use this reference when choosing or interpreting a repository branching model.

Repository-local conventions always win. Do not migrate a project to a
different branching model unless explicitly requested.

## Default Recommendation

For a new repository without established conventions, prefer trunk-based
development or GitHub Flow.

Both keep integration frequent and avoid long-lived branch divergence.

## Trunk-Based Development

Keep `main` always deployable. Work in short-lived feature branches that merge back within 1-3 days. Long-lived development branches are hidden costs — they diverge, create merge conflicts, and delay integration. DORA research consistently shows trunk-based development correlates with high-performing engineering teams.

Typical shape:

```text
main ──●──●──●──●──●──●──●──●──●──  (always deployable)
        ╲      ╱  ╲    ╱
         ●──●─╱    ●──╱    ← short-lived feature branches (1-3 days)
```

Guidelines:

- use very short-lived branches when branches are needed
- integrate frequently
- keep CI fast and trustworthy
- hide incomplete behavior behind feature flags when necessary
- avoid long-running feature branches

Best fit:

- continuous delivery
- strong automated testing
- teams comfortable integrating frequently

## GitHub Flow

GitHub Flow is a simple branch-and-PR model:

```text
main
 ├── feature/user-auth
 ├── feature/LD-329-classification
 └── fix/profile-image
```

Typical flow:

1. Branch from the default branch.
2. Make focused commits.
3. Push the branch.
4. Open a PR.
5. Review and verify CI.
6. Merge according to repository policy.
7. Delete the merged branch when appropriate.

Best fit:

- SaaS/web applications
- frequent releases
- teams using pull requests for review

## Gitflow

Use Gitflow only when the repository already uses it or release constraints
make its extra branches useful.

Typical model:

```text
main
 ├── hotfix/*
 └── develop
      ├── feature/*
      └── release/*
```

Roles:

- `main`: production releases
- `develop`: integration branch
- `feature/*`: branch from and merge into `develop`
- `release/*`: stabilize an upcoming release
- `hotfix/*`: urgent production fix from `main`

Release branches are normally merged back into both the production and
integration lines according to the project's workflow.

Costs:

- more branch management
- more merge paths
- greater divergence risk
- more complicated automation

Do not introduce `develop` merely because Gitflow is familiar.

## Release Branches Without Full Gitflow

A trunk-based project may still use temporary release branches when:

- a release must be stabilized while trunk continues moving
- multiple supported versions require patching
- regulatory or operational release gates require a frozen line

A release branch does not automatically imply Gitflow.

## Hotfixes

Follow the repository's current production-fix workflow.

Common patterns:

### Trunk/GitHub Flow

```text
main → fix/critical-issue → PR → main
```

### Gitflow

```text
main → hotfix/critical-issue
               ├──→ main
               └──→ develop
```

Do not assume a `hotfix/*` branch is required unless the repository uses that
convention.

## Branch Naming

Inspect existing remote branches first:

```bash
git branch -r
```

Follow the established pattern.

Fallback examples:

```text
feature/LD-329-social-classification
fix/LD-500-profile-image
hotfix/critical-auth-failure
release/1.4.0
chore/update-dependencies
refactor/advertiser-service
experiment/new-ranking-model
```

Ticket keys should be included when that is already repository/team practice.

## Choosing a Workflow

Prefer the simplest workflow that satisfies the project's release model.

Ask:

- Is the default branch expected to be deployable?
- Are deployments continuous or scheduled?
- Are multiple production versions supported?
- Does the team already use an integration branch?
- Are release branches required by existing automation?
- Are feature flags available?

Do not redesign the branching strategy during ordinary implementation work.
