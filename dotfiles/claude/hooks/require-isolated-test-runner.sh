#!/usr/bin/env bash
# PreToolUse hook (matcher: Bash). Denies a bare test-suite run when the
# project ships an isolating runner and more than one worktree is live.
#
# The failure: Laravel pins APP_ENV=testing in phpunit.xml, and .env.testing
# names ONE database and Redis index. Every worktree copies that same file, so
# two suites started at once drop and re-migrate each other's schema. There is
# no lock error -- just a suite failing for reasons unrelated to its own diff,
# in the run of whoever started second. The project's runner exists precisely
# to stop this: it derives DB_DATABASE and REDIS_PREFIX from the worktree
# directory name. Reaching for `php artisan test` is not a mistake anyone
# notices making -- it is the framework's own documented command.
#
# Deliberately evidence-gated, because this hook is global and most projects
# have no such runner:
#   - the repository must actually ship `bin/worktree-test.sh`;
#   - more than one worktree must be live (one checkout cannot collide with
#     itself, and the project's own rule is scoped that way).
# Either missing, and the hook allows. It never guesses that a project wants
# this discipline.
#
# Exit 0 always; the decision is JSON on stdout, per
# https://code.claude.com/docs/en/hooks.
set -uo pipefail

input="$(cat 2>/dev/null)" || exit 0
command="$(jq -r '.tool_input.command // empty' <<<"$input" 2>/dev/null)"
cwd="$(jq -r '.cwd // empty' <<<"$input" 2>/dev/null)"
[ -n "$command" ] || exit 0

# Command position only: a separator (or the start) then optional `php ...`.
# `grep 'php artisan test' docs/` and `echo "php artisan test"` put it after a
# quote, not after a separator, so they read as text and stay allowed.
sep='(^|[;&|(])[[:space:]]*'
artisan="${sep}(php[[:space:]]+([^;&|()]*[[:space:]]+)?)?\.?/?artisan[[:space:]]+test([[:space:]]|$)"
phpunit="${sep}(\.?/)?(vendor/bin/)?phpunit([[:space:]]|$)"
echo "$command" | grep -Eq "$artisan|$phpunit" || exit 0

# `test:foo` is a different artisan command and never matches above; the
# checks below decide whether this repository is the one that cares.
[ -n "$cwd" ] && [ -d "$cwd" ] || exit 0
cd "$cwd" 2>/dev/null || exit 0
top="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
[ -x "$top/bin/worktree-test.sh" ] || [ -f "$top/bin/worktree-test.sh" ] || exit 0
[ "$(git worktree list 2>/dev/null | wc -l)" -gt 1 ] || exit 0

jq -n --arg reason "$(cat <<'MSG'
Use `composer test`, not a bare test run: more than one worktree is live here.

phpunit.xml pins APP_ENV=testing and every worktree carries the same .env.testing,
so a bare run uses the one shared test database and Redis index. Two suites at once
drop and re-migrate each other's schema -- no lock error, just a suite that fails for
reasons unrelated to its own diff.

    composer test                      # bin/worktree-test.sh
    composer test -- --filter=CrmId    # extra arguments forward

It derives DB_DATABASE and REDIS_PREFIX from the worktree directory name and runs
--parallel, so each worktree gets its own database.
MSG
)" '{
  hookSpecificOutput: {
    hookEventName: "PreToolUse",
    permissionDecision: "deny",
    permissionDecisionReason: $reason
  }
}'
exit 0
