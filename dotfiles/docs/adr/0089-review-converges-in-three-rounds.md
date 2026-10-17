# Review converges in three rounds

**Context.** The loop `/review` → `/ship` NO-GO → `/build` fix → `/review`
had no limit. Each round reviewed the whole change again. A reviewer could
raise a finding already resolved, or find one instance of a defect per round.
Anthropic's Claude Code team measured the same loop (claude.dev, "Solving code
review at Anthropic", 2026-10). One pull request went through more than 50
rounds. About 59% of what the reviewer kept flagging had been there since the
first pass. Their fixes raised the share that passed after one fix round from
65% to 78%, and cut the share needing five or more rounds from 8.9% to 1.5%.

**Decision.**
- `/review` counts its round from the ticket's earlier review SARIF files.
- Round 4 returns REVIEW BLOCKED. It lists the findings that came back in more
  than one round and asks the user to reconsider the approach.
- From round 2, reviewers see only the diff since the last reviewed commit.
  `code-reviewer` also gets the earlier findings and their resolutions, and
  does not raise a resolved finding again. `blind-reviewer` still gets only
  the diff; `/review` drops its repeats of resolved findings.
- Specialists run again only when the new diff matches their trigger. The
  weakened-test guard and the ledger check still cover the whole candidate.
- A finding that is one instance of a pattern names the class and lists every
  instance in the diff (`component-response-contracts.md` §Shared conventions).

**Cost.** A later round can miss a defect the fix created outside its own
diff. The whole-candidate checks and `/ship`'s requirement evidence still run.
The round count resets only when the user deletes the old review files.
