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
/* Layout: an engineer's plate. One wide pipeline drawing opens the sheet;
   indexed plates follow, each a different view of the same harness. */
:root{
  --paper:#F2F3EF; --paper-2:#E6E8E2; --panel:#FAFAF7; --ink:#1A1F27; --ink-2:#4B525C; --ink-3:#6E757F;
  --rule:#8A9099; --rule-2:#CDD1CA;
  --gate:#B0680A; --gate-soft:#F5E3C4; --writer:#2F6390; --writer-soft:#D7E5F1; --ro:#5B6370;
  --ok:#3C7A4E;
  --display:"Bricolage Grotesque","Archivo",system-ui,sans-serif;
  --body:"IBM Plex Sans","Helvetica Neue",Arial,sans-serif;
  --mono:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,monospace;
  color-scheme:light;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --paper:#12161D; --paper-2:#1B212B; --panel:#171C24; --ink:#E7E9E4; --ink-2:#AEB4BC; --ink-3:#8A919A;
    --rule:#69717C; --rule-2:#2C3440;
    --gate:#E39A3D; --gate-soft:#3A2A12; --writer:#78AEDB; --writer-soft:#1B2E40; --ro:#9AA2AC; --ok:#79B98A;
    color-scheme:dark;
  }
}
:root[data-theme="dark"]{
  --paper:#12161D; --paper-2:#1B212B; --panel:#171C24; --ink:#E7E9E4; --ink-2:#AEB4BC; --ink-3:#8A919A;
  --rule:#69717C; --rule-2:#2C3440;
  --gate:#E39A3D; --gate-soft:#3A2A12; --writer:#78AEDB; --writer-soft:#1B2E40; --ro:#9AA2AC; --ok:#79B98A;
  color-scheme:dark;
}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--body);font-size:15px;line-height:1.55;padding-inline:clamp(16px,4vw,56px);padding-block:40px 80px}
a{color:inherit}
h1,h2,h3{font-family:var(--display);text-wrap:balance;margin:0;letter-spacing:-0.015em}
h1{font-size:clamp(40px,6.5vw,76px);line-height:0.98;font-weight:700}
h2{font-size:clamp(24px,3vw,34px);line-height:1.1;font-weight:700}
h3{font-size:17px;font-weight:600;line-height:1.25}
p{margin:0;max-width:68ch}
code,.mono{font-family:var(--mono);font-size:0.9em}
code{background:var(--paper-2);padding:1px 5px;border-radius:3px;overflow-wrap:anywhere}
:focus-visible{outline:2px solid var(--gate);outline-offset:2px}
.eyebrow{font-family:var(--mono);font-size:11px;letter-spacing:0.14em;text-transform:uppercase;color:var(--ink-3)}
.sheet{max-width:1280px;margin:0 auto;display:flex;flex-direction:column;gap:72px}
.muted{color:var(--ink-2)}

/* masthead */
.mast{display:grid;grid-template-columns:minmax(0,1.4fr) minmax(0,1fr);gap:40px;align-items:end;border-bottom:3px solid var(--ink);padding-bottom:28px}
.mast .lede{margin-top:16px;color:var(--ink-2);font-size:17px}
.figures{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1px;background:var(--rule-2);border:1px solid var(--rule-2)}
.figure{background:var(--paper);padding:12px 14px;display:flex;flex-direction:column;gap:2px}
.figure b{font-family:var(--display);font-size:30px;line-height:1;font-weight:700;font-variant-numeric:tabular-nums}
.figure span{font-family:var(--mono);font-size:11px;letter-spacing:0.06em;text-transform:uppercase;color:var(--ink-3)}
nav.toc{position:sticky;top:env(safe-area-inset-top,0px);z-index:5;background:var(--paper);margin-block:-48px;padding-block:12px;border-bottom:1px solid var(--rule-2);display:flex;flex-wrap:wrap;gap:6px 20px;font-family:var(--mono);font-size:12px}
nav.toc a{text-decoration:none;color:var(--ink-2);border-bottom:1px solid transparent;padding-bottom:1px}
nav.toc a:hover,nav.toc a:focus-visible{color:var(--ink);border-color:var(--gate);outline:none}

