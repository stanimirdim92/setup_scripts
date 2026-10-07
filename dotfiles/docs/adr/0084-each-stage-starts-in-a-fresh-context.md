# Each pipeline stage starts in a fresh context

**Context.** Every request re-reads the whole context from cache. A stage that
runs after another in the same session pays for the earlier stage's
conversation on each of its requests. The LD-380 harness test ran intake,
`/spec` and `/plan` in one session (2026-10-07, main session, one usage per
reply):

| Stage | Requests | Context at start → end | Cache read |
|---|---|---|---|
| intake | 12 | 78k → 145k | 1.38M |
| `/spec` | 40 | 147k → 270k | 8.54M |
| `/plan` | 11 | 272k → 312k | 3.21M |

`/spec` carried about 48k of raw Jira JSON from intake. The intake summary
that replaced it is about 5k. `/plan` carried the whole spec conversation,
but it reads the committed spec from disk anyway. A fresh context per stage
would have saved about 2.6M and 1.9M of cache read. That is about a third of
the session's 13.5M.

`/spec` could not start fresh: it accepted intake only from the current
conversation, and intake wrote no file.

**Decision.**
- Intake saves its summary to `docs/specs/<TICKET>-intake.md`, with the fetch
  date. It is the only file intake writes. `/spec` accepts that file as the
  complete intake.
- Intake, `/spec` and `/plan` end by recommending `/clear` before the next
  stage. In Codex, the wrappers say to start the next stage in a new session.
- The spec holds every recon conclusion planning needs. `/plan` no longer
  sees the recon report, so a chat-only conclusion is lost.

**Cost.** A stage cannot reuse the previous stage's recon or chat. Anything
it needs must be in the committed file. That was already the rule for
`/build`, and the spec skill already asked for it.
