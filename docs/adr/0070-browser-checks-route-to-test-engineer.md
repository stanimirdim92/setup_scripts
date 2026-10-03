# Browser checks route to test-engineer, and the DevTools MCP is installed

**Context.** `/build` told executors to prove browser-dependent acceptance
criteria with `browser-testing-with-devtools`, and to block BUILD when the
tooling was missing. The executor's `tools:` has no `mcp__chrome-devtools__*`,
and `mcp/setup.sh` never installed the server on the Claude side. So every
browser-dependent task blocked BUILD, or an executor offered component tests in
place of a browser. Only `test-engineer` was granted the browser tools.

**Decision — test-engineer owns real-browser checks.**
- `/build` never selects `browser-testing-with-devtools` for an executor.
- The executor lists each browser-dependent criterion as
  `Needs real-browser check: <REQ id> — <criterion>`. It does not claim the
  criterion, and component tests do not count as evidence for it.
- `verification-triggers.md` makes such a criterion a `/test` trigger. `/review`
  requires `/test`, and test-engineer runs the check in its isolated checkout.
- `validate-frontmatter.py` fails when the executor gains browser tools or
  test-engineer loses them.

**Decision — install Chrome DevTools MCP at user scope.** `mcp/setup.sh` adds
`chrome-devtools-mcp@1.10.1 --isolated` over stdio. `--isolated` gives each run
a throwaway Chrome profile, so no cookies or saved logins reach the agent. The
version is pinned in the script and in `dotfiles/codex/config.toml`, which ran
`@latest`: an unpinned stdio server runs whatever npm serves that day, with
the user's full access, outside the Bash sandbox.

**Rejected.**
- *Grant the executor browser tools.* The writer would then prove its own
  rendering claims, which is the self-verification `/test` exists to replace.
  Every executor run would also carry the MCP tool schemas.
- *A Playwright MCP instead.* The skill and test-engineer are written for
  DevTools (console, network, performance traces), and Codex already uses it.

**Codex parity.** Codex roles see every configured MCP server, so the Codex
executor relies on the shared executor skill's instruction, not on a tool
grant.
