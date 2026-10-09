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
import subprocess
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
# What each stage leaves behind. Artifact paths are the ones
# validate-artifact-paths.py guards; the gate words are the commands' own.
STAGE_OUTPUT = {
    'spec': 'docs/specs/[TICKET]-SPEC.md, Status: Draft',
    'plan': 'docs/tasks/[TICKET]-plan.md + -todo.md',
    'build': 'local commits, task Status: Done',
    'review': 'findings: BLOCKER / REQUIRED / ADVISORY',
    'test': 'VERIFY PASS / FAIL / BLOCKED',
    'ship': 'GO / NO-GO with a rollback plan',
}



def e(text):
    """Escape for HTML, then render `code` spans the way the sources mean them."""
    return re.sub(r'`([^`]+)`', r'<code>\1</code>', html.escape(str(text)))

CSS = r"""
/* Layout: a reference manual. A fixed index on the left, one column of
   sections on the right, each opening with a one-line summary, then a table. */
:root{
  --bg:#F3F4FB; --surface:#FFFFFF; --sunk:#ECEEF8; --ink:#141729; --ink-2:#454B66; --ink-3:#656B8A;
  --line:#DADDF0; --line-2:#BCC1E0;
  --brand:#5534D1; --brand-bg:#EEEAFE;
  --gate:#C2410C; --gate-bg:#FFEDD5; --write:#1D4ED8; --write-bg:#DBEAFE; --read:#0F766E; --read-bg:#CCFBF1;
  --ok:#15803D;
  --display:"Archivo","Hanken Grotesk","Helvetica Neue",Arial,sans-serif;
  --sans:"Hanken Grotesk","Helvetica Neue",Arial,sans-serif;
  --mono:"JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,monospace;
  color-scheme:light;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --bg:#0C0E1A; --surface:#151829; --sunk:#1D2136; --ink:#ECEEFB; --ink-2:#B4B9D8; --ink-3:#8C92B3;
    --line:#272C46; --line-2:#3A4062;
    --brand:#A897FF; --brand-bg:#2A2259;
    --gate:#FB923C; --gate-bg:#3D2211; --write:#82B1FF; --write-bg:#172B52; --read:#2DD4BF; --read-bg:#0E322E; --ok:#4ADE80;
    color-scheme:dark;
  }
}
:root[data-theme="dark"]{
  --bg:#0C0E1A; --surface:#151829; --sunk:#1D2136; --ink:#ECEEFB; --ink-2:#B4B9D8; --ink-3:#8C92B3;
  --line:#272C46; --line-2:#3A4062;
  --brand:#A897FF; --brand-bg:#2A2259;
  --gate:#FB923C; --gate-bg:#3D2211; --write:#82B1FF; --write-bg:#172B52; --read:#2DD4BF; --read-bg:#0E322E; --ok:#4ADE80;
  color-scheme:dark;
}
*{box-sizing:border-box}
[hidden]{display:none!important}
html{scroll-behavior:smooth}
@media (prefers-reduced-motion: reduce){html{scroll-behavior:auto}}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:17px;line-height:1.6;padding-inline:clamp(16px,3vw,40px);padding-block:32px 80px}
a{color:inherit}
h1,h2,h3{margin:0;text-wrap:balance;letter-spacing:-0.01em}
h1,h2{font-family:var(--display);font-stretch:112%;letter-spacing:-0.02em}
h1{font-size:clamp(34px,4.6vw,50px);line-height:1.1;font-weight:800}
h2{font-size:27px;line-height:1.25;font-weight:700}
h3{font-size:18px;font-weight:700}
p{margin:0;max-width:70ch}
code,.mono{font-family:var(--mono);font-size:0.88em}
code{background:var(--sunk);padding:1px 5px;border-radius:4px;overflow-wrap:anywhere}
:focus-visible{outline:2px solid var(--brand);outline-offset:2px;border-radius:2px}
.layout{max-width:1320px;margin:0 auto;display:grid;grid-template-columns:220px minmax(0,1fr);gap:48px}

/* index */
nav.index{position:sticky;top:calc(env(safe-area-inset-top,0px) + 24px);align-self:start;display:flex;flex-direction:column;gap:2px;font-size:16px}
nav.index .label{font-size:12.5px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:var(--ink-3);margin-bottom:8px}
nav.index a{text-decoration:none;color:var(--ink-2);padding:5px 10px;border-left:2px solid var(--line);display:flex;justify-content:space-between;gap:8px}
nav.index a span{font-family:var(--mono);font-size:13px;color:var(--ink-3);font-variant-numeric:tabular-nums}
nav.index a:hover,nav.index a:focus-visible{color:var(--brand);border-left-color:var(--brand);background:var(--brand-bg);outline:none}
main{display:flex;flex-direction:column;gap:56px;min-width:0}

/* header */
header.top{display:flex;flex-direction:column;gap:10px;padding-bottom:24px;border-bottom:1px solid var(--line)}
header.top .kicker{font-family:var(--mono);font-size:13.5px;color:var(--brand)}
header.top p{color:var(--ink-2);font-size:18.5px}
.counts{display:flex;flex-wrap:wrap;gap:8px;margin-top:6px}
.count{background:var(--surface);border:1px solid var(--line);border-radius:6px;padding:7px 14px;font-size:15px;color:var(--ink-2)}
.count b{color:var(--brand);font-variant-numeric:tabular-nums;margin-right:4px}
.legend{display:flex;flex-wrap:wrap;gap:6px 20px;font-size:15px;color:var(--ink-2)}
.legend span{display:inline-flex;align-items:center;gap:6px}

/* sections */
section{display:flex;flex-direction:column;gap:16px;scroll-margin-top:24px;min-width:0}
.sec-head{display:flex;flex-direction:column;gap:4px;border-left:4px solid var(--brand);padding-left:14px}
.sec-head .summary{color:var(--ink-2)}
.panel{background:var(--surface);border:1px solid var(--line);border-radius:8px;min-width:0}
.panel.pad{padding:18px 20px}
.option{display:flex;flex-direction:column;gap:10px}
.option-label{display:flex;align-items:baseline;gap:10px;font-size:15px;color:var(--ink-3)}
.option-label b{font-size:12px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:var(--ink)}

/* badges */
.badge{display:inline-block;font-size:13.5px;font-weight:600;padding:1px 8px;border-radius:999px;white-space:nowrap;border:1px solid transparent}
.badge.write{color:var(--write);background:var(--write-bg)}
.badge.read{color:var(--read);background:var(--read-bg)}
.badge.plain{color:var(--ink-2);border-color:var(--line-2)}
.badge.gate{color:var(--gate);background:var(--gate-bg)}
.badge.cond{color:var(--ink-3);border:1px dashed var(--line-2)}
.persona-name{font-family:var(--mono);font-size:15px;white-space:nowrap;color:var(--read)}
.persona-name.write{color:var(--write)}
.who{display:flex;flex-wrap:wrap;gap:4px 12px}

/* pipeline tabs */
.tabs{display:flex;flex-wrap:wrap;gap:4px;border-bottom:1px solid var(--line-2)}
.tabs button{font:inherit;font-size:16px;font-weight:600;color:var(--ink-2);background:none;border:0;border-bottom:3px solid transparent;padding:10px 16px;margin-bottom:-1px;cursor:pointer;border-radius:6px 6px 0 0}
.tabs button:hover{color:var(--ink);background:var(--sunk)}
.tabs button[aria-selected="true"]{color:var(--brand);border-bottom-color:var(--brand)}
.tabs button span{font-family:var(--mono);font-size:13px;color:var(--ink-3);margin-right:6px}

/* option 1: stage list */
ol.stages{list-style:none;margin:0;padding:0}
ol.stages > li{display:grid;grid-template-columns:110px minmax(0,1fr) minmax(0,300px);gap:6px 20px;padding:14px 20px;border-top:1px solid var(--line);align-items:baseline}
ol.stages > li:first-child{border-top:0}
ol.stages .cmd{font-family:var(--mono);font-size:18px;font-weight:700;color:var(--brand)}
ol.stages .does{color:var(--ink-2);font-size:16px}
ol.stages > li.cond{background:repeating-linear-gradient(135deg,transparent 0 10px,var(--sunk) 10px 11px)}
ol.stages > li.gate{display:flex;gap:10px;align-items:center;padding:8px 20px;background:var(--gate-bg);color:var(--gate);font-weight:600;font-size:16px}
.diamond{width:10px;height:10px;transform:rotate(45deg);background:var(--gate);display:inline-block;flex:none}

/* option 2: strip */
.strip{display:flex;flex-wrap:wrap;align-items:center;gap:8px;padding:18px 20px}
.strip .box{font-family:var(--mono);font-weight:700;font-size:16px;padding:8px 14px;border:1.5px solid var(--brand);border-radius:6px;background:var(--brand-bg);color:var(--brand)}
.strip .box.cond{border-style:dashed;color:var(--ink-2)}
.strip .sep{color:var(--ink-3)}
.strip .diamond{margin-inline:2px}

/* option 3: flowchart (inline SVG, styled from here) */
figure.flow{margin:0;display:flex;flex-direction:column}
.flow-scroll{overflow-x:auto;padding:12px}
.flow-scroll svg{display:block;width:100%;min-width:760px;max-width:980px;height:auto}
figure.flow figcaption{font-size:15px;color:var(--ink-2);padding:12px 20px 16px;border-top:1px solid var(--line)}
.f-cmd{font-family:var(--mono);font-size:19px;font-weight:700;fill:var(--brand)}
.f-desc{font-family:var(--sans);font-size:15.5px;fill:var(--ink)}
.f-who,.f-out{font-family:var(--mono);font-size:13.5px;fill:var(--ink-2)}
.f-label{font-family:var(--sans);font-size:13px;font-weight:700;fill:var(--ink-3);letter-spacing:0.04em}
.f-write{fill:var(--write);font-weight:700}
.f-read{fill:var(--read);font-weight:700}
.f-note{font-family:var(--sans);font-size:13px;font-style:italic;fill:var(--ink-3)}
.f-edge{stroke:var(--ink-2);stroke-width:1.6}
.f-edge-label{font-family:var(--sans);font-size:13.5px;fill:var(--ink-3)}
.f-gate{font-family:var(--sans);font-size:15.5px;font-weight:700;fill:var(--gate)}
ol.stages .leaves{display:block;font-family:var(--mono);font-size:13.5px;color:var(--ink-3);margin-top:4px}

/* tables */
.tablewrap{overflow-x:auto;min-width:0}
table{border-collapse:collapse;width:100%;font-size:16px}
th,td{text-align:left;vertical-align:top;padding:12px 16px;border-bottom:1px solid var(--line)}
tr:last-child td{border-bottom:0}
th{font-size:13px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:var(--brand);background:var(--brand-bg);border-bottom:1px solid var(--line)}
th:first-child{border-top-left-radius:8px}
th:last-child{border-top-right-radius:8px}
td.num{font-variant-numeric:tabular-nums;text-align:right;white-space:nowrap}
td .sub{display:block;font-size:15px;color:var(--ink-2);margin-top:2px;max-width:60ch}
td.cmdcell{font-family:var(--mono);font-size:14.5px;color:var(--ink-2)}
td.nowrap{white-space:nowrap}
td.group{font-weight:700;background:var(--sunk);font-size:15.5px;color:var(--brand)}
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
    # Tracked skills only: a skill fetched into a gitignored folder (Figma's)
    # exists on one machine and not in CI, and would make the page stale.
    tracked = set(subprocess.run(['git', '-C', str(ROOT), 'ls-files', 'dotfiles/claude/skills'],
                                 capture_output=True, text=True).stdout.split())
    for path in sorted((CLAUDE / 'skills').glob('*/SKILL.md')):
        if rel(path) not in tracked:
            continue
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
PIPELINE_VIEWS = ('list', 'strip', 'flow')
DEFAULT_VIEW = 'flow'


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
                    f'<span class="does">{e(c["description"])}{badge}'
                    f'<span class="leaves">Leaves {e(STAGE_OUTPUT.get(name, ""))}</span></span>'
                    f'<span class="who">{who}</span></li>')
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


def wrap(text, width):
    """Greedy word wrap by character count, for SVG text (no layout engine)."""
    lines, line = [], ''
    for word in text.split():
        if line and len(line) + 1 + len(word) > width:
            lines.append(line)
            line = word
        else:
            line = f'{line} {word}'.strip()
    return lines + ([line] if line else [])


def pipeline_flow(cmds, writers):
    """The pipeline as an inline SVG flowchart: one box per stage, top to bottom,
    with what it does, who does it and what it leaves behind. Every arrow names
    what passes along it; orange diamonds are the human decisions; /test is a
    dashed detour on the right. Themed through the page's CSS variables."""
    X, W, TX, TW = 24, 560, 640, 340          # main column, detour column
    PAD, LINE, SVGW = 20, 21, 1004
    out, y = [], 16

    def box(name, x, w, y, dashed=False):
        c = cmds[name]
        chars = (w - 2 * PAD) // 7.6
        desc = wrap(c['description'], int(chars))
        who = c['personas'] or []
        who_lines, cur = [], []
        for p in who:                          # persona names wrap as units
            if cur and len(', '.join(cur + [p])) + 5 > (w - 2 * PAD) // 7.9:
                who_lines.append(cur)
                cur = []
            cur.append(p)
        if cur:
            who_lines.append(cur)
        h = PAD + 24 + len(desc) * LINE + 8 + max(1, len(who_lines)) * LINE + LINE + PAD - 6
        fill = 'var(--sunk)' if dashed else 'var(--surface)'
        dash = ' stroke-dasharray="7 5"' if dashed else ''
        stroke = 'var(--ink-3)' if dashed else 'var(--brand)'
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" stroke="{stroke}" '
                   f'stroke-width="1.5"{dash}/>')
        ty = y + PAD + 16
        out.append(f'<text x="{x + PAD}" y="{ty}" class="f-cmd">/{e(name)}</text>')
        ty += 8
        for line in desc:
            ty += LINE
            out.append(f'<text x="{x + PAD}" y="{ty}" class="f-desc">{e(line)}</text>')
        ty += 8
        if who_lines:
            for i, group in enumerate(who_lines):
                ty += LINE
                spans = []
                for j, p in enumerate(group):
                    cls = 'f-write' if p in writers else 'f-read'
                    sep = ', ' if j < len(group) - 1 or i < len(who_lines) - 1 else ''
                    spans.append(f'<tspan class="{cls}">{e(p)}</tspan>{e(sep)}')
                lead = '<tspan class="f-label">Who </tspan>' if i == 0 else '<tspan class="f-label">    </tspan>'
                out.append(f'<text x="{x + PAD}" y="{ty}" class="f-who">{lead}{"".join(spans)}</text>')
        else:
            ty += LINE
            out.append(f'<text x="{x + PAD}" y="{ty}" class="f-who"><tspan class="f-label">Who </tspan>'
                       f'<tspan class="f-read">the session itself</tspan></text>')
        ty += LINE
        out.append(f'<text x="{x + PAD}" y="{ty}" class="f-out"><tspan class="f-label">Leaves </tspan>'
                   f'{e(STAGE_OUTPUT.get(name, ""))}</text>')
        return h

    def arrow(x, y1, y2, label=None, dashed=False):
        dash = ' stroke-dasharray="6 5"' if dashed else ''
        out.append(f'<line x1="{x}" y1="{y1}" x2="{x}" y2="{y2 - 2}" class="f-edge"{dash} marker-end="url(#f-arw)"/>')
        if label:
            out.append(f'<text x="{x + 12}" y="{(y1 + y2) / 2 + 5}" class="f-edge-label">{e(label)}</text>')

    cx = X + W / 2
    edge_label = {'spec': 'draft spec', 'plan': 'draft plan', 'build': 'candidate commits',
                  'ship': 'GO and rollback plan'}
    after_gate = {'spec': 'approved spec', 'plan': 'approved plan', 'ship': None}
    main = [n for n in PIPELINE if n in cmds and n not in CONDITIONAL]
    boxes = {}
    for i, name in enumerate(main):
        h = box(name, X, W, y)
        boxes[name] = (y, h)
        y += h
        nxt = main[i + 1] if i + 1 < len(main) else None
        if name in HUMAN_GATE_AFTER:
            arrow(cx, y, y + 34, edge_label.get(name))
            gy = y + 34 + 15
            out.append(f'<rect x="{cx - 13}" y="{gy - 13}" width="26" height="26" fill="var(--gate-bg)" '
                       f'stroke="var(--gate)" stroke-width="2" transform="rotate(45 {cx} {gy})"/>')
            out.append(f'<text x="{cx + 32}" y="{gy + 5}" class="f-gate">You decide: {e(HUMAN_GATE_AFTER[name])}</text>')
            y = gy + 15
            if nxt:
                arrow(cx, y, y + 34, after_gate.get(name))
                y += 34
        elif nxt:
            gap = 46
            if name == 'review' and 'test' in cmds and 'test' in CONDITIONAL:
                ty0 = boxes['review'][0] + boxes['review'][1] + 30
                th = box('test', TX, TW, ty0, dashed=True)
                boxes['test'] = (ty0, th)
                gap = max(gap, ty0 + th + 40 - y)
                ry = boxes['review'][0] + boxes['review'][1] - 30
                out.append(f'<path d="M{X + W},{ry} H{TX + TW / 2} V{ty0 - 2}" fill="none" class="f-edge" '
                           f'stroke-dasharray="6 5" marker-end="url(#f-arw)"/>')
                out.append(f'<text x="{X + W + 12}" y="{ry - 8}" class="f-edge-label">if /review requires it</text>')
                boxes['_test_join'] = ty0 + th
            arrow(cx, y, y + gap, 'findings and evidence' if name == 'review' else edge_label.get(name))
            y += gap
    if '_test_join' in boxes and 'ship' in boxes:
        sy, sh = boxes['ship']
        jy = sy + 34
        out.append(f'<path d="M{TX + TW / 2},{boxes["_test_join"]} V{jy} H{X + W + 2}" fill="none" class="f-edge" '
                   f'stroke-dasharray="6 5" marker-end="url(#f-arw)"/>')
        out.append(f'<text x="{TX + TW / 2 + 12}" y="{(boxes["_test_join"] + jy) / 2 + 5}" '
                   f'class="f-edge-label">VERIFY PASS</text>')
    height = y + 16
    svg = (f'<svg viewBox="0 0 {SVGW} {height}" role="img" aria-label="The pipeline from /spec to /ship: each '
           'stage, who runs it and what it leaves behind, with the three human decisions and the conditional '
           '/test detour.">'
           '<defs><marker id="f-arw" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" '
           'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="var(--ink-2)"/></marker></defs>'
           + ''.join(out) + '</svg>')
    return ('<figure class="panel flow">' + '<div class="flow-scroll">' + svg + '</div>'
            '<figcaption>Every arrow names what it carries. Nothing reaches the next stage past an orange diamond '
            'until you decide; /test runs only when /review requires it, and /ship then needs its VERIFY PASS.'
            '</figcaption></figure>')


