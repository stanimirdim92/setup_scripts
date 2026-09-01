# `repository-precedent.md` placement corrected: hot rules inline, cold ones referenced

**Decision.** [0047](0047-skill-trim-by-deduplication.md) de-duplicated the
recon and precedent rules into `references/repository-precedent.md` and reported
a saving. The de-duplication was right; the placement was not, and the reported
saving was wrong. This entry keeps the single source and fixes where each part
of it lives.

**What 0047 got wrong.** It counted the bytes that left `/spec`, `/plan` and
`spec-driven-development`, and never counted the read arriving. `/spec`
dispatches recon on every invocation —
[0041](0041-recon-delegated-to-repo-recon-subagent.md) rejected making recon
risk-triggered — so the reference is read on every run, and a read pulls the
whole file, not the cited section. Measured per `/spec` run:

| | `/spec` | skill | reference read | total |
|---|---:|---:|---:|---:|
| before 0047 | 858B | 2,794B | — | **3,652B** |
| after 0047 | 364B | 850B | 7,514B | **8,728B** |
| after this entry | 364B | 1,152B | 3,724B | **5,240B** |

0047 turned a 3,652B inline cost into 8,728B — a **5,076B regression** presented
as a saving. This recovers 3,488B of it.

0047 also contains the test that should have caught it. It rejected extracting
the Testing Strategy area because that area "is filled in for *every* spec, so
putting it behind a pointer trades a silent-truncation risk for a guaranteed
extra file read on every single run." The recon rules are needed on every run
too. The test was applied to one block and not the neighbouring one.

**The fix — split by read frequency, not by topic.**

1. **The evidence order goes back inline** into `spec-driven-development`. It is
   five lines and it is consulted whenever the spec names a file, class, table
   or layer, which is nearly every spec. Routing a five-line decision rule
   through a 1,878-token file read costs more than the duplication it avoided —
   and it is not even duplicated now: `planning-and-task-breakdown` points at
   the skill's copy, with the added rule that a plan does not get to re-rank the
   order `/spec` already applied.
2. **The worked example moves to `repository-precedent-example.md`.** At 965
   tokens it was over half the file and the single largest item on the hot path,
   while being needed once while learning the report shape rather than on every
   run.
3. **The reference keeps what stays cold or shared**: how to use a recon report
   (§1) and the no-precedent rules (§2), 931 tokens total.

**Honest residual.** This is still +1,588B per `/spec` run against the
pre-0047 inline arrangement. That is the standing price of one source of truth
for §1 and §2, and it is a price, not a win. Recording it as such is the point
of this entry.

**Rejected — moving §1 back into `/spec` and `/plan` as well.** It would close
roughly another 800B, because command bodies load one at a time: only `/spec`
or `/plan` is ever in context, so duplicating dispatch rules between exactly
those two files costs zero tokens and risks only drift. That is a real option and
the reason the residual above is not irreducible. Not taken here because it
re-creates the duplication this line of work set out to remove, and because
drift between two files that are edited independently is the failure 0047 was
correcting. Revisit if the recon rules turn out to be stable enough that drift
is theoretical.

**Rejected — reverting 0047 entirely.** The triplication was real: `/spec` and
`/plan` carried near-identical dispatch rules and the skill a third copy. Going
back to three copies to save 1,588B per run trades a maintenance guarantee for a
modest token win, and the copy that actually cost tokens — the skill's, loaded
alongside `/spec` — is the one this arrangement still removes.

**The general rule this pass earns.** Extract by read frequency, not by apparent
cohesion. A block used on every run belongs inline however self-contained it
looks; a block used occasionally belongs behind a pointer however tightly it
couples to its neighbours. Byte counts on files are not the measure — the
measure is bytes actually read per run, and a reference read is not free merely
because it is on demand.

**Revisit if** a stage stops needing §1 every run — for instance if recon
becomes reuse-driven per `Change kind` — at which point more of the reference
returns to being genuinely cold and the residual shrinks on its own.
