#!/usr/bin/env bash
# Fixture tests for dotfiles/claude/hooks/format-edited-file.sh (ADR 0107).
#
# Each case builds a tiny project with a stub formatter that records its
# arguments, edits one file through the hook's JSON input, and checks whether
# the formatter ran. The negative cases matter as much: a project without a
# declared formatter, or with the config but nothing installed, must be left
# alone, and vendored paths are never formatted.
set -uo pipefail

HOOK="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../claude/hooks" && pwd)/format-edited-file.sh"
command -v jq >/dev/null || { echo "test-format-hook: jq is required" >&2; exit 1; }
REAL_RUSTFMT="$(command -v rustfmt || true)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0

stub() {   # stub PATH: an executable that logs its arguments to $LOG
  mkdir -p "$(dirname "$1")"
  printf '#!/usr/bin/env bash\necho "$(basename "$0") $*" >> "%s"\n' "$TMP/log" > "$1"
  chmod +x "$1"
}
edit() {   # edit FILE: run the hook as Claude Code would after an Edit
  : > "$TMP/log"
  jq -n --arg f "$1" '{tool_name:"Edit", tool_input:{file_path:$f}}' | PATH="$TMP/bin:/usr/bin:/bin" "$HOOK"
}
expect() { # expect NAME PATTERN|-  (- means the formatter must not run)
  if [ "$2" = - ]; then
    [ ! -s "$TMP/log" ] && { PASS=$((PASS+1)); return; }
  else
    grep -qE "$2" "$TMP/log" && { PASS=$((PASS+1)); return; }
  fi
  FAIL=$((FAIL+1)); echo "FAIL: $1 (log: $(cat "$TMP/log"))"
}

# Laravel: laravel/pint in composer.json and vendor/bin/pint installed.
p="$TMP/laravel"; mkdir -p "$p/app" && echo '{"require-dev":{"laravel/pint":"^1"}}' > "$p/composer.json"
stub "$p/vendor/bin/pint"; echo '<?php' > "$p/app/A.php"
edit "$p/app/A.php"; expect "pint on a Laravel file" "^pint -q $p/app/A.php$"
mkdir -p "$p/vendor/x" && echo '<?php' > "$p/vendor/x/B.php"
edit "$p/vendor/x/B.php"; expect "vendored file is never formatted" -

# Config present, formatter not installed: leave it.
p="$TMP/noinstall"; mkdir -p "$p" && echo '{}' > "$p/pint.json" && echo '<?php' > "$p/A.php"
edit "$p/A.php"; expect "pint configured but not installed" -

# Prettier as a dependency only is not a config; a config file is.
p="$TMP/web"; mkdir -p "$p/src" && echo '{"devDependencies":{"prettier":"^3"}}' > "$p/package.json"
stub "$p/node_modules/.bin/prettier"; echo 'x' > "$p/src/a.ts"
edit "$p/src/a.ts"; expect "prettier dependency without config" -
echo '{}' > "$p/.prettierrc"
edit "$p/src/a.ts"; expect "prettier with a config" "^prettier --write --log-level warn $p/src/a.ts$"

# Python: ruff only when the project configures it.
p="$TMP/py"; mkdir -p "$p/pkg" "$TMP/bin" && stub "$TMP/bin/ruff" && echo 'x=1' > "$p/pkg/m.py"
printf '[project]\nname="x"\n' > "$p/pyproject.toml"
edit "$p/pkg/m.py"; expect "python without ruff config" -
printf '[project]\nname="x"\n[tool.ruff]\nline-length=100\n' > "$p/pyproject.toml"
edit "$p/pkg/m.py"; expect "ruff with [tool.ruff]" "^ruff format -q $p/pkg/m.py$"

# A nearer project that declares and installs a formatter beats an outer
# directory holding another declaration of the same formatter (here without
# the binary): all declarations at one level are checked before the parent.
p="$TMP/nest-pint"; mkdir -p "$p/inner/app" && echo '{}' > "$p/pint.json"
echo '{"require-dev":{"laravel/pint":"^1"}}' > "$p/inner/composer.json"
stub "$p/inner/vendor/bin/pint"; echo '<?php' > "$p/inner/app/A.php"
edit "$p/inner/app/A.php"; expect "inner composer pint beats outer pint.json" "^pint -q $p/inner/app/A.php$"

