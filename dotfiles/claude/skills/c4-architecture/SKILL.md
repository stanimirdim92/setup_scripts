---
name: c4-architecture
description: Generates a C4 model architecture workspace (Context and Container by default; Component, Deployment, and Dynamic views opt-in) for a codebase by inspecting it directly and writing Structurizr DSL, validated and rendered through the Structurizr MCP server. Use when asked to document, diagram, or explain a system's architecture, onboard someone to a codebase, or produce a C4 view at any of those levels. Independent of the spec/plan/build SDLC chain — this documents what already exists, it doesn't plan new work.
argument-hint: "[target directory or repo, defaults to repo root] [--components] [--deployment] [--dynamic \"scenario\"]"
---

# C4 Architecture Documentation

Inspired by the community `c4-architecture` Claude Code plugin
(github.com/amoustakas/claude-code-plugins), rewritten around the official
[Structurizr MCP server](https://docs.structurizr.com/ai/mcp) rather than
hand-written Markdown per level. Structurizr is the reference implementation
of C4: it understands the model's structural rules (components live inside
containers, containers live inside software systems, a person is never an
external system) and enforces them on the DSL you write, instead of Claude
having to police them by convention across a pile of separate documents.

## Overview

The [C4 model](https://c4model.com/diagrams) describes a system at up to four
zoom levels:

1. **Context** — the system as one box, its users, and the external systems
   around it.
2. **Container** — the deployable units (services, apps, databases, queues)
   inside that box.
3. **Component** — the logical groupings of code inside a container.
4. **Code** — functions, classes, and signatures inside a component.

Per the model's own guidance, most teams only need Context and Container —
**these are the default**. Component is opt-in depth; Code is out of scope
for this skill entirely (Structurizr's DSL doesn't model it either — that
level is better served by reading the code directly when someone asks a
code-level question, not by a standing diagram).

This skill produces one artifact, not one file per level: a single
Structurizr DSL workspace, which the MCP server validates and renders into
whatever views are needed.

## When to Use

- "Document/diagram the architecture of \<project\>"
- Onboarding someone to an unfamiliar codebase
- Producing a system context or container diagram for a design doc or ticket
- Any request for a C4-model view, at Context, Container, or Component depth

Not for: planning new work (that's `spec-driven-development` →
`planning-and-task-breakdown` → `incremental-implementation`). This skill
documents an existing system; it doesn't decide what to build next. Also not
for function/class-level ("Code" level) questions — read the source directly
for those instead of maintaining a diagram that will drift the next commit.

## Prerequisites

- The target codebase must actually be readable in this session. If it's a
  different repo than the one the session is currently scoped to, attach and
  clone it first (`add_repo`, then clone) — don't guess at a codebase's
  architecture from its name or README alone.
- The Structurizr MCP server must be registered (`dotfiles/claude/mcp/setup.sh`
  adds it, user scope, one time per machine). If its tools aren't visible yet,
  `ToolSearch` for `"structurizr"` — it's an HTTP MCP server, no local process
  to start. If it's genuinely not registered, say so and point at
  `mcp/setup.sh` rather than falling back to hand-validating DSL yourself.

## Workflow

### 1. Scope

Default is Context + Container — that's the whole output unless one of these
was asked for explicitly:

- `--components` — add Component views (opt-in depth, not default)
- `--deployment` — add a Deployment view (needs deployment evidence to exist)
- `--dynamic "scenario"` — add a Dynamic view for one named runtime workflow
  (e.g. `--dynamic "checkout flow"`) — this is the right place for
  request/response sequences and cross-container journeys; they don't belong
  in the static Context/Container model.

Code level (functions, classes, signatures) is out of scope for this skill
at any flag — see Overview.

Ask first before sweeping a large or unfamiliar repo at any depth: confirm
which subdirectory (or the whole thing), rather than defaulting to the whole
repo.

### 2. Discover

Inspect the repo directly — no subagent fan-out:

- `Glob`/`Grep` for entrypoints, routing/controller layers, and per-language
  project manifests — this is how containers are actually identified. A
  container is a separately runnable application or data store (an SPA, an
  API service, a background worker, a database schema); a repo can have
  several containers with zero deployment tooling in sight, and a Dockerfile
  is not required for something to count as one.
- Deployment definitions (Dockerfiles, compose files, k8s manifests, IaC,
  CI/CD configs) as *corroborating* evidence for the containers found above
  — never the sole source of them. Don't fold replica counts, load
  balancers, or cluster topology into the container model; that's Deployment
  view territory (opt-in, see Step 3b), not Container.
- Config/env files and client libraries (DB drivers, queue clients, HTTP
  clients to named external hosts) for containers' relationships and the
  external systems/APIs/databases around the system.
- README, requirements docs, and tests for **people** — human user types and
  roles — and what the system is actually for. Keep people and external
  software systems separate categories, never blend them: an external API,
  service, or queue is a `softwareSystem` tagged `External`, never a
  `person`, no matter how "programmatic" it feels. Tests reveal intended
  behavior even when nothing else documents it.
- If `--components`: within each container, group files by actual code
  structure (module/package/layer boundaries the codebase already uses), not
  an invented grouping.
- If `--deployment`: read the deployment definitions properly this time —
  replicas, regions/zones, load balancers, managed-service targets (RDS,
  managed queue, etc.) — this is where that detail belongs.
- If `--dynamic "scenario"`: trace the one named workflow through the
  containers involved, in call order, from an entrypoint (route handler,
  event consumer, CLI command) actually found in the code.

Every element and relationship you write into the DSL must trace back to
something actually read — a file, a config value, a deployment manifest line,
a test. Note inferred-vs-stated explicitly where documentation is thin (e.g.
"inferred from `docker-compose.yml`" vs. "stated in README") rather than
blending the two silently.

### 3. Draft the DSL

Write `C4-Documentation/workspace.dsl`:

```
workspace "System Name" "One-sentence description" {

    model {
        user = person "User" "Primary human persona"
        otherSystem = softwareSystem "External System" "What it provides" "External" {
            tags "External"
        }

        system = softwareSystem "System Name" "What it does" {
            webapp = container "Web Application" "Serves the UI/API" "Technology"
            database = container "Database" "Stores X" "PostgreSQL" {
                tags "Database"
            }

            webapp -> database "Reads from and writes to" "SQL"
        }

        user -> system "Uses"
        system -> otherSystem "Calls" "HTTPS/API"
    }

    views {
        systemContext system "SystemContext" {
            include *
            autoLayout
        }
        container system "Containers" {
            include *
            autoLayout
        }
        # component view(s) here only if Component depth was scoped in

        styles {
            element "Database" {
                shape cylinder
            }
            element "External" {
                background #999999
                color #ffffff
            }
        }
    }

}
```

Containers nest inside their software system; components (if in scope) nest
inside their container. Never declare a component at container scope or a
container outside any software system — that's exactly the structural error
Structurizr's inspection step below exists to catch, but don't rely on it to
catch mistakes you could avoid by following the nesting rules going in.

### 3b. Optional: Deployment and Dynamic views

Only when `--deployment` or `--dynamic` was passed — these are supporting
C4 diagrams, not part of the default Context/Container output, and each
adds its own `views {}` entry to the same workspace rather than a separate
file:

```
model {
    ...
    deploymentEnvironment "Production" {
        deploymentNode "AWS" {
            deploymentNode "ECS" {
                containerInstance webapp
            }
            deploymentNode "RDS" {
                containerInstance database
            }
        }
    }
}

views {
    ...
    deployment system "Production" "ProductionDeployment" {
        include *
        autoLayout
    }
    dynamic system "CheckoutFlow" "Describes the checkout scenario" {
        user -> webapp "Submits order"
        webapp -> database "Writes order"
        webapp -> otherSystem "Charges payment"
        autoLayout
    }
}
```

### 4. Validate and inspect (loop)

1. Call the Structurizr MCP's DSL validate tool on the draft.
2. If it parses, call the inspect tool for structural/semantic violations.
3. Fix each reported issue in the DSL and re-run both steps.
4. Repeat until clean, capped at 3 fix passes. If issues remain after 3
   passes, stop and show the user the remaining violations plus your draft —
   don't keep guessing at a fix silently.

### 5. Export views

Once validated, call the MCP's export tool(s) for the views defined in
`views {}` — Mermaid for inline rendering, PlantUML if the user asked for it
specifically. Write each exported view alongside the DSL.

## Output

```
C4-Documentation/
├── workspace.dsl              # the model — source of truth
├── context.mmd                # System Context view, exported (Mermaid)
├── container.mmd              # Container view, exported (Mermaid)
├── component-<name>.mmd       # only with --components
├── deployment-<env>.mmd       # only with --deployment
└── dynamic-<scenario>.mmd     # only with --dynamic
```

## Boundaries

- **Always**: every element/relationship backed by something actually read
  from the codebase, its config, or its docs — never invented; run the
  validate/inspect loop before treating the DSL as done; nest containers
  inside their software system and components inside their container, never
  at the wrong scope.
- **Ask first**: before sweeping a large or unfamiliar repo — confirm scope
  (subdirectory, Context+Container vs. +Component) rather than defaulting to
  the whole repo at full depth; before Code-level detail (out of scope by
  default — see Overview).
- **Never**: fabricate endpoints, deployment units, people, external systems,
  or relationships that aren't backed by something read from the codebase or
  its docs; classify an external API/service/queue as a `person`; skip the
  validate/inspect loop and hand-wave DSL correctness.