/* plates */
section{display:flex;flex-direction:column;gap:22px;scroll-margin-top:64px}
.plate-head{display:grid;grid-template-columns:120px minmax(0,1fr);gap:8px 24px;border-top:1px solid var(--ink);padding-top:16px}
.plate-head .eyebrow{padding-top:8px}
.plate-head p{color:var(--ink-2);grid-column:2}
.legend{display:flex;flex-wrap:wrap;gap:8px 22px;font-size:12px;color:var(--ink-2);font-family:var(--mono)}
.legend span{display:inline-flex;align-items:center;gap:8px}
.sw{width:14px;height:14px;display:inline-block;border:1.5px solid var(--ink)}
.sw.gate{border-color:var(--gate);background:var(--gate-soft);transform:rotate(45deg) scale(.8)}
.sw.writer{border-color:var(--writer);background:var(--writer-soft)}
.sw.ro{border-style:dashed;border-color:var(--ro)}
.scroll{overflow-x:auto;min-width:0}
figure{margin:0}
.drawing{border:1px solid var(--rule-2);background:var(--panel);padding:8px}
.drawing svg{display:block;width:100%;min-width:980px;height:auto}
.tag{display:inline-block;font-family:var(--mono);font-size:11.5px;padding:1px 8px;border:1px solid var(--rule);border-radius:2px;white-space:nowrap}
.tag.writer{border-color:var(--writer);color:var(--writer);background:var(--writer-soft)}
.tag.ro{border-style:dashed;color:var(--ro)}
.tag.gate{border-color:var(--gate);color:var(--gate);background:var(--gate-soft)}
.chips{display:flex;flex-wrap:wrap;gap:5px}
.chip{font-family:var(--mono);font-size:11.5px;padding:2px 7px;background:var(--paper-2);border-radius:2px}
.aside{font-size:14px;color:var(--ink-2)}

/* boot */
.boot{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(0,1fr);gap:28px}
.rules{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px 28px}
.rules li{display:grid;grid-template-columns:30px minmax(0,1fr);gap:6px}
.rules li > i{font-style:normal;font-family:var(--display);font-size:24px;line-height:1;color:var(--gate);font-weight:700}
.rules b{display:block;font-weight:600}
.rules span{display:block;color:var(--ink-2);font-size:13.5px}
.rules em{display:block;font-style:normal;font-size:12.5px;color:var(--ink-3);margin-top:3px}
dl.kv{margin:0;display:grid;grid-template-columns:auto minmax(0,1fr);gap:8px 16px;font-size:13.5px}
dl.kv dt{font-family:var(--mono);font-size:12px;color:var(--ink-2);padding-top:2px}
dl.kv dd{margin:0;min-width:0}
.stack{display:flex;flex-direction:column;gap:22px;min-width:0}
.panel-title{font-family:var(--mono);font-size:11px;letter-spacing:0.12em;text-transform:uppercase;color:var(--ink-3);border-bottom:1px solid var(--rule-2);padding-bottom:6px;margin-bottom:10px}

/* personas */
.personas{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:16px}
.persona{background:var(--panel);border:1px solid var(--rule-2);padding:16px 18px;display:flex;flex-direction:column;gap:10px;min-width:0}
.persona.writer{border-top:3px solid var(--writer)}
.persona.ro{border-top:3px dashed var(--ro)}
.persona header{display:flex;justify-content:space-between;align-items:baseline;gap:10px}
.persona h3{font-family:var(--mono);font-size:15px;font-weight:500;letter-spacing:0}
.persona .role{font-size:13.5px;color:var(--ink-2)}
.persona .model{font-family:var(--mono);font-size:12px}
.persona dl.kv{font-size:12.5px;gap:4px 12px}

