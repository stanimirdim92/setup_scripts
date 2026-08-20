# Releases and Versioning

Use this reference when the task involves versions, tags, changelogs, release
branches, release preparation, or breaking-change version decisions.

Follow project-specific release conventions first.

## Determine the Existing Release Model

Inspect:

- existing tags
- changelog format
- version files
- package metadata
- release automation
- CI/CD workflows
- release branches
- project instructions

Useful commands:

```bash
git tag --sort=-version:refname | head
git log --oneline -20
git branch -a
```

Do not introduce SemVer, changelog formats, or release branches when the
project already follows a different established scheme.

## Semantic Versioning

When a project uses Semantic Versioning:

```text
MAJOR.MINOR.PATCH
```

Meaning:

- `MAJOR` — incompatible/breaking consumer-visible change
- `MINOR` — backward-compatible functionality
- `PATCH` — backward-compatible bug fix

Examples:

```text
1.4.2 → 1.4.3   patch
1.4.2 → 1.5.0   minor
1.4.2 → 2.0.0   major
```

Version based on observable compatibility, not diff size.

A small code change may still be breaking.

## Breaking Changes

Treat a change as potentially breaking when consumers must modify behavior,
configuration, integration code, stored data, or expectations to upgrade.

Examples:

- removing or renaming a public API
- changing request/response contracts incompatibly
- changing persisted schema without compatible migration
- changing required configuration
- changing behavior consumers explicitly rely on

When uncertain, inspect the project's compatibility policy before selecting a
version bump.

## Conventional Commits and Versions

If the project derives releases from Conventional Commits, common mappings are:

```text
fix       → PATCH
feat      → MINOR
BREAKING  → MAJOR
```

Other commit types normally do not imply a release bump by themselves.

Use the repository's actual release tooling as the source of truth.

## Tags

A release tag identifies an immutable commit.

Typical annotated tag:

```bash
git tag -a v1.4.0 -m "Release 1.4.0"
```

Inspect before publishing:

```bash
git show v1.4.0
```

Publishing a tag changes the remote and may trigger deployment/release
automation:

```bash
git push origin v1.4.0
```

Do not push release tags without the authorization required by the surrounding
workflow.

Do not move or recreate published release tags casually.

## Tag Naming

Follow existing tags.

Examples:

```text
v1.4.0
1.4.0
release-1.4.0
2026.08.20
```

Do not introduce a `v` prefix or different scheme if the repository already
uses another convention.

## Version Source of Truth

Prefer one authoritative version source.

Depending on the project, that may be:

- Git tag
- package manifest
- generated build metadata
- release automation

Do not hand-edit multiple version locations independently unless the project
requires it.

If automation derives the version from tags, do not duplicate manual version
state unnecessarily.

## Changelog

A changelog is consumer-facing release documentation, not a raw `git log`.

When the project maintains a changelog, describe impact rather than internal
implementation details.

A common format:

```markdown
## [1.4.0] - YYYY-MM-DD

### Added
- ...

### Changed
- ...

### Fixed
- ...

### Deprecated
- ...

### Removed
- ...

### Security
- ...
```

Use only categories relevant to the release.

Follow the repository's existing changelog format before adopting this one.

## Changelog Content

Include items consumers need to know:

- new capabilities
- behavior changes
- bug fixes with user impact
- deprecations
- removals
- security changes
- migration requirements

Avoid dumping every internal refactor or test-only change.

Breaking changes should include migration guidance when the repository's
release process expects it.

## Release Branches

Do not create release branches unless the repository's release process uses
them.

A release branch may be useful when:

- an upcoming release must stabilize while trunk continues
- multiple maintained versions require backports
- formal release validation happens on a frozen branch

Typical naming:

```text
release/1.4.0
```

Follow existing naming and merge-back rules.

For full branching models, see `branching.md`.

## Hotfix Releases

Production fixes should follow the repository's current hotfix model.

Possible patterns:

```text
main → fix/... → PR → main
```

or, in Gitflow-style repositories:

```text
main → hotfix/... → main + develop
```

Do not invent a hotfix branch model during an incident.

## Release Verification

Before calling a release ready, confirm the project's required gates.

Possible checks include:

- tests
- lint/static analysis
- build/package generation
- migration validation
- security checks
- changelog validation
- version consistency
- CI status

Do not claim a release is verified unless those checks actually ran
successfully.

## Release Checklist

When applicable:

- [ ] version matches compatibility impact
- [ ] expected release commit is identified
- [ ] working tree contains no accidental release changes
- [ ] required tests/checks passed
- [ ] changelog/release notes follow project conventions
- [ ] migration notes exist for breaking changes
- [ ] tag name matches repository conventions
- [ ] published tag points to the intended commit

## Published History

Release commits and tags are shared history.

Do not:

- rewrite published release commits casually
- move published tags without explicit approval
- delete remote release tags as routine cleanup
- force-push protected release branches

Prefer corrective commits/releases over rewriting artifacts consumers may
already depend on.
