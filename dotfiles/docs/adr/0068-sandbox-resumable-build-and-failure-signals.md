# OS sandbox, resumable `/build`, and failure signals from transcripts

Drawn from two LangChain guides read 2026-10-02 ("The Engineering Guide to
Long-Horizon Agents in Production" and "The Agentic Operating Model"). Most of
both concerns hosting agents for many users and does not apply here; four
ideas do.

**Decision — Bash sandbox on, credentials denied.** Both guides: only isolation
protects the host, and credentials never enter the sandbox. The hooks match
command text and can be routed around (first harness review). `settings.json`
enables Claude Code's sandbox with `autoAllowBashIfSandboxed`, lets it write
the package-manager caches (`~/.cache`, Composer, npm, Yarn, pnpm), denies
sandboxed commands `~/.ssh`, `~/.aws`, `~/.config/gh`, `~/.git-credentials`,
Docker, npm, Composer, Claude and Codex credential files, unsets token
variables, and pre-allows the package and GitHub hosts. The validator pins
`enabled` and the four core credential paths.

The Linux sandbox has its own network namespace with no route to localhost and
no SSH, so database-backed commands (`php artisan *`, `composer test*`,
PHPUnit/Pest), `docker`, `mysql`, `redis-cli`, `ssh`, and git fetch/pull/push
are excluded: they run unsandboxed through the normal permission flow and
hooks. The approver kept `Bash(php *)` and `Bash(find:*)` allowed; with
`php artisan *` excluded, PHP execution stays outside the boundary by that
choice. Without `bubblewrap` and `socat` Claude Code silently runs unsandboxed
(`failIfUnavailable` is left off so a missing dependency does not lock the
machine out); check `/sandbox` once per machine.

**Decision — `/build` resumes from committed progress.** Durable execution
checkpoints every step; here the durable record is git. Each task packet
carries `Status: Pending`, and the executor's commit that completes the task
flips it to `Done` in that same commit, so progress lives with the code and the
tree stays clean for `/review`. `/build` reads statuses at `HEAD` and skips
`Done` tasks, so a crashed, compacted or fresh session resumes at the first
unfinished task. A status flip is progress, not a plan revision. Writing
progress from `/build` itself was rejected: it leaves uncommitted changes that
fail the candidate-identity check.

**Decision — failure signals from transcripts.** Both guides close the loop
from traces to fixes; here that loop is the observation log, filled by eye.
`run-metrics.sh` now reports errored and denied tool results (with targets),
handoff-gate blocks, turn-cap mentions and repeated identical commands, across
main session and subagents. The LD-380 `/plan` run — 15 of 23 tool results
denied, reported as a footnote — is the case it would have counted.

**Decision — a fixed failure leaves a check behind.** From "regression datasets
curated from previously resolved failures": an observation-log row reads
`Fixed — <check>` only when it names the test, eval expectation, workflow case
or failure signal that now catches a recurrence; a prose-only change is
`Mitigated`.

**Rejected** — the guides' gateway, multi-tenancy, no-code builder rings,
scheduled runs, per-agent owners and three-tier risk taxonomy: either
multi-user hosting concerns or already covered by `verification-triggers.md`
and `reviewer-triggers.md`.
