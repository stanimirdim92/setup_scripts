#!/usr/bin/env python3
"""agent-sessions: a read-only local MCP server (stdio, no dependencies).

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
    if len(sys.argv) > 1 and sys.argv[1] == "--print":
        print(json.dumps(list_sessions({"days": 30}), indent=2))
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
