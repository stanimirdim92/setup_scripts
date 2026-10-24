# Lessons from LD-507: same quality, less owner time and fewer tokens

**Context.** LD-507 went through the whole pipeline on 2026-10-23 and reached
GO. The owner sent the four sessions, and an audit read every stage. The
owner set one hard rule for the fixes: quality stays the same or improves.
The audit found these problems:

- The owner read a 652-line spec for 68 minutes. It was drafted on a
  Jira-versus-Figma conflict that intake had flagged as a Blocker. The owner
  then dropped the sorting it was built on, and the spec was rewritten.
- `require-handoff-report.sh` blocked five complete executor reports. It read
  the last text block, but executors report through `SubagentHandback`.
- The spec header said Approved by while Status stayed Draft. The agent
  reported it as approved.
- `/ship` accepted an open item on its own, with no owner decision.
- The verifier ran 231 turns at about 254k context: 58.7M tokens, about $15
  of $43. It took one browser action per turn, resumed a 360k context twice,
  and waited 10 minutes in a `pgrep -f` loop that matched itself.
- /test ran before /review set the depth. /ship then had to resume the
  verifier for the full suite.
- Executors were resumed after an hour idle at 344k context. The plan needed
  two extra owner messages: pre-answering the stops, and "commit the plan".
- 24 review findings were 19 issues. The summary was too terse, so the owner
  asked "CODE-5 what? CODE-7 what?".
- `ticket-stats.py` reported 32 minutes of owner time for a 3.5-hour ticket.

**Decision.**
- `/spec` asks the questions that decide whether a requirement exists before
  it drafts. Each question has one recommended option, High included.
  Dependent questions merge into one. In interactive mode, Low questions
  and those the ticket or precedent settles are decided by default and
  listed for override. High questions always stay questions.
- `check-spec.py` fails when the approval lines disagree with Status.
- The handoff hook reads the latest handback. The requirements are unchanged.
- `/plan` asks for pre-authorizations of each foreseeable stop and commits the
  plan on approval. It probes each external tool it relies on. A stop that
  is not pre-authorized stays a stop.
- An executor is resumed only when idle under about 15 minutes and under about
  350k context (raised from 5 minutes / 150k on 2026-10-24, owner decision:
  the short window forced fresh executors on nearly every task). Review-fix rounds always start fresh, with the findings, the
  last handoff and the diff.
- `/test` works out the risk tier itself, and the higher tier wins. At Deep the
  full suite starts first, in the background. Re-verification goes to a
  fresh verifier with the last VERIFY report and the diff. When unsure, it
  re-runs.
- The verifier scripts one step per browser state. It still saves every
  screenshot, and it reads them when visuals matter. Real input tools stay
  required for focus, hover, keyboard, drag and upload.
- The base suite result is cached per base SHA and exact command.
  `junit-diff.py` compares by test identity.
- Review findings keep every id. Duplicates are grouped, and the group takes
  its highest disposition. Each line states the effect, the fix and the
  owner's choice. The new resolution `answered` cites the REQ or DEC line,
  and it is never used for a BLOCKER.
- `/ship` sets an open item only from a recorded owner decision. It ends with
  one question: apply the chosen ADVISORY fixes, or post a Jira summary.
- `ticket-stats.py` reports elapsed, agent, waiting and owner time, with a
  header row. ADR 0113 is amended.
- In worktree sessions, commands use literal or `~` paths, never a computed
  `$HOME`.

**Rejected.**
- *Lower the risk tier for an additive optional parameter.* It would drop
  the full suite, the mutation probes and the full read. The owner refused
  any loss of depth.
- *Drop screenshots and console checks to save tokens.* The evidence stays;
  only the method changes.

**Consequences.**
- The owner merged these changes before the evals ran. The evals compare
  the commit before them with the one after: review-eval for the reviewer
  changes (ADR 0111), spec-eval, and the add-business pipeline eval. A
  change behind a WORSE verdict is reverted on its own.
- Owner reading and token use should fall. The audit estimates about 40% off
  the verifier's tokens. No gate is removed.
