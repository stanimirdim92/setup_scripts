# One spec per ticket; the capability map is a section of it

**Decision.** A multi-capability initiative is specified in one spec,
`docs/specs/[TICKET]-SPEC.md`, instead of a `[TICKET]-CAPABILITY-MAP.md` file
plus one `[TICKET]-SPEC-<module-id>.md` per module (approver's call). The map
becomes a `## Capability Map` section after Objective: module id,
responsibility, dependencies, and a Requirements column that is the one place a
`REQ-###` is assigned to a module. The human still reviews the map before any
requirement is written, and approves the spec as a whole.

**Why.** Per-module specs had no matching plan path. `/plan` writes only
`docs/tasks/[TICKET]-plan.md` and stops when that target belongs to different
work, so the second module of any initiative collided with the first. Breaking
the work into modules inside one spec gives `/plan` the same selection handle
(module ids, build order) without new artifact paths.

**Decision — planning by module.** `/plan` plans the module ids it is given, or
the whole spec. It takes modules in build order, refuses one whose dependencies
are neither planned nor built, follows module boundaries for workstreams, and
checks coverage against the selected modules' requirements; the plan header
records `Modules:` and `Not yet planned:`. There is one plan per ticket:
planning a later module revises it in place, keeps built task ids, and returns
it to `Needs replan` for renewed approval.

**Decision — enforcement.** `tools/validate-artifact-paths.py` no longer
accepts the map file or per-module spec paths, so a pipeline file that
reintroduces them fails CI.

**Rejected — per-module plan and todo paths.** Workable, but it adds two more
artifact families and a module index for every consumer (`/build`, `/test`,
`/review`, `/ship`) to resolve, where one spec and one plan keep today's
target resolution unchanged.
