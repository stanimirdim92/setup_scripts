# Infra + security reviewers merged into `security-auditor`

**Decision.** `infra-reviewer` (nginx/redis/mysql/sysctl/PHP-FPM/Dockerfile
pattern review) and `security-reviewer` (security pass over the same infra
surface) are replaced by a single `security-auditor` agent — one persona
covering input handling, auth, data protection, infra security, third-party
integrations, and LLM/OWASP-LLM-Top-10 findings. `reviewer-triggers.md` and
`build.md`/`review.md`/`code-reviewer.md`'s Composition blocks now point at
`security-auditor` alone. Filled in `tools: Read, Grep, Glob, Bash` and
`model: claude-opus-4-8` / `effort: high` on the new agent file, matching
the tier the two agents it replaces already carried — the merge shipped
without frontmatter the first time, which this repo's own "every agent
pins a model" rule (see `0002-model-split-sonnet-orchestrator-tiered-subagents.md`)
doesn't allow.

**Resolved.** `infra-reviewer`'s job also included pattern-*consistency*
review (does this Dockerfile/nginx config match what this repo already
established), not just security — `security-auditor`'s Infrastructure
section only covers the security half. Confirmed with the user: leave it
dropped. `code-reviewer`'s Architecture axis ("does this follow existing
patterns") is generic enough to cover infra files too; no dedicated
consistency check is being reintroduced.
