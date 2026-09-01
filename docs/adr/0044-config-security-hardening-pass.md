# Config security hardening: enforcement made to match the stated guarantees

**Decision.** An external review of this repo's config surfaced a single
recurring shape: a guarantee stated in a comment, a README line or an ADR that
nothing actually enforced. Each item below closes that gap rather than adding a
new control.

**Codex sandbox.** `sandbox_mode` moved from `danger-full-access` to
`workspace-write`, with `[sandbox_workspace_write] network_access = true`.
Writes are confined to the workspace with `.git`/`.agents`/`.codex` read-only
inside it, and anything outside needs a per-task approval instead of a standing
grant. Network stays on because npx, composer, `mcp-remote` and the remote MCP
servers all need it, and turning it off trades a boundary Codex enforces itself
for a stream of approvals a human will learn to click through. Under
`danger-full-access` the whole `rules/default.rules` file was decoration: it
governed which commands get approved, while nothing at all governed what an
approved command could reach.

**Codex approval rules.** Blanket `sed` removed. It covered `sed -i` — in-place
overwrite of any readable file — and GNU sed's `s///e` flag, which executes the
substitution result as a shell command; prefix matching cannot express "no `-i`
anywhere", so there is no narrowed form of that rule and it had to go rather
than shrink. `rg` stays: it cannot write. Also removed: approvals recorded for
other projects (`leadbuster`, `ad_creation_agent`) that a synced global file had
no business carrying, and rules already subsumed by a broader prefix.

**Filesystem MCP dropped.** `mcp/setup.sh` added
`@modelcontextprotocol/server-filesystem` at user scope rooted on `$HOME`,
unpinned. The root reached around `settings.json`'s `Read` deny paths
(`~/.ssh`, `~/.aws`, `~/.config/gh`, `~/.git-credentials`) — that deny list
constrains Claude Code's own file tools, not an MCP server's — while the
built-in `Read`/`Write`/`Glob`/`Grep` tools already covered the workspace. Its
only real addition was reach outside the workspace, which is the part that
wasn't wanted.

**MCP secrets and re-runs.** Auth headers are written as literal
`${GITHUB_TOKEN}` / `${CONTEXT7_API_KEY}` placeholders that Claude Code expands
at load time, so `~/.claude.json` holds variable names instead of a PAT. The
script's header claimed re-running was safe because a duplicate `claude mcp add`
"fails loudly"; with `set -e` that failure aborted the script before the later
servers were ever added, so the claim was true of one command and false of the
script. Each add is now guarded by an existence check.

**Git hooks made alias-aware.** `dotfiles/.gitconfig` defines `rlc`
(`reset --hard HEAD~1`), `co` (`checkout`), `fu` (`push --force-with-lease -u`)
and roughly a dozen `push` typo shortcuts. Both hooks grepped for the
spelled-out command, so every alias walked past them. They now expand the
relevant aliases before matching, and `warn-force-push.sh` resolves the
checked-out branch from the hook payload's `cwd` because an alias-expanded force
push carries no refspec — `git fu` on `main` never spells "main" out.
`help.autocorrect = 1` remains outside what any fixed alias list can cover.

**Explicit-only skills enforce it.**
[0039](0039-runtime-catalog-narrowed-by-observed-use.md) keeps
`incremental-implementation`, `test-driven-development` and
`code-review-and-quality` for standalone use while the gates route to the
compact components, but nothing stopped them auto-triggering; each now sets
`disable-model-invocation: true`.

**Review contract completed.** `/review` requires every finding to carry a
confidence and `/ship` uses it to separate a confirmed BLOCKER from a suspected
one, but only `code-reviewer` emitted it — so a `security-auditor` or
`distributed-systems-reviewer` BLOCKER could never be resolved except by a fix,
including a false one. Both contracts now define confidence the same way
`code-reviewer` does. `/ship` also gained an evidence-refutation resolution for
REQUIRED findings, which previously had to be laundered as an "accepted risk",
recording against the release a risk it does not carry.

**Codex global instructions.** `CLAUDE.md` is now also linked to
`~/.codex/AGENTS.md`. Codex reads its global instructions from there and never
from `~/.claude`, so Codex had been running with no global rules at all while
Claude Code had the full set. One file, linked twice, keeps a single source of
truth; its "Agent orchestration" section is marked Claude Code-specific for the
Codex reader.

**Kept as-is — `Bash(php *)`.** This is an arbitrary-execution allow: `php -r`
runs any code, so it reads or overwrites anything the user can, regardless of
`settings.json`'s `Read`/`Edit` deny paths. Kept at the user's decision; the
hole is recorded here rather than closed, so it doesn't get rediscovered as
news. Narrowing it means enumerating the exact PHP commands in use
(`php artisan:*`, `vendor/bin/pint`, `vendor/bin/phpstan`,
`vendor/bin/deptrac`) and accepting a prompt whenever a new one appears.
**Revisit if** a session is ever run against a repository whose contents aren't
trusted.

**Kept as-is — `enableAllProjectMcpServers: true`.** Any cloned repository's
`.mcp.json` activates its servers with no per-server approval, so a repo can
ship a server that runs a command the moment a session starts there. Kept at
the user's decision. The residual risk is bounded by which repositories get
opened, not by anything in this config. **Revisit if** untrusted or unreviewed
repositories start being opened directly.

**Noted, not changed — `["codex", "mcp"]`.** The prefix still allows
`codex mcp add`, i.e. writing new MCP servers into Codex's own config from
inside a session. Same class of hole as the `sed` rule; outside the scope
agreed for this pass.

**Rejected — `workspace-write` with `network_access = false`.** Strictly safer,
and it would put an approval prompt in front of every `npx`, `composer` and
remote MCP call in a normal workflow. A boundary that gets clicked through
dozens of times a day is weaker than one that holds and is believed.

**Rejected — strip the machine-specific blocks from `codex/config.toml`.** The
`[desktop]`, `[projects]`, `[plugins.*]` and `[mcp_servers.node_repl]` blocks
carry absolute `/home/stanimir` paths, app build versions and stale
per-conversation trust entries. They are written by the Codex app itself and are
rewritten on launch, so stripping them is churn that reappears. Documented as
expected `git status` noise in `README.md` instead. The trust entries are inert
on a machine with a different home path.

**Rejected — link the Claude skills into `~/.codex/skills`.**
`~/.codex/skills` holds Codex's vendor-shipped `.system` skills, which a
whole-directory symlink would shadow, and the pipeline skills are written around
`/build`, `/test`, `/review` and `/ship`, which Codex has no equivalent of.
Linking them would install instructions that reference commands that don't
exist.

**Rejected — point the caveman skill's dead link at a guessed upstream URL.**
`skills/caveman/README.md` linked `../../README.md`, the upstream project's root
README, which isn't vendored here. The vendored license names the author but no
repository, so the link now points at that license rather than at an invented
URL.
