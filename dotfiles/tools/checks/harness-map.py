#!/usr/bin/env python3
"""Generate dotfiles/docs/harness-map.html from the harness's own sources.

The map used to be drawn by hand and stamped with a commit. It went stale
within weeks (six personas when there were seven, Sonnet 5 after the 5.5
upgrade, nineteen skills after one was dropped) while still reading as
authoritative. Every fact on the page now comes from a file that owns it:

    personas      dotfiles/claude/agents/*.md frontmatter
    pipeline      dotfiles/claude/commands/*.md frontmatter + persona mentions
    boot          dotfiles/claude/AGENTS.md rules, settings.json pins
    enforcement   settings.json hooks + agent-scoped hooks, hook headers
    references    dotfiles/claude/references/**.md first heading
    skills        dotfiles/claude/skills/*/SKILL.md + Codex openai.yaml policy
    self-tests    .github/workflows/ci.yml steps and their comments
    records       dotfiles/docs/adr/*.md

The output is deterministic: no timestamps, no commit ids, sorted inputs.
`--check` exits 1 when the committed page differs from a fresh render, which
is how CI keeps it current (dotfiles/docs/adr/0069).

    python3 dotfiles/tools/checks/harness-map.py           # rewrite dotfiles/docs/harness-map.html
    python3 dotfiles/tools/checks/harness-map.py --check   # fail if it is stale
"""
import argparse
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CLAUDE = ROOT / 'dotfiles/claude'
CODEX = ROOT / 'dotfiles/codex'
OUT = ROOT / 'dotfiles/docs/harness-map.html'

# The gate order is design, not data: no file states it as a list. Everything
# else on a stage card is read from the command file.
PIPELINE = ['spec', 'plan', 'build', 'review', 'test', 'ship']
HUMAN_GATE_AFTER = {'spec': 'approve spec', 'plan': 'approve plan', 'ship': 'push / merge'}
CONDITIONAL = {'test': 'only when /review requires it'}



def e(text):
    """Escape for HTML, then render `code` spans the way the sources mean them."""
    return re.sub(r'`([^`]+)`', r'<code>\1</code>', html.escape(str(text)))

