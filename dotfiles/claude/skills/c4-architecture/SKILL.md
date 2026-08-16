---
name: c4-architecture
description: Generates C4 model architecture documentation (Context, Container, Component, Code) for a codebase via bottom-up analysis across four coordinated subagents. Use when asked to document, diagram, or explain a system's architecture, onboard someone to a codebase, or produce Context/Container/Component/Code-level views. Independent of the spec/plan/build SDLC chain — this documents what already exists, it doesn't plan new work.
argument-hint: "[target directory or repo — defaults to the current repo root]"
---

# C4 Architecture Documentation

Inspired by the community `c4-architecture` Claude Code plugin
(github.com/amoustakas/claude-code-plugins) — rewritten from scratch as this skill plus
four house-tiered subagents (`c4-code`, `c4-component`, `c4-container`, `c4-context`)
rather than vendored verbatim, to match this repo's own agent/skill conventions.

## Overview

The [C4 model](https://c4model.com/diagrams) describes a system at four zoom levels:

1. **Context** — the system as one box, its users, and the external systems around it.
2. **Container** — the deployable units (services, apps, databases) inside that box.
3. **Component** — the logical groupings of code inside each container.
4. **Code** — the actual functions, classes, and signatures inside each component.

This skill builds all four bottom-up: read the code first, then synthesize upward
through Component and Container to the stakeholder-facing Context view. Each level's
documentation is only as good as the level below it, so nothing above Code is written
before the Code level backing it exists.

Per the model's own guidance, most teams only need Context and Container — Component
and Code are opt-in depth, not a default. Treat Phase 1/2 below as something to scope
deliberately, not run reflexively on a whole large repo.

## When to Use

- "Document/diagram the architecture of \<project\>"
- Onboarding someone to an unfamiliar codebase
- Producing a system context or container diagram for a design doc or ticket
- Any request for a C4-model view, at any single level or all four

Not for: planning new work (that's `spec-driven-development` → `planning-and-task-breakdown`
→ `incremental-implementation`). This skill documents an existing system; it doesn't
decide what to build next.

## Prerequisites

The target codebase must actually be readable in this session. If it's a different
repo than the one the session is currently scoped to, attach and clone it first
(`add_repo`, then clone) — the same requirement as any other cross-repo task in this
environment. Don't guess at a codebase's architecture from its name or README alone.

## The Four Phases (bottom-up)

### Phase 1 — Code

- Enumerate subdirectories (`Glob`), excluding non-code directories (`node_modules`,
  `.git`, `vendor`, `build`, `dist`, and the like).
- Sort deepest-first.
- Dispatch `c4-code` once per directory, in that order.
- **Cost note**: this is one subagent call per subdirectory. For a large repo, that's a
  lot of calls on the cheap tier but still real cost — scope to a subdirectory the user
  actually asked about, or skip straight to Phase 3/4 if Code/Component depth isn't
  actually wanted (see Overview).

### Phase 2 — Component

- Once every `c4-code-*.md` exists, dispatch `c4-component` once per identified
  component (grouping is `c4-component`'s own judgment call, not decided here).
- Dispatch `c4-component` one more time for the master index, after every
  per-component doc exists.

### Phase 3 — Container

- Search the repo for deployment definitions (Dockerfiles, k8s manifests, compose
  files, IaC, CI/CD configs).
- Dispatch `c4-container` once, handing it every `c4-component-*.md` plus the
  deployment definitions found.

### Phase 4 — Context

- Dispatch `c4-context` once, handing it `c4-container.md`, `c4-component.md`, and
  whatever system documentation exists (README, requirements, tests).

## Output

```
C4-Documentation/
├── c4-code-*.md         # one per directory (Phase 1)
├── c4-component-*.md    # one per component (Phase 2)
├── c4-component.md      # master component index (Phase 2)
├── c4-container.md      # all containers (Phase 3)
├── c4-context.md        # system context (Phase 4)
└── apis/
    └── *-api.yaml       # OpenAPI 3.1+ per container (Phase 3)
```

## Boundaries

- **Always**: bottom-up order — never dispatch a synthesis phase before the phase
  below it is complete; every code-level claim backed by a real `file:line`, never
  invented.
- **Ask first**: before running the full Phase 1/2 sweep on a large or unfamiliar repo
  — confirm scope (which subdirectory, which containers) rather than defaulting to
  "the whole repo" and burning a call per directory.
- **Never**: fabricate endpoints, deployment units, personas, or dependencies that
  aren't backed by something actually read from the codebase or its docs.

## Composition

This skill is the one place allowed to dispatch all four C4 agents in sequence — the
agents themselves never call each other, same rule as every other agent in this repo
(see `code-reviewer.md`'s Composition section for the precedent).
