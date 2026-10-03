# Ticket trailers on commits

**Context.** Plan recall finds a ticket's commits by searching commit messages
for the ticket key. Pipeline commits put it in the subject, `(LD-442 T002)`,
but no harness file defines that form; it is a habit. A squash or summary
commit that names a ticket only in its body is counted too, so LD-441's run
needed `--subject-only`, and a subject match still counts any commit that
mentions the key in passing.

**Decision — git trailers.** A commit for a ticket ends with:

```text
Refs: LD-442
Task: T002
```

`Refs:` carries the ticket key (one trailer per ticket, or comma-separated
keys). `Task:` carries the plan task id and is omitted for unplanned commits
such as review fixes. The subject keeps following the repository's own
convention; trailers do not compete with it. A repository that already uses a
ticket trailer under another key keeps its key.

`git-workflow-and-versioning` §Ticket trailers defines the form;
`executor-development-discipline` requires it for every task commit.

**Decision — plan recall reads them.** `recall.py --trailer-only` matches a
ticket only when it equals a `Refs:` value, read through
`git log --format='%(trailers:key=Refs,valueonly)'`. `LD-4410` does not match
`LD-441`, and text in the body does not match at all. `--subject-only` stays
for history written before this decision.

**Rejected.**
- *Keep the subject form and define it.* Subject text is free-form; git cannot
  parse it, and other tools cannot either.
- *Conventional Commits scope, `feat(LD-442): …`.* It takes over the subject
  convention, which belongs to the repository, and holds one ticket only.
