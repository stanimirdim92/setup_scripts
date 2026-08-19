---
name: c4-architecture
description: Generates a C4 model architecture workspace (Context, Container, and optionally Component/Code) for a codebase by inspecting it directly and writing Structurizr DSL, validated and rendered through the Structurizr MCP server. Use when asked to document, diagram, or explain a system's architecture, onboard someone to a codebase, or produce Context/Container/Component-level views. Independent of the spec/plan/build SDLC chain — this documents what already exists, it doesn't plan new work.
argument-hint: "[target directory or repo — defaults to the current repo root]"
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

Ask first before sweeping a large or unfamiliar repo: which subdirectory (or
the whole thing), and Context+Container only, or Component too. Default to
Context+Container on an unscoped "document the architecture" request.

### 2. Discover

Inspect the repo directly — no subagent fan-out:

- `Glob`/`Grep` for entrypoints, routing/controller layers, and per-language
  project manifests to find the deployable units.
- Deployment definitions (Dockerfiles, compose files, k8s manifests, IaC,
  CI/CD configs) to confirm what actually ships as a separate container
  versus what's just a source directory.
- Config/env files and client libraries (DB drivers, queue clients, HTTP
  clients to named external hosts) for containers' relationships and the
  external systems/APIs/databases around the system.
- README, requirements docs, and tests for personas (human and programmatic)
  and what the system is actually for — tests reveal intended behavior even
  when nothing else documents it.
- If Component depth was requested: within each container, group files by
  actual code structure (module/package/layer boundaries the codebase
  already uses), not an invented grouping.

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
└── component-<name>.mmd       # only if Component depth was scoped in
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
- **Never**: fabricate endpoints, deployment units, personas, or dependencies
  that aren't backed by something read from the codebase or its docs; skip
  the validate/inspect loop and hand-wave DSL correctness.
