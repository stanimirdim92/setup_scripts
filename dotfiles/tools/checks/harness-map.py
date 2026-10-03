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
:root{
  --paper:#F3F4F1; --paper-2:#E9EBE6; --ink:#1B2028; --ink-2:#4A515B; --rule:#8A9099; --rule-2:#C9CDC7;
  --gate:#C77A12; --gate-soft:#F6E4C7; --writer:#3D6B8E; --writer-soft:#D9E6F0; --ro:#5E6672;
  --display:"Bricolage Grotesque","Archivo",system-ui,sans-serif;
  --body:"IBM Plex Sans","Helvetica Neue",Arial,sans-serif;
  --mono:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,monospace;
  color-scheme:light dark;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --paper:#141820; --paper-2:#1C222C; --ink:#E6E8E3; --ink-2:#AEB4BC; --rule:#6F7680; --rule-2:#2E3540;
    --gate:#E0973A; --gate-soft:#3A2B14; --writer:#6FA3C9; --writer-soft:#1D2F3E; --ro:#98A0AA;
  }
}
:root[data-theme="dark"]{
  --paper:#141820; --paper-2:#1C222C; --ink:#E6E8E3; --ink-2:#AEB4BC; --rule:#6F7680; --rule-2:#2E3540;
  --gate:#E0973A; --gate-soft:#3A2B14; --writer:#6FA3C9; --writer-soft:#1D2F3E; --ro:#98A0AA;
}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--body);font-size:15px;line-height:1.5;padding:0 clamp(16px,4vw,48px);padding-block:32px 72px}
a{color:inherit}
h1,h2,h3{font-family:var(--display);text-wrap:balance;margin:0;font-weight:700;letter-spacing:-0.01em}
h1{font-size:clamp(34px,5vw,56px);line-height:1.02}
h2{font-size:clamp(22px,2.6vw,30px);line-height:1.15}
h3{font-size:17px;font-weight:600}
p{margin:0;max-width:68ch}
code,.mono{font-family:var(--mono);font-size:0.92em}
code{background:var(--paper-2);padding:1px 5px;border-radius:3px}
.eyebrow{font-family:var(--mono);font-size:11px;letter-spacing:0.12em;text-transform:uppercase;color:var(--ink-2)}
.sheet{max-width:1240px;margin:0 auto;display:flex;flex-direction:column;gap:56px}
header.title{display:grid;grid-template-columns:1fr auto;gap:24px;align-items:end;border-bottom:2px solid var(--ink);padding-bottom:20px}
header .lede{max-width:62ch;color:var(--ink-2);margin-top:12px}
.meta{font-family:var(--mono);font-size:12px;color:var(--ink-2);display:grid;gap:4px;text-align:right}
.meta b{color:var(--ink);font-weight:500}
nav.toc{display:flex;flex-wrap:wrap;gap:8px 18px;font-family:var(--mono);font-size:12px;color:var(--ink-2)}
nav.toc a{text-decoration:none;border-bottom:1px solid var(--rule-2);padding-bottom:1px}
nav.toc a:hover,nav.toc a:focus-visible{border-color:var(--gate);color:var(--ink);outline:none}
section{display:flex;flex-direction:column;gap:18px}
.plate-head{display:grid;grid-template-columns:1fr;gap:6px;border-top:1px solid var(--rule-2);padding-top:14px}
.plate-head p{color:var(--ink-2)}
.legend{display:flex;flex-wrap:wrap;gap:8px 20px;font-size:12px;color:var(--ink-2);font-family:var(--mono)}
.legend span{display:inline-flex;align-items:center;gap:7px}
.sw{width:14px;height:14px;border:1.5px solid var(--ink);display:inline-block}
.sw.gate{background:var(--gate-soft);border-color:var(--gate);transform:rotate(45deg);width:11px;height:11px}
.sw.writer{background:var(--writer-soft);border-color:var(--writer)}
.sw.ro{border-style:dashed;border-color:var(--ro)}
figure{margin:0;display:flex;flex-direction:column;gap:10px}
figure svg{max-width:100%;height:auto;display:block;color:var(--ink)}
figcaption{font-size:13px;color:var(--ink-2);max-width:78ch}
.scroll{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:13.5px}
th,td{text-align:left;vertical-align:top;padding:9px 10px;border-bottom:1px solid var(--rule-2)}
th{font-family:var(--mono);font-size:11px;letter-spacing:0.08em;text-transform:uppercase;color:var(--ink-2);font-weight:500;border-bottom:1px solid var(--rule)}
td.num{font-variant-numeric:tabular-nums;text-align:right;white-space:nowrap}
td .mono,th .mono{white-space:nowrap}
.tag{display:inline-block;font-family:var(--mono);font-size:11px;padding:1px 7px;border:1px solid var(--rule);border-radius:2px;white-space:nowrap}
.tag.writer{border-color:var(--writer);color:var(--writer);background:var(--writer-soft)}
.tag.ro{border-style:dashed;color:var(--ro)}
.tag.gate{border-color:var(--gate);color:var(--gate);background:var(--gate-soft)}
.grid{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(280px,1fr))}
.tile{border:1px solid var(--rule-2);padding:14px 16px;display:flex;flex-direction:column;gap:8px;background:var(--paper)}
.tile h3{display:flex;justify-content:space-between;gap:10px;align-items:baseline}
.tile h3 small{font-family:var(--mono);font-size:11px;color:var(--ink-2);font-weight:400}
.tile ul{margin:0;padding-left:0;list-style:none;display:flex;flex-direction:column;gap:5px;font-size:13.5px}
.tile li{display:grid;grid-template-columns:auto 1fr;gap:10px;align-items:baseline}
.tile li code{white-space:nowrap}
.tile li span{color:var(--ink-2)}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.chip{font-family:var(--mono);font-size:12px;padding:3px 9px;border:1px solid var(--rule-2);border-radius:2px;background:var(--paper-2)}
.chip.dmi::after{content:" ·explicit";color:var(--gate)}
.rules{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:10px 24px;counter-reset:rule}
.rules li{list-style:none;display:grid;grid-template-columns:28px 1fr;gap:8px;font-size:13.5px;color:var(--ink-2)}
.rules li b{color:var(--ink);font-weight:600}
.rules li::before{counter-increment:rule;content:counter(rule);font-family:var(--mono);color:var(--gate);font-size:12px;padding-top:2px}
.pins{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:10px}
.pin{border-left:3px solid var(--gate);padding:6px 12px;font-size:13.5px;display:grid;gap:2px}
.pin code{background:none;padding:0;font-size:12.5px}
.pin span{color:var(--ink-2)}
.open{border:1px dashed var(--gate);padding:14px 16px;display:grid;gap:6px;font-size:13.5px}
.open .eyebrow{color:var(--gate)}
footer{font-family:var(--mono);font-size:12px;color:var(--ink-2);border-top:1px solid var(--rule-2);padding-top:14px}
@media (max-width:640px){header.title{grid-template-columns:1fr}.meta{text-align:left}}
@media (prefers-reduced-motion: no-preference){nav.toc a{transition:border-color .15s}}
.stages{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}
.stage{border:1.5px solid var(--ink);padding:12px 14px;display:flex;flex-direction:column;gap:8px;background:var(--paper)}
.stage.cond{border-style:dashed}
.stage h3 code{background:none;padding:0;font-size:17px}
.stage p{font-size:13px;color:var(--ink-2)}
.stage .gate-after{margin-top:auto;font-family:var(--mono);font-size:11px;color:var(--gate)}
.stage .gate-after::before{content:"\25C6  "}
.aside{font-size:13px;color:var(--ink-2)}
.stage .tag{white-space:normal;overflow-wrap:anywhere;max-width:100%}
td{overflow-wrap:anywhere}
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


