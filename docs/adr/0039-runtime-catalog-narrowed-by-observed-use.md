# Runtime plugins narrowed; standalone engineering skills retained

**Decision.** Keep three optional plugins installed and their marketplaces known,
but stop enabling them globally:

- `superpowers@claude-plugins-official`;
- `code-simplifier@claude-plugins-official`;
- `commit-commands@claude-plugins-official`.

They can be enabled at project scope when a real task requires them. Disabling
is a runtime-routing decision, not an uninstall or a rejection of their
capabilities. The tracked `.claude/settings.json` project override that kept
Commit Commands and Superpowers enabled in this repository is removed too.
Qdrant Skills and LLM Application Dev remain globally enabled and are not part
of this reduction.

Retain the locally reconciled, MIT-licensed `incremental-implementation`,
`test-driven-development`, and `code-review-and-quality` skills for explicit
standalone use. The automatic SDLC routes remain compact: `/build` selects
`executor-development-discipline`, `/test` dispatches `test-engineer`, and
`/review` dispatches `code-reviewer`. The fuller skills are available when their
methodology is itself useful, without being loaded automatically by those gates.
The standalone review skill embeds its own finding, severity-mapping, and output
contract instead of depending on the compact agent file or repository-only ADR
paths.

**Evidence.** Claude Code 2.1.247's current `plugin details` projection puts the
three disabled plugins at about 855 always-on tokens per session: Superpowers
688, Commit Commands 103, and Code Simplifier 64. These are comparison estimates
rather than billed-token measurements. Lifetime counters showed no deliberate
Commit Commands or Code Simplifier invocation. Superpowers' plugin counter was
dominated by its session hook; its recorded skill calls were seven overlapping
workflow routes and zero calls to the one capability still named as unique,
`systematic-debugging`.

The three retained local skills contribute about 320 projected always-on tokens
through discoverable metadata; their full bodies are paid only when invoked.
An initial deletion based on low lifetime counters was rejected: counters are
weak evidence of future value, the skills retain useful standalone depth beyond
their compact pipeline counterparts, and removing them would save little beside
the plugin reduction. With Qdrant and LLM Application Dev also retained, the
three disabled plugins reduce the measured fixed custom catalog by roughly 14%.

Kept globally enabled:

- PhpStorm and episodic memory, both with substantial observed runtime use;
- Qdrant Skills and LLM Application Dev, retained by the current global config;
- Context7, with observed calls and no projected always-on cost;
- Security Guidance, whose hooks are heavily active but whose optional LLM
  review is currently disabled without credentials;
- TypeScript LSP and Playwright, which add no projected always-on model context.

Episodic memory remains distinct from versioned `docs/MEMORY.md`: it searches
past conversations, while the document stores reviewed durable project facts.
Claude's automatic project memory stays disabled per [0037](0037-fixed-session-context-reduced.md).

This disables the Code Simplifier addition from
[0011](0011-plugin-set-dropped-feature-dev-added-official-plugins.md), and closes
the remaining Superpowers routing from
[0021](0021-reconcile-superpowers-overlap-with-current-sdlc.md).

**Rejected — uninstall the plugins.** Installation is not the token cost; global
discovery is. Keeping them installed makes project-scoped opt-in reversible and
avoids another download/update step when a matching task appears.

**Rejected — disable every zero-counter plugin.** TypeScript LSP activity is not
reliably represented in transcript tool calls, and deferred MCP schemas add no
projected always-on context. Token optimization should remove measured model
context, not conflate it with connection tidiness.

**Rejected — keep Superpowers only for systematic debugging.** Paying for
fourteen skill descriptions in every session preserved one capability with no
recorded invocation while the plugin continued to route into brainstorming,
planning, execution, and branch-finishing methods already owned locally.

**Rejected — remove the three overlapping local skills.** Their large bodies are
loaded progressively only when invoked, while the always-on descriptions are a
small part of the catalog. Explicit access to their fuller incremental, TDD, and
review methods is worth that fixed cost; automatic pipeline routing remains on
the compact components to prevent duplicate invocation.

**Revisit if** repeated work needs a specialized Superpowers debugging method.
Enable it at project scope and measure actual invocations before restoring it
globally. Reassess Qdrant and LLM Application Dev after a longer usage window;
their current global enablement is preserved rather than changed by this ADR.
