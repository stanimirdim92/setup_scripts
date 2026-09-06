#!/usr/bin/env python3
"""Install the Codex adapters without copying their shared Claude sources."""

import argparse
import os
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dest", type=Path, default=Path.home() / ".agents" / "skills",
        help="skill directory (default: ~/.agents/skills)",
    )
    parser.add_argument("--check", action="store_true", help="check links without changing files")
    args = parser.parse_args()
    source = Path(__file__).resolve().parent / "skills"
    skills = sorted(path.parent for path in source.glob("*/SKILL.md"))
    if not skills:
        parser.exit(1, f"No skill adapters found in {source}\n")

    destination = args.dest.expanduser().absolute()
    missing = []
    errors = []
    for skill in skills:
        link = destination / skill.name
        if not os.path.lexists(link):
            missing.append((link, skill))
        elif not link.is_symlink() or link.resolve() != skill:
            errors.append(f"Refusing to replace existing path: {link}")

    # Preflight the whole set before creating anything.
    if errors:
        parser.exit(1, "\n".join(errors) + "\n")
    if args.check and missing:
        parser.exit(1, "\n".join(f"Missing: {link}" for link, _ in missing) + "\n")
    if not args.check:
        destination.mkdir(parents=True, exist_ok=True)
        for link, skill in missing:
            link.symlink_to(skill, target_is_directory=True)

    for skill in skills:
        print(f"OK {destination / skill.name} -> {skill}")
    print(f"{len(skills)} skill links verified. Invoke a skill by its $name in Codex.")


if __name__ == "__main__":
    try:
        main()
    except OSError as error:
        print(f"Installation failed: {error}", file=sys.stderr)
        sys.exit(1)
