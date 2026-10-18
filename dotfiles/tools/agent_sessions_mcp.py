#!/usr/bin/env python3
"""agent-sessions: read-only session lister for Claude Code, Codex and Gemini CLI.

Modes (no dependencies, Python 3.8+):
  python3 agent_sessions_mcp.py --serve [--port 8787]   live dashboard at http://127.0.0.1:8787
  python3 agent_sessions_mcp.py --print                 dump JSON to stdout
  python3 agent_sessions_mcp.py                         MCP server over stdio


Lists recent Claude Code, Codex and Gemini CLI sessions found on this machine
so the Session Command Center board can show them.

Reads only:
  ~/.claude/projects/*/*.jsonl        Claude Code transcripts
  ~/.claude/jobs/*/state.json         Claude Code agent view state (if present)
  ~/.codex/sessions/**/rollout-*.jsonl Codex sessions
  ~/.gemini/tmp/*/chats/*.json        Gemini CLI saved sessions

Returns metadata only: id, agent, folder, branch, title (first prompt, cut to
140 chars), last activity, message count and a status guess. No file contents,
no tool output.
"""
import json
import os
import sys
import time
from pathlib import Path

HOME = Path(os.environ.get("AGENT_SESSIONS_HOME", str(Path.home())))
VERSION = "1.0.0"
HEAD_LINES = 400
TAIL_BYTES = 96 * 1024
TITLE_MAX = 140
SKIP_PREFIXES = ("<command", "<local-command", "Caveat:", "<environment_context", "<user_instructions",
                 "# AGENTS.md", "<system-reminder", "[Request interrupted")


# ---------- helpers ----------

def iso_to_ts(s):
    if not s or not isinstance(s, str):
        return None
    try:
        from datetime import datetime
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


def clean_title(text):
    if not isinstance(text, str):
        return None
    t = " ".join(text.split())
    if not t or t.startswith(SKIP_PREFIXES):
        return None
    return t[:TITLE_MAX]


