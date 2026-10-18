#!/usr/bin/env python3
"""Fixture tests for dotfiles/tools/agent_sessions_mcp.py (--serve dashboard).

The dashboard hands the user a "Copy resume" command to paste into a shell.
The session folder and id come from transcript files, so they are untrusted:
the command must run the same program whatever those values contain.

Each test serves a fake HOME with one session and asks the real HTTP API for
its command. The command then runs in real bash with a stub `claude`."""
import http.client
import importlib.util
import json
import os
import socket
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'agent_sessions_mcp.py'
FAKE_HOME = tempfile.TemporaryDirectory()
os.environ['AGENT_SESSIONS_HOME'] = FAKE_HOME.name
spec = importlib.util.spec_from_file_location('asm', SCRIPT)
asm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(asm)

GOOD_ID = '3f2b8c1e-0d4a-4c55-9a7e-1b2c3d4e5f60'
STUB = '#!/usr/bin/env bash\nprintf "PWD=%s ARGS=%s\\n" "$PWD" "$*"\n'


def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def start_server():
    port = free_port()
    threading.Thread(target=asm.serve, args=('127.0.0.1', port), daemon=True).start()
    for _ in range(100):
        try:
            socket.create_connection(('127.0.0.1', port), timeout=0.1).close()
            return port
        except OSError:
            time.sleep(0.05)
    raise RuntimeError('dashboard did not start')


PORT = start_server()


def get(path, headers=None):
    c = http.client.HTTPConnection('127.0.0.1', PORT, timeout=5)
    c.request('GET', path, headers=headers or {})
    r = c.getresponse()
    return r.status, r.read().decode('utf-8')


def write_session(cwd, sid):
    proj = Path(FAKE_HOME.name) / '.claude' / 'projects' / 'p'
    proj.mkdir(parents=True, exist_ok=True)
    for old in proj.glob('*.jsonl'):
        old.unlink()
    line = {'type': 'user', 'sessionId': sid, 'cwd': str(cwd), 'message': {'content': 'hello'}}
    (proj / 'session.jsonl').write_text(json.dumps(line) + '\n', encoding='utf-8')


def session_command(cwd, sid):
    write_session(cwd, sid)
    status, body = get('/api/sessions')
    assert status == 200, status
    return json.loads(body)['sessions'][0].get('resume')


class ResumeCommand(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.start = self.root / 'start'
        self.start.mkdir()
        bindir = self.root / 'bin'
        bindir.mkdir()
        (bindir / 'claude').write_text(STUB)
        (bindir / 'claude').chmod(0o755)
        self.env = dict(os.environ, PATH=f'{bindir}{os.pathsep}{os.environ["PATH"]}')

    def tearDown(self):
        self.tmp.cleanup()

    def paste(self, command):
        """Run a copied command in bash, from a folder with no marker files."""
        return subprocess.run(['bash', '-c', command], cwd=self.start, env=self.env,
                              capture_output=True, text=True)

    def markers(self):
        return sorted(p.name for p in self.root.rglob('MARK*'))

    def check_folder(self, name):
        target = self.root / name
        target.mkdir()
        command = session_command(target, GOOD_ID)
        self.assertIsNotNone(command)
        out = self.paste(command)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout, f'PWD={target} ARGS=--resume {GOOD_ID}\n')
        self.assertEqual(self.markers(), [])

    def test_plain_folder_resumes_in_that_folder(self):
        self.check_folder('project')

    def test_dollar_substitution_in_folder_is_not_run(self):
        self.check_folder('project-$(touch MARK_SUBST)')

    def test_backticks_in_folder_are_not_run(self):
        self.check_folder('project-`touch MARK_TICK`')

    def test_single_quote_in_folder(self):
        self.check_folder("it's")

    def test_double_quote_in_folder(self):
        self.check_folder('say "hi"')

    def test_spaces_in_folder(self):
        self.check_folder('my project dir')

    def test_newline_in_folder(self):
        self.check_folder('first\ntouch MARK_NEWLINE')

    def test_session_id_with_shell_syntax_gets_no_command(self):
        target = self.root / 'project'
        target.mkdir()
        self.assertIsNotNone(session_command(target, GOOD_ID))
        for bad in ('x; touch MARK_ID', 'x$(touch MARK_ID)', 'x`touch MARK_ID`', "x' y", 'x y', '-rf'):
            with self.subTest(sid=bad):
                self.assertIsNone(session_command(target, bad))
        self.assertEqual(self.markers(), [])


if __name__ == '__main__':
    unittest.main()
