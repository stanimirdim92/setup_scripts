# Stage handoff line

Every stage report ends with one machine-readable line. The runner
(`tools/run/ticket.py`, `tools/run/pipeline.py`) decides the next step from
this line alone; it never reads the prose above it (HR-1, REQ-001/002).

```
HANDOFF: result=<RESULT> route=<ROUTE> ids=<IDS> decide=<N>
```

- `result` — the command's own verdict, one word:
  `/plan` COMPLETE | BLOCKED · `/build` COMPLETE | BLOCKED ·
  `/test` PASS | FAIL | BLOCKED · `/review` CLEAN | FINDINGS | BLOCKED.
- `route` — who acts next, exactly one: `none` (the pipeline goes on),
  `/spec`, `/plan`, `/build`, `/test`, or `owner` (a person decides or does).
  When two parties are owed, name the one that acts first and list the rest
  in the report; the next stage raises them again.
- `ids` — what it is about, comma-separated with no spaces: `REQ-008`,
  `DEC-006`, `T007,T008`, a finding id; `-` when nothing.
- `decide` — how many numbered options the report offers a person; `0`
  when none. With `decide=n` the report holds a numbered list of n options
  and marks the recommended one.

The line is the last line of the report, after the result line the
command already writes (`BUILD COMPLETE`, `VERIFY PASS`, the review count
line). One line, no markdown around it.

Examples:

- `/build` blocked on a criterion the code contradicts:
  `HANDOFF: result=BLOCKED route=/spec ids=REQ-008 decide=2`
- `/build` done, with tasks handed on:
  `HANDOFF: result=COMPLETE route=/test ids=T007,T008 decide=0`
- `/plan` clean: `HANDOFF: result=COMPLETE route=none ids=- decide=0`
- `/build` blocked on the environment:
  `HANDOFF: result=BLOCKED route=owner ids=- decide=1`
- `/test` failed on a production defect, with a spec question too:
  `HANDOFF: result=FAIL route=/build ids=REQ-017,REQ-009 decide=1`
- `/review` with findings to fix:
  `HANDOFF: result=FINDINGS route=/build ids=CODE-1,SEC-2 decide=0`

A report without the line, or with a value outside these sets, stops the
runner with the file named. That is the intended failure: the command, not
the runner, owns the verdict.
