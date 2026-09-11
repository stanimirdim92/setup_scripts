# Dotfiles harness architecture

This repository maintains shared agent workflows and installs them into Claude
Code and Codex. It contains instructions, adapters, configuration, and checking
utilities; the host application executes the workflows. Installation instructions
and the full synced-file inventory live in [README.md](README.md).

## Source ownership

| Source | Owns |
|---|---|
| [dotfiles/claude/CLAUDE.md](dotfiles/claude/CLAUDE.md) | Shared global defaults; project-local rules may be more specific |
| [dotfiles/claude/commands](dotfiles/claude/commands) | Workflow entry points, orchestration, evidence gates, and stopping conditions |
| [dotfiles/claude/skills](dotfiles/claude/skills) | Reusable methodology, including project documentation |
| [dotfiles/claude/agents](dotfiles/claude/agents) | Persona responsibilities, Claude tool/model declarations, and report contracts |
| [dotfiles/claude/references](dotfiles/claude/references) | Shared gate definitions, templates, and supporting guidance |
| [dotfiles/claude/docs/agents.md](dotfiles/claude/docs/agents.md) | Human-readable orchestration overview, linked to the owning commands |
| [dotfiles/codex/skills](dotfiles/codex/skills) | Thin Codex entry points into shared commands and skills |
| [dotfiles/codex/references/workflow-runtime.md](dotfiles/codex/references/workflow-runtime.md) | Codex invocation, explicit skill loading, and persona dispatch adaptation |
| [docs/adr](docs/adr) | This repository's accepted architectural decisions and rejected alternatives |

Methodology is maintained in the shared Claude tree. Codex adapters refer to that
source rather than maintaining a second version of the workflow. A shared edit
therefore affects both hosts; a Codex-specific runtime translation belongs in the
adapter/reference. Descriptions and invocation metadata still need reconciliation
when a shared skill's discovery contract changes.

## Installation and reads

[tools/link_dotfiles.sh](tools/link_dotfiles.sh) links the Claude directories and
configuration into the user's home and links the global rules to Codex's
`AGENTS.md`. It preflights every destination (including the Codex adapter
links below) before mutating anything, refuses to overwrite an existing
`.bak`, and reverts paths changed by the current run if a later link fails.
Its general link helper backs up existing real files and replaces old
symlinks; review its output when moving an installation.

The script calls [dotfiles/codex/install-skills.py](dotfiles/codex/install-skills.py)
for individual Codex skill links under `~/.agents/skills`. That installer checks
all destination conflicts first and refuses to replace an existing unrelated
path. Repeated installation preserves correct links; `--check` only checks link
state. It leaves bundled Codex system skills and other user skills in place.

The resulting read paths are:

```text
Claude skill/command -> ~/.claude/... -> dotfiles/claude/... -> shared references
Codex $skill -> ~/.agents/skills/<name> -> dotfiles/codex/skills/<name>
            -> shared Claude source + Codex runtime conventions
```

Relative references resolve from each source file's physical directory, including
when reached through a symlink. Keeping sources in the checkout preserves their
sibling references, templates, and license files. Machine-specific credentials,
logs, databases, and session state are outside this synced architecture; see the
README's exclusions. Editing a linked runtime file edits its repository source.

## Workflow and project boundaries

The pipeline is `spec -> plan -> build -> review -> ship`, with independent
`test` verification when requested or required by review. Commands own the gates;
personas perform bounded work and do not dispatch other personas. The details,
including executor reuse and concurrency, live in
[the orchestration guide](dotfiles/claude/docs/agents.md) and its command sources.

Ticket specs, plans, task packets, and project documentation belong to the target
project. Global skills supply their workflow and shape without becoming a copy of
project-specific facts. [project-docs](dotfiles/claude/skills/project-docs/SKILL.md)
can generate or refresh a useful document set independently of the ticket stages;
[documentation practices](dotfiles/claude/references/documentation-practices.md#project-documentation)
defines document ownership and change-driven maintenance.

## Host enforcement and integrations

Claude's [settings](dotfiles/claude/settings.json) configure PreToolUse hooks from
[dotfiles/claude/hooks](dotfiles/claude/hooks) and pin the subagent spawn depth
to 1, so no persona can dispatch another; persona frontmatter declares its
Claude tools, models, turn caps, and — for the writing personas — agent-scoped
hooks that deny pushing and gate the handoff report. Those declarations are not Codex enforcement. Codex's
own sandbox, approvals, and available tools determine its actual capabilities;
the runtime adapter passes persona constraints as instructions and uses available
Codex delegation. A textual restriction is not an OS permission boundary.

Concurrent writers require separate checkouts and isolated runtimes; `/build`
fans out whenever those conditions are established and queues a workstream
when any is unproven. Review and verification contexts remain independent from executors.
Missing required tools or delegation produce an explicit blocker.

MCP connections and authentication remain host-specific. A linked browser, Jira,
or architecture skill does not establish a working connection. The Claude
[MCP setup script](dotfiles/claude/mcp/setup.sh) is separate from link installation;
Codex tools must be available in its own session.

## Verification and maintenance

- `python3 dotfiles/codex/install-skills.py --check` checks installed link targets.
- `tools/test-install-skills.py` regression-tests the installer's preflight and
  rollback behavior (conflict detection, injected-failure rollback) in a
  temporary destination, without touching real links.
- `tools/test-hooks.sh` exercises the Claude command hooks with fixtures;
  `tools/test-handoff-hook.sh` does the same for the `SubagentStop` handoff gate.
- `tools/validate-artifact-paths.py` fails when any pipeline file spells a
  spec/capability-map/plan/todo artifact path differently from the canonical
  set (the drift class fixed in c4584dd); `tools/validate-artifact-paths-test.py`
  covers the allow and deny cases.
- [Workflow checks](tools/tests/workflow/README.md) document the isolated
  Jira/spec/plan/build/review runner, its invocation, and what its evidence
  does not cover.
- Changed instructions need focused behavioral checks when their decisions or
  orchestration change; syntax and valid paths alone do not establish behavior.

Update this overview when ownership, installation paths, host adaptation, or
execution boundaries change. Keep detailed policy in its existing source and
link to it here. Record genuine new architectural choices in the ADRs.
