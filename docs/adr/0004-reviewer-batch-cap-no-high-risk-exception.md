# Reviewer batch cap: no high-risk exception

**Decision.** The review fan-out's "never more than 2 reviewers at once"
cap originally had an exception: a diff already flagged high-risk could
run the full specialist fan-out concurrently, "since it's earning the
cost." That exception directly contradicted this repo's own README,
which stated the cap as "regardless of how many are eligible" with no
carve-out — a real drift between what two files claimed about the same
rule (rule 6 territory). Fixed by removing the exception: the cap holds
unconditionally, including for high-risk diffs that trigger every
specialist — those diffs get all the same reviewers, just in sequential
batches of 2 instead of all at once. A high-risk diff earns more
distinct review perspectives, not a faster concurrent token burn.
