#!/usr/bin/env bash
# PostToolUse hook (matcher: Edit|Write|MultiEdit). Runs the project's own
# formatter on the one file just edited, when the project has one (ADR 0107).
#
# Formatting is the project's decision, not the agent's: a reviewer comment
# about spacing is noise, and a hand-formatted file drifts from the tool the
# team runs. So the hook formats only with a formatter the project declares
# AND has installed. It never installs anything, never picks a default, and
# formats nothing else:
#
#   PHP         vendor/bin/pint            (pint.json or laravel/pint in composer.json)
#               vendor/bin/php-cs-fixer    (.php-cs-fixer.php or .php-cs-fixer.dist.php)
#   JS/TS/CSS   node_modules/.bin/biome    (biome.json or biome.jsonc)
#               node_modules/.bin/prettier (a prettier config file or "prettier" in package.json)
#   Python      ruff format                (ruff.toml, .ruff.toml or [tool.ruff] in pyproject.toml)
#               black                      ([tool.black] in pyproject.toml)
#   Rust        rustfmt --edition <Cargo.toml edition>   (a Cargo.toml above the file)
#   Go          gofmt -w                   (a go.mod above the file)
#
# The project root is the nearest directory above the file holding the
# formatter's config. Exit 0 always: a formatter that fails (a syntax error
# mid-edit) prints one line and leaves the file as it was written.
set -uo pipefail

input="$(cat)"
file="$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty' 2>/dev/null)"
[ -n "$file" ] && [ -f "$file" ] || exit 0
case "$file" in
  */vendor/*|*/node_modules/*|*/.git/*|*/target/*) exit 0 ;;
esac

# up DIR TEST...: the nearest directory from DIR upwards where any of the given
# files exists; empty when none.
up() {
  local dir="$1"; shift
  while :; do
    for name in "$@"; do
      [ -e "$dir/$name" ] && { printf '%s\n' "$dir"; return 0; }
    done
    [ "$dir" = / ] || [ -z "$dir" ] && return 1
    dir="$(dirname "$dir")"
  done
}

# up_grep DIR FILE PATTERN: nearest DIR upwards whose FILE matches PATTERN.
up_grep() {
  local dir="$1" name="$2" pattern="$3"
  while :; do
    [ -f "$dir/$name" ] && grep -qE "$pattern" "$dir/$name" && { printf '%s\n' "$dir"; return 0; }
    [ "$dir" = / ] || [ -z "$dir" ] && return 1
    dir="$(dirname "$dir")"
  done
}

run() {
  local root="$1"; shift
  if ! out="$(cd "$root" && "$@" 2>&1)"; then
    echo "format-edited-file: $1 failed on $file; left as written: $(printf '%s' "$out" | tail -1)"
  fi
  exit 0
}

dir="$(cd "$(dirname "$file")" && pwd)"
file="$dir/$(basename "$file")"

case "$file" in
  *.php)
    if root="$(up "$dir" pint.json)" || root="$(up_grep "$dir" composer.json '"laravel/pint"')"; then
      [ -x "$root/vendor/bin/pint" ] && run "$root" vendor/bin/pint -q "$file"
    fi
    if root="$(up "$dir" .php-cs-fixer.php .php-cs-fixer.dist.php)"; then
      [ -x "$root/vendor/bin/php-cs-fixer" ] && run "$root" vendor/bin/php-cs-fixer fix -q "$file"
    fi
    ;;
  *.js|*.jsx|*.ts|*.tsx|*.mjs|*.cjs|*.vue|*.css|*.scss|*.json|*.md|*.html|*.yml|*.yaml)
    if root="$(up "$dir" biome.json biome.jsonc)"; then
      [ -x "$root/node_modules/.bin/biome" ] && run "$root" node_modules/.bin/biome format --write "$file"
    fi
    if root="$(up "$dir" .prettierrc .prettierrc.json .prettierrc.yml .prettierrc.yaml .prettierrc.js \
                 .prettierrc.cjs .prettierrc.mjs prettier.config.js prettier.config.cjs prettier.config.mjs)" \
       || root="$(up_grep "$dir" package.json '"prettier"[[:space:]]*:[[:space:]]*\{')"; then
      [ -x "$root/node_modules/.bin/prettier" ] && run "$root" node_modules/.bin/prettier --write --log-level warn "$file"
    fi
    ;;
  *.py)
    if root="$(up "$dir" ruff.toml .ruff.toml)" || root="$(up_grep "$dir" pyproject.toml '^\[tool\.ruff')"; then
      command -v ruff >/dev/null && run "$root" ruff format -q "$file"
    fi
    if root="$(up_grep "$dir" pyproject.toml '^\[tool\.black\]')"; then
      command -v black >/dev/null && run "$root" black -q "$file"
    fi
    ;;
  *.rs)
    if root="$(up "$dir" Cargo.toml)" && command -v rustfmt >/dev/null; then
      edition="$(sed -nE 's/^edition[[:space:]]*=[[:space:]]*"([0-9]+)".*/\1/p' "$root/Cargo.toml" | head -1)"
      # Format through stdin: rustfmt on a named module root also rewrites the
      # external `mod child;` files it finds, and skip_children is nightly-only.
      # stdin formats the one file; write back only on success. Run from the
      # file's directory so rustfmt.toml discovery matches a named-file run.
      tmp="$(mktemp)"
      if err="$(cd "$dir" && rustfmt --edition "${edition:-2021}" --emit stdout < "$file" 2>&1 >"$tmp")"; then
        [ -s "$tmp" ] && cat "$tmp" > "$file"
      else
        echo "format-edited-file: rustfmt failed on $file; left as written: $(printf '%s' "$err" | tail -1)"
      fi
      rm -f "$tmp"
      exit 0
    fi
    ;;
  *.go)
    if root="$(up "$dir" go.mod)" && command -v gofmt >/dev/null; then
      run "$root" gofmt -w "$file"
    fi
    ;;
esac
exit 0
