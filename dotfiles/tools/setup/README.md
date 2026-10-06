# setup — install the harness on a machine

You run these once per machine, and again when the harness gains a new file
or a pinned skill moves. Nothing here runs during ticket work.

| File | What it does | Run |
| --- | --- | --- |
| `link_dotfiles.sh` | Links `dotfiles/claude` and `dotfiles/codex` into `~/.claude` and `~/.codex`, so Claude Code and Codex use this repository's agents, commands, skills and hooks. It backs up any real file it would replace, and shows the plan before it changes anything. | `./dotfiles/tools/setup/link_dotfiles.sh` |
| `fetch-figma-skill.sh` | Downloads Figma's design-to-code skill at a pinned version and checks its fingerprint. It is fetched, not committed, because Figma ships it without a licence. | `./dotfiles/tools/setup/fetch-figma-skill.sh` |

After a `git pull`, run `link_dotfiles.sh` again. It changes nothing when the
links are already right.
