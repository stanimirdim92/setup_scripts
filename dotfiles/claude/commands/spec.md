---
description: Start spec-driven development — write a structured specification before writing code
---

First invoke the `superpowers:brainstorming` skill to classify the request (spike / bounded / architectural) and get explicit approval on direction — don't formalize a spec on an idea nobody's signed off on yet.

Once that's approved, invoke the `spec-driven-development` skill.

Begin by understanding what the user wants to build. Ask clarifying questions about:
1. The objective and target users
2. Core features and acceptance criteria
3. Tech stack preferences and constraints
4. Known boundaries (what to always do, ask first about, and never do)

Then generate a structured spec covering all six core areas: objective, commands, project structure, code style, testing strategy, and boundaries.

Save the spec as SPEC.md in the project root and confirm with the user before proceeding.