def tag(name, writer):
    return f'<span class="tag {"writer" if writer else "ro"}">{e(name)}</span>'


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

    out = ['<!doctype html>', '<html lang="en">', '<head>', '<meta charset="utf-8">',
           '<meta name="viewport" content="width=device-width, initial-scale=1">',
           '<title>Harness Map</title>',
           '<!-- Generated by dotfiles/tools/harness-map.py. Do not edit by hand; CI fails when this page is stale. -->',
           '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">',
           '<style>' + CSS + '</style>', '</head>', '<body>', '<div class="sheet">']

    out.append(f'''<header class="title">
  <div>
    <div class="eyebrow">stanimirdim92/setup_scripts · dotfiles/claude</div>
    <h1>Harness Map</h1>
    <p class="lede">Every layer of the Claude Code harness, generated from the files that define it: what loads at session start, how the gate commands hand work to personas, which rules the host enforces, and what tests the harness itself. Regenerate with <code>python3 dotfiles/tools/checks/harness-map.py</code>; CI fails when this page is stale.</p>
  </div>
  <div class="meta">
    <div>{len(cmds)} commands · {len(persona_rows)} personas · {len(skill_rows)} skills</div>
    <div>{len(ref_rows) - len(templates)} references + {len(templates)} templates · {len(hook_rows)} hook bindings</div>
    <div>{len(adr_rows)} ADRs · {len(steps)} CI steps</div>
  </div>
</header>
<nav class="toc" aria-label="Sections">
  <a href="#pipeline">Pipeline</a><a href="#boot">Session boot</a><a href="#personas">Personas</a><a href="#enforcement">Enforcement</a><a href="#references">References</a><a href="#skills">Skills</a><a href="#tests">Harness tests</a><a href="#records">Records</a>
</nav>''')

    # Pipeline
    out.append('''<section id="pipeline">
  <div class="plate-head">
    <div class="eyebrow">Layer 1 · Flow</div>
    <h2>Gate commands, left to right</h2>
    <p>Commands orchestrate; personas never dispatch personas (spawn depth 1). A persona appears on a card when the command names it. Amber diamonds mark decisions only a human makes.</p>
  </div>
  <div class="legend"><span><i class="sw writer"></i> persona that can change files</span><span><i class="sw ro"></i> read-only persona</span><span>dashed card = conditional stage</span></div>
  <div class="stages">''')
    for name in PIPELINE:
        c = cmds.get(name)
        if not c:
            continue
        chips = ' '.join(tag(p, p in writers) for p in c['personas']) or '<span class="aside">no persona — the session itself</span>'
        model = f' <small>{e(c["model"])}</small>' if c['model'] else ''
        cond = f'<p><b>{e(CONDITIONAL[name])}</b></p>' if name in CONDITIONAL else ''
        gate = f'<div class="gate-after">{e(HUMAN_GATE_AFTER[name])}</div>' if name in HUMAN_GATE_AFTER else ''
        out.append(f'''    <div class="stage{" cond" if name in CONDITIONAL else ""}">
      <h3><code>/{e(name)}</code>{model}</h3>
      <p>{e(c["description"])}</p>{cond}
      <div class="chips">{chips}</div>{gate}
    </div>''')
    out.append('  </div>')
    extra = [n for n in sorted(cmds) if n not in PIPELINE]
    for name in extra:
        c = cmds[name]
        out.append(f'  <p class="aside">Outside the gates: <code>/{e(name)}</code> — {e(c["description"])}.</p>')
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
        ('permissions', f'{perms.get("defaultMode", "default")} · {len(perms.get("allow", []))} allow · {len(perms.get("deny", []))} deny'),
        ('sandbox', f'{"on" if sandbox.get("enabled") else "off"} · {len(sandbox.get("excludedCommands", []))} excluded commands · {len(denied)} credential paths denied'),
        ('worktree.baseRef', settings.get('worktree', {}).get('baseRef', '—')),
    ]
    out.append(f'''<section id="boot">
  <div class="plate-head">
    <div class="eyebrow">Layer 0 · Context</div>
    <h2>What every session loads</h2>
    <p><code>AGENTS.md</code> (linked as <code>CLAUDE.md</code> and Codex's <code>AGENTS.md</code>) and <code>settings.json</code>.</p>
  </div>
  <div class="grid">
    <div class="tile"><h3>AGENTS.md — {len(rules)} rules <small>each names what it catches</small></h3>
      <ol class="rules">''')
    for title, lead, catches in rules:
        out.append(f'        <li><div><b>{e(title)}</b> {e(lead)}<br><span>{e(catches)}</span></div></li>')
    out.append(f'''      </ol>
      <p class="aside">Also: {", ".join(e(s) for s in other_sections)}.</p>
    </div>
    <div class="tile"><h3>settings.json — enforcement pins <small>env</small></h3><div class="pins">''')
    for k, v in pins:
        out.append(f'      <div class="pin"><code>{e(k)}={e(str(v))}</code></div>')
    out.append('    </div></div>\n    <div class="tile"><h3>settings.json — defaults</h3><ul>')
    for k, v in defaults:
        out.append(f'      <li><code>{e(k)}</code><span>{e(str(v))}</span></li>')
    out.append('    </ul></div>\n  </div>\n</section>')

    # Personas
    n_writers = len(writers)
    out.append(f'''<section id="personas">
  <div class="plate-head">
    <div class="eyebrow">Layer 2 · Workers</div>
    <h2>{len(persona_rows)} personas, {n_writers} of which can write</h2>
    <p>Read-only is a tool grant, not an instruction. Writers carry agent-scoped hooks.</p>
  </div>
  <div class="scroll"><table>
    <thead><tr><th>Persona</th><th>Role</th><th>Tools</th><th>Model · effort</th><th>maxTurns</th><th>Hooks</th><th>Preloaded skill</th></tr></thead>
    <tbody>''')
    for p in persona_rows:
        model = e(p['model']) + (f' · {e(p["effort"])}' if p['effort'] else '') + (f' · <b>{e(p["isolation"])}</b>' if p['isolation'] else '')
        hooks_cell = ' · '.join(f'<code>{e(ev)}</code> {e(s[:-3])}' for ev, s in p['hooks']) or '—'
        out.append(f'      <tr><td>{tag(p["name"], p["writer"])}</td><td>{e(p["description"])}</td>'
                   f'<td class="mono">{e(" ".join(p["tools"]))}</td><td>{model}</td><td class="num">{e(p["maxTurns"])}</td>'
                   f'<td>{hooks_cell}</td><td class="mono">{e(", ".join(p["skills"])) or "—"}</td></tr>')
    out.append('    </tbody>\n  </table></div>\n</section>')

    # Enforcement
    out.append('''<section id="enforcement">
  <div class="plate-head">
    <div class="eyebrow">Layer 3 · Guards</div>
    <h2>Where a rule stops being a sentence</h2>
    <p>Every hook binding, global or agent-scoped, with the first line of the script's own header and the suites that exercise it.</p>
  </div>
  <div class="scroll"><table>
    <thead><tr><th>Hook</th><th>Event · matcher</th><th>Scope</th><th>What it does</th><th>Tested by</th></tr></thead>
    <tbody>''')
    for script, event, matcher, scope, summary, tests in hook_rows:
        tests_cell = ' '.join(f'<code>{e(t)}</code>' for t in tests) or '—'
        out.append(f'      <tr><td><code>hooks/{e(script)}</code></td><td>{e(event)} · <code>{e(matcher)}</code></td>'
                   f'<td>{e(scope)}</td><td>{e(summary)}</td><td>{tests_cell}</td></tr>')
    out.append('    </tbody>\n  </table></div>\n</section>')

    # References
    out.append(f'''<section id="references">
  <div class="plate-head">
    <div class="eyebrow">Layer 4 · Sources</div>
    <h2>{len(ref_rows)} references the commands point at</h2>
  </div>
  <div class="tile"><ul>''')
    for path, title in ref_rows:
        out.append(f'    <li><code>references/{e(path)}</code><span>{e(title)}</span></li>')
    out.append('  </ul></div>\n</section>')

    # Skills
    out.append(f'''<section id="skills">
  <div class="plate-head">
    <div class="eyebrow">Layer 5 · Methodology</div>
    <h2>{len(skill_rows)} skills</h2>
    <p>Marked <span class="tag gate">explicit</span> when the Codex adapter sets <code>allow_implicit_invocation: false</code>: a stage or role loads it, never a keyword match.</p>
  </div>
  <div class="scroll"><table>
    <thead><tr><th>Skill</th><th>Description</th></tr></thead>
    <tbody>''')
    for name, desc, explicit in skill_rows:
        flag = ' <span class="tag gate">explicit</span>' if explicit else ''
        out.append(f'      <tr><td><code>{e(name)}</code>{flag}</td><td>{e(desc)}</td></tr>')
    out.append('    </tbody>\n  </table></div>\n</section>')

    # Tests
    out.append(f'''<section id="tests">
  <div class="plate-head">
    <div class="eyebrow">Layer 6 · Self-tests</div>
    <h2>{len(steps)} CI steps on every push to main and every pull request</h2>
  </div>
  <div class="scroll"><table>
    <thead><tr><th>Step</th><th>Runs</th><th>Why</th></tr></thead>
    <tbody>''')
    for name, runs, comment in steps:
        out.append(f'      <tr><td>{e(name)}</td><td class="mono">{"<br>".join(e(r) for r in runs)}</td><td>{e(comment)}</td></tr>')
    out.append('    </tbody>\n  </table></div>\n</section>')

    # Records
    out.append(f'''<section id="records">
  <div class="plate-head">
    <div class="eyebrow">Records</div>
    <h2>{len(adr_rows)} architecture decisions</h2>
    <p>Index: <code>dotfiles/docs/adr/README.md</code>. The latest ten:</p>
  </div>
  <div class="tile"><ul>''')
    for num, title, path in adr_rows[-10:][::-1]:
        out.append(f'    <li><code>{e(num)}</code><span>{e(title)}</span></li>')
    out.append('  </ul></div>\n</section>')

    out.append('<footer>Generated by dotfiles/tools/checks/harness-map.py from the repository sources. Do not edit by hand.</footer>')
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