def text_of(content):
    """First text from a message content (str or list of blocks)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        for b in content:
            if isinstance(b, dict):
                if b.get("type") in ("text", "input_text") and isinstance(b.get("text"), str):
                    return b["text"]
            elif isinstance(b, str):
                return b
    return None


def read_head(path, n=HEAD_LINES):
    out = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f):
                if i >= n:
                    break
                line = line.strip()
                if line:
                    try:
                        out.append(json.loads(line))
                    except Exception:
                        pass
    except OSError:
        pass
    return out


def read_tail(path, nbytes=TAIL_BYTES):
    out = []
    try:
        size = path.stat().st_size
        with open(path, "rb") as f:
            if size > nbytes:
                f.seek(size - nbytes)
                f.readline()  # drop partial line
            for raw in f:
                raw = raw.strip()
                if raw:
                    try:
                        out.append(json.loads(raw.decode("utf-8", "replace")))
                    except Exception:
                        pass
    except OSError:
        pass
    return out


def count_lines(path):
    try:
        with open(path, "rb") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


def guess_status(mtime, last_role, now):
    age = now - mtime
    if age < 120:
        return "working"
    if last_role == "assistant" and age < 6 * 3600:
        return "needs"
    return "parked"


# ---------- Claude Code ----------

def claude_jobs():
    """Agent view state, keyed by any session id we can find in it."""
    jobs = {}
    base = HOME / ".claude" / "jobs"
    if not base.is_dir():
        return jobs
    for st in base.glob("*/state.json"):
        try:
            d = json.loads(st.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        state = d.get("state") or d.get("status")
        info = {"jobId": st.parent.name, "state": state if isinstance(state, str) else None}
        for k in ("sessionId", "session_id", "conversationId", "id"):
            v = d.get(k)
            if isinstance(v, str):
                jobs[v] = info
        jobs.setdefault(st.parent.name, info)
    return jobs


def map_job_state(s):
    if not s:
        return None
    s = s.lower()
    if any(k in s for k in ("input", "permission", "waiting", "blocked_on_user")):
        return "needs"
    if "review" in s:
        return "review"
    if any(k in s for k in ("complete", "done", "finished", "exited")):
        return "done"
    if any(k in s for k in ("error", "fail", "crash")):
        return "blocked"
    if any(k in s for k in ("work", "run", "busy", "active")):
        return "working"
    return None


def scan_claude(cutoff, now):
    base = HOME / ".claude" / "projects"
    if not base.is_dir():
        return []
    jobs = claude_jobs()
    out = []
    for f in base.glob("*/*.jsonl"):
        try:
            mtime = f.stat().st_mtime
        except OSError:
            continue
        if mtime < cutoff:
            continue
        head = read_head(f)
        tail = read_tail(f)
        sid = f.stem
        cwd = branch = title = summary = None
        for e in head:
            if not isinstance(e, dict):
                continue
            sid = e.get("sessionId") or sid
            cwd = cwd or e.get("cwd")
            branch = branch or e.get("gitBranch")
            if e.get("type") == "summary" and isinstance(e.get("summary"), str):
                summary = summary or e["summary"]
            if not title and e.get("type") == "user" and not e.get("isMeta") and not e.get("isSidechain"):
                title = clean_title(text_of((e.get("message") or {}).get("content")))
        last_role = None
        for e in tail:
            if not isinstance(e, dict):
                continue
            if e.get("gitBranch"):
                branch = e["gitBranch"]
            if e.get("type") == "summary" and isinstance(e.get("summary"), str):
                summary = e["summary"]
            if e.get("type") in ("user", "assistant") and not e.get("isSidechain"):
                msg = e.get("message") or {}
                content = msg.get("content")
                # a user line that only carries tool results is the agent still working
                if e["type"] == "user" and isinstance(content, list) and all(
                        isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
                    last_role = "tool"
                else:
                    last_role = e["type"]
        status = guess_status(mtime, last_role, now)
        job = jobs.get(sid)
        if job:
            status = map_job_state(job.get("state")) or status
        out.append({
            "agent": "claude", "id": sid, "cwd": cwd, "project": Path(cwd).name if cwd else f.parent.name,
            "branch": branch if branch and branch != "HEAD" else None,
            "title": clean_title(summary) or title or "(no prompt yet)",
            "lastActive": int(mtime * 1000), "messages": count_lines(f),
            "status": status, "jobId": job.get("jobId") if job else None,
            "jobState": job.get("state") if job else None,
        })
    return out


# ---------- Codex ----------

def scan_codex(cutoff, now):
    base = HOME / ".codex" / "sessions"
    if not base.is_dir():
        return []
    out = []
    for f in base.rglob("rollout-*.jsonl"):
        try:
            mtime = f.stat().st_mtime
        except OSError:
            continue
        if mtime < cutoff:
            continue
        head = read_head(f)
        sid = cwd = branch = title = None
        for e in head:
            if not isinstance(e, dict):
                continue
            p = e.get("payload") if isinstance(e.get("payload"), dict) else e
            t = e.get("type")
            if t == "session_meta" or (sid is None and isinstance(p.get("id"), str) and p.get("cwd")):
                sid = sid or p.get("id")
                cwd = cwd or p.get("cwd")
                g = p.get("git") or {}
                branch = branch or (g.get("branch") if isinstance(g, dict) else None)
            if not title:
                if p.get("type") == "user_message":
                    title = clean_title(p.get("message"))
                elif p.get("type") == "message" and p.get("role") == "user":
                    title = clean_title(text_of(p.get("content")))
        last_role = None
        for e in read_tail(f):
            if not isinstance(e, dict):
                continue
            p = e.get("payload") if isinstance(e.get("payload"), dict) else e
            if p.get("type") == "message" and p.get("role") in ("user", "assistant"):
                last_role = p["role"]
            elif p.get("type") in ("user_message",):
                last_role = "user"
            elif p.get("type") in ("agent_message", "task_complete"):
                last_role = "assistant"
            elif p.get("type") in ("function_call", "function_call_output", "exec_command_begin"):
                last_role = "tool"
        if not sid:
            # rollout-<timestamp>-<uuid>.jsonl
            parts = f.stem.split("-")
            sid = "-".join(parts[-5:]) if len(parts) >= 6 else f.stem
        out.append({
            "agent": "codex", "id": sid, "cwd": cwd, "project": Path(cwd).name if cwd else None,
            "branch": branch, "title": title or "(no prompt yet)",
            "lastActive": int(mtime * 1000), "messages": count_lines(f),
            "status": guess_status(mtime, last_role, now),
        })
    return out


# ---------- Gemini CLI ----------

def scan_gemini(cutoff, now):
    base = HOME / ".gemini" / "tmp"
    if not base.is_dir():
        return []
    out = []
    for f in base.glob("*/chats/*.json"):
        try:
            mtime = f.stat().st_mtime
            if mtime < cutoff:
                continue
            d = json.loads(f.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            continue
        msgs = d.get("messages") if isinstance(d, dict) else d
        msgs = msgs if isinstance(msgs, list) else []
        title = None
        last_role = None
        for m in msgs:
            if not isinstance(m, dict):
                continue
            role = m.get("type") or m.get("role")
            txt = m.get("content")
            if not isinstance(txt, str):
                txt = text_of(txt) or text_of(m.get("parts"))
            if role == "user" and not title:
                title = clean_title(txt)
            if role in ("user",):
                last_role = "user"
            elif role in ("gemini", "model", "assistant"):
                last_role = "assistant"
        sid = (d.get("sessionId") if isinstance(d, dict) else None) or f.stem
        out.append({
            "agent": "gemini", "id": sid, "cwd": None, "project": None,
            "projectHash": f.parent.parent.name, "branch": None,
            "title": title or "(no prompt yet)", "lastActive": int(mtime * 1000),
            "messages": len(msgs), "status": guess_status(mtime, last_role, now),
        })
    return out


def list_sessions(args):
    days = args.get("days", 14) if isinstance(args, dict) else 14
    try:
        days = max(1, min(90, int(days)))
    except Exception:
        days = 14
    limit = args.get("limit", 150) if isinstance(args, dict) else 150
    try:
        limit = max(1, min(500, int(limit)))
    except Exception:
        limit = 150
    now = time.time()
    cutoff = now - days * 86400
    sessions, errors = [], []
    for name, fn in (("claude", scan_claude), ("codex", scan_codex), ("gemini", scan_gemini)):
        try:
            sessions.extend(fn(cutoff, now))
        except Exception as e:  # keep the other agents working
            errors.append(f"{name}: {e}")
    sessions.sort(key=lambda s: s["lastActive"], reverse=True)
    return {"scannedAt": int(now * 1000), "host": os.uname().nodename if hasattr(os, "uname") else os.environ.get("COMPUTERNAME"),
            "days": days, "total": len(sessions), "sessions": sessions[:limit], "errors": errors}


# ---------- local dashboard (--serve) ----------

PAGE = r"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Agent sessions</title>
<style>
:root{--bg:#f3f4f7;--s:#fff;--s2:#eceef3;--line:#dfe2ea;--fg:#141821;--mu:#5d6577;--fa:#8b92a3;
--work:#2f6fed;--need:#d98a00;--rev:#8a4fe0;--block:#e0384d;--park:#7a8396;--done:#13a06b;--cl:#d2692e;--cx:#0d9488;--gm:#3f6fe8;
--mono:ui-monospace,"JetBrains Mono","IBM Plex Mono",Menlo,Consolas,monospace;--sans:system-ui,-apple-system,"Segoe UI",Ubuntu,Roboto,sans-serif;color-scheme:light}
@media (prefers-color-scheme:dark){:root{--bg:#0d1016;--s:#161a23;--s2:#1e2330;--line:#2a3040;--fg:#e9ecf3;--mu:#a2a9b8;--fa:#6f7789;
--work:#5b8cff;--need:#f2a93b;--rev:#ad7dff;--block:#ff5c70;--park:#8e97aa;--done:#2fc98a;--cl:#ec8a4f;--cx:#2bbfae;--gm:#6f93ff;color-scheme:dark}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.45 var(--sans)}
button,input{font:inherit;color:inherit}button{cursor:pointer}
.w{max-width:1100px;margin:0 auto;padding:18px 16px 40px}
header{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:14px}
.logo{width:34px;height:34px;border-radius:9px;background:conic-gradient(from 200deg,var(--cl),var(--cx),var(--gm),var(--cl));display:grid;place-items:center;color:#fff;font:700 16px var(--mono)}
h1{margin:0;font-size:19px}.sub{font:12.5px var(--mono);color:var(--mu)}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--done);margin-right:6px;vertical-align:1px}
.dot.off{background:var(--block)}
.grow{flex:1}
.strip{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin-bottom:12px}
.st{display:flex;gap:10px;align-items:center;background:var(--s);border:1px solid var(--line);border-left:4px solid var(--c);border-radius:12px;padding:10px 12px;text-align:left}
.st b{font-size:22px;line-height:1}.st span{font-size:12px;color:var(--mu)}
.st[aria-pressed=true]{box-shadow:0 0 0 1px var(--c) inset;border-color:var(--c)}
.bar{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}
.q{flex:1 1 220px;background:var(--s);border:1px solid var(--line);border-radius:9px;padding:9px 11px;outline:none}
.chip{border:1px solid var(--line);background:var(--s);border-radius:999px;padding:6px 12px;font-size:13px;font-weight:500;color:var(--mu)}
.chip i{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--c,var(--fa));margin-right:6px}
.chip[aria-pressed=true]{color:var(--fg);border-color:var(--c,var(--fg))}
h3{display:flex;gap:8px;align-items:center;font-size:13.5px;margin:16px 2px 8px}h3 i{width:10px;height:10px;border-radius:3px;background:var(--c)}h3 small{font:12px var(--mono);color:var(--mu)}
.row{display:flex;gap:10px;align-items:center;background:var(--s);border:1px solid var(--line);border-left:3px solid var(--c);border-radius:11px;padding:10px 12px;margin-bottom:7px}
.ag{width:30px;height:30px;border-radius:8px;display:grid;place-items:center;color:#fff;background:var(--t);font:700 12px var(--mono);flex:none}
.mid{flex:1;min-width:0}.t{font-weight:600;font-size:14px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.m{font:11.5px var(--mono);color:var(--mu);margin-top:3px;display:flex;gap:10px;flex-wrap:wrap}
.btn{border:1px solid var(--line);background:var(--s);border-radius:8px;padding:6px 10px;font-size:13px;white-space:nowrap}
.btn:hover{border-color:var(--fa)}
.empty{text-align:center;color:var(--mu);padding:40px;border:1px dashed var(--line);border-radius:14px;background:var(--s)}
.toast{position:fixed;left:50%;bottom:20px;transform:translateX(-50%);background:var(--fg);color:var(--bg);padding:8px 14px;border-radius:9px;font-size:13px;opacity:0;transition:.2s;pointer-events:none}
.toast.on{opacity:1}
@media (max-width:640px){.strip{grid-template-columns:repeat(2,1fr)}.row{flex-wrap:wrap}.row .btn{margin-left:40px}}
</style></head><body><div class="w">
<header><div class="logo">&gt;_</div><div class="grow"><h1>Agent sessions</h1><div class="sub" id="sub">loading…</div></div>
<button class="btn" id="rf">Refresh</button></header>
<div class="strip" id="strip"></div>
<div class="bar"><input class="q" id="q" placeholder="Search title, project, branch, id…"><div id="chips" style="display:flex;gap:6px;flex-wrap:wrap"></div></div>
<main id="main"></main></div><div class="toast" id="toast"></div>
<script>
const ST={working:["Working","var(--work)"],needs:["Needs input","var(--need)"],review:["Ready for review","var(--rev)"],blocked:["Blocked","var(--block)"],parked:["Parked","var(--park)"],done:["Done","var(--done)"]};
const AG={claude:["Claude Code","var(--cl)","CC",id=>"claude --resume "+id],codex:["Codex","var(--cx)","CX",id=>"codex resume "+id],gemini:["Gemini CLI","var(--gm)","GM",id=>"gemini --resume "+id]};
let data={sessions:[]},ok=false,f={st:null,ag:"all",q:""};
const $=i=>document.getElementById(i),esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const ago=t=>{const s=(Date.now()-t)/1e3;return s<60?"just now":s<3600?Math.floor(s/60)+"m ago":s<86400?Math.floor(s/3600)+"h ago":Math.floor(s/86400)+"d ago"};
async function load(){try{const r=await fetch("/api/sessions?days="+(new URLSearchParams(location.search).get("days")||14));data=await r.json();ok=true}catch(e){ok=false}draw()}
function draw(){
 $("sub").innerHTML=ok?`<span class="dot"></span>${esc(data.host||"this PC")} · ${data.total} sessions · scanned ${ago(data.scannedAt)}`:`<span class="dot off"></span>can't reach the local server`;
 const c={};Object.keys(ST).forEach(k=>c[k]=0);data.sessions.forEach(s=>c[s.status]=(c[s.status]||0)+1);
 $("strip").innerHTML=["working","needs","parked","done"].map(k=>`<button class="st" style="--c:${ST[k][1]}" data-st="${k}" aria-pressed="${f.st===k}"><b>${c[k]||0}</b><span>${ST[k][0]}</span></button>`).join("");
 $("chips").innerHTML=[["all","All",""]].concat(Object.entries(AG).map(([k,v])=>[k,v[0],v[1]])).map(([k,l,col])=>`<button class="chip" ${col?`style="--c:${col}"`:""} data-ag="${k}" aria-pressed="${f.ag===k}"><i></i>${l}</button>`).join("");
 const q=f.q.toLowerCase();
 const list=data.sessions.filter(s=>(f.ag==="all"||s.agent===f.ag)&&(!f.st||s.status===f.st)&&(!q||[s.title,s.project,s.branch,s.id,s.cwd].join(" ").toLowerCase().includes(q)));
 if(!list.length){$("main").innerHTML=`<div class="empty">${data.sessions.length?"Nothing matches.":"No sessions found in the last "+(data.days||14)+" days."}</div>`;return}
 $("main").innerHTML=Object.keys(ST).map(k=>{const it=list.filter(s=>(ST[s.status]?s.status:"parked")===k);if(!it.length)return"";
  return `<h3 style="--c:${ST[k][1]}"><i></i>${ST[k][0]}<small>${it.length}</small></h3>`+it.map(s=>{const a=AG[s.agent]||AG.claude;const cmd=(s.cwd?"cd "+JSON.stringify(s.cwd)+" && ":"")+a[3](s.id);
  return `<div class="row" style="--c:${ST[k][1]}"><span class="ag" style="--t:${a[1]}" title="${a[0]}">${a[2]}</span><div class="mid"><div class="t" title="${esc(s.title)}">${esc(s.title)}</div>
  <div class="m"><span>${esc(s.project||a[0])}</span>${s.branch?`<span>⎇ ${esc(s.branch)}</span>`:""}<span>${ago(s.lastActive)}</span><span>${esc(String(s.id).slice(0,8))}</span></div></div>
  <button class="btn" data-cp="${esc(cmd)}">Copy resume</button></div>`}).join("")}).join("");
}
document.addEventListener("click",e=>{const b=e.target.closest("button");if(!b)return;
 if(b.id==="rf")return load();
 if(b.dataset.st){f.st=f.st===b.dataset.st?null:b.dataset.st;return draw()}
 if(b.dataset.ag){f.ag=b.dataset.ag;return draw()}
 if(b.dataset.cp){navigator.clipboard.writeText(b.dataset.cp).then(()=>{const t=$("toast");t.textContent="Copied";t.classList.add("on");setTimeout(()=>t.classList.remove("on"),1300)})}});
$("q").addEventListener("input",e=>{f.q=e.target.value;draw()});
load();setInterval(()=>{if(document.visibilityState==="visible")load()},5000);
</script></body></html>"""


