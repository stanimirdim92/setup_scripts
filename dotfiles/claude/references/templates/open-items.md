# Open Items Template

The canonical shape of `docs/tasks/[TICKET]-open.md`: one register per ticket
for everything the spec, plan and todo do not track. The rules for it are in
`../plan-quality-gates.md` §6, and `check-ledger.py` reads it.

```markdown
# Open items: [TICKET]

| Id | Item | Kind | Owner | Disposition |
|---|---|---|---|---|
| OPEN-001 | REQ-009 timezone is not stored | deferred gap | [name] | Open |
| OPEN-002 | `FooTest:566` fails since 7135aa7 | failing test | [name] | Open |
| OPEN-003 | Can an old run overwrite newer values? | question | [name] | Open |
| OPEN-004 | 1c1865d one metrics row per crawl, outside /build | unplanned commit | [name] | Done — DEC-016, T014 |
```

- **Id**: `OPEN-###`, never renumbered. A plan or todo line that defers work
  names this id.
- **Kind**: `deferred gap`, `question`, `failing test`, `follow-up` or
  `unplanned commit`.
- **Owner**: the person who decides it. Never leave it empty.
- **Disposition**: one of these:
  - `Open`;
  - `Done — <evidence>`;
  - `Accepted — <reason>`;
  - `Moved — <ticket>`.
