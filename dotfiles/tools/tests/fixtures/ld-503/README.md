# LD-503 reports, 2026-10-20

The stage reports of the first real ticket through `ticket.py`, as the
commands wrote them, for the replay test (HR-1 REQ-008). Each file name
says what the runner should do with it. The owner's Slack channel, email
and user id do not appear in them; commit shas are the ticket's.

| File | Stage | Expected route | What happened that day |
|---|---|---|---|
| `01-build-blocked-req-001.md` | /build | /spec (REQ-001) + owner (schema drift) | stop 1, a real decision; the runner stopped |
| `02-build-blocked-note-contradicts-spec.md` | /build | /spec (REQ-001) | stop 2; the runner built again instead of /spec |
| `03-build-blocked-req-008-and-cp-001.md` | /build | /spec (REQ-008) + owner (red baseline) | stop 3; the conflict cap stopped it |
| `04-build-blocked-route-plan-or-spec.md` | /build | /spec (REQ-008) | stop 4; the wording was not recognised |
| `05-build-blocked-handed-on-tasks.md` | /build | /test (T007), owner (T008) | stop 5; build.md could not hand tasks on |
| `06-verify-no-result-line.md` | /test | none (no HANDOFF line) | stop 6; the verifier ran in the background |
| `07-build-complete-handed-on.md` | /build | /test | the first run that went on by itself |
| `08-verify-fail-two-findings.md` | /test | /build (D-1) + /spec (D-2) | a real failure: a stale URL key, and a style decision |
| `09-verify-fail-repro-patch.md` | /test | /build (REQ-017) + /spec (REQ-009) | the earlier /test on the same candidate, with a repro patch |
