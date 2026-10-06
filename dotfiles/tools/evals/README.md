# evals — does the harness do good work?

Checks and tests only show that the harness is put together correctly. They
cannot show whether a change made its specs or plans better or worse. That
needs a ticket whose right answer is already known: one that shipped.

An eval runs the harness, or part of it, on such a ticket and measures how
close it gets to what really happened. Two of them run a real model and cost
money, so you run them by hand, after a ticket ships or after you change the
harness. Their scoring code has its own tests (`test_*.py`), which CI runs for
free.

| Folder | The question it answers | Cost |
| --- | --- | --- |
| `plan-recall/` | Did the plan name the files that really changed? Before coding, a plan lists the files it expects to touch. After the ticket ships, this compares that list with the real diff. 18 of 20 files named is 90%. | Free: it reads git and the plan |
| `spec-eval/` | How close does today's harness get to the spec you approved? It writes a fresh spec for a shipped ticket, on the code as it was before the work began, then compares it with the approved one. | One real `/spec` run, about $1.40. Scoring a spec you already have is free |
| `workflow/` | Does the pipeline make the right calls on small made-up cases: which reviewers run, and whether `/test` is needed? | Real model runs |

## Did my harness change help?

Score before the change and save the result, then score after it and compare
the two item by item. Both `plan-recall` and `spec-eval` take `--baseline`.
They list what was gained and what was lost, so a loss cannot hide behind a
better average. Each folder's README has the commands.

## Ticket content stays local

Real tickets are private. `spec-eval` keeps its fixtures and run output in
folders git ignores, and this repository is public. Do not commit them.
