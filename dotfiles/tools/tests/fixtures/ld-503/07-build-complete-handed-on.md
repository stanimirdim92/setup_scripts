# BUILD COMPLETE — LD-503

Every task that `/build` owns was already `Done` at HEAD, so this run dispatched no executors and created no commits. CP-001 passed at `090d8c88`. The only change since then is to `docs/tasks/LD-503-open.md`, so I reused that run's results instead of running it again.

**Owner notes:** The spec already records both Slack notes, so neither conflicts with it.
- The REQ-008 EXPLAIN change is DEC-010. T003 checks it: no `ALL` scan, and the pivot is read through `ix_afp_profile_advertiser`.
- The accepted CP-001 red baseline is DEC-011.

**Scope checks**
- The plan and the spec are both `Approved`.
- `git diff` between the pinned spec (`9f6f6c71`) and HEAD is empty, so the plan is current.
- `bin/worktree-doctor.sh --infrastructure` exited 0.

**Tasks**
- **Already complete:** T001, T002 and T003 (ws-backend), and T004, T005 and T006 (ws-frontend).
- **Handed on:**
  - T007 goes to `/test`: the Playwright check at 1440×960 in EN and DE.
  - T008 goes to you: the replica timing per DEC-001, with results recorded in LD-504.
- **Blocked or not started:** none.

**CP-001** ran at `090d8c88` and passed under DEC-011:
- **`composer test -- --compact`:** 585 passed, 186 failed, exit 2.
  - All LD-503 tests pass.
  - The advertiser-path and translation failures fail the same way with `main`'s versions of the six LD-503 files (15 tests).
  - No other failure is in an LD-503 file.
- **Frontend:** `yarn test` passed 650 tests, `tsc --noEmit` is clean, and `bin/worktree-setup.sh --build` passed.
- **Static checks:** phpstan and deptrac show no new findings.
- **Request keys:** the frontend sends only `detected` and `not_detected`, which `AdvertiserIndexRequest` accepts.

**Needs real-browser check** (component tests do not count as evidence):
- REQ-011: Snapshot → details → browser Back keeps both selections.
- REQ-009: closed, open and selected states, and placement against Figma.
- REQ-014: German and English labels and options show in full, without truncation.

**Tree and candidate**
- Branch `worktree-LD-503`, tree clean.
- HEAD is `80b5751fc1fef443351ea445fb116916316619e1`.
- Base is `main` at `cfa80c897aa2ba0033c160b98df3cbfa89d86f97`, which is also the merge-base.

**Run metrics:** no executors dispatched or resumed, no model overrides, no rework, no scope expansions.

Next stage: `/review`, then `/test` for T007.
