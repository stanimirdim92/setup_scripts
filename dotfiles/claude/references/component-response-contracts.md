# Component Response Contracts

Every component in this harness that another component consumes — a hook feeding
the host runtime, a persona feeding an orchestrating command, a command feeding
the next command or the human — communicates through a fixed response shape.
This document is that shape, catalogued once per component and grouped by kind,
per rule 8 (Modules Communicate Through Contracts, `AGENTS.md`): consume the
published interface, never the implementation behind it.

This is a reference, not the source of truth. When a hook, agent, or command
changes its output shape, edit that file first; update this document in the
same change. Nothing automated checks that this document still matches its
sources — review it whenever a file listed below changes shape.

## 1. Claude hooks

Eight hooks live in `../hooks/`. Each is a `PreToolUse`, `SubagentStop`, or
`SessionStart` script that reads one JSON object on stdin and prints one JSON
decision object on stdout, always exiting 0 — the decision, not the exit code,
is what the host runtime acts on (per
[code.claude.com/docs/en/hooks](https://code.claude.com/docs/en/hooks)).

| Hook | Event / matcher | Scope | Response shape |
|---|---|---|---|
| `block-agent-push.sh` | `PreToolUse` (`Bash`) | `executor`, `test-engineer` only (via their frontmatter `hooks:`) | `permissionDecision: "deny"` |
| `block-destructive-bash.sh` | `PreToolUse` (`Bash`) | global | `permissionDecision: "deny"` |
| `warn-force-push.sh` | `PreToolUse` (`Bash`) | global | `permissionDecision: "ask"` |
| `require-isolated-test-runner.sh` | `PreToolUse` (`Bash`) | global, evidence-gated | `permissionDecision: "deny"` or silent allow |
| `require-worktree-for-writers.sh` | `PreToolUse` (`Agent`\|`Task`) | dispatch of `executor`/`test-engineer` only | `permissionDecision: "deny"` or silent allow |
| `require-handoff-report.sh` | `SubagentStop` | `executor`, `test-engineer` only | `decision: "block"` or silent allow |
| `warn-stale-base.sh` | `SessionStart` (`startup`\|`resume`) | global | `systemMessage` + `additionalContext`, or silent |
| `worktree-readiness.sh` | not a hook — a sourced shell function | shared library | `0`/`1` return + one line on stdout |

### `PreToolUse` deny/ask — `{hookSpecificOutput: {hookEventName, permissionDecision, permissionDecisionReason}}`

`block-agent-push.sh`, `block-destructive-bash.sh`, `require-isolated-test-runner.sh`,
and `require-worktree-for-writers.sh` all deny with:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "<one paragraph, addressed to the caller>"
  }
}
```

`warn-force-push.sh` uses the same envelope with `"permissionDecision": "ask"` —
the one hook in this set that interrupts for confirmation rather than refusing
outright, reserved for a force-push to `main`/`master`, `push --mirror`, and a
plain push from a local IDE session (`CLAUDE_CODE_REMOTE` unset).

A command not matched by the hook's own trigger condition produces no stdout at
all — an empty response is a silent allow, not a passing decision to report.

**Consumers and specifics:**

- **`block-agent-push.sh`** denies `git push` in every spelling (aliases and
  common typos normalized first) and the `gh` commands that publish without the
  word push (`pr create`, `pr merge`, `release create`, `repo sync`). Scoped to
  the two writer personas by their own frontmatter, not globally.
- **`block-destructive-bash.sh`** hard-blocks a fixed list of destructive
  commands, globally, regardless of persona.
- **`require-isolated-test-runner.sh`** denies a bare `php artisan test` /
  `phpunit` / `paratest` invocation only when *both* conditions hold: the
  project ships `bin/worktree-test.sh`, and more than one Git worktree is
  currently live. Either missing, it allows silently — this hook never assumes
  a project wants the discipline. The denial reason names the replacement
  command (`composer test`) and explains the shared-database failure mode it
  prevents.
- **`require-worktree-for-writers.sh`** gates dispatch of `executor`/
  `test-engineer` via the `Agent`/`Task` tool. It denies when: the dispatch
  input cannot be verified (missing/malformed JSON, non-string fields); `cwd`
  is missing, unreadable, or not a verifiable Git checkout; `HEAD` is detached;
  the checkout is the default branch in the main (non-worktree) checkout; or
  `worktree_infrastructure_ready` (below) reports not-ready. A parser failure
  (no `jq` and no `python3`) still returns a valid deny JSON via a
  dependency-free fallback string, never a raw shell error.

### `SubagentStop` block — `{decision: "block", reason}`

`require-handoff-report.sh` reads the writer persona's last assistant message
from its transcript and denies completion with:

```json
{"decision": "block", "reason": "Handoff report incomplete — add: <missing pieces>. The orchestrator accepts evidence, not a completion claim."}
```

It checks for three things by pattern, not by meaning — a shape check, not a
truth check: verification language paired with an outcome word, the word
`commit`, and working-tree language. Missing any one names it in `reason`. It
blocks **at most once** (`stop_hook_active` guards the retry) and allows
silently on any transcript-read failure, so a broken hook can never wedge a
build. Scoped to `executor`/`test-engineer` only; every other persona passes
through untouched.

### `SessionStart` — `{systemMessage, hookSpecificOutput: {hookEventName, additionalContext}}`

`warn-stale-base.sh` runs at session start and warns, never blocks (a
`SessionStart` hook has no deny path):

```json
{
  "systemMessage": "<the same warning, verbatim>",
  "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "<the same warning, verbatim>"}
}
```

It fires under exactly two conditions: the checkout sits *on* the default
branch and is behind `origin/<default>` (`git pull` fixes it), or a fresh
ticket worktree carries no commits of its own yet and is behind (its base was
already stale when `claude --worktree` branched from local `HEAD`). Every
other arrangement — ongoing branch work, a checkout already current — produces
no output. It also folds in the infrastructure-readiness check (next section)
ahead of the Git-base check, so both concerns surface in one startup message.
Called with `--report`, it emits this JSON directly; this is the entry point
the Codex adapter (§2) reuses.

### Shared library — `worktree_infrastructure_ready(top)`

Not a hook. A shell function sourced by `require-worktree-for-writers.sh` and
`warn-stale-base.sh`. Contract: **return 0 with no output on ready, return 1
with one explanatory line on stdout on not-ready.** It looks for the project's
own `bin/worktree-doctor.sh --infrastructure`; when absent, it falls back to
comparing the current worktree against the main checkout for that same file.
Callers turn a `1` into their own response shape (a `deny` in the writer-dispatch
hook, a plain warning line in the session-start hook) — this function never
speaks the hook protocol itself.

## 2. Codex hook adapter

Codex has one native hook entry point per event, not eight. `../../codex/hooks.json`
routes `SessionStart`, `PreToolUse` (`Bash`\|`Agent`\|`spawn_agent`), and
`SubagentStop` (writer roles only) to a single script:

```
python3 "$HOME/.codex/hooks/policy.py" [role]
```

`policy.py` is the only Codex-side hook logic. It normalizes the Codex payload
shape to the Claude one, then **calls the same eight bash hooks above as
subprocesses** (`SHARED = .../claude/hooks`), passing through their JSON output
byte-for-byte when they return one. The two harnesses share one set of policy
reasons; nothing is reimplemented or restated in Python.

**Response shape by event**, matching Claude's own envelopes:

| Event | Response |
|---|---|
| `SessionStart` | delegates entirely to `warn-stale-base.sh --report` |
| `PreToolUse` | `{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision, permissionDecisionReason}}` |
| `Stop` / `SubagentStop` | `{decision: "block", reason}` or `{}` |

**What `policy.py` adds beyond delegation:**

- **Role-scoped dispatch denial.** A Codex persona itself may never dispatch
  another agent (`Harness personas may not dispatch other agents.`) — Codex has
  no per-persona tool grant to enforce this by omission, so the adapter denies
  it explicitly for every role.
- **A read-only shell allowlist** (`read_only_shell()`) for the five reader
  roles (`repo-recon`, `code-reviewer`, `blind-reviewer`, `security-auditor`,
  `distributed-systems-reviewer`), because Codex sandboxing has no equivalent to
  Claude's `tools:` frontmatter grant. It permits a fixed command set (`pwd`,
  `ls`, `cat`, `head`, `tail`, `nl`, `wc`, `stat`, `readlink`, `realpath`,
  `true`, bounded `rg`/`sed -n`, and `git --no-pager {status,diff,show,log,...}`
  with `--no-ext-diff --no-textconv` on diff/show/log) and denies everything
  else with `permissionDecisionReason: "This persona may only read repository
  evidence..."`. Edits, notebook/REPL tools, and any further dispatch are
  denied outright for readers regardless of shell content.