# The harness's shared vocabulary. Each entry names the file that defines it
# and the exact text that must still appear there; render() fails when it does
# not, so a renamed marker cannot leave this page describing the old one.
# The task, decision and checkpoint ids come from plan-quality-gates.md §3.
CONVENTIONS = [
    ('Ids', '`ws-<name>`', 'A workstream in the plan, e.g. `ws-main`', '/plan', 'references/templates/plan.md', 'ws-'),
    ('Ids', '`SEC-#`', 'A security finding', 'security-auditor', 'agents/security-auditor.md', 'SEC-'),
    ('Ids', '`DIST-#`', 'A retries, ordering or concurrency finding', 'distributed-systems-reviewer', 'agents/distributed-systems-reviewer.md', 'DIST-'),
    ('Ids', '`BLIND-#`', 'A finding from the review that never saw the goal', 'blind-reviewer', 'agents/blind-reviewer.md', 'BLIND-'),
    ('Ids', '`NNNN-title.md`', 'An architecture decision, 4-digit, never renumbered', 'you', 'skills/adr-recording/SKILL.md', 'NNNN'),
    ('Ids', '`~~T003~~ superseded by T007`', 'A dropped task keeps its id; the next one takes a new number', '/plan', 'references/plan-quality-gates.md', 'superseded by'),
    ('Ids', 'marked withdrawn', 'A withdrawn requirement keeps its id', '/spec', 'references/spec-quality-gates.md', 'marked withdrawn'),
    ('Fixed forms', '`### Requirement: REQ-001 — Title`', 'One requirement, followed by a `Source:` line', '/spec', 'references/templates/spec.md', '### Requirement: REQ-'),
    ('Fixed forms', '`#### Scenario: Name`', 'One case, written as GIVEN / WHEN / THEN', '/spec', 'references/templates/spec.md', '#### Scenario:'),
    ('Fixed forms', '`**Files/areas likely touched:**`', 'The places a task changes; plan recall reads this list', '/plan', 'references/templates/task.md', '**Files/areas likely touched:**'),
    ('Fixed forms', '`**Change-surface search:**`', 'The search that finds every consumer; /build reruns it', '/plan', 'references/templates/task.md', '**Change-surface search:**'),
    ('Fixed forms', '`path` — unchanged — reason', 'A place checked and deliberately left alone', '/plan', 'references/templates/task.md', 'unchanged — '),
    ('Fixed forms', '`MUST` / `SHOULD` / `MAY`', 'RFC 2119 obligation in a requirement; a SHOULD names its exception, a MAY needs no evidence', '/spec', 'skills/spec-driven-development/SKILL.md', 'RFC 2119'),
    ('Fixed forms', '`When <trigger>, the <system> MUST <response>.`', 'A requirement statement in an EARS pattern: ubiquitous, While, When, Where, If … then, or combined', '/spec', 'references/templates/spec.md', 'EARS pattern'),
    ('Fixed forms', '`Refs: LD-442` / `Task: T002`', 'Git trailers ending a ticket commit; `recall.py --trailer-only` reads `Refs:`', 'executor', 'skills/git-workflow-and-versioning/SKILL.md', '### Ticket trailers'),
    ('Fixed forms', '`<type>[scope]: <description>`', 'Commit subject when the repository has no convention of its own', 'executor', 'skills/git-workflow-and-versioning/SKILL.md', 'use Conventional Commits'),
    ('Fixed forms', '`path.md` §Section, `test-engineer` §6', 'A reference to a section; CI fails when the heading is gone', 'every file', '../tools/checks/check-references.py', 'NAMED = re.compile'),
    ('Fixed forms', 'One instruction per sentence, 20 words or fewer', 'Prose a person reads: active voice, one word for one thing, steps in a list, result first; `check-writing.py` measures ADR sentences', 'every stage', 'AGENTS.md', 'ASD-STE100'),
    ('Fixed forms', '`file:line`', 'How evidence and findings point at code', 'reviewers', 'agents/blind-reviewer.md', 'file:line'),
    ('Status words', 'Draft / Approved / Needs reapproval / Superseded', 'Spec header; only a human sets Approved', '/spec', 'references/spec-quality-gates.md', 'Needs reapproval'),
    ('Status words', 'New / Modify / Remove / Rename / Bugfix', 'Spec `Change kind`', '/spec', 'references/templates/spec.md', 'Change kind:'),
    ('Status words', 'Pending / Done', 'Task status in the todo; flipped to Done in the commit that finishes it', 'executor', 'references/templates/task.md', '**Status:** Pending'),
    ('Status words', 'BUILD COMPLETE / BUILD BLOCKED', 'The /build result', '/build', 'commands/build.md', 'BUILD COMPLETE'),
    ('Status words', 'VERIFY PASS / FAIL / BLOCKED', 'The /test result', '/test', 'commands/test.md', 'VERIFY BLOCKED'),
    ('Status words', 'BLOCKER / REQUIRED / ADVISORY', 'How serious a review finding is: the reviewer sets it, /ship decides on it', 'reviewers', 'references/component-response-contracts.md', '#### Dispositions'),
    ('Status words', 'killed / survived', 'A mutation probe: a surviving mutant is a missing test', 'test-engineer', 'agents/test-engineer.md', 'has survived'),
    ('Status words', 'Weakened tests: none found / Not verified', 'The /review result of the weakened-test guard', '/review', 'commands/review.md', 'Weakened tests: none found'),
    ('Status words', 'GO / NO-GO / SHIP BLOCKED', 'The /ship decision', '/ship', 'commands/ship.md', 'SHIP BLOCKED'),
    ('Status words', 'Open / Mitigated / Fixed — <check>', 'A failure row in the observation log; Fixed names the check that catches it', 'you', '../docs/observation-log.md', 'Fixed — <check>'),
    ('Flags', '`OPEN QUESTION:` block', 'A choice that is yours; the spec cannot be approved while one remains', '/spec', 'skills/spec-driven-development/SKILL.md', 'OPEN QUESTION:'),
    ('Flags', '`SPEC CONFLICT`', 'The spec promises what the code or plan cannot deliver; back to /spec', '/plan, /build', 'commands/plan.md', 'SPEC CONFLICT'),
    ('Flags', 'Not surveyed', 'Not looked at, so not known', 'repo-recon, /spec', 'references/repository-precedent.md', 'Not surveyed'),
    ('Flags', 'No precedent found for', 'Looked at; the repository gives no guidance', 'repo-recon, /spec', 'references/repository-precedent.md', 'No precedent found for'),
    ('Flags', 'Not verified', 'A check that did not run; never read as "works"', 'personas', 'agents/code-reviewer.md', 'Not verified'),
    ('Flags', '`Needs real-browser check: REQ-x — …`', 'Browser behavior the executor cannot prove; /test does it', 'executor', 'commands/build.md', 'Needs real-browser check'),
    ('Flags', '`Handoff:`', 'The last line of a stage, naming the next one', 'each stage', 'references/templates/plan.md', 'Handoff:'),
    ('Paths', '`docs/specs/[TICKET]-SPEC.md`', 'The one spec per ticket; any other spelling fails CI', '/spec', 'references/templates/plan.md', 'docs/specs/[TICKET]-SPEC.md'),
    ('Paths', '`docs/tasks/[TICKET]-plan.md`, `-todo.md`', 'The plan and its task packets', '/plan', 'references/templates/plan.md', 'docs/tasks/[TICKET]-'),
    ('Paths', '`.git/explain/<TICKET>-<sha>.html`', 'An /explain review page, outside the working tree', '/explain', 'commands/explain.md', 'git-common-dir)/explain/'),
    ('Paths', '`.git/review/<TICKET>-<sha>.sarif`', 'The review findings as SARIF 2.1.0; disposition decides the level (error / warning / note)', '/review', 'commands/review.md', 'git-common-dir)/review/'),
]
# Where a convention comes from, when it is an outside standard rather than
# the harness's own; keyed by the marker shown in CONVENTIONS.
ORIGIN = {
    '`NNNN-title.md`': 'Nygard ADRs, MADR-style numbering',
    '`### Requirement: REQ-001 — Title`': 'OpenSpec (ADR 0040)',
    '`#### Scenario: Name`': 'Gherkin / BDD, via OpenSpec',
    '`MUST` / `SHOULD` / `MAY`': 'RFC 2119, RFC 8174',
    '`When <trigger>, the <system> MUST <response>.`': 'EARS (Mavin et al., 2009)',
    '`Refs: LD-442` / `Task: T002`': 'git trailers',
    '`<type>[scope]: <description>`': 'Conventional Commits 1.0',
    'One instruction per sentence, 20 words or fewer': 'ASD-STE100 (its rules, not its dictionary)',
    '`file:line`': 'GNU error-message format',
    '`.git/review/<TICKET>-<sha>.sarif`': 'SARIF 2.1.0 (OASIS)',
    'killed / survived': 'Mutation testing',
}
# Seen in the target projects' history, not defined by any harness file.
OBSERVED = [
    ('`feat(area): … (LD-442 T002)`', 'Commit subject: conventional type, then ticket and task id. Older history; `recall.py --subject-only` reads it. New commits use the `Refs:` trailer.'),
    ('`(LD-442 review R-04)`', 'Review fix commits numbered by the review run; no reviewer file defines `R-##`.'),
]