CSS = r"""
/* Layout: a reference manual. A fixed index on the left, one column of
   sections on the right, each opening with a one-line summary, then a table. */
:root{
  --bg:#F6F7F9; --surface:#FFFFFF; --sunk:#EDF0F3; --ink:#111827; --ink-2:#4A5361; --ink-3:#717A87;
  --line:#DCE1E7; --line-2:#C3CAD3;
  --gate:#A9620B; --gate-bg:#FBF0DD; --write:#1F5FAE; --write-bg:#E3EDFA; --read:#5A6472;
  --ok:#2F7A4F;
  --sans:"Hanken Grotesk","Helvetica Neue",Arial,sans-serif;
  --mono:"JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,monospace;
  color-scheme:light;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --bg:#0E1116; --surface:#151A21; --sunk:#1C222B; --ink:#E8EBEF; --ink-2:#AAB2BD; --ink-3:#848D99;
    --line:#262D37; --line-2:#36404C;
    --gate:#E8A24A; --gate-bg:#33240F; --write:#7AAEF0; --write-bg:#172A42; --read:#9BA5B2; --ok:#6FBF8C;
    color-scheme:dark;
  }
}
:root[data-theme="dark"]{
  --bg:#0E1116; --surface:#151A21; --sunk:#1C222B; --ink:#E8EBEF; --ink-2:#AAB2BD; --ink-3:#848D99;
  --line:#262D37; --line-2:#36404C;
  --gate:#E8A24A; --gate-bg:#33240F; --write:#7AAEF0; --write-bg:#172A42; --read:#9BA5B2; --ok:#6FBF8C;
  color-scheme:dark;
}
*{box-sizing:border-box}
[hidden]{display:none!important}
html{scroll-behavior:smooth}
@media (prefers-reduced-motion: reduce){html{scroll-behavior:auto}}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:17px;line-height:1.6;padding-inline:clamp(16px,3vw,40px);padding-block:32px 80px}
a{color:inherit}
h1,h2,h3{margin:0;text-wrap:balance;letter-spacing:-0.01em}
h1{font-size:clamp(34px,4.6vw,50px);line-height:1.1;font-weight:800}
h2{font-size:27px;line-height:1.25;font-weight:700}
h3{font-size:18px;font-weight:700}
p{margin:0;max-width:70ch}
code,.mono{font-family:var(--mono);font-size:0.88em}
code{background:var(--sunk);padding:1px 5px;border-radius:4px;overflow-wrap:anywhere}
:focus-visible{outline:2px solid var(--write);outline-offset:2px;border-radius:2px}
.layout{max-width:1320px;margin:0 auto;display:grid;grid-template-columns:220px minmax(0,1fr);gap:48px}

/* index */
nav.index{position:sticky;top:calc(env(safe-area-inset-top,0px) + 24px);align-self:start;display:flex;flex-direction:column;gap:2px;font-size:16px}
nav.index .label{font-size:12.5px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:var(--ink-3);margin-bottom:8px}
nav.index a{text-decoration:none;color:var(--ink-2);padding:5px 10px;border-left:2px solid var(--line);display:flex;justify-content:space-between;gap:8px}
nav.index a span{font-family:var(--mono);font-size:13px;color:var(--ink-3);font-variant-numeric:tabular-nums}
nav.index a:hover,nav.index a:focus-visible{color:var(--ink);border-left-color:var(--write);outline:none}
main{display:flex;flex-direction:column;gap:56px;min-width:0}

/* header */
header.top{display:flex;flex-direction:column;gap:10px;padding-bottom:24px;border-bottom:1px solid var(--line)}
header.top .kicker{font-family:var(--mono);font-size:13.5px;color:var(--ink-3)}
header.top p{color:var(--ink-2);font-size:18.5px}
.counts{display:flex;flex-wrap:wrap;gap:8px;margin-top:6px}
.count{background:var(--surface);border:1px solid var(--line);border-radius:6px;padding:7px 14px;font-size:15px;color:var(--ink-2)}
.count b{color:var(--ink);font-variant-numeric:tabular-nums;margin-right:4px}
.legend{display:flex;flex-wrap:wrap;gap:6px 20px;font-size:15px;color:var(--ink-2)}
.legend span{display:inline-flex;align-items:center;gap:6px}

/* sections */
section{display:flex;flex-direction:column;gap:16px;scroll-margin-top:24px;min-width:0}
.sec-head{display:flex;flex-direction:column;gap:4px}
.sec-head .summary{color:var(--ink-2)}
.panel{background:var(--surface);border:1px solid var(--line);border-radius:8px;min-width:0}
.panel.pad{padding:18px 20px}
.option{display:flex;flex-direction:column;gap:10px}
.option-label{display:flex;align-items:baseline;gap:10px;font-size:15px;color:var(--ink-3)}
.option-label b{font-size:12px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:var(--ink)}

/* badges */
.badge{display:inline-block;font-size:13.5px;font-weight:600;padding:1px 8px;border-radius:999px;white-space:nowrap;border:1px solid transparent}
.badge.write{color:var(--write);background:var(--write-bg)}
.badge.read{color:var(--read);border-color:var(--line-2)}
.badge.gate{color:var(--gate);background:var(--gate-bg)}
.badge.cond{color:var(--ink-3);border:1px dashed var(--line-2)}
.persona-name{font-family:var(--mono);font-size:15px;white-space:nowrap}
.persona-name.write{color:var(--write)}
.who{display:flex;flex-wrap:wrap;gap:4px 12px}

/* pipeline tabs */
.tabs{display:flex;flex-wrap:wrap;gap:4px;border-bottom:1px solid var(--line-2)}
.tabs button{font:inherit;font-size:16px;font-weight:600;color:var(--ink-2);background:none;border:0;border-bottom:3px solid transparent;padding:10px 16px;margin-bottom:-1px;cursor:pointer;border-radius:6px 6px 0 0}
.tabs button:hover{color:var(--ink);background:var(--sunk)}
.tabs button[aria-selected="true"]{color:var(--ink);border-bottom-color:var(--write)}
.tabs button span{font-family:var(--mono);font-size:13px;color:var(--ink-3);margin-right:6px}
.mermaid-wrap{overflow-x:auto;min-width:0}
.mermaid-wrap svg{max-width:none!important;height:auto}

/* option 1: stage list */
ol.stages{list-style:none;margin:0;padding:0}
ol.stages > li{display:grid;grid-template-columns:110px minmax(0,1fr) minmax(0,300px);gap:6px 20px;padding:14px 20px;border-top:1px solid var(--line);align-items:baseline}
ol.stages > li:first-child{border-top:0}
ol.stages .cmd{font-family:var(--mono);font-size:18px;font-weight:700}
ol.stages .does{color:var(--ink-2);font-size:16px}
ol.stages > li.cond{background:repeating-linear-gradient(135deg,transparent 0 10px,var(--sunk) 10px 11px)}
ol.stages > li.gate{display:flex;gap:10px;align-items:center;padding:8px 20px;background:var(--gate-bg);color:var(--gate);font-weight:600;font-size:16px}
.diamond{width:10px;height:10px;transform:rotate(45deg);background:var(--gate);display:inline-block;flex:none}

/* option 2: strip */
.strip{display:flex;flex-wrap:wrap;align-items:center;gap:8px;padding:18px 20px}
.strip .box{font-family:var(--mono);font-weight:700;font-size:16px;padding:8px 14px;border:1.5px solid var(--ink);border-radius:6px;background:var(--surface)}
.strip .box.cond{border-style:dashed;color:var(--ink-2)}
.strip .sep{color:var(--ink-3)}
.strip .diamond{margin-inline:2px}

/* option 3: mermaid */
pre.mermaid{margin:0;padding:18px 20px;font-family:var(--mono);font-size:13.5px;color:var(--ink-2);white-space:pre;overflow-x:auto;background:none}

/* tables */
.tablewrap{overflow-x:auto;min-width:0}
table{border-collapse:collapse;width:100%;font-size:16px}
th,td{text-align:left;vertical-align:top;padding:12px 16px;border-bottom:1px solid var(--line)}
tr:last-child td{border-bottom:0}
th{font-size:13px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:var(--ink-3);background:var(--sunk);border-bottom:1px solid var(--line)}
th:first-child{border-top-left-radius:8px}
th:last-child{border-top-right-radius:8px}
td.num{font-variant-numeric:tabular-nums;text-align:right;white-space:nowrap}
td .sub{display:block;font-size:15px;color:var(--ink-2);margin-top:2px;max-width:60ch}
td.cmdcell{font-family:var(--mono);font-size:14.5px;color:var(--ink-2)}
td.nowrap{white-space:nowrap}
td.group{font-weight:700;background:var(--bg);font-size:15.5px;color:var(--ink)}
td.group span{font-weight:400;color:var(--ink-3);font-family:var(--mono);font-size:13.5px;margin-left:8px}
.tested{color:var(--ok);font-family:var(--mono);font-size:14px}

/* boot */
.two{display:grid;grid-template-columns:minmax(0,1.25fr) minmax(0,1fr);gap:20px}
ol.rules{margin:0;padding:6px 20px 6px 44px;display:flex;flex-direction:column}
ol.rules li{padding:9px 0;border-top:1px solid var(--line)}
ol.rules li:first-child{border-top:0}
ol.rules li::marker{font-weight:700;color:var(--ink-3);font-variant-numeric:tabular-nums}
ol.rules .sub{display:block;font-size:15px;color:var(--ink-2)}
dl.kv{margin:0;display:grid;grid-template-columns:auto minmax(0,1fr);font-size:15.5px}
dl.kv dt,dl.kv dd{padding:8px 16px;border-top:1px solid var(--line);margin:0;min-width:0}
dl.kv dt:first-of-type,dl.kv dd:first-of-type{border-top:0}
dl.kv dt{font-family:var(--mono);font-size:14px;color:var(--ink-2)}
.panel-title{font-size:13px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:var(--ink-3);padding:10px 16px;background:var(--sunk);border-bottom:1px solid var(--line);border-radius:8px 8px 0 0}
.stack{display:flex;flex-direction:column;gap:20px;min-width:0}
.note{font-size:15.5px;color:var(--ink-2)}
footer{font-size:14px;color:var(--ink-3);border-top:1px solid var(--line);padding-top:14px}

@media (max-width:900px){
  .layout{grid-template-columns:minmax(0,1fr);gap:24px}
  nav.index{position:static;flex-direction:row;flex-wrap:wrap;gap:6px}
  nav.index .label{width:100%;margin-bottom:0}
  nav.index a{border-left:0;border:1px solid var(--line);border-radius:999px;padding:4px 12px}
  .two{grid-template-columns:minmax(0,1fr)}
  ol.stages > li{grid-template-columns:minmax(0,1fr);gap:2px}
}
"""


