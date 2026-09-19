# Codex native roles and hook adapters

**Decision.** Keep `dotfiles/claude/AGENTS.md` as the single global instruction
source and link both `~/.codex/AGENTS.md` and Claude's global entry point
`~/.claude/CLAUDE.md` to it. Claude 2.1.277 added project `AGENTS.md` discovery;
its documented global entry point remains `CLAUDE.md`. No retired source copy
is recreated. Link setup checks every source exists before mutating destinations,
so a source rename cannot silently install dangling links again.

**Decision.** Preserve the user's explicit Claude session `opus[1m]` selection.
The frontmatter validator accepts that extended-context alias as well as the
previous `claude-opus-5` session pin, while retaining strict version pins for
personas. This narrows only the session-pin check from [0056](0056-role-tiered-models-blind-review-recon-width-writer-isolation.md);
it does not turn persona model validation into a floating-alias check.

**Decision.** Add standalone native Codex roles while keeping persona bodies,
skills, task packets, and workflow gates shared. Executor, test-engineer, and
repo-recon use `gpt-5.6-sol` / high. Code-reviewer, blind-reviewer,
security-auditor, distributed-systems-reviewer, and executor-high use
`gpt-6-astra` / high. The orchestrator keeps the user's session model. The
separate executor-high role is necessary because a native role's model pin
overrides per-call model arguments. This extends the role-tiering decision in
[0056](0056-role-tiered-models-blind-review-recon-width-writer-isolation.md)
to Codex without interpreting Claude model names as Codex configuration.

**Decision.** Native role files disable nested agents and set sandbox defaults.
Fresh dispatch packets load the shared persona and selected skills explicitly;
review contexts remain independent, with no conversation fork or implementer
narrative given to a blind reviewer. A surface that lacks native-role selection
must pass the configured model and effort explicitly and disclose that role
hooks and sandbox defaults are unavailable there. Task names are not role
selectors. Required enforced boundaries block that fallback; they cannot be
replaced with a claim that a prompt supplied structural isolation.

**Decision.** Adapt Codex hook payloads to the existing shared shell policies
instead of copying their command patterns. Global hooks cover startup reporting,
destructive commands, push approval, isolated test runners, writer dispatch,
and writer handoff fields. Native role PreToolUse hooks additionally deny writer
publication, check branch/infrastructure before writer shell or patch calls,
and restrict recon/review shell operations to reads. The trusted hook command
supplies the role, rather than trusting a model-supplied role in a tool payload.
Codex handoffs use `last_assistant_message`, not Claude's transcript format, and
block at most once. This extends [0055](0055-multi-agent-enforcement-and-parallel-when-safe.md)
and replaces the instruction-only Codex guard described in
[0058](0058-sequential-ticket-checkout-and-infrastructure-readiness.md)
where native role hooks are supported and trusted.

**Decision.** Preserve Codex's hook trust review. Newly installed or changed
hooks are inactive until the user trusts their definitions through `/hooks`.
Tests exercise registered commands, representative real Git states, malformed
payloads, read-only restrictions, and handoff behavior without a model call.
They prove adapter behavior, not a completed live build or universal tool
coverage. Hooks do not parse arbitrary shell programs; `write_stdin` and some
specialized tool paths do not rerun PreToolUse. Parent runtime permission
overrides can supersede role sandbox defaults. Worktree and mutable runtime
resource isolation still belong to orchestration, including a separate verifier
checkout. These limits are part of the runtime contract, not hidden exceptions.

**Rejected — duplicate the Claude harness for Codex.** Independent persona
bodies and policy patterns would drift while preserving the same intended
workflow. The maintained client layer needs only model/config declarations,
payload translation, and explicit runtime capability handling.

**Rejected — rely on Claude frontmatter or role names alone.** Neither selects
a Codex model, activates a Codex hook, or changes a subagent's permissions.

**Rejected — bypass trust or claim hooks are a sandbox.** Installing configuration
does not authorize changing Codex's persisted trust state. Command guards are
useful accident prevention, but tool coverage and runtime overrides prevent an
honest claim of complete Claude/Codex enforcement parity.
