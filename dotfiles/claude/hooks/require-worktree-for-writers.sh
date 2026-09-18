#!/usr/bin/env bash
# PreToolUse hook (Agent|Task). Writers require a verified ticket checkout or
# feature branch and current project test infrastructure. Sequential executors
# inherit that checkout; parallel dispatch explicitly requests isolation.
# Invalid input/state denies dispatch; read-only personas remain unrestricted.
# Exit 0, with a JSON permissionDecision on stdout. See docs/adr/0058.
set -uo pipefail

# Fixed strings use this dependency-free response when no JSON parser works.
deny_unverified() {
  printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"Cannot verify agent dispatch input. Restore jq or Python 3 and supply valid JSON with string persona/cwd fields before retrying."}}'
  exit 0
}
deny() {
  if command -v jq >/dev/null; then
    jq -n --arg reason "$1" '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$reason}}' || deny_unverified
  else
    python3 -c 'import json,sys; print(json.dumps({"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":sys.argv[1]}}))' "$1" || deny_unverified
  fi
  exit 0
}

input="$(cat 2>/dev/null)" || deny_unverified
if command -v jq >/dev/null; then
  parsed="$(jq -ser '
    if length != 1 then error("one input object required") else .[0] end |
    if type != "object" then error("object required") else . end |
    (.tool_input | if . == null then {} else . end) as $tool |
    if ($tool | type) != "object" then error("tool_input object required") else . end |
    if all([.cwd, .agent_type, $tool.subagent_type, $tool.agent_type][]; . == null or type == "string")
    then [$tool.subagent_type // $tool.agent_type // .agent_type // "", .cwd // ""]
    else error("string fields required") end |
    if all(.[]; type == "string" and (test("[\\x00-\\x1f\\x7f]") | not))
    then .[0] + "\n" + .[1] + "\nend" else error("string fields required") end
  ' <<<"$input" 2>/dev/null)" || deny_unverified
elif command -v python3 >/dev/null; then
  parsed="$(python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)
    if not isinstance(data, dict): raise ValueError()
    tool = data.get("tool_input")
    if tool is None: tool = {}
    if not isinstance(tool, dict): raise ValueError()
    fields = [tool.get("subagent_type"), tool.get("agent_type"), data.get("agent_type"), data.get("cwd")]
    if any(v is not None and not isinstance(v, str) for v in fields): raise ValueError()
    agent = next((v for v in fields[:3] if v is not None), "")
    cwd = fields[3] if fields[3] is not None else ""
    if any(not isinstance(v, str) or any(ord(c) < 32 or ord(c) == 127 for c in v) for v in (agent, cwd)): raise ValueError()
    print(agent + "\n" + cwd + "\nend")
except (ValueError, TypeError):
    sys.exit(1)
' <<<"$input" 2>/dev/null)" || deny_unverified
else
  deny_unverified
fi
agent="${parsed%%$'\n'*}"
rest="${parsed#*$'\n'}"
cwd="${rest%$'\n'*}"
case "$agent" in
  executor|test-engineer) ;;
  *) exit 0 ;;
esac

[ -n "$cwd" ] && [ -d "$cwd" ] || deny "Refusing to dispatch $agent: cwd is missing or unavailable. Select the ticket checkout before retrying."
cd "$cwd" 2>/dev/null || deny "Refusing to dispatch $agent: cannot enter the ticket checkout."
top="$(git rev-parse --show-toplevel 2>/dev/null)" || deny "Refusing to dispatch $agent: cwd is not a verifiable Git checkout."
branch="$(git symbolic-ref --quiet --short HEAD 2>/dev/null)" || deny "Refusing to dispatch $agent: detached HEAD has no branch to receive the work. Select the ticket branch first."
git rev-parse --verify HEAD >/dev/null 2>&1 || deny "Refusing to dispatch $agent: HEAD cannot be verified."
git_dir="$(cd "$(git rev-parse --git-dir 2>/dev/null)" && pwd -P)" || deny "Refusing to dispatch $agent: Git worktree metadata cannot be verified."
common_dir="$(cd "$(git rev-parse --git-common-dir 2>/dev/null)" && pwd -P)" || deny "Refusing to dispatch $agent: Git common directory cannot be verified."

if [ "$git_dir" = "$common_dir" ]; then
  default="$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null)"
  default="${default#origin/}"
  if [ -z "$default" ]; then
    for candidate in main master; do
      git show-ref --verify --quiet "refs/heads/$candidate" && { default="$candidate"; break; }
    done
  fi
  [ -n "$default" ] || deny "Refusing to dispatch $agent: the default branch cannot be verified. Set origin/HEAD or use a ticket worktree."
  [ "$branch" != "$default" ] || deny "Refusing to dispatch $agent: this is the default branch in the main checkout. Start with claude --worktree <ticket>, or create a feature branch before writing."
fi

hook_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)" || deny "Refusing to dispatch $agent: hook directory cannot be verified."
source "$hook_dir/worktree-readiness.sh" || deny "Refusing to dispatch $agent: the infrastructure readiness helper is unavailable."
readiness="$(worktree_infrastructure_ready "$top")" || deny "$readiness"
exit 0
