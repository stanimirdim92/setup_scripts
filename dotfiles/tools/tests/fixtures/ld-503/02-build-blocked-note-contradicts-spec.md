## BUILD BLOCKED: LD-503
I did not dispatch any executor. Your Slack note ("use 200 status code") settles the open 422 conflict. It still contradicts the approved spec, so `/build` cannot act on it yet.
**Why it stopped**
- The spec at `docs/specs/LD-503-SPEC.md:128` (REQ-001) says an invalid value MUST get HTTP 422. The two scenarios at `:140` and `:146` say the same.
- The todo copies this into T001 (`:15`) and T003 (`:107`).
- `ValidationFailedOverride` returns HTTP 200 with an `errors` body for non-Inertia requests. Your note picks that behaviour, which is option (1).
- Changing what the API returns is a behaviour change to the spec. `/build` does not edit the spec. After the spec changes, the plan is out of date and needs `/plan` again.
**Plan and spec checks**
- Plan and spec both have `Status: Approved`.
- The pinned spec `3e832161` matches the working copy exactly, so the plan is current against the spec as written.
- The worktree infrastructure check passed at session start.
**Task state at HEAD**

| Task | Status | Note |
|---|---|---|
| T004, T005, T006 | Done | Frontend work, already committed |
| T001 | Pending | Blocked by the 422 vs 200 conflict |
| T002 | Pending | Waits on T001 |
| T003 | Pending | Waits on T002; also has the 422 criterion |
| T007, T008 | Pending | Wait on CP-001, which has not run |
**Checkpoints:** none ran. CP-001 needs the backend tasks first.
**Commits:** `9f0580c7` adds your decision and the next steps to `docs/tasks/LD-503-open.md`. That one file is the whole commit, and the tree is clean.
**Verification:** I ran no tests. There was no code change.