/* lifecycle */
.lifecycle{list-style:none;margin:0;padding:0;display:flex;flex-direction:column}
.lifecycle > li{display:grid;grid-template-columns:200px minmax(0,1fr);gap:20px;padding-block:16px;border-top:1px solid var(--rule-2)}
.lifecycle > li:first-child{border-top:0}
.moment b{display:block;font-family:var(--display);font-size:18px}
.moment span{font-family:var(--mono);font-size:11.5px;color:var(--ink-3)}
.guards{display:flex;flex-direction:column;gap:12px;min-width:0}
.guard{display:grid;grid-template-columns:minmax(0,260px) minmax(0,1fr);gap:4px 18px;padding-left:14px;border-left:3px solid var(--gate)}
.guard code{background:none;padding:0;font-size:13px;font-weight:500}
.guard .scope{font-family:var(--mono);font-size:11px;color:var(--ink-3)}
.guard p{font-size:13.5px}
.guard .tests{grid-column:2;font-family:var(--mono);font-size:11px;color:var(--ok)}

/* skills, references, tests, records */
.skills{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:1px;background:var(--rule-2);border:1px solid var(--rule-2)}
.skill{background:var(--paper);padding:14px 16px;display:flex;flex-direction:column;gap:6px;min-width:0}
.skill header{display:flex;justify-content:space-between;gap:8px;align-items:baseline}
.skill code{background:none;padding:0;font-size:13px;font-weight:500}
.skill p{font-size:13px;color:var(--ink-2)}
.cols{display:grid;grid-template-columns:minmax(0,1.6fr) minmax(0,1fr);gap:28px}
ul.index{list-style:none;margin:0;padding:0;display:flex;flex-direction:column}
ul.index li{display:grid;grid-template-columns:minmax(0,240px) minmax(0,1fr);gap:16px;padding-block:7px;border-top:1px solid var(--rule-2);font-size:13.5px}
ul.index li:first-child{border-top:0}
ul.index code{background:none;padding:0}
ul.index span{color:var(--ink-2)}
table{border-collapse:collapse;width:100%;font-size:13.5px}
th,td{text-align:left;vertical-align:top;padding:10px 12px;border-bottom:1px solid var(--rule-2)}
th{font-family:var(--mono);font-size:11px;letter-spacing:0.08em;text-transform:uppercase;color:var(--ink-3);font-weight:500;border-bottom:1px solid var(--rule)}
td .why{display:block;font-size:12.5px;color:var(--ink-2);margin-top:3px;max-width:62ch}
td.cmd{font-family:var(--mono);font-size:12px;color:var(--ink-2);white-space:nowrap}
ol.adrs{list-style:none;margin:0;padding:0;display:flex;flex-direction:column}
ol.adrs li{display:grid;grid-template-columns:64px minmax(0,1fr);gap:12px;padding-block:8px;border-top:1px solid var(--rule-2)}
ol.adrs li:first-child{border-top:0}
ol.adrs b{font-family:var(--mono);font-weight:500;color:var(--gate);font-variant-numeric:tabular-nums}
footer{font-family:var(--mono);font-size:12px;color:var(--ink-3);border-top:1px solid var(--rule-2);padding-top:14px}

@media (max-width:860px){
  .mast,.boot,.cols{grid-template-columns:minmax(0,1fr)}
  .rules{grid-template-columns:minmax(0,1fr)}
  .plate-head{grid-template-columns:minmax(0,1fr)}
  .plate-head p{grid-column:1}
  .lifecycle > li{grid-template-columns:minmax(0,1fr);gap:10px}
  .guard{grid-template-columns:minmax(0,1fr)}
  .guard .tests{grid-column:1}
  ul.index li{grid-template-columns:minmax(0,1fr);gap:2px}
  nav.toc{margin-block:-56px}
}
@media (prefers-reduced-motion: no-preference){nav.toc a{transition:border-color .15s,color .15s}}
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
    """The first sentence of a description, for cards that cannot hold a paragraph."""
    sentence = re.split(r'(?<=[.!?])\s', text.strip(), maxsplit=1)[0]
    return sentence if len(sentence) <= limit else sentence[:limit - 1].rstrip() + '…'


def tag(name, writer):
    return f'<span class="tag {"writer" if writer else "ro"}">{e(name)}</span>'


