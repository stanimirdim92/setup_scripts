# Supply-Chain Security Reference

Package-manager-specific companion to `security-checklist.md`.

> Point-in-time operational details change quickly. Always corroborate commands and defaults against the **pinned package-manager version's official documentation** before relying on them.

## Find the Installation Boundary First

If the package is matched by a parent `workspaces` declaration, use that workspace root. Otherwise use the nearest project root that owns both its manifest and dependency graph.

At that boundary, corroborate:

1. `packageManager` / toolchain metadata when present.
2. The committed lockfile.
3. CI installs commands.

Stop if they disagree or if competing package-manager lockfiles exist at the same installation boundary. A nested project is independent only when it is outside the parent workspace; independent subprojects may legitimately use different package managers.

## Frozen / Immutable CI Installs

| Manager/version signal | Frozen/immutable CI install | Known-advisory audit |
|---|---|---|
| npm (`package-lock.json` / `npm-shrinkwrap.json`) | `npm ci` | `npm audit` |
| pnpm | `pnpm install --frozen-lockfile` | `pnpm audit` |
| Yarn 2+ | `yarn install --immutable` | `yarn npm audit -A -R` |
| Yarn 1 | `yarn install --frozen-lockfile` | `yarn audit` |

For an unlisted manager/version, use its official documentation rather than substituting another manager's commands or newer defaults.

## Install-Script Gate

Never discover dependency lifecycle scripts by first executing an ordinary install on a client whose defaults have not been verified.

1. Bootstrap with dependency scripts disabled, or with a documented default-deny policy plus fail-closed enforcement.
2. Inspect the exact script source and package version before approval.
3. Record the narrowest native allow/deny policy at the installation boundary and commit it.
4. Run a clean frozen/immutable install with that policy and verify required packages still build.

## Point-in-Time Native Policies

The table below preserves the reviewed behavior from the original checklist. Re-check it whenever the pinned package manager changes.

| Manager version | Native policy |
|---|---|
| npm without verified granular approvals | Bootstrap with `npm ci --ignore-scripts`, or persist `ignore-scripts=true` when project-wide blocking is intended. Keep scripts disabled or deliberately upgrade before allowing any reviewed dependency script. |
| npm 11.18.x (verified on 11.18.0) | Unreviewed dependency scripts run with a warning by default. Enforce `strict-allow-scripts=true` before a normal install, then use the workspace-unaware `npm install-scripts ls` from the installation boundary; keep approvals version-pinned and denials name-wide. |
| npm 12.x (verified on 12.0.1) | Unreviewed dependency scripts are skipped by default; `strict-allow-scripts=true` makes their presence fail the install before execution. Use the same `npm install-scripts` review and approval flow. |
| pnpm 11+ | Use `pnpm approve-builds` and commit `allowBuilds` decisions; `strictDepBuilds` defaults to `true`, so unreviewed builds fail. |
| pnpm 10.26–10.x | Configure `allowBuilds` explicitly, or use `pnpm approve-builds` with the legacy `onlyBuiltDependencies` / `ignoredBuiltDependencies` lists. Set `strictDepBuilds: true`; its v10 default is `false`. |
| pnpm 10.1–10.25 | `pnpm approve-builds` records the legacy lists; enable `strictDepBuilds` where supported (10.3+). |
| Older/unknown pnpm | Bootstrap with `pnpm install --frozen-lockfile --ignore-scripts`. Keep scripts disabled unless the pinned version documents an enforceable policy. |
| Yarn 4.14+ | Dependency postinstalls are disabled by default. Grant only required exceptions with top-level `dependenciesMeta.<package>.built: true`. |
| Yarn 2–4.13 | Set `enableScripts: false` in `.yarnrc.yml`, then grant only required exceptions with top-level `dependenciesMeta.<package>.built: true`; do not enable scripts globally. |
| Yarn 1 | Bootstrap with `yarn install --ignore-scripts`; keep scripts disabled unless each required exception is reviewed under the pinned client's documented workflow. |

## Supply-Chain Review Checklist

- [ ] One authoritative lockfile per installation boundary
- [ ] CI never silently rewrites the lockfile
- [ ] Lifecycle scripts blocked/reviewed before first execution
- [ ] Critical/high advisory findings triaged for reachability
- [ ] Deferrals have owner, reason, and review date
- [ ] Forced audit remediation is never automatic without reviewing diffs/changelogs
- [ ] Registry signatures/provenance verified where supported
- [ ] New dependencies reviewed for ownership, maintenance, release age/history, provenance, transitive graph, and typosquatting
- [ ] CI actions/build plugins pinned and reviewed
- [ ] Base images pinned/scanned
- [ ] Production artifacts have provenance/SBOM where required

## Authoritative Documentation

- npm install scripts: https://docs.npmjs.com/cli/v11/commands/npm-install-scripts/
- npm install policy: https://docs.npmjs.com/cli/v11/commands/npm-install/
- npm CLI releases: https://github.com/npm/cli/releases
- pnpm approve-builds: https://pnpm.io/cli/approve-builds
- pnpm build settings: https://pnpm.io/settings#allowbuilds
- Yarn security: https://yarnpkg.com/features/security
- Yarn manifest / `dependenciesMeta`: https://yarnpkg.com/configuration/manifest#dependenciesMeta