- **Unrecognized role** (not in the writer or reader sets) raises and is
  reported through the same failure path below — never silently allowed.
- **A single failure path.** Any parse, subprocess, or validation failure
  becomes, per event: a `SessionStart` context message, a `Stop`/`SubagentStop`
  block, or a `PreToolUse` deny — each carrying `"Codex harness policy could not
  verify this call: <error>"`. Codex never receives a bare stack trace or a
  silent pass on a broken hook input.

## 3. Claude agent report contracts

Seven personas live in `../../claude/agents/`. Each is invoked with a bounded
task packet and returns one report in a fixed shape; `docs/agents.md` names who
dispatches each one and when.

| Persona | Report shape | Finding ids |
|---|---|---|
| `repo-recon` | `## Recon: [area]` markdown template | — |
| `executor` | bullet-list handoff (consumed by `require-handoff-report.sh`, §1) | — |
| `test-engineer` | bullet-list evidence-per-`REQ-###`, or `## Test Coverage Analysis` template | — |
| `code-reviewer` | `## Review Summary` template, `APPROVE`\|`REQUEST CHANGES` | `CODE-N` |
| `blind-reviewer` | `## Blind Review` template | `BLIND-N` |
| `security-auditor` | `SEC-N` findings list | `SEC-N` |
| `distributed-systems-reviewer` | `DIST-N` findings list | `DIST-N` |

