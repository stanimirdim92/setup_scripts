# Intake — EX-1 (invented)

**EX-1 — Export customer records**
Status: Ready for Dev. Records exported through the reporting service are
retained indefinitely so they can be re-downloaded.
Acceptance: a user can export; the export is re-downloadable later.

**EX-2 — Spike: retention policy for exports** (relates to EX-1)
Spike result: exports must be purged after 30 days to satisfy the retention
policy. Vendor for the export pipeline is undecided — Acme and Globex were both
evaluated and the spike did not conclude.

**Blockers**
- Retention conflict between EX-1 and EX-2 is unresolved.
- Export pipeline vendor undecided.
