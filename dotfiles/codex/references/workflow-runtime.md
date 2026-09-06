# Codex workflow conventions

These adapters reuse the Claude harness's maintained methodology, templates,
and gates. Resolve linked files from the physical adapter directory (follow
the installed directory symlink), then resolve each source's relative references
from that source's own directory. Do not copy or rewrite the shared sources.

- Read a required skill's `SKILL.md` directly; Codex need not have Claude's
  `Skill` tool. Read only the references needed for the active stage.
- In user-facing next actions, `/name` means `$name` for an installed adapter.
  These are workflow stages, not Codex's built-in planning mode. Preserve shared
  artifact fields and approval rules so a new session or Claude can resume.
- Use available Codex tools for file reads, searches, questions, and Jira
  access. A configured Claude connector is not proof of Codex access; report
  unavailable sources under the shared intake's coverage and blocker rules.
- Tool-dependent skills still require callable tools. Claude MCP setup examples
  and hooks do not configure or enforce anything in Codex. Report missing
  capabilities instead of claiming successful browser, diagram, or Jira checks.

## Agent dispatch

For a persona selected by a shared command, read its definition under
[the shared agent directory](../../claude/agents). Use Codex's available subagent
mechanism with the command's bounded packet, the persona file pointer, and this
runtime reference. The child must read the persona body and any skills listed
in its frontmatter before working; Claude's automatic skill preloading does not
occur in Codex. In particular, executors must load
[executor-development-discipline](../../claude/skills/executor-development-discipline/SKILL.md).

Claude model names and tool allowlists are not Codex configuration. Use the
session's configured Codex model unless an applicable Codex configuration or
explicit instruction selects another. Preserve each persona's tool restrictions
in the task packet. For read-only recon/review personas, shell use may implement
file listing, searching, reading, and read-only git inspection, but must not
execute project code, tests, builds, installs, or mutations. Recon reports
discovered commands, not execution results. Test-engineer retains its test-only
write scope; executor retains its planned implementation scope.

Resume the same executor for subsequent tasks in its workstream. Default to
sequential writers. Claude's `isolation: worktree` flag is not a Codex tool
argument: before parallel writing, establish separate worktrees/branches and
bind each agent's reads, writes, and commands to its assigned checkout, then
integrate sequentially. If that isolation cannot be enforced, stay sequential.
Keep verifier/reviewer contexts independent from implementers and each other.
If required delegation is unavailable, report the stage's blocker instead of
silently replacing an independent agent with self-review. Personas never dispatch
personas. Shared command gates and commit authority remain unchanged.