### `repo-recon`

```markdown
## Recon: [area]

### Rules and precedent
- [rule or convention] — `path:line`

### Verification
- Framework/location/fixtures: [...]
- Repository-defined commands: [exact commands]

### Constraints
- [what this area depends on / what depends on it]

### Unknowns
- No precedent found for: [aspect or None]
- Not surveyed: [excluded area and why, or None]
```

Reads widely; only pointers, verification, constraints, and unknowns leave its
context — its own reads never enter the caller's.

### `executor`

No fenced template — a fixed bullet checklist that `require-handoff-report.sh`
(§1) and `commands/build.md` both parse by content, not by markup:

- behavior implemented; tests added/changed;
- exact verification commands and outcomes;
- workstream verification when applicable;
- required checks not run and why;
- commit message/id;
- working-tree state;
- required scope expansion; anything noticed but untouched;
- blocker, if incomplete.

### `test-engineer`

Dispatched by `/test`: one evidence entry per in-scope `REQ-###` (test/check,
exact command and outcome, candidate/version, unverified portion — evidence
provenance distinguished from inherited results and code reasoning), reproduced
defects, test-only files/commits and tree state, required checks not run.
Asked only for coverage analysis instead, it returns the `## Test Coverage
Analysis` template (Current Coverage / Recommended Tests / Priority).

### `code-reviewer`

```markdown
## Review Summary

**Verdict:** APPROVE | REQUEST CHANGES

**Overview:** [1-2 sentences]

### Critical Issues
- [CODE-1] [file:line] (confidence: high|med|low) [problem + fix]

### Important Issues
- [CODE-2] ...

### Suggestions
- [CODE-3] ...

### What's Done Well
- [...]

### Verification Story
- Tests reviewed / Build verified / Security checked / Not verified
```