def read(path):
    return path.read_text(encoding='utf-8')


def rel(path):
    return path.relative_to(ROOT).as_posix()


def frontmatter(text):
    """Top-level `key: value` pairs, folded scalars joined, plus the raw block."""
    if not text.startswith('---'):
        return {}, ''
    block = text.split('---', 2)[1]
    lines = block.splitlines()
    data = {}
    for i, line in enumerate(lines):
        m = re.match(r'^([A-Za-z_][\w-]*):\s*(.*)$', line)
        if not m:
            continue
        key, value = m.group(1), m.group(2).strip()
        if value in {'>', '>-', '|', '|-', ''}:
            cont = []
            for nxt in lines[i + 1:]:
                if nxt.startswith((' ', '\t')):
                    cont.append(nxt.strip())
                else:
                    break
            value = ' '.join(cont)
        elif value.startswith('"'):
            value = json.loads(value)
        elif value.startswith("'"):
            value = value[1:-1].replace("''", "'")
        data[key] = ' '.join(value.split())
    return data, block


def agent_hooks(block):
    """[(event, script)] declared in an agent's frontmatter `hooks:` key."""
    found, event, inside = [], None, False
    for line in block.splitlines():
        if re.match(r'^hooks:\s*$', line):
            inside = True
            continue
        if inside and re.match(r'^\S', line):
            inside = False
        if not inside:
            continue
        m = re.match(r'^  ([A-Za-z]+):\s*$', line)
        if m:
            event = m.group(1)
        m = re.search(r'hooks/([\w.-]+\.sh)', line)
        if m and event:
            found.append((event, m.group(1)))
    return found


def personas():
    rows = []
    for path in sorted((CLAUDE / 'agents').glob('*.md')):
        data, block = frontmatter(read(path))
        tools = [t.strip() for t in data.get('tools', '').split(',') if t.strip()]
        skills = re.findall(r'^\s+-\s+([\w-]+)\s*$', block.split('skills:', 1)[1].split('\n\S', 1)[0],
                            re.M) if re.search(r'^skills:', block, re.M) else []
        rows.append({
            'name': data.get('name', path.stem),
            'description': data.get('description', ''),
            'tools': tools,
            'writer': bool({'Edit', 'Write', 'Bash'} & set(tools)),
            'model': data.get('model', '—'),
            'effort': data.get('effort', ''),
            'maxTurns': data.get('maxTurns', '—'),
            'isolation': data.get('isolation', ''),
            'hooks': agent_hooks(block),
            'skills': skills,
        })
    return rows


