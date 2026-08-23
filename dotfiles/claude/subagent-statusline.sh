#!/bin/bash
# Custom row body for each subagent shown in the agent panel.
# Input: base hook fields + `columns` + `tasks[]` (see docs.claude.com/en/statusline#subagent-status-lines)
# Output: one JSON line per row to override: {"id": "<task id>", "content": "<row body>"}
input=$(cat)
NOW_MS=$(date +%s%3N)

echo "$input" | jq -c --argjson now "$NOW_MS" '
  def esc(code): "[" + code + "m";
  .tasks[]?
  | . as $t
  | (if $t.status == "completed" then "✅"
     elif ($t.status == "failed" or $t.status == "error") then "❌"
     elif ($t.status == "running" or $t.status == "in_progress") then "⏳"
     else "•" end) as $icon
  | (if $t.startTime then (($now - $t.startTime) / 1000 | floor) else null end) as $es
  | (if $es != null then
        (if $es >= 60 then "\($es / 60 | floor)m\($es % 60)s" else "\($es)s" end)
     else null end) as $elapsed
  | (if ($t.contextWindowSize and $t.tokenCount) then (($t.tokenCount * 100 / $t.contextWindowSize) | floor) else null end) as $pct
  | (if $pct != null then
        (if $pct >= 90 then esc("31") elif $pct >= 70 then esc("33") else esc("32") end)
     else null end) as $pcolor
  | (if $pct != null then "\($pcolor)\($pct)%\(esc("0"))"
     elif $t.tokenCount then "\($t.tokenCount)tok"
     else null end) as $tok
  | [$icon, $t.name, $t.model, $tok, $elapsed] | map(select(. != null)) | join(" · ") as $body
  | {id: $t.id, content: (esc("36") + $body + esc("0"))}
'