`REQUEST CHANGES` while any Critical or Important finding is unresolved,
`APPROVE` otherwise — a review recommendation, never a release verdict.

### `blind-reviewer`

```markdown
## Blind Review

**What this change appears to do:** [2-4 sentences, read from the diff alone]

### Critical
- [BLIND-1] [file:line] (confidence: high|med|low) [...]

### Important
- [BLIND-2] ...

### Suggestions
- [BLIND-3] ...

### Intent-dependent
- [BLIND-4] [file:line] [the two readings, and what would settle it]

### Not verified
- [what could not be determined, and the command/file that would settle it]
```

Receives the diff alone — no spec, plan, acceptance criteria, or goal. "What
this change appears to do" and the Intent-dependent section are unique to this
persona; `/review` (§5) is the only place both get resolved, since only it
holds the diff and the actual intent together.

### `security-auditor`

`SEC-N`, severity, confidence, file:line, attack path/failure mode, impact,
specific remediation. Severity: **Critical** (broad compromise/breach) /
**High** (significant, practical exploit) / **Medium** (limited/conditional) /
**Low** (defense-in-depth) / **Info** (non-blocking). No GO/NO-GO, no dispatch
of another agent.

### `distributed-systems-reviewer`

`DIST-N`, severity, confidence, file:line, failure scenario, recommendation.
Severity: **Critical** (data loss, duplicate irreversible effects, broad
outage) / **Important** (release-relevant reliability/consistency defect) /
**Suggestion** (non-blocking). No fenced template — findings are reported
inline in this shape.

### Shared conventions across all seven

Confidence (`high`/`medium`/`low`) travels separately from severity — a
low-confidence finding stays at its true severity, marked low-confidence,
rather than being downgraded. A `maxTurns` cap ending a run early is reported
as a partial result with everything unexamined named explicitly; a truncated
report is never presented as clean or complete. No persona issues GO/NO-GO,
and no persona invokes another agent or slash command — only a command or the
user orchestrates (`AGENTS.md` §Agent orchestration).

## 4. Codex roles

Eight roles live in `../../codex/agents/*.toml`, one per Claude persona plus
`executor-high` (a higher-effort/different-model variant of `executor` for
build-orchestrator-selected high-risk workstreams). **Their response contract
is not redefined — each role's `developer_instructions` explicitly directs it
to read and follow the matching file in §3**, e.g.:

```
Read ~/.codex/references/workflow-runtime.md, then ~/.claude/agents/executor.md.
... Follow the shared persona body ... Claude frontmatter does not configure Codex.
```

| Role | Claude persona followed | Model | Sandbox |
|---|---|---|---|
| `repo-recon` | `repo-recon` | `gpt-5.6-terra` (xhigh) | read-only |
| `executor` | `executor` | `gpt-5.6-terra` (xhigh) | workspace-write |
| `executor-high` | `executor` | `gpt-6-astra` (high) | workspace-write |
| `test-engineer` | `test-engineer` | — | workspace-write |
| `code-reviewer` | `code-reviewer` | — | read-only |
| `blind-reviewer` | `blind-reviewer` | — | read-only |
| `security-auditor` | `security-auditor` | — | read-only |
| `distributed-systems-reviewer` | `distributed-systems-reviewer` | — | read-only |

`[agents] enabled = false` on every role (no further dispatch), and every role
wires `[[hooks.PreToolUse]]` to `policy.py <role-name>` (§2) as its enforcement
— Claude enforces the same boundary through tool grants and hook frontmatter
instead, but the response shape each role produces is identical either way.

## 5. Command stage-gate contracts

Six commands in `../../claude/commands/` own the pipeline
(`docs/agents.md`): `/spec -> /plan -> /build -> /review -> /ship`, with `/test`
as an optional branch before `/review`. Each ends in exactly one named terminal
state and, except `/ship`, writes an artifact to a fixed path.

