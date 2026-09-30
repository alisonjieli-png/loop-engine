"""Prepare original creative components through the existing native factory.

No external source is copied, no model is called and nothing is approved or
published. The factory refuses a changed or uncommitted source revision.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

if __name__ == "__main__" and __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from tools.build_creative_components import main
    raise SystemExit(main())

from tools.creative_components.packaging import json_bytes, proposals
from tools.prepare_harness_candidates import (
    PreparationRequest,
    _validated_sources,
    prepare,
)


def build(repository, folder, *, authorized=False, proposal_factory=None):
    repository, folder = Path(repository).resolve(), Path(folder).absolute()
    if not authorized:
        raise ValueError("preparation is not authorized")
    if folder == repository or repository in folder.parents or folder.exists() or folder.is_symlink():
        raise ValueError("use a new run folder outside the repository")
    if folder.resolve() != folder or not folder.parent.is_dir():
        raise ValueError("run folder must have an existing, non-symlink parent")
    revision = subprocess.run(["git", "-C", str(repository), "rev-parse", "HEAD"],
                              check=True, capture_output=True, text=True).stdout.strip()
    record = (proposal_factory or proposals)(repository, revision)
    _validated_sources(repository, record)
    folder.mkdir(mode=0o700)
    request_file = folder / "proposals.json"
    request_file.write_bytes(json_bytes(record))
    return prepare(PreparationRequest(repository, request_file, folder / "candidates", True))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repository", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--run-folder", type=Path, required=True)
    parser.add_argument("--authorize-preparation", action="store_true")
    args = parser.parse_args(argv)
    print(json.dumps(build(args.repository, args.run_folder, authorized=args.authorize_preparation), indent=2))
    return 0
