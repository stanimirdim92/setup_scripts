# Sequential ticket checkout reuse and project infrastructure readiness

**Decision.** Sequential executors inherit the ticket checkout, so
`dotfiles/claude/agents/executor.md` no longer declares unconditional
`isolation: worktree`. `dotfiles/claude/commands/build.md` explicitly requests it
for every concurrent writer and verifies each assigned checkout; runtime
isolation remains mandatory. This narrows only the executor-isolation decision
in [0056](0056-role-tiered-models-blind-review-recon-width-writer-isolation.md).
The test-engineer's isolated checkout, independent review contexts, configured
models, and `worktree.baseRef: head` remain unchanged. One worktree per ticket
already isolates sequential implementation; another child checkout creates
extra dependency installations, database namespaces and integration work
without isolating concurrent writers that do not exist.

**Decision.** The existing PreToolUse writer guard now denies detached HEAD,
missing/unverifiable cwd, Git identity, default-branch identity in the main
checkout, and malformed dispatch input instead of allowing on failure. Valid
read-only personas remain unrestricted. JSON parsing uses jq with Python 3 as
a fallback; absent or broken parsers cannot silently authorize dispatch. This
supersedes the fail-open portions of
[0057](0057-worktree-base-guards-at-the-session-level.md). Linked ticket
worktrees and verifiable non-default branches remain supported. These checks
are necessary when a sequential executor writes directly into the session's
checkout, and also protect the integration destination of isolated writers.

**Decision.** The startup and dispatch hooks share
`dotfiles/claude/hooks/worktree-readiness.sh`. A project can expose executable
`bin/worktree-doctor.sh --infrastructure`: a nonmutating check with no project
dependency requirement, exit 0 when current, nonzero with actionable diagnostics
otherwise. Hooks bound it to five seconds. Startup warns and writer dispatch
denies on failure, even when a ticket already contains commits. A checkout
without the doctor is stale when Git's main registered checkout has it; a
project that provides no doctor retains existing behavior. Git's null-delimited
registered paths include external worktrees and paths containing spaces.
Codex performs the same pre-dispatch contract explicitly because Claude hooks
do not run there. The existing stale-base warning remains limited to default
branches and fresh tickets; infrastructure drift does not authorize an
arbitrary merge into an active ticket.

**Rejected — unconditional child worktrees for sequential executors.** The
worktree-per-ticket boundary already separates the implementation from other
tickets. Always creating another checkout multiplies setup, database ownership
and retirement work without any concurrent implementation to separate. Parallel
writers still require explicit child isolation.

**Rejected — disable independent verifier isolation.** Test engineers may add
test-only changes and must verify the selected candidate independently. Reducing
implementation setup does not justify sharing the verifier's mutable checkout.

**Rejected — treat every behind-default ticket as stale.** Active tickets are
normally behind the default branch. A project-owned compatibility check can
identify actual runner drift without demanding unrelated merges.

**Rejected — let failed guard checks authorize writers.** A missing cwd, parser
or Git identity is no evidence that a writing destination is safe. Denial names
the repair; valid read-only agents still pass without checkout requirements.

**Decision.** `tools/test-worktree-hooks.sh` exercises real Git fixtures and
stub project doctors, including malformed input, missing tools, detached HEAD,
external paths, mid-ticket drift, and both Agent/Task dispatch. Frontmatter
validation preserves verifier isolation while rejecting unconditional executor
isolation. These prove local hooks and declarations; they do not claim a live
Claude dispatch was exercised.