def commands(persona_names):
    out = {}
    for path in sorted((CLAUDE / 'commands').glob('*.md')):
        text = read(path)
        data, _ = frontmatter(text)
        named = sorted({n for n in persona_names if f'`{n}`' in text})
        out[path.stem] = {'description': data.get('description', ''), 'model': data.get('model', ''),
                          'personas': named, 'path': rel(path)}
    return out


def agents_rules():
    rules = []
    text = read(CLAUDE / 'AGENTS.md')
    for m in re.finditer(r'^## (\d+)\. (.+)$', text, re.M):
        body = text[m.end():].split('\n## ', 1)[0]
        lead = re.search(r'^\*\*(.+?)\*\*\s*$', body, re.M)
        catches = re.search(r'\*Catches: (.+?)\*', body)
        rules.append((m.group(2), lead.group(1) if lead else '', catches.group(1) if catches else ''))
    sections = re.findall(r'^## ([^\d].+)$', text, re.M)
    return rules, [s for s in sections if s != 'Rules']


def hook_summary(script):
    """The first sentence of a hook's header comment that is not its 'X hook (...)' label."""
    lines = []
    for line in read(CLAUDE / 'hooks' / script).splitlines()[1:]:
        if not line.startswith('#'):
            break
        line = line[1:].strip()
        if not line:
            if lines:
                break
            continue
        lines.append(line)
    sentences = re.split(r'(?<=[.!?])\s+', ' '.join(lines))
    if sentences and re.search(r'\bhook \(|^\w+ hook\b', sentences[0]):
        sentences = sentences[1:]
    summary = sentences[0] if sentences else ''
    return summary if len(summary) <= 200 else summary[:197].rstrip() + '…'


def hook_tests(script):
    return sorted(rel(p) for p in (ROOT / 'dotfiles/tools/tests').glob('test-*') if p.is_file() and script in read(p))


def hooks(settings, persona_rows):
    rows = []
    for event, groups in sorted(settings.get('hooks', {}).items()):
        for group in groups:
            for hook in group.get('hooks', []):
                m = re.search(r'hooks/([\w.-]+\.sh)', hook.get('command', ''))
                if m:
                    rows.append((m.group(1), event, group.get('matcher', '—'), 'every session'))
    scoped = {}
    for p in persona_rows:
        for event, script in p['hooks']:
            scoped.setdefault((script, event), []).append(p['name'])
    for (script, event), names in sorted(scoped.items()):
        rows.append((script, 'SubagentStop' if event == 'Stop' else event, 'Bash' if event == 'PreToolUse' else '—',
                     ', '.join(names) + ' (frontmatter)'))
    return [(s, ev, mt, scope, hook_summary(s), hook_tests(s)) for s, ev, mt, scope in rows]


def references():
    rows = []
    for path in sorted((CLAUDE / 'references').rglob('*.md')):
        title = re.search(r'^# (.+)$', read(path), re.M)
        rows.append((path.relative_to(CLAUDE / 'references').as_posix(), title.group(1) if title else ''))
    return rows


def skills():
    rows = []
    for path in sorted((CLAUDE / 'skills').glob('*/SKILL.md')):
        name = path.parent.name
        data, _ = frontmatter(read(path))
        policy = CODEX / 'skills' / name / 'agents/openai.yaml'
        explicit = policy.is_file() and re.search(r'allow_implicit_invocation:\s*false', read(policy))
        rows.append((name, data.get('description', ''), bool(explicit)))
    return rows


def ci_steps():
    """[(name, commands, comment)] from the workflow, without a YAML dependency."""
    steps, comment, current, in_run = [], [], None, False
    for line in read(ROOT / '.github/workflows/ci.yml').splitlines():
        stripped = line.strip()
        m = re.match(r'^\s+- name:\s*(.+)$', line)
        if m:
            current = {'name': m.group(1), 'run': [], 'dir': '', 'comment': ' '.join(comment)}
            steps.append(current)
            comment, in_run = [], False
            continue
        if re.match(r'^\s+- uses:', line):
            current, comment, in_run = None, [], False
            continue
        if stripped.startswith('#'):
            if line.startswith('      #'):
                comment.append(stripped.lstrip('#').strip())
            continue
        if current is None:
            continue
        m = re.match(r'^\s+working-directory:\s*(.+)$', line)
        if m:
            current['dir'] = m.group(1)
            continue
        m = re.match(r'^\s+run:\s*(.*)$', line)
        if m:
            in_run = m.group(1) in {'|', '>'}
            if not in_run:
                current['run'].append(m.group(1))
            continue
        if in_run and line.startswith('          '):
            current['run'].append(stripped)
    return [(s['name'], [f"cd {s['dir']} && {r}" if s['dir'] else r for r in s['run']], s['comment'])
            for s in steps]


def adrs():
    rows = []
    for path in sorted((ROOT / 'dotfiles/docs/adr').glob('[0-9][0-9][0-9][0-9]-*.md')):
        title = re.search(r'^# (.+)$', read(path), re.M)
        rows.append((path.name[:4], title.group(1) if title else path.stem, rel(path)))
    return rows


def first_sentence(text, limit=180):
    """The first sentence of a description, for rows that cannot hold a paragraph."""
    sentence = re.split(r'(?<=[.!?])\s', text.strip(), maxsplit=1)[0]
    return sentence if len(sentence) <= limit else sentence[:limit - 1].rstrip() + '…'