def pipeline_svg(cmds, writers):
    """The gate commands left to right, human decisions as diamonds, /test as a
    conditional detour below /review, and each stage's personas under it."""
    main = [n for n in PIPELINE if n in cmds and n not in CONDITIONAL]
    x0, step, w, h, top = 40, 214, 156, 64, 64
    pos = {n: x0 + i * step for i, n in enumerate(main)}
    out = ['<svg viewBox="0 0 1200 470" role="img" font-family="IBM Plex Mono, ui-monospace, monospace" '
           'aria-label="Gate commands from left to right with human approval points, the conditional /test stage '
           'under /review, and the personas each stage dispatches.">',
           '<defs><marker id="arw" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
           'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="var(--ink)"/></marker>'
           '<marker id="arwg" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
           'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="var(--ro)"/></marker></defs>']

    def stage(name, x, y, dashed=False):
        c = cmds[name]
        dash = ' stroke-dasharray="6 4"' if dashed else ''
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="var(--panel)" stroke="var(--ink)" '
                   f'stroke-width="1.6"{dash}/>')
        out.append(f'<text x="{x + 14}" y="{y + 28}" font-family="Bricolage Grotesque, system-ui, sans-serif" '
                   f'font-size="22" font-weight="700" fill="var(--ink)">/{e(name)}</text>')
        sub = c['model'] or ('conditional' if dashed else 'session model')
        out.append(f'<text x="{x + 14}" y="{y + 50}" font-size="11" fill="var(--ink-3)">{e(sub)}</text>')
        for i, persona in enumerate(c['personas']):
            py = y + h + 22 + i * 30
            writer = persona in writers
            out.append(f'<line x1="{x + 14}" y1="{py - 22 if i == 0 else py - 16}" x2="{x + 14}" y2="{py}" '
                       f'stroke="var(--rule)" stroke-width="1"/>')
            fill = 'var(--writer-soft)' if writer else 'var(--panel)'
            stroke = 'var(--writer)' if writer else 'var(--ro)'
            dash2 = '' if writer else ' stroke-dasharray="4 3"'
            cw = max(w - 24, round(7.1 * len(persona) + 18))   # IBM Plex Mono 11.5px is ~7px a glyph
            out.append(f'<rect x="{x + 24}" y="{py - 9}" width="{cw}" height="22" fill="{fill}" '
                       f'stroke="{stroke}" stroke-width="1.2"{dash2}/>')
            out.append(f'<text x="{x + 32}" y="{py + 6}" font-size="11.5" fill="{stroke}">{e(persona)}</text>')

    for name in main:
        stage(name, pos[name], top)
    for a, b in zip(main, main[1:]):
        x1, x2, y = pos[a] + w, pos[b], top + h / 2
        if a in HUMAN_GATE_AFTER:
            mid = (x1 + x2) / 2
            out.append(f'<line x1="{x1}" y1="{y}" x2="{mid - 12}" y2="{y}" stroke="var(--ink)" stroke-width="1.6"/>')
            out.append(f'<rect x="{mid - 9}" y="{y - 9}" width="18" height="18" fill="var(--gate-soft)" '
                       f'stroke="var(--gate)" stroke-width="1.8" transform="rotate(45 {mid} {y})"/>')
            out.append(f'<line x1="{mid + 12}" y1="{y}" x2="{x2 - 2}" y2="{y}" stroke="var(--ink)" '
                       f'stroke-width="1.6" marker-end="url(#arw)"/>')
            out.append(f'<text x="{mid}" y="{top - 16}" font-size="11" text-anchor="middle" '
                       f'fill="var(--gate)">{e(HUMAN_GATE_AFTER[a])}</text>')
        else:
            out.append(f'<line x1="{x1}" y1="{y}" x2="{x2 - 2}" y2="{y}" stroke="var(--ink)" stroke-width="1.6" '
                       f'marker-end="url(#arw)"/>')
    last = main[-1]
    if last in HUMAN_GATE_AFTER:
        x1, y = pos[last] + w, top + h / 2
        mid = x1 + 30
        out.append(f'<line x1="{x1}" y1="{y}" x2="{mid - 12}" y2="{y}" stroke="var(--ink)" stroke-width="1.6"/>')
        out.append(f'<rect x="{mid - 9}" y="{y - 9}" width="18" height="18" fill="var(--gate-soft)" '
                   f'stroke="var(--gate)" stroke-width="1.8" transform="rotate(45 {mid} {y})"/>')
        out.append(f'<text x="{mid}" y="{top - 16}" font-size="11" text-anchor="middle" '
                   f'fill="var(--gate)">{e(HUMAN_GATE_AFTER[last])}</text>')

    for name in CONDITIONAL:
        if name not in cmds or 'review' not in pos or 'ship' not in pos:
            continue
        # Under /ship, so the detour never crosses /review's persona column:
        # down /review's left edge, along under its personas, up into /ship.
        x, y = pos['ship'], 330
        stage(name, x, y, dashed=True)
        rx = pos['review'] + 6
        out.append(f'<path d="M{rx},{top + h} V{y + h / 2} H{x - 2}" fill="none" stroke="var(--ro)" '
                   f'stroke-width="1.4" stroke-dasharray="6 4" marker-end="url(#arwg)"/>')
        out.append(f'<path d="M{x + w / 2},{y} V{top + h + 2}" fill="none" stroke="var(--ro)" '
                   f'stroke-width="1.4" stroke-dasharray="6 4" marker-end="url(#arwg)"/>')
        out.append(f'<text x="{(rx + x) / 2}" y="{y + h / 2 - 8}" font-size="11" text-anchor="middle" '
                   f'fill="var(--ink-3)">{e(CONDITIONAL[name])}</text>')
    out.append('</svg>')
    return '\n'.join(out)


