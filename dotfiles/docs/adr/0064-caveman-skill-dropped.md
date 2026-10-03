# Caveman skill dropped

**Decision.** Remove the vendored `caveman` skill, its license file, its Codex
adapter, and the `AGENTS.md` line that made it the default chat style
(approver's call). Chat style falls back to the `AGENTS.md` §Session and
context rules, which already ask for concise progress updates.

**Why.** The skill contradicted the rules it was meant to sit under. It said
"No preamble, plan, or progress note before or between calls" while `AGENTS.md`
requires announcing phases and an update roughly every 60 seconds, and "state a
brief plan" for multi-step work. It was also never actually loaded by default:
nothing referenced it except the one `AGENTS.md` sentence, so "default" meant a
bare "terse responses" instruction without the skill's levels or safeguards.

**Decision — retiring the adapter link.** `install-skills.py` now removes a
link in `~/.agents/skills` that points into this repository's adapter
directory at an adapter that no longer exists, and `--check` reports one.
Links it did not create are left alone. Without this, every machine that had
installed `caveman` would keep a dangling `~/.agents/skills/caveman`.

**Rejected — keep the skill and carve out progress updates.** It would still
be an unloaded default whose main rule the carve-out undoes.
