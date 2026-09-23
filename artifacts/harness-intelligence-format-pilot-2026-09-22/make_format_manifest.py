"""Bind exact bytes of heterogeneous, candidate-only harness files.

The manifest inventories source and review files under context/, tools/,
and connections/. It does not classify runtime effects, approve an item,
or copy any file into a real harness. Generated caches and symlinks are
refused so a later admission step cannot silently package them.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "manifest.json"
GROUPS = ("connections", "context", "tools")
FORBIDDEN_DIRECTORIES = frozenset({
    "__pycache__", ".pytest_cache", ".venv", "venv", "node_modules",
    "source", "snapshot", "tmp", "home", "dist", "build",
})
MAX_FILE_BYTES = 500_000
MAX_FILES = 10_000
RECORD_TYPE = "heterogeneous_harness_candidate_file_manifest/v1"


def inventory(root: Path = ROOT) -> list[dict]:
    if root.is_symlink() or not root.is_dir():
        raise ValueError("candidate root missing or symlinked")
    entries = []
    for group in GROUPS:
        folder = root / group
        if folder.is_symlink() or not folder.is_dir():
            raise ValueError(f"candidate group missing or symlinked: {group}")
        for current, directories, files in os.walk(folder, followlinks=False):
            current_path = Path(current)
            for directory in directories:
                child = current_path / directory
                if directory in FORBIDDEN_DIRECTORIES or child.is_symlink():
                    raise ValueError(f"generated, runtime, or symlinked folder refused: {child}")
            for filename in files:
                path = current_path / filename
                if path.is_symlink() or not path.is_file():
                    raise ValueError(f"symlinked or nonregular file refused: {path}")
                if filename.endswith((".pyc", ".pyo", ".log", ".key", ".pem")):
                    raise ValueError(f"generated or secret-like file refused: {path}")
                raw = path.read_bytes()
                if not raw or len(raw) > MAX_FILE_BYTES:
                    raise ValueError(f"empty or overlarge candidate file: {path}")
                entries.append({
                    "group": group,
                    "path": path.relative_to(root).as_posix(),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "bytes": len(raw),
                })
                if len(entries) > MAX_FILES:
                    raise ValueError("candidate file count exceeds offline limit")
    return sorted(entries, key=lambda item: item["path"])


def render(base_revision: str, root: Path = ROOT) -> str:
    if not re.fullmatch(r"[0-9a-f]{40}", base_revision):
        raise ValueError("base revision must be a full Git object ID")
    entries = inventory(root)
    return json.dumps({
        "record_type": RECORD_TYPE,
        "prepared_from_repository_revision": base_revision,
        "approval_state": "none",
        "rights_state": "pending_independent_review",
        "effect_qualification": "none",
        "native_load": "unqualified",
        "physical_file_count": len(entries),
        "logical_package_count": "not_inferred_from_files",
        "entries": entries,
    }, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--write", action="store_true")
    choice.add_argument("--check", action="store_true")
    parser.add_argument("--base-revision")
    args = parser.parse_args()
    try:
        if args.write:
            if not args.base_revision:
                raise ValueError("--write requires --base-revision")
            rendered = render(args.base_revision)
            temporary = MANIFEST.with_suffix(".json.tmp")
            temporary.write_text(rendered, encoding="utf-8")
            temporary.replace(MANIFEST)
            print(f"wrote {MANIFEST}")
        else:
            if args.base_revision:
                raise ValueError("--base-revision applies only to --write")
            stored = json.loads(MANIFEST.read_text(encoding="utf-8"))
            if stored.get("record_type") != RECORD_TYPE:
                raise ValueError("unsupported candidate manifest")
            expected = render(stored["prepared_from_repository_revision"])
            if MANIFEST.read_text(encoding="utf-8") != expected:
                raise ValueError("candidate manifest differs from exact current files")
            print(f"checked {stored['physical_file_count']} candidate source and review files")
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        parser.exit(1, f"mixed-format manifest refused: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
