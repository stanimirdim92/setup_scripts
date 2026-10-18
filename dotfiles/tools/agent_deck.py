#!/usr/bin/env python3
"""agent-deck: run and watch many Claude Code / Codex / Gemini CLI sessions
from one browser tab, with live output and typing straight into each one.

Every session is a tmux session, so it keeps running when you close the tab,
and you can still `tmux attach -t <name>` from any terminal.

  sudo apt install tmux
  python3 agent_deck.py            # http://127.0.0.1:8788/?t=<token>  (printed)
  python3 agent_deck.py --port 9000

Binds to 127.0.0.1 only. Every API call needs the token printed at start,
and requests from other hosts/origins are refused.
"""
import json
import os
import re
import secrets
import shlex
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

PREFIX = "ad-"
AGENTS = {
    "claude": {"cmd": "claude", "resume": "claude --resume {id}", "prompt": "claude {p}"},
    "codex": {"cmd": "codex", "resume": "codex resume {id}", "prompt": "codex {p}"},
    "gemini": {"cmd": "gemini", "resume": "gemini --resume {id}", "prompt": "gemini -i {p}"},
    "shell": {"cmd": os.environ.get("SHELL", "bash"), "resume": None, "prompt": None},
}
TOKEN = os.environ.get("AGENT_DECK_TOKEN") or secrets.token_urlsafe(18)
NAME_RE = re.compile(r"^[A-Za-z0-9_.-]{1,60}$")

# history from the sibling script, if present
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import agent_sessions_mcp as history  # noqa: E402
except Exception:  # pragma: no cover
    history = None


def tmux(*args, check=True):
    r = subprocess.run(["tmux", *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout).strip() or "tmux failed")
    return r.stdout


def slug(s):
    s = re.sub(r"[^A-Za-z0-9_-]+", "-", s or "").strip("-").lower()
    return s[:40] or "session"


def list_live():
    fmt = "#{session_name}\t#{session_created}\t#{session_activity}\t#{pane_current_path}\t#{pane_current_command}\t#{pane_dead}\t#{@ad_agent}\t#{@ad_title}"
    out = tmux("list-sessions", "-F", fmt, check=False)
    now = time.time()
    rows = []
    for line in out.splitlines():
        p = line.split("\t")
        if len(p) < 8 or not p[0].startswith(PREFIX):
            continue
        act = int(p[2] or 0)
        idle = now - act
        dead = p[5] == "1"
        rows.append({
            "name": p[0], "created": int(p[1] or 0) * 1000, "activity": act * 1000,
            "cwd": p[3], "command": p[4], "agent": p[6] or "shell", "title": p[7] or p[0][len(PREFIX):],
            "state": "exited" if dead else ("working" if idle < 4 else "waiting"),
        })
    rows.sort(key=lambda r: r["created"])
    return rows


def start(body):
    agent = body.get("agent", "claude")
    if agent not in AGENTS:
        raise ValueError("unknown agent")
    cwd = os.path.expanduser(body.get("cwd") or "~")
    if not os.path.isdir(cwd):
        raise ValueError(f"folder not found: {cwd}")
    title = (body.get("title") or "").strip() or Path(cwd).name
    name = PREFIX + slug(f"{agent}-{title}")
    existing = {r["name"] for r in list_live()}
    base, n = name, 2
    while name in existing:
        name, n = f"{base}-{n}", n + 1
    a = AGENTS[agent]
    if body.get("resumeId") and a["resume"]:
        cmd = a["resume"].format(id=shlex.quote(str(body["resumeId"])))
    elif body.get("prompt") and a["prompt"]:
        cmd = a["prompt"].format(p=shlex.quote(body["prompt"]))
    else:
        cmd = a["cmd"]
    cols, rows = int(body.get("cols") or 160), int(body.get("rows") or 45)
    # login shell so PATH (nvm, ~/.local/bin) matches your terminal; stay open after the agent exits
    shell = os.environ.get("SHELL", "/bin/bash")
    wrapped = f"{cmd}; echo; echo '[agent exited — press Enter to close]'; read _"
    tmux("new-session", "-d", "-s", name, "-c", cwd, "-x", str(cols), "-y", str(rows), shell, "-lic", wrapped)
    tmux("set-option", "-t", name, "@ad_agent", agent)
    tmux("set-option", "-t", name, "@ad_title", title[:80])
    tmux("set-option", "-t", name, "status", "off")
    tmux("set-option", "-t", name, "history-limit", "20000")
    tmux("set-window-option", "-t", name, "window-size", "manual", check=False)
    return {"name": name}


