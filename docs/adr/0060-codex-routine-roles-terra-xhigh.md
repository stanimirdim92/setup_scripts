# Codex routine roles use Terra at xhigh

**Decision.** At the user's explicit request, `executor`, `test-engineer`, and
`repo-recon` use `gpt-5.6-terra` with `model_reasoning_effort = "xhigh"` in
`dotfiles/codex/agents/`. The fallback dispatch table in
`dotfiles/codex/references/workflow-runtime.md` uses the same values. This
supersedes only the Sol/high selection in
[0059](0059-codex-native-roles-and-hook-adapters.md). Reviewers and
executor-high retain Astra/high; the session model and hook policies are unchanged.

**Rejected — retain Sol/high for these roles.** The user explicitly selected
Terra/xhigh instead. This is a configuration preference, not a measured claim
about cost or quality.
