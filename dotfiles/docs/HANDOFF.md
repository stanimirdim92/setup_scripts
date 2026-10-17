# Handoff — harness work, 2026-10-07 to 2026-10-12

The state at the end of one long session, so the next one can start cold.
Replace this file at the next handoff; git keeps the old ones.

## State

- Branch `main` holds everything (last commit `3b7c3ff`). The session branch
  `claude/dotfiles-harness-review-gtsrw6` matches it.
- All 28 CI checks pass locally.
- ADRs end at 0093 (0087–0088 came from other sessions).

## What changed in this period

**Measurement tools fixed (numbers before 2026-10-07 are suspect):**
- `run-metrics.sh`: one usage per reply (it counted about 2.5× too high),
  reads subagent transcripts, finds worktree sessions, counts sandbox
  failures apart from denials.
- `plan-recall/recall.py`: reads every path on a Files bullet, counts a
  planned entry once.
- `spec-eval/run.py`: fixture base must be the code before the ticket
  (`--at`), keeps `export-ignore` paths such as `tests/`, allows the spec
  check, matches terms in the forms a spec writes them (at judge time), and
  ignores the intake's own "left out" list in the date check.

**Pipeline:**
- Each stage starts in a fresh context (ADR 0084). Intake saves
  `docs/specs/<TICKET>-intake.md`; `/spec`, `/plan` and intake end with
  "`/clear`, then the next stage".
- Rule conflicts fixed: test-engineer commits carry `Refs:`; the bugfix
  template passes check-spec; `/ship` blocks on "Weakened tests: Not
  verified"; `Task:` only on planned commits; `/plan` works from the spec.

**Security and the public repo:**
- The OS sandbox is off by the owner's choice (ADR 0085). Credential files
  keep `Read` denials, and shell commands that name them are denied
  (ADR 0086).
- `~/.codex/config.toml` is a local file. `codex/install-config.py` merges
  the harness base into it. CI lints the base for machine state.
- `spec-batch.txt` is gitignored; `spec-batch.example.txt` shows the format.
- Push, PR create, PR merge and release ask. Project `.mcp.json` servers are
  not auto-trusted.
- Codex personas follow the Claude MCP grants.
- Old commits still hold the leaked Codex config, the backlog and the
  `.trash` skills. The owner chose not to rewrite history.

**Code review, from Anthropic's write-up (2026-10-17):**
- Review converges in three rounds; later rounds see only the fix diff
  (ADR 0089).
- Pre-existing findings do not block; `/ship` tracks them as follow-ups
  (ADR 0090).
- A project `REVIEW.md` guides every reviewer; template in
  `references/templates/review.md` (ADR 0091).
- Every BLOCKER gets an independent check (ADR 0092).
- `tools/evals/review-eval/` and `tools/run/review-noise.py` (ADR 0093).

## Measured results

- LD-380 single-session run: $9.75. About a third of the cache reads would
  go with a fresh context per stage.
- LD-380 plan coverage: 69% of existing files (`observation-log.md`
  §Plan recall). The original 08-27 plan cannot be scored.
- Spec-eval on LD-380: two runs of one harness differ by 3–4 of 35 terms.
  A change must beat that to count.
- `repo-recon` on Haiku 5.5 scored worse than Sonnet 5.5. Rejected
  (`IDEAS.md`).

## Open items

1. **Owner, on the machine:**
   - before the next `git pull`, run the steps in `dotfiles/README.md` for
     `~/.codex/config.toml` and keep a copy of `spec-batch.txt`;
   - re-trust the Codex hooks in `/hooks` (`hooks.json` changed);
   - delete the remote branch `experiment/haiku-recon`
     (`git push origin --delete experiment/haiku-recon`) and the worktree
     `../setup_scripts-haiku`. The cloud session could not delete it.
2. **Re-score LD-442 plan coverage** with the fixed `recall.py`. The logged
   miss of `lang/de/ticker.php` was a parser bug (`observation-log.md`).
3. **Spec-eval baseline:** keep `spec-eval/base1/` and `base2/` (Sonnet,
   after the `tests/` fix). Compare every harness change against `base1`.
4. **Repeated spec misses to work on:** the existing duplicate check
   (`buildHashAdvertiser`) and every UI entry point. Both point at recon.
   Change the recon brief, then measure with spec-eval.
5. **Next ticket:** run intake → `/clear` → `/spec` → `/clear` → `/plan`,
   with `/cost` before each `/clear`, to confirm the fresh-context saving.
6. **Code review:** put a `REVIEW.md` in leadbuster (a draft was given in
   the session), build 3–5 review-eval cases from real bugfixes plus 2 clean
   commits, and run a baseline.
7. **Proposed, not built:** a measurement script (`eval-ticket.sh`) that
   runs plan coverage, spec-eval and run-metrics in one go; and dropping
   plan approval when check-plan is clean (from the AMPECO comparison).

## Rules the owner set

- Do not rewrite or delete git history.
- Keep `Bash(php *)` and `Bash(find:*)` allowed.
- Git tags are allowed locally; agents never push them.
- Never commit ticket content, eval fixtures or the Figma skill.
- No model identifiers in commits. No PRs unless asked.
- Commit on the session branch, merge `origin/main`, push to `main`.
