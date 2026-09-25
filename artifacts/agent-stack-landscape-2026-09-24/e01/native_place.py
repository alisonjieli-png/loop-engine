#!/usr/bin/env python3
"""Baltor's native placement engine for the E01 pilot.

Places every file of one package, byte for byte, at the Claude Code and Codex
native skill roots through the repository's confined writer
(tools/install_selected_material.py: write_confined_file). The writer never
follows a link, never replaces a different existing file and creates files
with mode 0644. It serves single bodies today; walking a package folder here
is the pilot's own loop around the same writer, not a shipped feature.

Usage: native_place.py <package_dir> <project_dir> <native_name>
"""
import os
import sys
from pathlib import Path

import install_selected_material as m

PROFILES = (m.CLAUDE_CODE_PROFILE, m.CODEX_PROFILE)


def main():
    package, project, name = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    files = sorted(p for p in package.rglob("*") if p.is_file())
    written = 0
    for profile in PROFILES:
        location = profile.location_for("skill")
        for path in files:
            rel = path.relative_to(package).parts
            parts = (*location.directory_segments, name, *rel)
            if m.write_confined_file(project, parts, path.read_bytes()):
                written += 1
    print(f"placed {written} files for {len(PROFILES)} clients")


if __name__ == "__main__":
    try:
        main()
    except m.InstallRefusal as refusal:
        print(f"refused: {refusal.code.value} {refusal.detail}", file=sys.stderr)
        sys.exit(3)