| Command | Artifact | Terminal states |
|---|---|---|
| `/spec` | `docs/specs/[TICKET]-SPEC.md`, or `[TICKET]-CAPABILITY-MAP.md` + `[TICKET]-SPEC-<module-id>.md` | Draft \| Needs reapproval \| Approved |
| `/plan` | `docs/tasks/[TICKET]-plan.md` / `-todo.md`, or a bounded `SPEC CONFLICT` | Draft \| Needs replan \| Approved, Ready for `/build` |
| `/build` | scoped local commits | **BUILD COMPLETE** \| **BUILD BLOCKED** |
| `/test` | test-only commits | **VERIFY PASS** \| **VERIFY FAIL** \| **VERIFY BLOCKED** |
| `/review` | — (a report only) | disposition table (below) |
| `/ship` | — (a decision only) | **GO** \| **NO-GO** \| **SHIP BLOCKED** |

### `/build` → BUILD COMPLETE / BUILD BLOCKED

**BUILD COMPLETE** only when every selected task is implemented, every
workstream integrated, every plan checkpoint in scope executed and passed,
required verification is green with executed evidence, scoped local commits
are complete (or the uncommitted exception was explicitly requested), and the
tree is in the expected state. **BUILD BLOCKED** in every other terminal
state — never reported with open blockers, skipped checkpoints, or unimplemented
selected tasks. Both include: tasks/workstreams completed or blocked (with
blocker and routing stage), checkpoints and outcomes, commits, exact
verification commands/outcomes, required scope expansions, untouched items
noticed, branch/tree state, the full candidate identity, and actual run
metrics when exposed (never estimated).

### `/test` → VERIFY PASS / FAIL / BLOCKED

**PASS** requires evidence for every in-scope acceptance criterion, required
checks passing, no known in-scope production defect, and test-only changes
committed — reported one line per `REQ-###` with its evidence, provenance kept
distinct (inherited/code-reasoning vs. executed here). **FAIL** reports the
failing behavior/criterion with its `REQ-###`, reproduction, expected vs.
actual, and the handoff back to `/build`. **BLOCKED** covers scope/identity,
missing handoff/evidence, environment, permissions, or unrelated pre-existing
failures — a reproduced production defect is FAIL, not a blocker. Any
production-code fix invalidates a prior VERIFY result.

### `/review` → disposition table + requirement evidence

Every reviewer's native severity maps to one of three canonical dispositions:

| Source | Native severity | Disposition |
|---|---|---|
| `code-reviewer` | Critical | BLOCKER |
|  | Important | REQUIRED |
|  | Suggestion | ADVISORY |
| `blind-reviewer` | Critical | BLOCKER |
|  | Important | REQUIRED |
|  | Suggestion | ADVISORY |
|  | Intent-dependent | resolved by `/review` itself |
| `security-auditor` | Critical, High | BLOCKER |
|  | Medium | REQUIRED |
|  | Low, Info | ADVISORY |
| `distributed-systems-reviewer` | Critical | BLOCKER |
|  | Important | REQUIRED |
|  | Suggestion | ADVISORY |

Report includes: candidate branch/diff scope, BUILD candidate and any accepted
post-BUILD test-only commits, **Independent verification: NOT REQUIRED \|
PASS**, required-reviewer list and trigger decisions, each reviewer's result,
every finding with disposition and its `REQ-###` where applicable, and one
requirement-evidence line per spec `REQ-###` (implementation + verification, or
an explicit gap — `/ship` blocks on a missing entry). Confidence travels with
each finding so `/ship` can tell a confirmed BLOCKER from a suspected one.

### `/ship` → GO / NO-GO / SHIP BLOCKED

```markdown
## Ship Decision: GO | NO-GO | SHIP BLOCKED

### Blockers
- ...

### Required findings / refutations / accepted risks
- ...

### Requirement evidence
- REQ-001: [implementing change] / [verification evidence]

### Release-readiness
- Infrastructure: ...
- Documentation: ...

### Rollback plan
- Trigger conditions: ...
- Procedure: ...
- Recovery target: ...

### Candidate
- Branch:
- Commits:
- Diff/status:
```