def persona_label(name, writers):
    return f'<span class="persona-name{" write" if name in writers else ""}">{e(name)}</span>'


# The pipeline is shown three ways, as tabs; the flowchart opens first.
PIPELINE_VIEWS = ('list', 'strip', 'mermaid')
DEFAULT_VIEW = 'mermaid'


def pipeline_list(cmds, writers):
    rows = []
    for name in PIPELINE:
        if name not in cmds:
            continue
        c = cmds[name]
        cond = name in CONDITIONAL
        badge = f' <span class="badge cond">{e(CONDITIONAL[name])}</span>' if cond else ''
        who = ''.join(persona_label(p, writers) for p in c['personas']) or '<span class="note">the session itself</span>'
        cls = ' class="cond"' if cond else ''
        rows.append(f'<li{cls}><span class="cmd">/{e(name)}</span>'
                    f'<span class="does">{e(c["description"])}{badge}</span><span class="who">{who}</span></li>')
        if name in HUMAN_GATE_AFTER:
            rows.append(f'<li class="gate"><i class="diamond"></i>You decide: {e(HUMAN_GATE_AFTER[name])}</li>')
    return '<div class="panel"><ol class="stages">' + ''.join(rows) + '</ol></div>'


def pipeline_strip(cmds, writers):
    parts = []
    for name in PIPELINE:
        if name not in cmds:
            continue
        if parts:
            parts.append('<span class="sep">→</span>')
        parts.append(f'<span class="box{" cond" if name in CONDITIONAL else ""}">/{e(name)}</span>')
        if name in HUMAN_GATE_AFTER:
            parts.append(f'<i class="diamond" title="{e(HUMAN_GATE_AFTER[name])}"></i>')
    rows = ''.join(f'<tr><td class="cmdcell">/{e(n)}</td><td><div class="who">'
                   + (''.join(persona_label(p, writers) for p in cmds[n]['personas']) or '<span class="note">—</span>')
                   + '</div></td></tr>' for n in PIPELINE if n in cmds)
    return (f'<div class="panel"><div class="strip">{"".join(parts)}</div>'
            '<div class="tablewrap"><table><thead><tr><th>Stage</th><th>Personas</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div></div>')


def mermaid_text(text):
    """Safe inside a Mermaid quoted label."""
    return text.replace('"', '#quot;').replace('`', "'")


def pipeline_mermaid(cmds, writers):
    """The stage list as a diagram: one box per stage, top to bottom, holding
    the command, what it does and who does it. Approvals are diamonds between
    boxes; /test is a dashed detour. Drawn by the Mermaid script when the page
    is online; the source shows otherwise. (Mermaid drops a subgraph's own
    direction when its nodes link outside it, so personas live in the label.)"""
    lines = ['flowchart TB']
    order = [n for n in PIPELINE if n in cmds]
    for name in order:
        c = cmds[name]
        who = ', '.join(f'{p} (writes)' if p in writers else p for p in c['personas']) or 'the session itself'
        label = f'<b>/{name}</b><br/>{mermaid_text(c["description"])}<br/><i>Who: {mermaid_text(who)}</i>'
        if name in CONDITIONAL:
            label += f'<br/><i>{mermaid_text(CONDITIONAL[name])}</i>'
        lines.append(f'  {name}["{label}"]:::{"cond" if name in CONDITIONAL else "stage"}')
    main = [n for n in order if n not in CONDITIONAL]
    prev = None
    for name in main:
        if prev:
            lines.append(f'  {prev} --> {name}')
        prev = name
        if name in HUMAN_GATE_AFTER:
            gate = f'g_{name}'
            lines.append(f'  {gate}{{"You decide:<br/>{mermaid_text(HUMAN_GATE_AFTER[name])}"}}:::gate')
            lines.append(f'  {name} --> {gate}')
            prev = gate
    for name in CONDITIONAL:
        if name in cmds and 'review' in cmds and 'ship' in cmds:
            lines.append(f'  review -. "if required" .-> {name} -.-> ship')
    lines += ['  classDef stage fill:#FFFFFF,stroke:#111827,stroke-width:1.5px,color:#111827',
              '  classDef cond fill:#F3F5F8,stroke:#717A87,stroke-dasharray:6 4,color:#111827',
              '  classDef gate fill:#FBF0DD,stroke:#A9620B,color:#7A4708']
    return ('<div class="panel mermaid-wrap"><pre class="mermaid">' + e('\n'.join(lines)) + '</pre></div>')


LIFECYCLE = [('SessionStart', None, 'Session starts'),
             ('PreToolUse', 'Agent|Task', 'A persona is dispatched'),
             ('PreToolUse', 'Bash', 'Any shell command'),
             ('SubagentStop', None, 'A writer tries to finish')]


