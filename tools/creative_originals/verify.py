"""Run a family's native verifier over its items and write one evidence record per item.

    PYTHONPATH=src:. python -m tools.creative_originals.verify --family godot_shaders \
        --output /run/media/username/baltor-offload/creative-3d-20261009/evidence [--item ID ...] [--jobs 3]

The family's ``native.py`` defines ``verify(context) -> {"engine": dict, "checks": [...], "preview": bytes|None}``.
``context`` carries family, item, family_dir, item_dir, shared_dir, workspace (an empty folder of its own) and the
engines module. A record binds the item digest (every item and shared byte), so editing an item makes its old record
stale; an unchanged item's record is reused unless --force. A verifier that raises produces a failed record with the
error, never a pass. Records carry no time stamp: the same bytes and engine give the same record.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import importlib.util
import json
import shutil
import sys
import traceback
from pathlib import Path
from types import SimpleNamespace

from . import engines
from .assemble import item_digest, json_bytes
from .pngio import PngError, decode
from .records import EVIDENCE_RECORD, FAILED, PASSED, CreativeRecordError, item_identities, read_family, read_item

ROOT = Path(__file__).resolve().parent


def _verifier(family_directory: Path, family: dict):
    path = family_directory / family["native_verifier"]
    specification = importlib.util.spec_from_file_location(f"creative_native_{family['family']}", path)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    if not callable(getattr(module, "verify", None)):
        raise CreativeRecordError("native_verifier_invalid", f"{path} defines no verify(context)")
    return module


def verify_item(family_directory: Path, family: dict, module, identity: str, output: Path, force: bool) -> dict:
    target = output / family["family"] / f"{identity}.json"
    try:
        item = read_item(family_directory, identity, family)
        digest = item_digest(family_directory, identity, family, item)
    except CreativeRecordError as error:
        return {"identity": identity, "state": "item_invalid", "reason": error.reason, "detail": error.detail}
    if target.is_file() and not force:
        try:
            previous = json.loads(target.read_text())
            if previous.get("item_digest") == digest:
                return {"identity": identity, "state": previous["state"], "reused": True}
        except (OSError, ValueError):
            pass
    workspace = output / "work" / family["family"] / identity
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)
    context = SimpleNamespace(family=family, item=item, family_dir=family_directory,
                              item_dir=family_directory / "items" / identity, shared_dir=family_directory / "shared",
                              workspace=workspace, engines=engines)
    preview, preview_record = None, None
    try:
        result = module.verify(context)
        checks = list(result["checks"])
        engine = dict(result["engine"])
        preview = result.get("preview")
        if preview is not None:
            image = decode(preview)
            preview_record = {"path": "preview.png", "sha256": hashlib.sha256(preview).hexdigest(),
                              "width": image["width"], "height": image["height"]}
    except PngError as error:
        checks, engine = [{"name": "preview_png", "state": FAILED, "detail": {"reason": error.reason}}], {}
        preview = None
    except Exception as error:  # a verifier bug is recorded as a failure, never a pass
        checks = [{"name": "verifier_error", "state": FAILED,
                   "detail": {"error": f"{type(error).__name__}: {error}"[:600],
                              "trace": traceback.format_exc()[-1500:]}}]
        engine, preview = {}, None
    for check in checks:
        if not isinstance(check, dict) or set(check) != {"name", "state", "detail"} or check["state"] not in (
                PASSED, FAILED):
            checks = [{"name": "verifier_output_invalid", "state": FAILED, "detail": {"check": repr(check)[:300]}}]
            preview, preview_record = None, None
            break
    state = PASSED if checks and all(check["state"] == PASSED for check in checks) else FAILED
    if state != PASSED:
        preview, preview_record = None, None
    record = {"record_type": EVIDENCE_RECORD, "family": family["family"], "identity": identity, "item_digest": digest,
              "engine": engine, "checks": checks, "state": state, "preview": preview_record}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(json_bytes(record))
    image_path = target.with_suffix(".png")
    if preview is not None:
        image_path.write_bytes(preview)
    elif image_path.exists():
        image_path.unlink()
    if state == PASSED:
        shutil.rmtree(workspace, ignore_errors=True)
    return {"identity": identity, "state": state,
            "failed_checks": [check["name"] for check in checks if check["state"] != PASSED]}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--family", required=True)
    parser.add_argument("--root", type=Path, default=ROOT, help="the folder holding the families")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--item", action="append", default=[])
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    family_directory = args.root.resolve() / args.family
    family = read_family(family_directory)
    if family["native_verifier"] is None:
        print(json.dumps({"family": args.family, "state": "no_native_verifier"}))
        return 0
    module = _verifier(family_directory, family)
    identities = args.item or item_identities(family_directory)
    output = args.output.resolve()
    rows = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(args.jobs, 8))) as pool:
        futures = [pool.submit(verify_item, family_directory, family, module, identity, output, args.force)
                   for identity in identities]
        for future in concurrent.futures.as_completed(futures):
            row = future.result()
            rows.append(row)
            print(json.dumps(row), flush=True)
    rows.sort(key=lambda row: row["identity"])
    summary = {"family": args.family, "items": len(rows),
               "passed": sum(row["state"] == PASSED for row in rows),
               "failed": [row for row in rows if row["state"] != PASSED]}
    (output / args.family).mkdir(parents=True, exist_ok=True)
    (output / args.family / "SUMMARY.json").write_bytes(json_bytes(summary))
    print(json.dumps({key: summary[key] for key in ("family", "items", "passed")} | {"failed": len(summary["failed"])}))
    return 0 if not summary["failed"] else 1


if __name__ == "__main__":
    sys.exit(main())
