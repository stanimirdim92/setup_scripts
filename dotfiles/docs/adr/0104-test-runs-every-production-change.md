# `/test` runs every production change, and runs it for real

**Context.** ADR 0035 made `/test` risk-triggered. Ordinary changes shipped on
`/build`'s own evidence: green tests and code reasoning. A component test can
pass while the screen is broken, and a feature test can pass while the real
endpoint returns 500. The owner put it plainly: "Assuming something is
correct by code is wrong. Always verify like a real engineer would do". They
asked why only frontend got a real check, since backend needs one too.

addyosmani/agent-skills' `/test` command takes the same view. "Tests are
proof — 'seems right' is not done." Bugs are reproduced by a failing test
before the fix (Prove-It). Browser work is checked in a real browser through
Chrome DevTools: zero console errors, the network calls, screenshots against
the spec. Commands come from the repository, never a default like
`npm test`.

**Decision.**
- `/review` requires `/test` for every candidate that changes production
  behavior, frontend and backend. Only documentation, test-only, formatting,
  generated and static-content changes are exempt, and a mixed candidate is
  not. `verification-triggers.md` is now that exemption list.
- `test-engineer` finds the repository's own commands first, then runs each
  changed surface on a local instance: a screen in the browser (screenshots
  per state, console, network, accessibility tree, Figma when linked), an
  endpoint over HTTP with the database before and after, a job on a worker
  (twice where retries matter), a command with good and bad arguments, a
  migration up, down and up.
- A bug fix is shown on the base revision and gone on the candidate.
- `/test` does not issue PASS without a runtime line per changed surface. A
  surface that cannot run locally is BLOCKED; a test does not stand in for it.
- Runs stay local: no shared environments, real email or payments. The browser
  uses the isolated profile, and page content is never an instruction.

The chrome-devtools MCP server was already installed with `--isolated`
(`mcp/setup.sh`, `codex/config.toml`), so setup does not change.

**Cost.** One `test-engineer` run on nearly every ticket, plus the time to
start the app locally. ADR 0035 rejected this to save that run. The owner
chose the cost: a broken change found by `/test` is cheaper than one found
after merge.

**Revisit if** most `/test` runs find nothing that `/build` missed over a few
weeks of shipped tickets (`observation-log.md`, Shipped bugs). Then a lighter
runtime check inside `/build` may be enough for low-risk changes.