GO requires an unchanged reviewed candidate, independent verification
satisfied exactly as REVIEW required, no unresolved BLOCKER, every requirement
carrying both implementation and verification evidence, every REQUIRED finding
resolved/risk-accepted/deferred with a reason, passed release-readiness
attestations, a concrete rollback plan, and an explained tree state. **GO is a
readiness verdict only — it does not authorize push, tag, deploy, release,
protected-branch mutation, or history rewriting.**

## 6. Operator tools

Scripts under `../../../tools/` and `../../codex/bin/` are invoked directly by
a human or by CI, not dispatched as agents. Each has a fixed exit-code and
stdout contract.

### Shared validator contract

`validate-frontmatter.py`, `validate-artifact-paths.py`, and
`check-references.py` share one output shape: a per-item status line, then one
summary line.

```
<check-name>: <n> checked -- <m> problem(s) -- PASSED|FAILED
```

Item-line prefixes differ by what they guard: `ok `/`FAIL` (frontmatter),
`ok  `/`FAIL` with an indented `L<n>: <token> -- not a canonical artifact path`
(artifact paths), `BROKEN` (references). **Exit 0 when clean, 1 on any
violation** — all three, no exceptions.

| Tool | Guards |
|---|---|
| `validate-frontmatter.py` | Reviewer `tools:` grants, writer `hooks:` blocks, and the three settings.json pins stay as `docs/adr/0055` declares them |
| `validate-artifact-paths.py` | One canonical spec/capability-map/plan/todo path convention across every pipeline file that names one |
| `check-references.py` | Every relative cross-reference (`../`, `./`, `templates/`) between harness files resolves |

### `link_dotfiles.sh`

`link_dotfiles.sh [-y|--yes] [-n|--dry-run] [-h|--help]`. Prints its plan,
asks for confirmation (required non-interactively via `-y`), then links.
**Exit 0** on success or a completed dry run; **exit 1** when declined or on
any link failure, having changed nothing beyond what completed atomically.

### `run-metrics.sh`

`run-metrics.sh [session.jsonl | --list | --since T --until T | --large-lines N]`.
Reports measured-only figures (never estimated) from a transcript: tool-call
batching, token usage, main/subagent split, oversized inline results. **Exit 1**
on a missing dependency (`jq`), bad argument, or unreadable transcript; **0**
otherwise, including `--list`/`--help`.

### `batch-spec.sh`

`batch-spec.sh [-m FILE] [-p N] [-b USD] [-o DIR] [-n|--dry-run] [-y|--yes]`.
Runs `/spec` for many tickets, one worktree per job, stopping every job at the
Draft-spec gate (spec writes no migrations, binds no shared state — the
`/build` concurrency conditions don't apply to it). Per job it appends
`<slug>|<ok|FAILED|NO SPEC>|<path or log>` to a results file, then prints a
summary table. **Exit 1** if any job produced no spec (or on a setup failure);
**0** otherwise, including a dry run.

### `codex-worktree`

`codex-worktree [--dry-run] [--no-setup] TICKET [-- CODEX_ARGS...]`. Creates or
reuses `.codex/worktrees/<ticket>` on branch `codex/<ticket>`, copies
`.worktreeinclude` matches, runs the project's `bin/worktree-setup.sh` when
present, verifies checkout readiness via `require-worktree-for-writers.sh`
(§1) before and after setup, then execs `codex` in that checkout. Every
message is prefixed `codex-worktree: `. **Exit 0** on success or a completed
dry run; **exit 1** on any `RuntimeError`/`OSError`/`ValueError` (printed to
stderr as `FAILED: <reason>`, checkout retained for retry); **exit 130** on
`KeyboardInterrupt` (checkout retained). A per-ticket flock prevents two
launches of the same ticket from racing.
