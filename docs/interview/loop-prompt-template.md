# Interview loop prompt

## Part A — your fill-in checklist (not part of the prompt)

Do these before you write, in order:

1. Read the agent specs. Note:
   - the tools
   - fresh context or continued context per iteration
   - the exit signal
   - the iteration cap
   - the roles
2. Number the business requirements R1..Rn. Keep the business wording, then add a threshold to each vague word.
3. For each requirement, write at least one success case and one failure or boundary case.
4. For each operational concern, mark it as required or out of scope:
   - auth and privacy
   - errors and retries
   - logging
   - data migration
   - performance
5. List the gaps. Fill each gap with an assumption (A1..An), or mark it "do not guess".
6. Delete every section the agent specs already cover. Delete every placeholder you cannot fill.

Ask the interviewer: fresh context per iteration? Exit signal? Can it run tests? Who reviews the output?

---

## Part B — the prompt

```xml
<goal>
Build {{project}} for {{users}} so that {{business outcome}}.
Success means every acceptance criterion below passes with an executed check.
It does not mean that the code looks complete.

You run in a loop. Each iteration does ONE unit of work, verifies it, records it in files, and exits.
Assume that you remember nothing from earlier iterations. The files in <state> are the only memory.
</goal>

<context>
{{Domain facts, existing systems, integrations, data shapes, users.
Include only facts that change a decision.}}
</context>

<requirements>
R1. {{behavior}}. Why: {{business reason}}.
R2. {{behavior}}. Why: {{business reason}}.
...
Thresholds: {{every "fast/secure/scalable" rewritten as metric + limit + how measured}}

Operational concerns:
- Required: {{e.g. input validation on all external input, structured error responses, audit log of X}}
- Out of scope: {{e.g. auth, i18n, horizontal scaling}}

Out of scope: {{features the business did not ask for}}
Build nothing outside R1..Rn. If you think something is missing, record it in DECISIONS.md. Do not build it.
</requirements>

<constraints>
{{Stack and versions, data rules, security rules, each with its reason.}}
Decisions already made (do not revisit): {{...}}
Keep it simple:
- Write the minimum code that meets the requirements.
- Add no speculative abstractions.
- Add no configuration that nobody requested.
Components talk only through their defined interfaces. Define an interface before the code that depends on it.
</constraints>

<state>
PLAN.md      — tasks. Each task has: id, R-ids, dependencies, acceptance check (a command), Status (Pending | Done | Blocked), attempts.
PROGRESS.md  — append-only. Each iteration records: task, what changed, the commands run and their results, the next step.
DECISIONS.md — assumptions and choices, each with its reason and the R-ids it affects.
Git history  — one commit per finished task. The committed state is the truth. Unverified notes are not.
</state>

<each_iteration>
1. Orient. Read PLAN.md, PROGRESS.md, and DECISIONS.md. Run `git log --oneline -10` and `git status`.
   If uncommitted changes exist from an interrupted iteration, finish them and verify them, or revert them.
2. If PLAN.md does not exist, write it. This is the whole iteration:
   - Check the requirements first. Every requirement must be measurable and must have success and failure cases. No two requirements may conflict.
   - Record each gap as an assumption in DECISIONS.md, or as a Blocked question.
   - Split R1..Rn into small vertical tasks, ordered by dependency. Each task must cover at least one R-id. Every R-id must have at least one task.
   - Make the first task the project skeleton, with a test command that passes.
   - Commit, then exit.
3. Run the full test suite. If a task marked Done now fails, repairing it is this iteration's task.
4. Otherwise choose the first Pending task whose dependencies are Done.
5. Implement the smallest slice that meets the acceptance check:
   - Write the test first. Confirm that the test fails for the right reason.
   - Change only what the task needs. Do not refactor unrelated code.
6. Verify. Run the task check, the full suite, and lint.
   Use only commands and tests as evidence. "I reviewed the code" is not evidence.
7. Record the result:
   - Pass: set Status: Done. Log the commands and their results in PROGRESS.md. Commit as "<task-id> (R-ids): <what>".
   - Fail: read the error, then change code or configuration based on it. Never re-run an unchanged command.
   - After 3 failed attempts on the same task: set Status: Blocked. Record the error, your hypothesis, and what you tried. Commit, then exit.
8. Exit. Do not start a second task.
</each_iteration>

<ambiguity>
Assumptions already made:
- A1: {{...}}
- A2: {{...}}

For any other unclear point:
- Choose the simplest option that meets R1..Rn.
- Record the choice in DECISIONS.md.
- Continue.

Do not guess when the choice affects any of these:
- data loss or data migration
- authentication or permissions
- money
- an external contract or API

Instead, set the task to Blocked and record the question.
Do not weaken a requirement to make a test pass. A conflict between a requirement and a test is a blocker.
</ambiguity>

<acceptance_criteria>
AC1 (R1): Given {{state}}, when {{action}}, then {{observable result}}. Check: `{{command}}`
AC2 (R1, failure): Given {{bad input or failure}}, when {{action}}, then {{error behavior}}. Check: `{{command}}`
AC3 (R2): ...
</acceptance_criteria>

<definition_of_done>
Check this list in every iteration, not only at the end:
- The full test suite and lint pass.
- Every R-id has at least one passing test. Every test maps to an R-id.
- New behavior has tests that fail without the change.
- The code has no dead code, debug output, or commented-out blocks.
- The code has no features outside R1..Rn.
- The README states how to install, run, and test the project.
</definition_of_done>

<completion>
When no Pending tasks remain:
1. Run a final verification pass from a clean state. Install, build, run the full suite, and run every AC check.
2. Review the full diff against R1..Rn. Look for missing behavior, scope creep, and untested paths.
   Any finding becomes a new Pending task. Exit without the signal.
3. When everything passes, write REPORT.md:
   - For each R-id: status, evidence (the command and its result), and related assumptions.
   - Blocked tasks and open questions.
   - Known gaps and limits.
4. Output {{EXIT_SIGNAL}}.

If only Blocked tasks remain, write the same report. Put the blockers first, then output {{EXIT_SIGNAL}}.
Never output {{EXIT_SIGNAL}} while any work is unverified. Report a failure as a failure.
</completion>
```

---

## Part C — adapt to the agent specs

- **Continued context, not fresh:** keep the state files anyway. They are still the trace and the audit record.
- **Planner, executor, and reviewer roles:** the planner owns step 2 and PLAN.md. The executor owns steps 3–8. The reviewer owns completion step 2, and it does not edit code. An agent that builds a task does not review that task.
- **The harness runs the tests:** change step 6 to "read the harness test result" and keep the same evidence rule.
- **The agent can ask a human:** change "set to Blocked" in `<ambiguity>` to "ask, then wait". Ask only for the listed categories.
- **Small iteration cap:** make tasks coarser, and say so in the plan step.

Say this line out loud: *"In a loop, the prompt is a control system. It needs state, one step at a time, a check after each step, and a clear stop condition."*
