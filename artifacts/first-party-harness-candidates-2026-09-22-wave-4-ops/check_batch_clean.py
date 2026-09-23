"""Check candidate bytes and refuse generated caches anywhere in this batch.

The shared exact-byte manifest inventories native skills and review notes.
This wrapper adds a whole-batch cache and symlink check; neither kind is a
candidate or an allowed source artifact.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SHARED_MANIFEST_TOOL = ROOT.parent / "first-party-harness-candidates-2026-09-22" / "make_manifest.py"


def check(root: Path) -> None:
    if root.is_symlink() or not root.is_dir():
        raise ValueError("batch root is missing or symlinked")
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"symlink in candidate batch: {path}")
        if path.name == "__pycache__" or path.suffix == ".pyc":
            raise ValueError(f"generated cache in candidate batch: {path}")
    result = subprocess.run(
        [sys.executable, "-B", str(SHARED_MANIFEST_TOOL), "--check", "--root", str(root)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        raise ValueError(result.stderr.strip() or result.stdout.strip())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        check(args.root.absolute())
    except ValueError as error:
        parser.exit(1, f"candidate batch refused: {error}\n")
    print(f"checked candidate manifest and no generated caches in {args.root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
