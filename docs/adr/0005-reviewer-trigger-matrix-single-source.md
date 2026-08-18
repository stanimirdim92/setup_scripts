# Reviewer trigger matrix: one file, not two copies

**Decision.** `build.md` claimed its reviewer trigger conditions "must
match `review.md` exactly," but `review.md` never defined conditions for
`infra-reviewer` at all — there was
nothing for `build.md`'s copy to match wasn't wired into either command's routing despite existing specifically
for LLM-call-site review, which is the majority of this machine's actual
project work. Fixed by moving the trigger matrix into
`dotfiles/claude/references/reviewer-triggers.md` as the single source,
with both commands reading it instead of each keeping its own copy, and
adding `llm-integration-reviewer`'s trigger (diff touches an LLM API call
site: new/changed prompt, model call, tool definition, or model output
feeding a record write or downstream action).