def id_table():
    """Rows of plan-quality-gates.md §3, the owner table for REQ, DEC, TD, T and CP."""
    text = read(CLAUDE / 'references/plan-quality-gates.md')
    section = text.split('## 3.', 1)[1].split('\n## ', 1)[0]
    rows = []
    for line in section.splitlines():
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) == 4 and cells[0].startswith('`') and cells[0] != '`Id`':
            rows.append(cells)
    if not rows:
        raise SystemExit('harness-map: plan-quality-gates.md §3 id table not found')
    return rows


def conventions():
    """CONVENTIONS, each checked against the file that defines it."""
    missing = [f'{src}: {needle!r}' for _, _, _, _, src, needle in CONVENTIONS
               if needle not in read((CLAUDE / src).resolve())]
    missing += [f'ORIGIN key not in CONVENTIONS: {k}' for k in ORIGIN if k not in {c[1] for c in CONVENTIONS}]
    if missing:
        raise SystemExit('harness-map: conventions no longer found in their source:\n  ' + '\n  '.join(missing))
    return CONVENTIONS


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

    ids = id_table()
    conv = conventions()
    sections = [('pipeline', 'Pipeline', len([n for n in PIPELINE if n in cmds])),
                ('personas', 'Personas', len(persona_rows)), ('guards', 'Guards', len(hook_rows)),
                ('conventions', 'Conventions', len(ids) + len(conv)),
                ('session', 'Session setup', len(rules)), ('skills', 'Skills', len(skill_rows)),
                ('references', 'References', len(ref_rows)), ('ci', 'Self-tests', len(steps)),
                ('decisions', 'Decisions', len(adr_rows))]

    out = ['<!doctype html>', '<html lang="en">', '<head>', '<meta charset="utf-8">',
           '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">',
           '<title>Harness Map</title>',
           '<!-- Generated by dotfiles/tools/checks/harness-map.py. Do not edit by hand; CI fails when this page is stale. -->',
           '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@100..125,700..800&family=Hanken+Grotesk:wght@400;600;700;800&family=JetBrains+Mono:wght@400;700&display=swap">',
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
               'The orange rows are decisions only you make.</p></div>'
               '<div class="legend"><span><i class="diamond"></i>you decide</span>'
               '<span><span class="persona-name write">blue</span> can change files</span>'
               '<span><span class="persona-name">teal</span> read-only</span>'
               '<span><span class="badge cond">dashed</span> only when needed</span></div>')
    views = {'list': ('1', 'Stage list', pipeline_list),
             'strip': ('2', 'Strip', pipeline_strip),
             'flow': ('3', 'Flowchart', pipeline_flow)}
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
        note = ''
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
            access += f' <span class="badge plain">{e(p["isolation"])}</span>'
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

    # Conventions
    out.append('<section id="conventions"><div class="sec-head"><h2>Conventions</h2>'
               '<p class="summary">The ids, fixed forms, status words and flags every stage reads and writes. '
               'Each names the file that defines it; this page fails to build if one disappears from there.</p>'
               '</div><div class="panel tablewrap"><table><thead><tr><th>Convention</th><th>Means</th>'
               '<th>Owner</th><th>Defined in</th><th>Origin</th></tr></thead><tbody>')
    out.append('<tr><td class="group" colspan="5">Ids<span>never renumbered; one owner each</span></td></tr>')
    for ident, lives, owner, meaning in ids:
        out.append(f'<tr><td class="cmdcell nowrap">{e(ident)}</td><td>{e(meaning)} <span class="sub">in the {e(lives)}</span></td>'
                   f'<td class="cmdcell">{e(owner)}</td><td class="cmdcell">references/plan-quality-gates.md</td>'
                   f'<td><span class="sub">Harness</span></td></tr>')
    group = 'Ids'
    for grp, marker, meaning, owner, src, _ in conv:
        if grp != group:
            out.append(f'<tr><td class="group" colspan="5">{e(grp)}</td></tr>')
            group = grp
        shown = src.replace('../docs/', 'dotfiles/docs/').replace('../tools/', 'dotfiles/tools/')
        origin = e(ORIGIN[marker]) if marker in ORIGIN else '<span class="sub">Harness</span>'
        out.append(f'<tr><td class="cmdcell">{e(marker)}</td><td>{e(meaning)}</td><td class="cmdcell">{e(owner)}</td>'
                   f'<td class="cmdcell">{e(shown)}</td><td>{origin}</td></tr>')
    out.append('<tr><td class="group" colspan="5">Seen in project history<span>not defined by the harness</span></td></tr>')
    for marker, meaning in OBSERVED:
        out.append(f'<tr><td class="cmdcell">{e(marker)}</td><td colspan="4">{e(meaning)}</td></tr>')
    out.append('</tbody></table></div></section>')

    # Session setup
    env = settings.get('env', {})
    pins = [(k, v) for k, v in sorted(env.items()) if k.startswith('CLAUDE_CODE_')]
    sandbox = settings.get('sandbox', {})
    perms = settings.get('permissions', {})
    read_denied = [r for r in perms.get('deny', []) if r.startswith('Read(')]
    defaults = [
        ('model', settings.get('model', '—')),
        ('effortLevel', settings.get('effortLevel', '—')),
        ('advisorModel', settings.get('advisorModel', '—')),
        ('modelSettings', ', '.join(f'{k} → {v.get("effortLevel", v)}' if isinstance(v, dict) else f'{k} → {v}'
                                    for k, v in sorted(settings.get('modelSettings', {}).items())) or '—'),
        ('permissions', f'{perms.get("defaultMode", "default")} · {len(perms.get("allow", []))} allow · '
                        f'{len(perms.get("deny", []))} deny'),
        ('sandbox', f'{"on" if sandbox.get("enabled") else "off"} (adr 0085) · '
                    f'{len(read_denied)} credential files denied to Read'),
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
        badge = '<span class="badge gate">explicit</span>' if is_explicit else '<span class="badge plain">on match</span>'
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
    out.append('''<script>
(function () {
  var tabs = Array.prototype.slice.call(document.querySelectorAll('[role="tab"]'));
  function show(key, focus) {
    tabs.forEach(function (tab) {
      var on = tab.dataset.view === key;
      tab.setAttribute('aria-selected', on ? 'true' : 'false');
      tab.tabIndex = on ? 0 : -1;
      document.getElementById('view-' + tab.dataset.view).hidden = !on;
      if (on && focus) { tab.focus(); }
    });
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
