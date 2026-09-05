# Repository Precedent

How `/spec` and `/plan` gather repository evidence, when to dispatch
`repo-recon`, and what to do when the repository gives no guidance.

The **evidence order** itself is not here — it is five lines, needed on nearly
every run, and lives inline in `../skills/spec-driven-development/SKILL.md`
where it is used. Routing a five-line decision rule through a file read costs
more than the duplication it avoids. A worked example report is in
`repository-precedent-example.md`, read while learning the shape rather than on
every run.

## 1. Choose the smallest evidence path

Before naming files, classes, tables, architectural layers, test helpers, or
implementation patterns, you need the project's applicable rules, the owning
module's conventions and architectural chain, its test setup, and the closest
sibling implementations.

Use the first adequate option:

1. **Reuse** a report while its relevant sources and conclusions remain current.
   Changes to instructions, ADRs, or documented commands can stale it even when
   implementation files are unchanged. Refresh only the affected evidence;
   unrelated edits or committing unchanged evidence do not require a new survey.
2. **Bounded check** when the affected files are known, the change stays in one
   familiar area, and no schema, public contract, lifecycle, concurrency, or
   cross-module concern is involved. Read applicable instructions plus only the
   named source, test, README, manifest, and CI files needed to confirm
   conventions and exact commands.
3. **Dispatch `repo-recon`** when the area is unfamiliar or broad; crosses
   modules; changes schema, contract, lifecycle, or concurrency behavior; lacks
   a source-supported command or precedent; or a prior report is stale or marked
   **Not surveyed** where evidence is now needed.

Do not turn a bounded check into an inline repository survey. Whatever path is
used, distinguish verified facts from inference and surface:

- **No precedent found for** — surveyed, but the repository gives no guidance.
- **Not surveyed** — outside the evidence gathered; never assume from silence.

If no exact repository-defined verification command is found, dispatch recon or
record the command as unresolved. Never normalize or abbreviate a guessed
equivalent.

Recon establishes what command the repository defines; its read-only agent
does not execute it. Report execution results only when a caller supplies
current run evidence, and keep that evidence distinct from source discovery.

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