def need_name(name):
    if not NAME_RE.match(name or "") or not name.startswith(PREFIX):
        raise ValueError("bad session name")
    return name


def screen(name, scroll=0):
    need_name(name)
    start_line = f"-{int(scroll)}" if scroll else "0"
    text = tmux("capture-pane", "-p", "-e", "-t", name, "-S", start_line)
    info = tmux("display-message", "-p", "-t", name, "#{cursor_x},#{cursor_y},#{pane_width},#{pane_height}")
    cx, cy, w, h = (int(x) for x in info.strip().split(","))
    return {"text": text, "cursor": [cx, cy], "size": [w, h]}


def send_bytes(name, data):
    need_name(name)
    raw = data.encode("utf-8")
    if not raw:
        return
    for i in range(0, len(raw), 512):
        chunk = raw[i:i + 512]
        tmux("send-keys", "-t", name, "-H", *[f"{b:02x}" for b in chunk])


def resize(name, cols, rows):
    need_name(name)
    cols, rows = max(20, min(400, int(cols))), max(5, min(200, int(rows)))
    tmux("resize-window", "-t", name, "-x", str(cols), "-y", str(rows), check=False)


def kill(name):
    need_name(name)
    tmux("kill-session", "-t", name)


def recent_history():
    if not history:
        return []
    try:
        return history.list_sessions({"days": 14, "limit": 60})["sessions"]
    except Exception:
        return []


class H(BaseHTTPRequestHandler):
    server_version = "agent-deck"

    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        b = body if isinstance(body, bytes) else (body if isinstance(body, str) else json.dumps(body)).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(b)

    def _host_ok(self):
        port = self.server.server_address[1]
        host = (self.headers.get("Host") or "").lower()
        if host not in (f"127.0.0.1:{port}", f"localhost:{port}"):
            return False
        origin = self.headers.get("Origin")
        return origin in (None, f"http://127.0.0.1:{port}", f"http://localhost:{port}")

    def _auth(self):
        return self._host_ok() and secrets.compare_digest(self.headers.get("X-Token", ""), TOKEN)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > 1_000_000:
            raise ValueError("too large")
        return json.loads(self.rfile.read(n) or b"{}") if n else {}

    def do_GET(self):
        if not self._host_ok():
            return self._send(403, {"error": "forbidden"})
        u = urlparse(self.path)
        if u.path in ("/", "/index.html"):
            return self._send(200, PAGE, "text/html; charset=utf-8")
        if not self._auth():
            return self._send(401, {"error": "token"})
        try:
            if u.path == "/api/live":
                return self._send(200, {"sessions": list_live(), "home": str(Path.home())})
            if u.path == "/api/history":
                return self._send(200, {"sessions": recent_history()})
            m = re.match(r"^/api/live/([^/]+)/screen$", u.path)
            if m:
                q = parse_qs(u.query)
                return self._send(200, screen(m.group(1), int(q.get("scroll", ["0"])[0] or 0)))
        except Exception as e:
            return self._send(400, {"error": str(e)})
        self._send(404, {"error": "not found"})

    def do_POST(self):
        if not self._auth():
            return self._send(401, {"error": "token"})
        u = urlparse(self.path)
        try:
            body = self._body()
            if u.path == "/api/live":
                return self._send(200, start(body))
            m = re.match(r"^/api/live/([^/]+)/(keys|resize|kill)$", u.path)
            if m:
                name, act = m.group(1), m.group(2)
                if act == "keys":
                    send_bytes(name, body.get("data", ""))
                elif act == "resize":
                    resize(name, body.get("cols", 120), body.get("rows", 40))
                else:
                    kill(name)
                return self._send(200, {"ok": True})
        except Exception as e:
            return self._send(400, {"error": str(e)})
        self._send(404, {"error": "not found"})


