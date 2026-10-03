#!/usr/bin/env bash
# Fetch Figma's figma-design-to-code skill at a pinned commit, verify it, and
# place it where Claude Code loads skills.
#
# Why fetched rather than vendored: figma/mcp-server-guide ships no licence, so
# its files cannot be redistributed from this public repository. The copy lands
# in dotfiles/claude/skills/figma-design-to-code/, which .gitignore excludes, so
# it reaches ~/.claude/skills through the usual directory link and never git.
# Pinned and hash-checked like chrome-devtools-mcp (dotfiles/docs/adr/0070,
# 0072): a changed upstream file is refused, not silently loaded.
#
#   dotfiles/tools/setup/fetch-figma-skill.sh          # fetch or verify
#
# FIGMA_SKILL_URL overrides the source (the self-test points it at a local file).
set -euo pipefail

COMMIT=aaa07946b60797706c131ca50e50ca526a44b073
SHA256=a6e852421e4db72260b2ca641929b1f84684e5b067aead081e35111f5b5feee4
URL="${FIGMA_SKILL_URL:-https://raw.githubusercontent.com/figma/mcp-server-guide/$COMMIT/skills/figma-design-to-code/SKILL.md}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
DEST="${FIGMA_SKILL_DEST:-$REPO_DIR/dotfiles/claude/skills/figma-design-to-code}"

sum() { sha256sum "$1" 2>/dev/null | cut -d' ' -f1 || shasum -a 256 "$1" | cut -d' ' -f1; }

if [ -f "$DEST/SKILL.md" ] && [ "$(sum "$DEST/SKILL.md")" = "$SHA256" ]; then
  echo "figma-design-to-code: already present at the pinned version"
  exit 0
fi

tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT
if ! curl -fsSL "$URL" -o "$tmp"; then
  echo "figma-design-to-code: download failed from $URL" >&2
  exit 1
fi
got="$(sum "$tmp")"
if [ "$got" != "$SHA256" ]; then
  echo "figma-design-to-code: checksum mismatch (got $got, pinned $SHA256); not installed." >&2
  echo "  Review the upstream change, then update COMMIT and SHA256 in this script." >&2
  exit 1
fi
mkdir -p "$DEST"
mv "$tmp" "$DEST/SKILL.md"
trap - EXIT
echo "figma-design-to-code: installed at $DEST (commit ${COMMIT:0:12})"
