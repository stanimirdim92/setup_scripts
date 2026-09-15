#!/usr/bin/env bash
# Fixture tests for dotfiles/claude/hooks/require-isolated-test-runner.sh.
#
# This hook is global and denies a command the framework itself documents, so
# the allow cases are the ones that decide whether it survives: a project with
# no isolating runner, a single checkout, `artisan test:foo`, and the suite run
# the right way. Each case builds real repositories, because the hook decides
# from `git worktree list` and a file on disk.
#
# Run: tools/test-isolated-test-runner.sh
set -uo pipefail

HOOK="$(cd "$(dirname "${BASH_SOURCE[0]}")/../dotfiles/claude/hooks" && pwd)/require-isolated-test-runner.sh"
command -v jq >/dev/null || { echo "test-isolated-test-runner: jq is required" >&2; exit 1; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0; FAILED=()
G=(-c user.email=t@t -c user.name=t -c init.defaultBranch=main)

make_repo() {  # name, with_runner(1/0) -> path
  local d="$TMP/$1"; git "${G[@]}" init -q "$d"
  ( cd "$d" && mkdir -p bin && [ "$2" = 1 ] && printf '#!/bin/sh\n' > bin/worktree-test.sh
    echo x > README.md; git "${G[@]}" add -A; git "${G[@]}" commit -qm base ) >/dev/null 2>&1
  echo "$d"
}
decision() { # command, cwd
  jq -n --arg c "$1" --arg d "$2" '{tool_input:{command:$c},cwd:$d}' \
    | bash "$HOOK" 2>/dev/null | jq -r '.hookSpecificOutput.permissionDecision // "allow"' 2>/dev/null
}
check() { # label, expected, command, cwd
  local got; got="$(decision "$3" "$4")"; [ -z "$got" ] && got=allow
  if [ "$2" = "$got" ]; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); FAILED+=("[$1] '$3' expected $2, got $got"); fi
}

ISO="$(make_repo isolated 1)"                       # has the runner
BARE="$(make_repo bare 0)"                          # no runner: not our business
git -C "$ISO" "${G[@]}" worktree add -q -b t/1 "$TMP/wt1" >/dev/null 2>&1
git -C "$BARE" "${G[@]}" worktree add -q -b t/1 "$TMP/wt-bare" >/dev/null 2>&1
SOLO="$(make_repo solo 1)"                          # runner, but one checkout

# ------------------------------------------------------------------ denials
check artisan_test              deny 'php artisan test'                       "$ISO"
check artisan_test_filter       deny 'php artisan test --filter=CrmId'        "$ISO"
check artisan_test_parallel     deny 'php artisan test --parallel'            "$ISO"
check dot_artisan               deny './artisan test'                         "$ISO"
check bare_artisan              deny 'artisan test'                           "$ISO"
check php_with_flags            deny 'php -d memory_limit=-1 artisan test'    "$ISO"
check after_and                 deny 'cd modules && php artisan test'         "$ISO"
check after_semicolon           deny 'composer install; php artisan test'     "$ISO"
check piped_chain               deny 'php artisan test | tee out.txt'         "$ISO"
check phpunit_vendor            deny 'vendor/bin/phpunit'                     "$ISO"
check phpunit_dot_vendor        deny './vendor/bin/phpunit'                   "$ISO"
check phpunit_bare              deny 'phpunit --filter=Foo'                   "$ISO"
# Env-prefixed forms. `DB_DATABASE=... php artisan test --parallel` is the line
# inside bin/worktree-test.sh itself, so it is the spelling anyone reaches for
# after reading that script -- and the one that undoes the isolation.
check env_prefix_one            deny 'APP_ENV=testing php artisan test'       "$ISO"
check env_prefix_two            deny 'DB_DATABASE="$DB" REDIS_PREFIX="$S-" php artisan test --parallel' "$ISO"
check env_word_prefix           deny 'env APP_ENV=testing php artisan test'   "$ISO"
check env_prefix_phpunit        deny 'XDEBUG_MODE=off vendor/bin/phpunit'     "$ISO"
check env_prefix_after_and      deny 'cd m && FOO=1 php artisan test'         "$ISO"
# Reported by an external review: the command boundary was whitespace-or-end,
# so anything chained after the test command slipped past -- and chaining is
# the first thing anyone does. The interpreter was matched as the literal word
# `php`, so every absolute path and versioned binary slipped past too.
check trailing_semicolon        deny 'php artisan test; echo done'            "$ISO"
check trailing_and              deny 'php artisan test&&echo x'               "$ISO"
check trailing_pipe             deny 'php artisan test|tee out.txt'           "$ISO"
check trailing_redirect         deny 'php artisan test>out.txt'               "$ISO"
check trailing_paren            deny '(php artisan test)'                     "$ISO"
check absolute_php              deny '/usr/bin/php artisan test'              "$ISO"
check versioned_php             deny 'php8.2 artisan test'                    "$ISO"
check php_runs_phpunit          deny 'php vendor/bin/phpunit'                 "$ISO"
check paratest                  deny 'php vendor/bin/paratest'                "$ISO"
check absolute_phpunit          deny '/app/vendor/bin/phpunit --filter=X'     "$ISO"
check inside_a_worktree         deny 'php artisan test'                       "$TMP/wt1"

