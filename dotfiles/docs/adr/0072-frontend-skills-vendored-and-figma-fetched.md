# Frontend skills: three vendored, Figma's fetched

**Context.** Frontend work in the target projects is React 19 with Inertia on
Laravel, Tailwind 4, Vite and Vitest, often built from a Figma design. Framework
and version guidance for a project lives in that project's own instruction
files and is out of the harness's scope. The harness had no skill for component API design, for Vite or
Vitest, or for the Figma design-to-code loop; LD-442 left Figma parity as a
manual, visual-only check.

**Decision — vendor three MIT skills at pinned commits.**

| Skill | Source | Licence |
| --- | --- | --- |
| `vercel-composition-patterns` | vercel-labs/agent-skills `063bee94c3f4` | MIT, declared in its README and frontmatter; the repository has no LICENSE file, so `VERCEL_AGENT_SKILLS_LICENSE` carries the standard text with that note |
| `vite`, `vitest` | antfu/skills `e53a142a2420`, generated from the official docs | MIT, `ANTFU_SKILLS_LICENSE` |

Each keeps its upstream text, with a "Local workflow integration" note on top
naming the source, commit and licence, and saying that project rules and
installed versions win. The Vercel description is folded onto one line so the
Codex adapter's description check can compare it. Each has a Codex adapter.

**Decision — fetch Figma's skill, do not commit it.** skills.sh still lists
`figma-implement-design`; Figma's repository replaced it with
`figma-design-to-code`. That repository ships no licence, so its file cannot be
redistributed here. `dotfiles/tools/setup/fetch-figma-skill.sh` downloads it at
commit `aaa07946b607`, checks its SHA-256, and places it in a gitignored skills
folder; a changed upstream file is refused until the pin is reviewed and moved.
`mcp/setup.sh` runs it after adding the Figma server. The harness map lists
tracked skills only, so a local copy cannot make the committed page stale. No
Codex adapter: Codex has no Figma MCP configured.

**Decision — wire them into the gates.**
- `/build` selects `figma-design-to-code` for a task whose spec or packet links
  a Figma design, `vercel-composition-patterns` for component API work, and
  `vite` / `vitest` for build config and tests.
- `/test` selects `figma-design-to-code` when a claim is "matches the Figma
  design": the Figma screenshot is the target, the rendered screen comes from
  Chrome DevTools, a mismatch is `VERIFY FAIL`, a missing connection is
  `VERIFY BLOCKED`.
- `executor` and `test-engineer` gain `mcp__figma__*`; without it neither could
  follow the skill. Reviewers stay read-only.

**Rejected.**
- *`web-design-guidelines` (Vercel).* Not chosen by the approver; it also
  fetches its rules from the network on every run.
- *`npx skills add`.* `~/.claude/skills` links into this repository, so it would
  write unpinned, unreviewed files into git.
- *`react-best-practices` (Vercel).* Mostly Next.js server patterns that Inertia
  does not use.
