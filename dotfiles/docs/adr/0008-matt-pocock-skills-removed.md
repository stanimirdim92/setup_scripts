# Matt Pocock's skills: removed, committing to the addyosmani SDLC shape

**Decision.** `research` and `handoff` (`MATTPOCOCK_SKILLS_LICENSE`) are
removed entirely — files deleted, all README/CLAUDE.md references
dropped. This machine commits to `addyosmani/agent-skills`'s phase-mapped
SDLC shape (`spec-driven-development` → `planning-and-task-breakdown` →
`incremental-implementation`/`code-review-and-quality`, orchestrated by
this repo's own `/spec`/`/plan`/`/build`/`/review` commands) as the one
active planning/build/review router, with `superpowers` scoped
narrowly to classification (`brainstorming`), TDD, and debugging — not
as a competing SDLC router. Per `addyosmani/agent-skills`' own
`docs/comparison.md`: "cherry-picking individual skills works;
stacking both frameworks as active routers fight over command names and
produce unpredictable behavior." Matt Pocock's collection is built
around a different assumption — `to-spec`/`to-tickets`/`wayfinder` all
synthesize a conversation into an external issue tracker — which doesn't
match this team's actual shape of work: tickets (e.g. LD-329) arrive
already fully authored in Jira, DoD and all, before Claude ever sees
them. There's nothing here for those skills to do.
