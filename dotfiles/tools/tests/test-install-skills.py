#!/usr/bin/env python3
"""Regression checks for Codex skill installer preflight and rollback."""

import importlib.util
from pathlib import Path
import sys
import tempfile
from unittest import mock

sys.dont_write_bytecode = True

SCRIPT = Path(__file__).resolve().parents[3] / "dotfiles" / "codex" / "install-skills.py"
SPEC = importlib.util.spec_from_file_location("install_skills", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def run(*args):
    with mock.patch.object(sys, "argv", [str(SCRIPT), *map(str, args)]):
        MODULE.main()


with tempfile.TemporaryDirectory() as temporary:
    destination = Path(temporary) / "skills"
    run("--dest", destination, "--preflight")
    assert not destination.exists(), "preflight mutated the destination"

with tempfile.TemporaryDirectory() as temporary:
    destination = Path(temporary) / "skills"
    original = Path.symlink_to
    calls = 0

    def fail_third(link, target, target_is_directory=False):
        global calls
        calls += 1
        if calls == 3:
            raise OSError("injected link failure")
        return original(link, target, target_is_directory=target_is_directory)

    with mock.patch.object(Path, "symlink_to", fail_third):
        try:
            run("--dest", destination)
        except SystemExit as error:
            assert error.code == 1
        else:
            raise AssertionError("injected failure did not fail installation")

    assert not list(destination.glob("*")), "partial adapter links survived rollback"

# A removed adapter's dangling link is cleaned up; a user's own dangling link
# elsewhere is not.
with tempfile.TemporaryDirectory() as temporary:
    destination = Path(temporary) / "skills"
    destination.mkdir()
    source = SCRIPT.parent / "skills"
    retired = destination / "retired-adapter"
    retired.symlink_to(source / "retired-adapter", target_is_directory=True)
    foreign = destination / "users-own"
    foreign.symlink_to(Path(temporary) / "gone", target_is_directory=True)
    try:
        run("--dest", destination, "--check")
    except SystemExit as error:
        assert error.code == 1
    else:
        raise AssertionError("--check passed with a retired adapter still linked")
    assert retired.is_symlink(), "--check mutated the destination"
    run("--dest", destination)
    assert not retired.is_symlink(), "retired adapter link survived installation"
    assert foreign.is_symlink(), "installer removed a link it does not own"

print("install-skills: preflight, rollback and retired-link cleanup passed")
