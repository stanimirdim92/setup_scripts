# `c4-architecture`: fixed people/external-system terminology, added opt-in Deployment/Dynamic views

**Decision.** A second ChatGPT critique — written against the pre-Structurizr
four-agent design — was checked point-by-point against the just-merged
Structurizr rewrite ([0016](0016-c4-architecture-rewritten-around-structurizr-mcp.md))
rather than applied wholesale. Most of it (the directory→component→container
chain, per-directory Code agent, circular component dispatch, journeys inside
Context, OpenAPI generation, the component `type` field, hand-rolled diagram
notation rules) no longer applies — the DSL/MCP rewrite already removed each
of those by construction, not by convention.

Two points were genuine leftover bugs in the rewrite's first draft, both
fixed here: the Discover step still said "personas (human and programmatic)",
directly contradicting the skill's own stated rule that a person is never an
external system — external APIs/services/queues were getting invented into a
"programmatic persona" category C4 doesn't have. Fixed to keep people and
external software systems as the two separate categories C4 actually
defines. Second, the container-identification wording leaned too hard on
deployment definitions (Dockerfiles, k8s manifests) as though they were what
*defines* a container, when C4 defines a container as a separately runnable
application or data store — a repo can have several containers with zero
deployment tooling. Reworded so deployment definitions are corroborating
evidence, not the source of truth, and split deployment-topology detail
(replicas, load balancers, regions) out to its own opt-in view.

That last point plus the critique's point about journeys belonging in
Dynamic, not Context, prompted adding **Deployment and Dynamic as explicit
opt-in flags** (`--deployment`, `--dynamic "scenario"`) alongside the
existing `--components` — Structurizr's DSL already models both natively
(`deploymentEnvironment`, `dynamic` view blocks), so this is a few lines of
skill instructions, not new orchestration or a new agent. Default output
stays Context + Container only; Code level stays out of scope entirely per
[0016](0016-c4-architecture-rewritten-around-structurizr-mcp.md)'s reasoning.

**Rejected — a dedicated `references/c4-diagram-rules.md`.** The critique's
point about enforcing C4 notation basics (title, scope, technology labels,
labelled relationships) assumed hand-written Mermaid, which the DSL rewrite
already replaced — Structurizr's DSL makes technology/description/tags
first-class fields and its own export handles notation, so a duplicate
prompt-level rules file would solve a problem the tool switch already
solved.