def serve(host, port):
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from urllib.parse import urlparse, parse_qs

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, body, ctype):
            b = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(b)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(b)

        def do_GET(self):
            u = urlparse(self.path)
            if u.path in ("/", "/index.html"):
                return self._send(200, PAGE, "text/html; charset=utf-8")
            if u.path == "/api/sessions":
                qs = parse_qs(u.query)
                args = {"days": qs.get("days", ["14"])[0], "limit": qs.get("limit", ["300"])[0]}
                return self._send(200, json.dumps(list_sessions(args)), "application/json")
            self._send(404, "not found", "text/plain")

    srv = ThreadingHTTPServer((host, port), H)
    print(f"agent-sessions dashboard on http://{host}:{port}  (Ctrl+C to stop)", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


# ---------- MCP over stdio ----------

TOOLS = [{
    "name": "list_sessions",
    "title": "List agent sessions",
    "description": "List recent Claude Code, Codex and Gemini CLI sessions on this machine (metadata only).",
    "inputSchema": {"type": "object", "properties": {
        "days": {"type": "integer", "minimum": 1, "maximum": 90, "description": "Look back this many days (default 14)."},
        "limit": {"type": "integer", "minimum": 1, "maximum": 500, "description": "Max sessions (default 150)."}}},
    "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
}]


def send(msg):
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def handle(req):
    method, rid = req.get("method"), req.get("id")
    if rid is None:
        return  # notification
    if method == "initialize":
        pv = (req.get("params") or {}).get("protocolVersion") or "2025-06-18"
        return send({"jsonrpc": "2.0", "id": rid, "result": {
            "protocolVersion": pv, "capabilities": {"tools": {}},
            "serverInfo": {"name": "agent-sessions", "version": VERSION}}})
    if method == "ping":
        return send({"jsonrpc": "2.0", "id": rid, "result": {}})
    if method == "tools/list":
        return send({"jsonrpc": "2.0", "id": rid, "result": {"tools": TOOLS}})
    if method == "tools/call":
        p = req.get("params") or {}
        if p.get("name") != "list_sessions":
            return send({"jsonrpc": "2.0", "id": rid, "error": {"code": -32602, "message": "unknown tool"}})
        try:
            data = list_sessions(p.get("arguments") or {})
            return send({"jsonrpc": "2.0", "id": rid, "result": {
                "content": [{"type": "text", "text": json.dumps(data)}], "structuredContent": data}})
        except Exception as e:
            return send({"jsonrpc": "2.0", "id": rid, "result": {
                "content": [{"type": "text", "text": f"list_sessions failed: {e}"}], "isError": True}})
    send({"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": f"method not found: {method}"}})


def main():
    argv = sys.argv[1:]
    if "--print" in argv:
        print(json.dumps(list_sessions({"days": 30}), indent=2))
        return
    if "--serve" in argv:
        port = int(argv[argv.index("--port") + 1]) if "--port" in argv else 8787
        host = argv[argv.index("--host") + 1] if "--host" in argv else "127.0.0.1"
        serve(host, port)
        return
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception:
            continue
        try:
            handle(req)
        except Exception as e:
            if isinstance(req, dict) and req.get("id") is not None:
                send({"jsonrpc": "2.0", "id": req["id"], "error": {"code": -32603, "message": str(e)}})


if __name__ == "__main__":
    main()