LIFECYCLE = [('SessionStart', None, 'Session starts', 'before any work'),
             ('PreToolUse', 'Agent|Task', 'A persona is dispatched', 'PreToolUse · Agent|Task'),
             ('PreToolUse', 'Bash', 'Any shell command', 'PreToolUse · Bash'),
             ('SubagentStop', None, 'A writer tries to finish', 'SubagentStop')]


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

    out = ['<!doctype html>', '<html lang="en">', '<head>', '<meta charset="utf-8">',
           '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">',
           '<title>Harness Map</title>',
           '<!-- Generated by dotfiles/tools/checks/harness-map.py. Do not edit by hand; CI fails when this page is stale. -->',
           '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">',
           '<style>' + CSS + '</style>', '</head>', '<body>', '<div class="sheet">']

    figures = [(len(cmds), 'commands'), (len(persona_rows), 'personas'), (len(skill_rows), 'skills'),
               (len(hook_rows), 'hook bindings'), (len(adr_rows), 'decisions'), (len(steps), 'CI steps')]
    out.append('<header class="mast"><div>'
               '<div class="eyebrow">stanimirdim92/setup_scripts · dotfiles</div>'
               '<h1>Harness Map</h1>'
               '<p class="lede">The Claude Code harness as its files define it: what every session loads, how the '
               'gate commands hand work to personas, which rules the host enforces, and what tests the harness. '
               'Generated by <code>dotfiles/tools/checks/harness-map.py</code>; CI fails when it is stale.</p>'
               '</div><div class="figures">'
               + ''.join(f'<div class="figure"><b>{n}</b><span>{e(label)}</span></div>' for n, label in figures)
               + '</div></header>')
    out.append('<nav class="toc" aria-label="Sections">'
               '<a href="#pipeline">Pipeline</a><a href="#boot">Session boot</a><a href="#personas">Personas</a>'
               '<a href="#enforcement">Enforcement</a><a href="#skills">Skills</a><a href="#references">References</a>'
               '<a href="#tests">Self-tests</a><a href="#records">Decisions</a></nav>')

    # Pipeline
    out.append('<section id="pipeline"><div class="plate-head"><div class="eyebrow">Plate 1 · Flow</div>'
               '<h2>A ticket moves left to right through gates</h2>'
               '<p>Commands orchestrate; personas never dispatch personas (spawn depth 1). A persona hangs under the '
               'command that names it. Amber diamonds are decisions only a human makes.</p></div>'
               '<div class="legend"><span><i class="sw gate"></i>human decision</span>'
               '<span><i class="sw writer"></i>persona that can change files</span>'
               '<span><i class="sw ro"></i>read-only persona</span><span>dashed = conditional</span></div>'
               '<figure class="drawing scroll">' + pipeline_svg(cmds, writers) + '</figure>')
    for name in sorted(n for n in cmds if n not in PIPELINE):
        out.append(f'<p class="aside">Outside the gates: <code>/{e(name)}</code> — {e(cmds[name]["description"])}.</p>')
    out.append('</section>')

    # Boot
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
    out.append('<section id="boot"><div class="plate-head"><div class="eyebrow">Plate 2 · Context</div>'
               '<h2>What every session loads</h2>'
               '<p><code>AGENTS.md</code>, linked as Claude\'s <code>CLAUDE.md</code> and Codex\'s '
               '<code>AGENTS.md</code>, and <code>settings.json</code>.</p></div><div class="boot">'
               f'<div><div class="panel-title">AGENTS.md · {len(rules)} rules, each naming what it catches</div>'
               '<ol class="rules">')
    for i, (title, lead, catches) in enumerate(rules, 1):
        out.append(f'<li><i>{i}</i><div><b>{e(title)}</b><span>{e(lead)}</span>'
                   + (f'<em>Catches: {e(catches)}</em>' if catches else '') + '</div></li>')
    out.append(f'</ol><p class="aside" style="margin-top:14px">Also: {", ".join(e(s) for s in other_sections)}.</p></div>'
               '<div class="stack"><div><div class="panel-title">Enforcement pins · env</div><dl class="kv">')
    for k, v in pins:
        out.append(f'<dt>{e(k.replace("CLAUDE_CODE_", ""))}</dt><dd><code>{e(str(v))}</code></dd>')
    out.append('</dl></div><div><div class="panel-title">Defaults</div><dl class="kv">')
    for k, v in defaults:
        out.append(f'<dt>{e(k)}</dt><dd>{e(str(v))}</dd>')
    out.append('</dl></div></div></div></section>')

    # Personas: writers first, then by name
    ordered = sorted(persona_rows, key=lambda p: (not p['writer'], p['name']))
    out.append(f'<section id="personas"><div class="plate-head"><div class="eyebrow">Plate 3 · Workers</div>'
               f'<h2>{len(persona_rows)} personas, {len(writers)} of which can write</h2>'
               '<p>Read-only is a tool grant, not an instruction. Writers carry agent-scoped hooks.</p></div>'
               '<div class="personas">')
    for p in ordered:
        kind = 'writer' if p['writer'] else 'ro'
        model = e(p['model']) + (f' · effort {e(p["effort"])}' if p['effort'] else '')
        meta = [('maxTurns', e(p['maxTurns']))]
        if p['isolation']:
            meta.append(('isolation', e(p['isolation'])))
        if p['hooks']:
            meta.append(('hooks', '<br>'.join(f'{e(ev)} · {e(s[:-3])}' for ev, s in p['hooks'])))
        if p['skills']:
            meta.append(('preloads', e(', '.join(p['skills']))))
        out.append(f'<article class="persona {kind}"><header><h3>{e(p["name"])}</h3>'
                   f'<span class="tag {kind}">{"writes" if p["writer"] else "read-only"}</span></header>'
                   f'<div class="model">{model}</div><p class="role">{e(first_sentence(p["description"]))}</p>'
                   '<div class="chips">' + ''.join(f'<span class="chip">{e(t)}</span>' for t in p['tools']) + '</div>'
                   '<dl class="kv">' + ''.join(f'<dt>{k}</dt><dd>{v}</dd>' for k, v in meta) + '</dl></article>')
    out.append('</div></section>')

    # Enforcement as a lifecycle
    out.append('<section id="enforcement"><div class="plate-head"><div class="eyebrow">Plate 4 · Guards</div>'
               '<h2>Where a rule stops being a sentence</h2>'
               '<p>Every hook binding at the moment it fires, with the first line of the script\'s own header and the '
               'self-test that exercises it.</p></div><ol class="lifecycle">')
    placed = set()
    for event, matcher, title, label in LIFECYCLE:
        rows = [r for r in hook_rows if r[1] == event and (matcher is None or r[2] == matcher)]
        if not rows:
            continue
        out.append(f'<li><div class="moment"><b>{e(title)}</b><span>{e(label)}</span></div><div class="guards">')
        for script, ev, mt, scope, summary, tests in rows:
            placed.add((script, ev, mt))
            out.append(f'<div class="guard"><div><code>{e(script)}</code><div class="scope">{e(scope)}</div></div>'
                       f'<p>{e(summary)}</p>'
                       + (f'<div class="tests">tested by {" · ".join(e(t.rsplit("/", 1)[1]) for t in tests)}</div>'
                          if tests else '') + '</div>')
        out.append('</div></li>')
    rest = [r for r in hook_rows if (r[0], r[1], r[2]) not in placed]
    if rest:
        out.append('<li><div class="moment"><b>Other</b><span>unplaced events</span></div><div class="guards">')
        for script, ev, mt, scope, summary, tests in rest:
            out.append(f'<div class="guard"><div><code>{e(script)}</code><div class="scope">{e(ev)} · {e(mt)} · '
                       f'{e(scope)}</div></div><p>{e(summary)}</p></div>')
        out.append('</div></li>')
    out.append('</ol></section>')

    # Skills
    explicit = sum(1 for s in skill_rows if s[2])
    out.append(f'<section id="skills"><div class="plate-head"><div class="eyebrow">Plate 5 · Methodology</div>'
               f'<h2>{len(skill_rows)} skills</h2>'
               f'<p>{explicit} are <span class="tag gate">explicit</span>: their Codex adapter sets '
               '<code>allow_implicit_invocation: false</code>, so a stage or role loads them, never a keyword '
               'match.</p></div><div class="skills">')
    for name, desc, is_explicit in skill_rows:
        badge = '<span class="tag gate">explicit</span>' if is_explicit else ''
        out.append(f'<div class="skill"><header><code>{e(name)}</code>{badge}</header>'
                   f'<p>{e(first_sentence(desc, 150))}</p></div>')
    out.append('</div></section>')

    # References
    out.append(f'<section id="references"><div class="plate-head"><div class="eyebrow">Plate 6 · Sources</div>'
               f'<h2>{len(refs)} references and {len(templates)} templates</h2>'
               '<p>The single sources the commands point at, so a rule is written once.</p></div><div class="cols">'
               '<div><div class="panel-title">references/</div><ul class="index">')
    for path, title in refs:
        out.append(f'<li><code>{e(path)}</code><span>{e(title)}</span></li>')
    out.append('</ul></div><div><div class="panel-title">references/templates/</div><ul class="index">')
    for path, title in templates:
        out.append(f'<li><code>{e(path.split("/", 1)[1])}</code><span>{e(title)}</span></li>')
    out.append('</ul></div></div></section>')

    # Self-tests
    out.append(f'<section id="tests"><div class="plate-head"><div class="eyebrow">Plate 7 · Self-tests</div>'
               f'<h2>{len(steps)} CI steps on every push to main and every pull request</h2>'
               '<p>Every deterministic check. The live workflow runner and real spec runs stay manual; they spend '
               'tokens.</p></div><div class="scroll"><table><thead><tr><th>Step</th><th>Runs</th></tr></thead><tbody>')
    for name, runs, comment in steps:
        why = f'<span class="why">{e(comment)}</span>' if comment else ''
        out.append(f'<tr><td>{e(name)}{why}</td><td class="cmd">{"<br>".join(e(r) for r in runs)}</td></tr>')
    out.append('</tbody></table></div></section>')

    # Records
    out.append(f'<section id="records"><div class="plate-head"><div class="eyebrow">Plate 8 · Decisions</div>'
               f'<h2>{len(adr_rows)} architecture decisions</h2>'
               '<p>The ten most recent. The full index is <code>dotfiles/docs/adr/README.md</code>.</p></div>'
               '<ol class="adrs">')
    for num, title, path in adr_rows[-10:][::-1]:
        out.append(f'<li><b>{e(num)}</b><span>{e(title)}</span></li>')
    out.append('</ol></section>')

    out.append('<footer>Generated by dotfiles/tools/checks/harness-map.py from the repository sources. '
               'Do not edit by hand.</footer>')
    out.append('</div>\n</body>\n</html>\n')
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