PAGE = r"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Agent Deck</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@xterm/xterm@5.5.0/css/xterm.css">
<script src="https://cdn.jsdelivr.net/npm/@xterm/xterm@5.5.0/lib/xterm.js"></script>
<script src="https://cdn.jsdelivr.net/npm/@xterm/addon-fit@0.10.0/lib/addon-fit.js"></script>
<style>
:root{--bg:#0d1016;--s:#161a23;--s2:#1e2330;--line:#2a3040;--fg:#e9ecf3;--mu:#a2a9b8;--fa:#6f7789;
--work:#5b8cff;--need:#f2a93b;--block:#ff5c70;--done:#2fc98a;--cl:#ec8a4f;--cx:#2bbfae;--gm:#6f93ff;--sh:#8e97aa;
--mono:"JetBrains Mono","IBM Plex Mono",ui-monospace,Menlo,Consolas,monospace;--sans:system-ui,-apple-system,"Segoe UI",Ubuntu,sans-serif;color-scheme:dark}
*{box-sizing:border-box}html,body{height:100%;margin:0}
body{background:var(--bg);color:var(--fg);font:14px/1.4 var(--sans);display:grid;grid-template-columns:270px 1fr;overflow:hidden}
button,input,select,textarea{font:inherit;color:inherit}button{cursor:pointer}
aside{border-right:1px solid var(--line);display:flex;flex-direction:column;min-height:0;background:var(--s)}
.brand{display:flex;align-items:center;gap:10px;padding:14px;border-bottom:1px solid var(--line)}
.logo{width:30px;height:30px;border-radius:8px;background:conic-gradient(from 200deg,var(--cl),var(--cx),var(--gm),var(--cl));display:grid;place-items:center;font:700 13px var(--mono);color:#fff}
.brand b{font-size:15px}.brand small{display:block;color:var(--mu);font:11.5px var(--mono)}
.new{margin:12px;padding:9px;border-radius:9px;border:0;background:var(--fg);color:var(--bg);font-weight:600}
.sec{padding:6px 14px;font-size:11.5px;font-weight:600;color:var(--fa);text-transform:uppercase;letter-spacing:.06em;margin-top:6px}
.list{overflow-y:auto;flex:1;padding:0 8px 12px}
.it{display:flex;gap:9px;align-items:center;width:100%;text-align:left;background:none;border:1px solid transparent;border-radius:9px;padding:8px;margin-bottom:3px}
.it:hover{background:var(--s2)}
.it[aria-current=true]{background:var(--s2);border-color:var(--line)}
.ag{width:26px;height:26px;border-radius:7px;display:grid;place-items:center;font:700 10.5px var(--mono);color:#fff;background:var(--t);flex:none}
.it .tx{flex:1;min-width:0}.it .t{font-weight:600;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.it .m{font:11px var(--mono);color:var(--mu);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.dot{width:9px;height:9px;border-radius:50%;flex:none;background:var(--fa)}
.dot.working{background:var(--work);box-shadow:0 0 0 3px color-mix(in srgb,var(--work) 30%,transparent);animation:p 1.4s infinite}
.dot.waiting{background:var(--need)}.dot.exited{background:var(--block)}
@keyframes p{50%{box-shadow:0 0 0 6px transparent}}
.hist .it{opacity:.8}
main{display:flex;flex-direction:column;min-width:0;min-height:0}
.top{display:flex;align-items:center;gap:8px;padding:10px 12px;border-bottom:1px solid var(--line)}
.top .grow{flex:1}
.seg{display:inline-flex;border:1px solid var(--line);border-radius:8px;overflow:hidden}
.seg button{border:0;background:none;padding:6px 10px;color:var(--mu);font-size:13px}
.seg button[aria-pressed=true]{background:var(--s2);color:var(--fg)}
.btn{border:1px solid var(--line);background:var(--s);border-radius:8px;padding:6px 10px;font-size:13px}
.btn:hover{border-color:var(--fa)}.btn.red{color:var(--block)}
.grid{flex:1;display:grid;gap:8px;padding:8px;min-height:0}
.tile{display:flex;flex-direction:column;min-width:0;min-height:0;border:1px solid var(--line);border-radius:10px;overflow:hidden;background:#0a0c11}
.tile.focus{border-color:var(--t)}
.th{display:flex;align-items:center;gap:8px;padding:6px 8px;background:var(--s);border-bottom:1px solid var(--line);font-size:12.5px}
.th .ag{width:20px;height:20px;font-size:9px;border-radius:5px}
.th .t{font-weight:600;flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.th .k{font:11px var(--mono);color:var(--fa)}
.th button{border:0;background:none;color:var(--mu);padding:2px 6px;border-radius:5px}.th button:hover{background:var(--s2);color:var(--fg)}
.term{flex:1;min-height:0;padding:4px 6px}
.empty{flex:1;display:grid;place-items:center;color:var(--mu);text-align:center;padding:30px}
.empty b{display:block;color:var(--fg);font-size:17px;margin-bottom:6px}
dialog{background:var(--s);color:var(--fg);border:1px solid var(--line);border-radius:14px;padding:0;width:min(460px,92vw)}
dialog::backdrop{background:rgba(0,0,0,.55)}
dialog form{display:flex;flex-direction:column;gap:12px;padding:18px}
dialog h3{margin:0 0 2px}
label{font-size:12px;font-weight:600;color:var(--mu);display:block;margin-bottom:5px}
input,textarea{width:100%;background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:8px 10px;outline:none}
input:focus,textarea:focus{border-color:var(--work)}
.opts{display:flex;gap:6px;flex-wrap:wrap}
.opt{display:flex;align-items:center;gap:7px;border:1px solid var(--line);background:var(--bg);border-radius:8px;padding:6px 10px;font-size:13px;color:var(--mu)}
.opt[aria-pressed=true]{color:var(--fg);border-color:var(--t)}
.opt .ag{width:18px;height:18px;font-size:8.5px;border-radius:5px}
.row{display:flex;gap:8px;justify-content:flex-end}
.err{color:var(--block);font-size:13px;min-height:1em}
.toast{position:fixed;left:50%;bottom:18px;transform:translateX(-50%);background:var(--fg);color:var(--bg);padding:8px 14px;border-radius:8px;opacity:0;transition:.2s;pointer-events:none;font-size:13px}
.toast.on{opacity:1}
@media (max-width:800px){body{grid-template-columns:1fr}aside{display:none}}
</style></head><body>
<aside>
  <div class="brand"><div class="logo">&gt;_</div><div><b>Agent Deck</b><small id="host">local</small></div></div>
  <button class="new" id="newBtn">+ New session</button>
  <div class="sec">Running</div>
  <div class="list" id="live"></div>
  <div class="sec">Recent (resume)</div>
  <div class="list hist" id="hist" style="max-height:38%"></div>
</aside>
<main>
  <div class="top">
    <div class="seg" id="layout"></div>
    <div class="grow"></div>
    <span class="k" style="font:12px var(--mono);color:var(--fa)" id="hint">click a tile, then type</span>
  </div>
  <div class="grid" id="grid"></div>
</main>
<dialog id="dlg"><form method="dialog" id="form">
  <h3>New session</h3>
  <div><label>Agent</label><div class="opts" id="agentOpts"></div></div>
  <div><label for="fCwd">Folder</label><input id="fCwd" placeholder="~/setup_scripts" autocomplete="off"></div>
  <div><label for="fTitle">Name</label><input id="fTitle" placeholder="LD-442 re-score" autocomplete="off"></div>
  <div><label for="fPrompt">First prompt (optional)</label><textarea id="fPrompt" rows="3"></textarea></div>
  <div class="err" id="err"></div>
  <div class="row"><button class="btn" value="cancel" formnovalidate>Cancel</button><button class="btn" id="go" style="background:var(--fg);color:var(--bg);border-color:var(--fg)" value="ok">Start</button></div>
</form></dialog>
<div class="toast" id="toast"></div>
<script>
const TOKEN = new URLSearchParams(location.search).get("t") || sessionStorage.getItem("adt") || "";
if(TOKEN) sessionStorage.setItem("adt", TOKEN);
const AG = {claude:["Claude Code","var(--cl)","CC"],codex:["Codex","var(--cx)","CX"],gemini:["Gemini CLI","var(--gm)","GM"],shell:["Shell","var(--sh)","$"]};
const $ = id => document.getElementById(id);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const ago = t => { const s=(Date.now()-t)/1e3; return s<60?"now":s<3600?Math.floor(s/60)+"m":s<86400?Math.floor(s/3600)+"h":Math.floor(s/86400)+"d"; };
let live = [], hist = [], home = "", layout = Number(localStorage.getItem("ad-layout")||2), shown = JSON.parse(localStorage.getItem("ad-shown")||"[]"), focusName = null, newAgent = "claude", hidden = new Set(JSON.parse(localStorage.getItem("ad-hidden")||"[]"));
const tiles = new Map();

async function api(path, body){
  const r = await fetch(path, body===undefined ? {headers:{"X-Token":TOKEN}} : {method:"POST", headers:{"X-Token":TOKEN,"Content-Type":"application/json"}, body:JSON.stringify(body)});
  const d = await r.json().catch(()=>({}));
  if(!r.ok) throw new Error(d.error || r.status);
  return d;
}
function toast(m){ const t=$("toast"); t.textContent=m; t.classList.add("on"); clearTimeout(toast.t); toast.t=setTimeout(()=>t.classList.remove("on"),1600); }

/* sidebar */
function drawSide(){
  $("live").innerHTML = live.length ? live.map(s => { const a = AG[s.agent]||AG.shell; return `
    <button class="it" data-open="${esc(s.name)}" aria-current="${shown.includes(s.name)}">
      <span class="ag" style="--t:${a[1]}">${a[2]}</span>
      <span class="tx"><div class="t">${esc(s.title)}</div><div class="m">${esc(s.cwd.replace(home,"~"))}</div></span>
      <span class="dot ${s.state}" title="${s.state}"></span></button>`; }).join("") : `<div style="color:var(--fa);font-size:12.5px;padding:8px">Nothing running.</div>`;
  $("hist").innerHTML = hist.slice(0,40).map((s,i) => { const a = AG[s.agent]||AG.claude; return `
    <button class="it" data-resume="${i}" title="Resume in a new tile">
      <span class="ag" style="--t:${a[1]}">${a[2]}</span>
      <span class="tx"><div class="t">${esc(s.title)}</div><div class="m">${esc(s.project||"")} · ${ago(s.lastActive)}</div></span></button>`; }).join("");
}

/* layout */
function drawLayout(){
  $("layout").innerHTML = [[1,"1"],[2,"2"],[4,"4"],[6,"6"]].map(([n,l]) => `<button data-layout="${n}" aria-pressed="${layout===n}">${l}</button>`).join("");
  const g = $("grid");
  const cols = layout===1?1:layout===2?2:layout===4?2:3, rows = layout<=2?1:2;
  g.style.gridTemplateColumns = `repeat(${cols},minmax(0,1fr))`;
  g.style.gridTemplateRows = `repeat(${rows},minmax(0,1fr))`;
}

function syncTiles(){
  const names = new Set(live.map(s=>s.name));
  shown = shown.filter(n => names.has(n)).slice(0, layout);
  // fill empty slots with running sessions that aren't shown
  for(const s of live){ if(shown.length >= layout) break; if(!shown.includes(s.name) && !hidden.has(s.name)) shown.push(s.name); }
  localStorage.setItem("ad-shown", JSON.stringify(shown));
  const g = $("grid");
  for(const [n,t] of tiles){ if(!shown.includes(n)){ t.term.dispose(); t.el.remove(); tiles.delete(n); } }
  if(!shown.length){
    g.innerHTML = `<div class="empty" style="grid-column:1/-1"><div><b>No sessions running</b>Start one with “+ New session”, or resume a recent one from the sidebar.</div></div>`;
    return;
  }
  g.querySelector(".empty")?.remove();
  shown.forEach((n,i) => { if(!tiles.has(n)) makeTile(n); g.appendChild(tiles.get(n).el); });
  for(const [n,t] of tiles){
    const s = live.find(x=>x.name===n); if(!s) continue;
    t.el.querySelector(".k").textContent = s.state==="working" ? "working" : s.state==="exited" ? "exited" : "waiting · "+ago(s.activity);
    t.el.querySelector(".dot").className = "dot " + s.state;
  }
  requestAnimationFrame(()=>{ for(const t of tiles.values()) fit(t); });
  drawSide();
}

function makeTile(name){
  const s = live.find(x=>x.name===name) || {}; const a = AG[s.agent]||AG.shell;
  const el = document.createElement("div");
  el.className = "tile"; el.style.setProperty("--t", a[1]);
  el.innerHTML = `<div class="th"><span class="ag" style="--t:${a[1]}">${a[2]}</span><span class="dot"></span><span class="t">${esc(s.title||name)}</span><span class="k"></span>
    <button data-copy="tmux attach -t ${esc(name)}" title="Copy tmux attach command">attach</button>
    <button data-max="${esc(name)}" title="Show only this">⤢</button>
    <button data-hide="${esc(name)}" title="Hide tile (keeps running)">–</button>
    <button data-kill="${esc(name)}" title="Stop session" style="color:var(--block)">✕</button></div><div class="term"></div>`;
  const term = new Terminal({fontFamily:'"JetBrains Mono","IBM Plex Mono",ui-monospace,Menlo,monospace', fontSize:13, cursorBlink:true, convertEol:false, scrollback:0,
    theme:{background:"#0a0c11", foreground:"#e9ecf3", cursor:a[1].includes("cl")?"#ec8a4f":"#e9ecf3"}});
  const fitA = new FitAddon.FitAddon(); term.loadAddon(fitA);
  term.open(el.querySelector(".term"));
  const t = {name, el, term, fitA, last:"", size:"", busy:false, queue:"", sending:false};
  term.onData(d => { t.queue += d; flushKeys(t); });
  el.addEventListener("mousedown", () => setFocus(name));
  tiles.set(name, t);
  poll(t);
}
async function flushKeys(t){
  if(t.sending || !t.queue) return;
  t.sending = true; const data = t.queue; t.queue = "";
  try{ await api(`/api/live/${t.name}/keys`, {data}); }catch(e){ toast(e.message); }
  t.sending = false; setTimeout(()=>poll(t), 40);
  if(t.queue) flushKeys(t);
}
function fit(t){
  try{ t.fitA.fit(); }catch(e){ return; }
  const sz = t.term.cols+"x"+t.term.rows;
  if(sz !== t.size){ t.size = sz; api(`/api/live/${t.name}/resize`, {cols:t.term.cols, rows:t.term.rows}).then(()=>{ t.last=""; poll(t); }).catch(()=>{}); }
}
async function poll(t){
  if(t.busy || !tiles.has(t.name)) return;
  t.busy = true;
  try{
    const d = await api(`/api/live/${t.name}/screen`);
    const key = d.text + "|" + d.cursor;
    if(key !== t.last){
      t.last = key;
      const lines = d.text.replace(/\n$/,"").split("\n");
      t.term.write("\x1b[H\x1b[2J" + lines.map(l => l + "\x1b[0m").join("\r\n") + `\x1b[${d.cursor[1]+1};${d.cursor[0]+1}H`);
    }
  }catch(e){ /* session may have ended */ }
  t.busy = false;
}
function setFocus(name){
  focusName = name;
  for(const [n,t] of tiles) t.el.classList.toggle("focus", n===name);
  const t = tiles.get(name); if(t) t.term.focus();
}
setInterval(() => { for(const t of tiles.values()) if(t.name===focusName || document.visibilityState==="visible") poll(t); }, 350);
async function refresh(){
  try{ const d = await api("/api/live"); live = d.sessions; home = d.home; $("host").textContent = live.length + " running"; syncTiles(); }
  catch(e){ $("grid").innerHTML = `<div class="empty" style="grid-column:1/-1"><div><b>Can't reach agent-deck</b>${esc(e.message)==="token"?"Open the full link printed in the terminal (it ends with ?t=…).":esc(e.message)}</div></div>`; }
}
async function loadHist(){ try{ hist = (await api("/api/history")).sessions; drawSide(); }catch(e){} }

/* new session */
function drawAgentOpts(){
  $("agentOpts").innerHTML = Object.entries(AG).map(([k,a]) => `<button type="button" class="opt" style="--t:${a[1]}" data-agent="${k}" aria-pressed="${newAgent===k}"><span class="ag" style="--t:${a[1]}">${a[2]}</span>${a[0]}</button>`).join("");
}
$("newBtn").onclick = () => { newAgent = "claude"; drawAgentOpts(); $("err").textContent=""; $("fCwd").value = localStorage.getItem("ad-cwd") || ""; $("fTitle").value=""; $("fPrompt").value=""; $("dlg").showModal(); $("fCwd").focus(); };
$("form").addEventListener("submit", async ev => {
  if(ev.submitter && ev.submitter.value === "cancel") return;
  ev.preventDefault();
  const cwd = $("fCwd").value.trim() || "~";
  try{
    const r = await api("/api/live", {agent:newAgent, cwd, title:$("fTitle").value, prompt:$("fPrompt").value, cols:160, rows:45});
    localStorage.setItem("ad-cwd", cwd); $("dlg").close(); open(r.name);
  }catch(e){ $("err").textContent = e.message; }
});
async function open(name){
  hidden.delete(name); localStorage.setItem("ad-hidden", JSON.stringify([...hidden]));
  await refresh();
  shown = shown.filter(n=>n!==name); shown.unshift(name); shown = shown.slice(0, layout);
  syncTiles(); setTimeout(()=>setFocus(name), 150);
}

document.addEventListener("click", async ev => {
  const b = ev.target.closest("button"); if(!b) return;
  const d = b.dataset;
  if(d.agent){ newAgent = d.agent; drawAgentOpts(); return; }
  if(d.layout){ layout = Number(d.layout); localStorage.setItem("ad-layout", layout); drawLayout(); syncTiles(); return; }
  if(d.open){ open(d.open); return; }
  if(d.resume){
    const s = hist[Number(d.resume)]; if(!s) return;
    try{ const r = await api("/api/live", {agent:s.agent, cwd:s.cwd || "~", title:s.title.slice(0,40), resumeId:s.id}); open(r.name); }catch(e){ toast(e.message); }
    return;
  }
  if(d.max){ layout = 1; shown = [d.max]; localStorage.setItem("ad-layout", 1); drawLayout(); syncTiles(); setFocus(d.max); return; }
  if(d.hide){ hidden.add(d.hide); localStorage.setItem("ad-hidden", JSON.stringify([...hidden])); shown = shown.filter(n=>n!==d.hide); const t = tiles.get(d.hide); if(t){ t.term.dispose(); t.el.remove(); tiles.delete(d.hide);} localStorage.setItem("ad-shown", JSON.stringify(shown)); drawSide(); return; }
  if(d.kill){ if(!confirm("Stop this session? The agent process is killed.")) return; try{ await api(`/api/live/${d.kill}/kill`, {}); }catch(e){} refresh(); return; }
  if(d.copy){ navigator.clipboard.writeText(d.copy).then(()=>toast("Copied")); return; }
});
window.addEventListener("resize", () => { for(const t of tiles.values()) fit(t); });
drawLayout(); refresh(); loadHist();
setInterval(refresh, 2000); setInterval(loadHist, 30000);
</script></body></html>"""


def main():
    argv = sys.argv[1:]
    port = int(argv[argv.index("--port") + 1]) if "--port" in argv else 8788
    if subprocess.run(["which", "tmux"], capture_output=True).returncode != 0:
        sys.exit("agent-deck needs tmux:  sudo apt install tmux")
    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    print(f"Agent Deck: http://127.0.0.1:{port}/?t={TOKEN}", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