p="$TMP/nest-prettier"; mkdir -p "$p/inner/src" && echo '{}' > "$p/.prettierrc"
echo '{"prettier":{"semi":false}}' > "$p/inner/package.json"
stub "$p/inner/node_modules/.bin/prettier"; echo 'x' > "$p/inner/src/a.ts"
edit "$p/inner/src/a.ts"; expect "inner package.json prettier beats outer .prettierrc" "^prettier --write --log-level warn $p/inner/src/a.ts$"

p="$TMP/nest-ruff"; mkdir -p "$p/inner/pkg" "$TMP/pwdbin" && echo 'line-length = 80' > "$p/ruff.toml"
printf '#!/usr/bin/env bash\necho "ruff $PWD" >> "%s"\n' "$TMP/log" > "$TMP/pwdbin/ruff"; chmod +x "$TMP/pwdbin/ruff"
printf '[tool.ruff]\nline-length=100\n' > "$p/inner/pyproject.toml"; echo 'x=1' > "$p/inner/pkg/m.py"
: > "$TMP/log"; jq -n --arg f "$p/inner/pkg/m.py" '{tool_name:"Edit", tool_input:{file_path:$f}}' | PATH="$TMP/pwdbin:/usr/bin:/bin" "$HOOK"
expect "inner pyproject ruff beats outer ruff.toml" "^ruff $p/inner$"

# Rust: rustfmt with the crate's edition.
p="$TMP/rs"; mkdir -p "$p/src" && stub "$TMP/bin/rustfmt" && echo 'fn main(){}' > "$p/src/main.rs"
printf '[package]\nname="x"\nedition = "2024"\n' > "$p/Cargo.toml"
edit "$p/src/main.rs"; expect "rustfmt with the Cargo edition" "^rustfmt --edition 2024 --emit stdout$"

# Rust, real rustfmt: formatting a module root must not follow `mod child;`
# into files the edit did not touch. The stub above cannot show this.
if [ -n "$REAL_RUSTFMT" ]; then
  p="$TMP/rsmod"; mkdir -p "$p/src" "$TMP/realbin" && ln -sf "$REAL_RUSTFMT" "$TMP/realbin/rustfmt"
  printf '[package]\nname="x"\nedition = "2021"\n' > "$p/Cargo.toml"
  printf 'mod child;\nfn  a( ){}\n' > "$p/src/lib.rs"
  printf 'fn  b( ){}\n' > "$p/src/child.rs"
  jq -n --arg f "$p/src/lib.rs" '{tool_name:"Edit", tool_input:{file_path:$f}}' | PATH="$TMP/realbin:/usr/bin:/bin" "$HOOK"
  if grep -q '^fn a() {}$' "$p/src/lib.rs"; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); echo "FAIL: real rustfmt formats the edited module root"; fi
  if [ "$(cat "$p/src/child.rs")" = 'fn  b( ){}' ]; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); echo "FAIL: real rustfmt left the child module alone (got: $(cat "$p/src/child.rs"))"; fi
  printf 'fn  a( {' > "$p/src/bad.rs"
  out="$(jq -n --arg f "$p/src/bad.rs" '{tool_name:"Edit", tool_input:{file_path:$f}}' | PATH="$TMP/realbin:/usr/bin:/bin" "$HOOK")"; rc=$?
  if [ "$rc" = 0 ] && [ "$(cat "$p/src/bad.rs")" = 'fn  a( {' ] && printf '%s' "$out" | grep -q 'left as written'; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); echo "FAIL: real rustfmt syntax error leaves the file (rc=$rc out=$out)"; fi
else
  echo "SKIP: real rustfmt not installed; module-root scope check not run"
fi

# A file type no formatter owns, and a missing file.
edit "$p/Cargo.toml"; expect "toml is not formatted" -
edit "$p/src/gone.rs"; expect "missing file" -

# A failing formatter never fails the edit.
p="$TMP/broken"; mkdir -p "$p/vendor/bin" && echo '{}' > "$p/pint.json" && echo '<?php' > "$p/A.php"
printf '#!/usr/bin/env bash\necho "syntax error" >&2\nexit 1\n' > "$p/vendor/bin/pint"; chmod +x "$p/vendor/bin/pint"
out="$(edit "$p/A.php")"; rc=$?
if [ "$rc" = 0 ] && printf '%s' "$out" | grep -q 'left as written'; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); echo "FAIL: failing formatter (rc=$rc out=$out)"; fi

echo "format hook: $PASS passed, $FAIL failed"
[ "$FAIL" = 0 ]