def render():
    settings = json.loads(read(CLAUDE / 'settings.json'))
    persona_rows = personas()
    writers = {p['name'] for p in persona_rows if p['writer']}
    cmds = commands([p['name'] for p in persona_rows])
    rules, other_sections = agents_rules()
    hook_rows = hooks(settings, persona_rows)
    ref_rows = references()
    skill_rows = skills()
    steps = ci_steps()
    adr_rows = adrs()
    templates = [r for r in ref_rows if r[0].startswith('templates/')]
    refs = [r for r in ref_rows if not r[0].startswith('templates/')]
    dispatched_by = {p['name']: [f'/{n}' for n in PIPELINE if p['name'] in cmds.get(n, {}).get('personas', [])]
                     for p in persona_rows}

    sections = [('pipeline', 'Pipeline', len([n for n in PIPELINE if n in cmds])),
                ('personas', 'Personas', len(persona_rows)), ('guards', 'Guards', len(hook_rows)),
                ('session', 'Session setup', len(rules)), ('skills', 'Skills', len(skill_rows)),
                ('references', 'References', len(ref_rows)), ('ci', 'Self-tests', len(steps)),
                ('decisions', 'Decisions', len(adr_rows))]

    out = ['<!doctype html>', '<html lang="en">', '<head>', '<meta charset="utf-8">',
           '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">',
           '<title>Harness Map</title>',
           '<!-- Generated by dotfiles/tools/checks/harness-map.py. Do not edit by hand; CI fails when this page is stale. -->',
           '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@400;600;700;800&family=JetBrains+Mono:wght@400;700&display=swap">',
           '<style>' + CSS + '</style>', '</head>', '<body>', '<div class="layout">',
           '<nav class="index" aria-label="Sections"><div class="label">Harness map</div>'
           + ''.join(f'<a href="#{i}">{e(t)}<span>{n}</span></a>' for i, t, n in sections) + '</nav>',
           '<main>']

    out.append('<header class="top"><div class="kicker">stanimirdim92/setup_scripts · dotfiles</div>'
               '<h1>Harness Map</h1>'
               '<p>How a ticket moves through the Claude Code harness, who does the work at each step, and which '
               'rules the host enforces. Generated from the harness files; CI fails when it is out of date.</p>'
               '<div class="counts">'
               + ''.join(f'<span class="count"><b>{n}</b>{e(t.lower())}</span>' for _, t, n in sections)
               + '</div></header>')

    # Pipeline
    out.append('<section id="pipeline"><div class="sec-head"><h2>Pipeline</h2>'
               '<p class="summary">Commands run in this order. Personas never start other personas. '
               'The amber rows are decisions only you make.</p></div>'
               '<div class="legend"><span><i class="diamond"></i>you decide</span>'
               '<span><span class="persona-name write">blue</span> can change files</span>'
               '<span><span class="persona-name">grey</span> read-only</span>'
               '<span><span class="badge cond">dashed</span> only when needed</span></div>')
    views = {'list': ('1', 'Stage list', pipeline_list),
             'strip': ('2', 'Strip', pipeline_strip),
             'mermaid': ('3', 'Flowchart', pipeline_mermaid)}
    out.append('<div class="tabs" role="tablist" aria-label="Pipeline views">')
    for key in PIPELINE_VIEWS:
        num, label, _ = views[key]
        on = key == DEFAULT_VIEW
        out.append(f'<button type="button" role="tab" id="tab-{key}" aria-controls="view-{key}" '
                   f'aria-selected="{"true" if on else "false"}" tabindex="{0 if on else -1}" data-view="{key}">'
                   f'<span>{num}</span>{e(label)}</button>')
    out.append('</div>')
    for key in PIPELINE_VIEWS:
        hidden = '' if key == DEFAULT_VIEW else ' hidden'
        note = ('<p class="note">Needs the Mermaid script from a CDN; offline, its source shows instead.</p>'
                if key == 'mermaid' else '')
        out.append(f'<div role="tabpanel" id="view-{key}" aria-labelledby="tab-{key}" class="option"{hidden}>'
                   + views[key][2](cmds, writers) + note + '</div>')
    for name in sorted(n for n in cmds if n not in PIPELINE):
        out.append(f'<p class="note">Outside the pipeline: <code>/{e(name)}</code> — {e(cmds[name]["description"])}.</p>')
    out.append('</section>')

    # Personas
    ordered = sorted(persona_rows, key=lambda p: (not p['writer'], p['name']))
    out.append(f'<section id="personas"><div class="sec-head"><h2>Personas</h2>'
               f'<p class="summary">{len(persona_rows)} personas; {len(writers)} can change files. Read-only is a '
               'tool grant, not an instruction.</p></div><div class="panel tablewrap"><table><thead><tr>'
               '<th>Persona</th><th>Access</th><th>Model</th><th>Effort</th><th>Max turns</th>'
               '<th>Started by</th><th>Hooks</th></tr></thead><tbody>')
    for p in ordered:
        access = '<span class="badge write">writes</span>' if p['writer'] else '<span class="badge read">read-only</span>'
        if p['isolation']:
            access += f' <span class="badge read">{e(p["isolation"])}</span>'
        hooks_cell = '<br>'.join(e(s[:-3]) for _, s in p['hooks']) or '—'
        out.append(f'<tr><td>{persona_label(p["name"], writers)}<span class="sub">{e(first_sentence(p["description"], 140))}</span></td>'
                   f'<td>{access}</td><td class="cmdcell nowrap">{e(p["model"])}</td><td>{e(p["effort"] or "—")}</td>'
                   f'<td class="num">{e(p["maxTurns"])}</td><td class="cmdcell">{e(", ".join(dispatched_by[p["name"]]) or "direct use")}</td>'
                   f'<td class="cmdcell">{hooks_cell}</td></tr>')
    out.append('</tbody></table></div></section>')

    # Guards
    out.append('<section id="guards"><div class="sec-head"><h2>Guards</h2>'
               '<p class="summary">Rules the host enforces, in the order they fire. A guard here cannot be argued '
               'past; each one has a self-test.</p></div><div class="panel tablewrap"><table><thead><tr>'
               '<th>Hook</th><th>Applies to</th><th>What it does</th><th>Tested by</th></tr></thead><tbody>')
    placed = set()
    for event, matcher, title in LIFECYCLE:
        rows = [r for r in hook_rows if r[1] == event and (matcher is None or r[2] == matcher)]
        if not rows:
            continue
        label = event + (f' · {matcher}' if matcher else '')
        out.append(f'<tr><td class="group" colspan="4">{e(title)}<span>{e(label)}</span></td></tr>')
        for script, ev, mt, scope, summary, tests in rows:
            placed.add((script, ev, mt))
            out.append(f'<tr><td class="cmdcell">{e(script)}</td><td>{e(scope)}</td><td>{e(summary)}</td>'
                       f'<td class="tested">{"<br>".join(e(t.rsplit("/", 1)[1]) for t in tests) or "—"}</td></tr>')
    rest = [r for r in hook_rows if (r[0], r[1], r[2]) not in placed]
    if rest:
        out.append('<tr><td class="group" colspan="4">Other</td></tr>')
        for script, ev, mt, scope, summary, tests in rest:
            out.append(f'<tr><td class="cmdcell">{e(script)}</td><td>{e(ev)} · {e(scope)}</td><td>{e(summary)}</td>'
                       f'<td class="tested">{"<br>".join(e(t.rsplit("/", 1)[1]) for t in tests) or "—"}</td></tr>')
    out.append('</tbody></table></div></section>')

    # Session setup
    env = settings.get('env', {})
    pins = [(k, v) for k, v in sorted(env.items()) if k.startswith('CLAUDE_CODE_')]
    sandbox = settings.get('sandbox', {})
    denied = [f['path'] for f in sandbox.get('credentials', {}).get('files', []) if f.get('mode') == 'deny']
    perms = settings.get('permissions', {})
    defaults = [
        ('model', settings.get('model', '—')),
        ('effortLevel', settings.get('effortLevel', '—')),
        ('advisorModel', settings.get('advisorModel', '—')),
        ('modelSettings', ', '.join(f'{k} → {v.get("effortLevel", v)}' if isinstance(v, dict) else f'{k} → {v}'
                                    for k, v in sorted(settings.get('modelSettings', {}).items())) or '—'),
        ('permissions', f'{perms.get("defaultMode", "default")} · {len(perms.get("allow", []))} allow · '
                        f'{len(perms.get("deny", []))} deny'),
        ('sandbox', f'{"on" if sandbox.get("enabled") else "off"} · {len(sandbox.get("excludedCommands", []))} '
                    f'excluded commands · {len(denied)} credential paths denied'),
        ('worktree.baseRef', settings.get('worktree', {}).get('baseRef', '—')),
    ]
    out.append('<section id="session"><div class="sec-head"><h2>Session setup</h2>'
               '<p class="summary">What every session loads: the rules in <code>AGENTS.md</code> and the pins in '
               '<code>settings.json</code>.</p></div><div class="two">'
               f'<div class="panel"><div class="panel-title">AGENTS.md rules</div><ol class="rules">')
    for title, lead, catches in rules:
        out.append(f'<li><b>{e(title)}</b>' + (f'<span class="sub">{e(lead)}</span>' if lead else '')
                   + (f'<span class="sub">Catches: {e(catches)}</span>' if catches else '') + '</li>')
    out.append('</ol></div><div class="stack"><div class="panel"><div class="panel-title">settings.json · env pins</div>'
               '<dl class="kv">')
    for k, v in pins:
        out.append(f'<dt>{e(k.replace("CLAUDE_CODE_", ""))}</dt><dd><code>{e(str(v))}</code></dd>')
    out.append('</dl></div><div class="panel"><div class="panel-title">settings.json · defaults</div><dl class="kv">')
    for k, v in defaults:
        out.append(f'<dt>{e(k)}</dt><dd>{e(str(v))}</dd>')
    out.append(f'</dl></div><p class="note">AGENTS.md also covers: {", ".join(e(s) for s in other_sections)}.</p>'
               '</div></div></section>')

    # Skills
    explicit = sum(1 for s in skill_rows if s[2])
    out.append(f'<section id="skills"><div class="sec-head"><h2>Skills</h2>'
               f'<p class="summary">{len(skill_rows)} skills. {explicit} are explicit-only: a stage or role loads '
               'them, never a keyword match.</p></div><div class="panel tablewrap"><table><thead><tr>'
               '<th>Skill</th><th>Loading</th><th>What it is for</th></tr></thead><tbody>')
    for name, desc, is_explicit in sorted(skill_rows, key=lambda s: (not s[2], s[0])):
        badge = '<span class="badge gate">explicit</span>' if is_explicit else '<span class="badge read">on match</span>'
        out.append(f'<tr><td class="cmdcell">{e(name)}</td><td>{badge}</td><td>{e(first_sentence(desc, 160))}</td></tr>')
    out.append('</tbody></table></div></section>')

    # References
    out.append(f'<section id="references"><div class="sec-head"><h2>References</h2>'
               f'<p class="summary">{len(refs)} references and {len(templates)} templates. Each rule is written once, '
               'here, and the commands point at it.</p></div><div class="panel tablewrap"><table><thead><tr>'
               '<th>File</th><th>Title</th></tr></thead><tbody>')
    for path, title in refs + templates:
        out.append(f'<tr><td class="cmdcell">{e(path)}</td><td>{e(title)}</td></tr>')
    out.append('</tbody></table></div></section>')

    # Self-tests
    out.append(f'<section id="ci"><div class="sec-head"><h2>Self-tests</h2>'
               f'<p class="summary">{len(steps)} CI steps on every push to main and every pull request. Runs that '
               'spend model tokens stay manual.</p></div><div class="panel tablewrap"><table><thead><tr>'
               '<th>Step</th><th>Command</th></tr></thead><tbody>')
    for name, runs, comment in steps:
        why = f'<span class="sub">{e(comment)}</span>' if comment else ''
        out.append(f'<tr><td><b>{e(name)}</b>{why}</td><td class="cmdcell">{"<br>".join(e(r) for r in runs)}</td></tr>')
    out.append('</tbody></table></div></section>')

    # Decisions
    out.append(f'<section id="decisions"><div class="sec-head"><h2>Decisions</h2>'
               f'<p class="summary">{len(adr_rows)} architecture decisions; the ten most recent below. Full index: '
               '<code>dotfiles/docs/adr/README.md</code>.</p></div><div class="panel tablewrap"><table><thead><tr>'
               '<th>ADR</th><th>Decision</th></tr></thead><tbody>')
    for num, title, path in adr_rows[-10:][::-1]:
        out.append(f'<tr><td class="cmdcell">{e(num)}</td><td>{e(title)}</td></tr>')
    out.append('</tbody></table></div></section>')

    out.append('<footer>Generated by dotfiles/tools/checks/harness-map.py from the repository sources. '
               'Do not edit by hand.</footer></main></div>')
    if 'mermaid' in PIPELINE_VIEWS:
        out.append('<script src="https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js"></script>')
    out.append('''<script>
(function () {
  var tabs = Array.prototype.slice.call(document.querySelectorAll('[role="tab"]'));
  var drawn = false;
  function draw() {
    if (drawn || !window.mermaid) { return; }
    drawn = true;
    var dark = document.documentElement.dataset.theme === 'dark' ||
      (!document.documentElement.dataset.theme && matchMedia('(prefers-color-scheme: dark)').matches);
    mermaid.initialize({ startOnLoad: false, theme: dark ? 'dark' : 'neutral', securityLevel: 'strict',
      themeVariables: { fontSize: '17px', fontFamily: 'Hanken Grotesk, Helvetica Neue, Arial, sans-serif' },
      flowchart: { htmlLabels: true, useMaxWidth: false, wrappingWidth: 420, nodeSpacing: 40, rankSpacing: 36 } });
    mermaid.run({ querySelector: 'pre.mermaid' });
  }
  function show(key, focus) {
    tabs.forEach(function (tab) {
      var on = tab.dataset.view === key;
      tab.setAttribute('aria-selected', on ? 'true' : 'false');
      tab.tabIndex = on ? 0 : -1;
      document.getElementById('view-' + tab.dataset.view).hidden = !on;
      if (on && focus) { tab.focus(); }
    });
    if (key === 'mermaid') { draw(); }
    try { localStorage.setItem('harness-map-view', key); } catch (err) {}
  }
  tabs.forEach(function (tab, i) {
    tab.addEventListener('click', function () { show(tab.dataset.view); });
    tab.addEventListener('keydown', function (ev) {
      var step = ev.key === 'ArrowRight' ? 1 : ev.key === 'ArrowLeft' ? -1 : 0;
      if (step) { ev.preventDefault(); show(tabs[(i + step + tabs.length) % tabs.length].dataset.view, true); }
    });
  });
  var saved = null;
  try { saved = localStorage.getItem('harness-map-view'); } catch (err) {}
  show(saved && document.getElementById('view-' + saved) ? saved : '__DEFAULT_VIEW__');
})();
</script>'''.replace('__DEFAULT_VIEW__', DEFAULT_VIEW))
    out.append('</body>\n</html>\n')
    return '\n'.join(out)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--check', action='store_true', help='exit 1 if dotfiles/docs/harness-map.html is stale')
    args = parser.parse_args(argv)
    page = render()
    if args.check:
        current = OUT.read_text(encoding='utf-8') if OUT.is_file() else ''
        if current != page:
            print(f'{rel(OUT)} is stale: run python3 dotfiles/tools/checks/harness-map.py and commit the result', file=sys.stderr)
            return 1
        print(f'{rel(OUT)} is current')
        return 0
    OUT.write_text(page, encoding='utf-8')
    print(f'wrote {rel(OUT)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
