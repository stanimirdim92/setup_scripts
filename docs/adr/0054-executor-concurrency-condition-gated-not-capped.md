# Executor concurrency gated by conditions, not a fixed cap

**Decision.** `/build` has **no fixed concurrency cap**. It dispatches at most
one executor per genuinely independent workstream, and only for workstreams
satisfying every condition below; the rest are queued. This supersedes
[0031](0031-parallel-executors-via-worktree-isolation.md)'s cap of 2 and
[0042](0042-third-executor-as-conditional-exception.md)'s conditional third.

The conditions are the same ones 0042 already required, plus one it was missing:

1. the workstreams are genuinely independent — no unfinished dependency, no
   shared mutable state;
2. each is dependency-ready now, its gating checkpoint already passed;
3. every concurrent writer uses `isolation: worktree`;
4. **their verification commands do not share mutable runtime state**;
5. the session is not near its rate limit.

Integration stays strictly sequential, in dependency order, with verification
after each merge. That part of 0031 is not superseded.

## Why the number was the wrong control

0031 set the cap at 2 to match the reviewer cap and this repo's preference for
predictable spend. 0042 kept 2 and allowed a third under four conditions,
explicitly refusing to raise the cap. Both treated the number as the safety
control.

It never was. The four conditions in 0042 are what make concurrent execution
correct; the number is an arbitrary point on top of them. Two executors that
violate the conditions are unsafe, and five that satisfy them are not made safer
by being called three. Keeping both meant maintaining a numeric rule that
neither prevented the real failure nor described the real limit — and the real
limit, rate-limit headroom, is a condition already in the list.

## Condition 4 is new, and is why this ADR exists rather than a one-line edit

0031 established that `isolation: worktree` removes the shared mutable state two
writers contend on. That claim is true for **git and the filesystem** and was
never true beyond them. A worktree does not isolate a database, queue, cache,
search index, or a fixed port.

The concrete failure: in a Laravel project whose `phpunit.xml` sets no `DB_*`
overrides, every executor's test run inherits the same connection from `.env`.
Two suites running `RefreshDatabase` or `migrate:fresh` concurrently drop each
other's schema mid-run. There is no lock error and no `.git/index.lock`
analogue — one suite simply fails for reasons unrelated to its own diff, and
`/build` reports a verification failure that no amount of reading the code
explains. The same holds for a shared Redis queue.

This exposure existed at a cap of 2 and was never written down. Removing the cap
without stating condition 4 would have made an unguarded, silent, and
misattributed failure routine instead of occasional. So the cap is removed and
the condition that was actually doing the work is made explicit: each concurrent
executor needs its own instance of every mutable resource its checks touch, or
those checks are deferred and run serially at integration — established from
repository evidence, never assumed.

## Rejected alternatives

**Rejected — raise the cap to 4 or 5.** Same category error as 2 or 3: a number
that neither prevents the failure nor describes the limit. If the conditions
hold, the number is arbitrary; if they do not, no number is safe.

**Rejected — keep the cap and add condition 4 under it.** This was the smaller
change and it does make concurrent builds correct. It was rejected because it
preserves two overlapping controls where one suffices, and the numeric one is
the control that misleads: it implies a fan-out of 2 is inherently safe, which
condition 4 shows it is not.

**Rejected — solve runtime isolation in the harness.** Per-executor databases
and queue namespaces are a property of the project under build, not of these
dotfiles. `/build` can require the condition and refuse to dispatch without it;
it cannot provision it. Projects that want wide fan-out provision per-worktree
runtimes themselves.

## Consequences

- Wide fan-out is now reachable, but only for work that is genuinely independent
  *and* runtime-isolated. Most projects satisfy the first and not the second, so
  in practice the effective fan-out often stays small — now for a stated reason
  rather than an arbitrary one.
- `/build`'s completion report must say how condition 4 was satisfied for each
  concurrent executor, not merely how many ran. A dispatch made without
  establishing it is a reportable slip.
- 0031's economics are unchanged and still govern: parallelism buys elapsed
  time, not fewer tokens. Each isolated executor rediscovers context its peers
  already hold, so a wider fan-out costs strictly more tokens for the same work.
  This decision does not make parallel execution cheaper; it removes a numeric
  ceiling and names the condition that was silently load-bearing.