# ------------------------------------------------------------------- allows
# The right way, and the artisan commands that merely start with "test".
check composer_test             allow 'composer test'                         "$ISO"
check composer_test_args        allow 'composer test -- --filter=CrmId'       "$ISO"
check worktree_test_direct      allow 'bin/worktree-test.sh'                  "$ISO"
check artisan_test_colon        allow 'php artisan test:coverage'             "$ISO"
check artisan_migrate           allow 'php artisan migrate'                   "$ISO"
check env_prefix_migrate        allow 'APP_ENV=testing php artisan migrate'   "$ISO"
check env_prefix_composer       allow 'XDEBUG_MODE=off composer test'         "$ISO"
# The widened interpreter and boundary must not start matching neighbours.
check artisan_test_colon_chain  allow 'php artisan test:coverage; echo done'  "$ISO"
check phpstan_not_phpunit       allow 'vendor/bin/phpstan analyse'            "$ISO"
check php_cs_fixer              allow 'php vendor/bin/php-cs-fixer fix'       "$ISO"
check php_version               allow 'php -v'                                "$ISO"
check composer_chain            allow 'composer install && composer test'     "$ISO"
check artisan_tinker            allow 'php artisan tinker'                    "$ISO"
check artisan_route_list        allow 'php artisan route:list'                "$ISO"
check yarn_test                 allow 'yarn run test'                         "$ISO"
# Text, not a command: these are how you search for or explain the rule.
check grep_for_it               allow "grep -rn 'php artisan test' docs/"     "$ISO"
check echo_it                   allow 'echo "run php artisan test"'           "$ISO"
# These two need the command-position anchor specifically: the quoted text is
# followed by a space, so the trailing word boundary alone would let it match.
check grep_trailing_space       allow "grep -rn 'php artisan test ' docs/"    "$ISO"
check echo_mid_sentence         allow 'echo "php artisan test is wrong here"' "$ISO"
# Evidence gates: no runner in the repo, and a lone checkout.
check no_runner_in_project      allow 'php artisan test'                      "$BARE"
check no_runner_in_worktree     allow 'php artisan test'                      "$TMP/wt-bare"
check single_checkout           allow 'php artisan test'                      "$SOLO"
# Nothing to decide from.
check not_a_git_repo            allow 'php artisan test'                      "$TMP"
check missing_cwd               allow 'php artisan test'                      "$TMP/nope"
check empty_command             allow ''                                      "$ISO"

# The refusal has to name the replacement, or it only blocks work.
reason="$(jq -n --arg c 'php artisan test' --arg d "$ISO" '{tool_input:{command:$c},cwd:$d}' \
  | bash "$HOOK" 2>/dev/null | jq -r '.hookSpecificOutput.permissionDecisionReason // ""')"
case "$reason" in *"composer test"*) PASS=$((PASS+1)) ;; *) FAIL=$((FAIL+1)); FAILED+=("[names_the_fix] reason omits 'composer test'") ;; esac
case "$reason" in *"--filter"*) PASS=$((PASS+1)) ;; *) FAIL=$((FAIL+1)); FAILED+=("[shows_arg_forwarding] reason omits the --filter form") ;; esac

echo "isolated test runner: $PASS passed, $FAIL failed"
if [ "$FAIL" -gt 0 ]; then printf '\n'; for f in "${FAILED[@]}"; do echo "  FAIL $f"; done; exit 1; fi
