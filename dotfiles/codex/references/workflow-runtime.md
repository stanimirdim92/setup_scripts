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
  When a task packet selects `browser-testing-with-devtools`, use the available
  Codex browser tooling for equivalent runtime evidence or block the required
  check when no callable browser capability exists.

## Agent dispatch

For independent top-level CLI sessions, run `codex-worktree <ticket>` from the
project. The launcher creates/reuses `<main-checkout>/.codex/worktrees/<ticket>`
on `codex/<ticket>`, copies matching ignored `.worktreeinclude` files, checks
infrastructure, runs `bin/worktree-setup.sh` when provided, and starts Codex in
that checkout. Different tickets can run concurrently in separate terminals;
the same ticket is locked while its launcher/session runs. Use `--no-setup`
for spec/planning only; dependencies must be reconciled before implementation
or tests. Use `--dry-run` to inspect the plan without creating anything.
The CLI launcher does not automatically allocate child-agent worktrees: the
parallel writer and independent verifier rules below still apply.

For a persona selected by a shared command, read its definition under
[the shared agent directory](../../claude/agents). Use Codex's available subagent
mechanism with the command's bounded packet, the persona file pointer, and this
runtime reference. The child must read the persona body and any skills listed
in its frontmatter before working; Claude's automatic skill preloading does not
occur in Codex. In particular, executors must load
[executor-development-discipline](../../claude/skills/executor-development-discipline/SKILL.md).

Claude model names and tool allowlists are not Codex configuration. Installed
native roles in `~/.codex/agents/` set the Codex model, effort, sandbox default,
no-child-agent setting, and role hook. Select the native role by name when the
runtime's dispatch tool supports it:

| Shared persona | Codex role | Model / effort |
| --- | --- | --- |
| executor | executor | gpt-5.6-terra / xhigh |
| executor, high-risk work | executor-high | gpt-6-astra / high |
| test-engineer | test-engineer | gpt-5.6-terra / xhigh |
| repo-recon | repo-recon | gpt-5.6-terra / xhigh |
| code-reviewer | code-reviewer | gpt-6-astra / high |
| blind-reviewer | blind-reviewer | gpt-6-astra / high |
| security-auditor | security-auditor | gpt-6-astra / high |
| distributed-systems-reviewer | distributed-systems-reviewer | gpt-6-astra / high |

The orchestrating turn keeps the user's session model. A native role's model
pin overrides a per-call model argument: use `executor-high` for the shared
build command's high-risk escalation, not `executor` with a model override.

Some Codex surfaces expose only `spawn_agent(message, model, reasoning_effort,
fork_turns, ...)`, with no native-role selector. On that surface, supply the
table's model and effort explicitly and include the shared persona, runtime
reference, and restrictions in the packet. Do not invent an `agent_type`
argument or imply that a task name selects a native role. This fallback does
not load role-specific hooks or sandbox defaults; report that limitation and
perform the branch/infrastructure checks explicitly. Do not claim structural
read-only or no-push enforcement on that path. If the task requires those
enforced boundaries, use a runtime with native-role dispatch or report blocked.

Use fresh contexts for initial persona dispatch, especially independent and
blind reviewers: set `fork_turns="none"` when that argument is available and
provide a self-contained packet. Never pass a blind reviewer the implementer's
reasoning or another reviewer's findings. Resume only that workstream's own
executor for subsequent tasks.

Preserve tool restrictions in every packet. Recon/review personas may list,
search, read files, and inspect Git; never run project code, tests, builds,
installs, or mutations. The native hook permits ordinary read commands (`rg`,
`cat`, `nl`, `head`, `tail`, `ls`, `wc`, `stat`, `pwd`, `readlink`, `realpath`),
numeric `sed -n 'START,ENDp'`, and Git inspection with `--no-pager` (also
`--no-ext-diff --no-textconv` for diff/show/log). Shell substitutions,
redirection, interpreters, executable search options, and mutations are denied.
Recon reports discovered commands, not execution results. Test-engineer keeps
its test-only write scope; executor keeps its planned implementation scope.

Resume the same executor for subsequent tasks in its workstream. Sequential
executors use the ticket checkout. Before writing, verify its branch and run the
project's optional `bin/worktree-doctor.sh --infrastructure` as described in
`../../claude/commands/build.md`. The native Codex hooks reuse the shared check
at writer dispatch and before writer shell/patch calls. They do not create a
checkout or isolate runtime resources on the orchestrator's behalf.
Claude's `isolation: worktree` flag is not a Codex tool argument: before parallel
writing, establish separate worktrees/branches and
bind each agent's reads, writes, and commands to its assigned checkout, then
integrate sequentially. If that isolation cannot be enforced, stay sequential.
Always assign test-engineer a separate verifier checkout for the exact candidate,
even when implementation was sequential.
Keep verifier/reviewer contexts independent from implementers and each other.
If required delegation is unavailable, report the stage's blocker instead of
silently replacing an independent agent with self-review. Personas never dispatch
personas. Shared command gates and commit authority remain unchanged.

## Hook activation and limits

`~/.codex/hooks.json` adapts startup, shell/dispatch, and writer handoff events;
native role files attach role-specific PreToolUse policies. Review and trust
new or changed definitions in Codex CLI `/hooks`, including role-layer hooks
when surfaced. Until trusted, Codex skips them. Restart after installing agents
or hooks; an existing session is not proof the new configuration loaded.

These are accident guards for supported tool paths, not a complete security
boundary. Live parent permission overrides can supersede a role's sandbox;
MCP and specialized tools need their own permission controls. `write_stdin`
does not rerun PreToolUse, and shell guards do not parse arbitrary scripts.
Never use another tool, interpreter, session, or directory change to evade a
denial. Report missing enforcement honestly instead of claiming Claude parity.
