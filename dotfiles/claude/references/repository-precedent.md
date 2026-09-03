# Repository Precedent

How to use a `repo-recon` report, and how to decide when the repository gives no
guidance. Single-sourced because `/spec` and `/plan` had near-identical copies of the
dispatch rules and `spec-driven-development` a third.

The **evidence order** itself is not here — it is five lines, needed on nearly
every run, and lives inline in `../skills/spec-driven-development/SKILL.md`
where it is used. Routing a five-line decision rule through a file read costs
more than the duplication it avoids. A worked example report is in
`repository-precedent-example.md`, read while learning the shape rather than on
every run.

## 1. Using a recon report

Before naming files, classes, tables, architectural layers, test helpers, or
implementation patterns, you need the project's applicable rules, the owning
module's conventions and architectural chain, its test setup, and the closest
sibling implementations.

Do not gather that by reading the repository yourself. The calling stage
dispatches one `repo-recon` agent for the affected area and works from its
report — that survey is the largest avoidable cost of the command, and the
agent's reads stay in its own context. `repo-recon` owns the discovery method,
including which instruction sources to look for; do not restate that list.

- **Reuse** a report already in this conversation when it covers the same
  implementation and test area and that surveyed area has not changed. A spec,
  plan, or other documentation-only edit does not stale implementation
  precedent. Dispatch again only for a different or changed affected area, or
  when the report's **Not surveyed** section
  excludes something you now need.
- **Findings are pointers.** Open a file the report names only when a specific
  unresolved question turns on that file's detail — one or two files, not the
  survey again.
- **No precedent found for** is load-bearing: those are the aspects being
  decided without repository guidance.
- **Not surveyed** bounds what the report can support. If it excludes something
  the work depends on, ask for a follow-up recon rather than assuming.

Per-stage handling of **No precedent found for**:

| Stage | Obligation |
|---|---|
| `/spec` | The spec must justify each one explicitly, not present it as the obvious choice. |
| `/plan` | Carry them into the plan as risks, not as settled ground. |

## 2. When no precedent exists

- If an explicit user requirement or approved feature-specific decision requires
  a new layer, file, pattern, or abstraction, include it and label it clearly as
  a **new feature-specific decision**.
- If no requirement or decision justifies it, do not invent it merely because it
  is common framework practice.
- If the evidence is mixed, or the choice would change an acceptance criterion,
  schema, public contract, or lifecycle behavior, raise an `OPEN QUESTION` block
  instead of silently deciding.

Examples:

- A Factory may be introduced when comparable tests use factories, the feature
  needs reusable test/seed data, or it is an explicit feature decision.
- A DTO/Data layer may be introduced when project rules require it, repository
  precedent supports it, or an explicit feature decision accepts the additional
  boundary/complexity for a concrete benefit.
- Do not derive class/table names solely from ticket wording when sibling
  resources establish a different ownership/naming convention.

Do not confuse **no precedent** with **forbidden**. New patterns are acceptable
when they are intentional, justified, and identified as new rather than
misrepresented as existing repository convention.

## 3. See also

- `repository-precedent-example.md` — a filled-in recon report.
- `../agents/repo-recon.md` — the report format and the agent's own constraints,
  including which instruction sources it looks for.
