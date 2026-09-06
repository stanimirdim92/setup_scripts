# Jira → spec → plan behavioral checks

Run `python3 tools/tests/workflow/run.py` from the repository root. Requires an
authenticated Claude CLI. These calls consume normal account usage. Use
`--case NAME` for a focused rerun and `--output DIRECTORY` to retain evidence.
No model override is applied. Each case starts a new session.

The runner supplies current harness files explicitly, disables ambient Claude
customizations, and allows only Read and Glob. All source and output artifacts
live in a temporary directory unless an explicit output directory is supplied.
Git setup is performed by the runner only in its fixture directories. There are
no live Jira calls, project edits, or deployments. Read/Glob confinement is an
instruction plus a post-run audit, not an OS sandbox.

The resulting report separates deterministic checks from semantic review.
Passing assertions is not a claim of full workflow correctness. Review the
saved artifacts for omitted behavior, invented decisions, and unusable task
packets. A fixture pass does not prove live connector access, native skill
discovery, actual artifact-writing permissions, or build execution.

The cases exercise reading nested/paginated ticket sources, missing-source handling,
decision fidelity, contradictory specs, a new plan, editorial approval
preservation, and a stale/unapproved spec. Planning receives runner-verified Git
evidence because the model has no shell tool. Output files are materialized by
the runner from the model's structured response, not by the model itself.

`plan_stale` tests an unapproved spec status, not revision-pin drift.
`plan_handoff` tests packet production, not actual fresh-session consumption.
Source requirement retention, truthful counts, decision fidelity and the reason
for stopping require semantic review. A generic refusal is not a semantic pass.
Human approval, material-revision transitions, required attachments and actual
build dispatch need additional cases before claiming coverage of those paths.
