#!/usr/bin/env bash
# Shared by the startup warning and writing-dispatch guard. No network or
# mutation: projects own the optional doctor contract. See docs/adr/0058.
worktree_infrastructure_ready() {
  local top="$1" doctor="$1/bin/worktree-doctor.sh" entry main_checkout output list_pid
  local -a entries

  if [ ! -e "$doctor" ]; then
    # -z preserves spaces, backslashes and newlines in registered paths. The
    # first worktree is Git's main checkout, even when this is an external one.
    mapfile -d '' -t entries < <(git -C "$top" worktree list --porcelain -z 2>/dev/null)
    list_pid=$!
    if ! wait "$list_pid"; then
      printf 'Worktree infrastructure: registered checkouts cannot be verified. Repair Git worktree metadata before writing.\n'
      return 1
    fi
    entry="${entries[0]:-}"
    main_checkout="${entry#worktree }"
    if [ "$entry" != "$main_checkout" ] && [ -e "$main_checkout/bin/worktree-doctor.sh" ]; then
      printf 'Worktree infrastructure: this checkout lacks bin/worktree-doctor.sh, which exists in the main checkout. Reconcile the project runner changes before writing; do not merge unrelated ticket work.\n'
      return 1
    fi
    return 0
  fi

  if [ ! -x "$doctor" ]; then
    printf 'Worktree infrastructure: bin/worktree-doctor.sh is not executable. Restore its executable mode before writing.\n'
    return 1
  fi
  if ! command -v timeout >/dev/null; then
    printf 'Worktree infrastructure: timeout is unavailable; the bounded readiness check cannot run. Install coreutils before writing.\n'
    return 1
  fi
  if output="$(cd "$top" && timeout 5 "$doctor" --infrastructure 2>&1)"; then
    return 0
  fi
  printf 'Worktree infrastructure check failed or timed out. Reconcile the reported runner changes before writing.\n%s\n' "$output"
  return 1
}
