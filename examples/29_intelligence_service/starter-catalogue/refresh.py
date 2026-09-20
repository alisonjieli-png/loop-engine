"""Refresh the derived fields of the starter catalogue after a body was edited.

The files in ``bodies`` are the source of truth for the text, the digest and
the size of every item. This tool measures each body through the engine's own
``item_from_body`` function and rewrites only ``specifications.json`` and
``items.json`` in its own folder. It approves nothing, publishes nothing and
grants nothing. Every item stays a candidate.

Check without writing (the default), then write with explicit authority:

    PYTHONPATH=src python examples/29_intelligence_service/starter-catalogue/refresh.py
    PYTHONPATH=src python examples/29_intelligence_service/starter-catalogue/refresh.py --write
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import dataclass
import json
import os
from pathlib import Path

from loop_engine.core.harness_intelligence import HarnessIntelligenceDraft, item_from_body
from loop_engine.core.intelligence_tagging import RECORD_TYPE as TAG_RECORD_TYPE, TagSet

SPECIFICATIONS_RECORD_TYPE = "candidate_intelligence_specifications/v1"
ITEMS_RECORD_TYPE = "starter_catalogue_candidate_items/v1"
SPECIFICATIONS_FILE = "specifications.json"
ITEMS_FILE = "items.json"
BODIES_FOLDER = "bodies"
BODY_SUFFIX = ".md"


class CatalogueRefreshError(ValueError):
    """The catalogue files are unsupported, inconsistent or unsafe to rewrite."""


@dataclass(frozen=True)
class RefreshRequest:
    """One catalogue folder and the explicit authority to rewrite its derived fields."""

    folder: Path
    write: bool = False

    def __post_init__(self):
        if not isinstance(self.folder, Path) or type(self.write) is not bool:
            raise CatalogueRefreshError("a refresh needs a folder path and an explicit write flag")


def _regular_file(folder: Path, name: str) -> Path:
    path = folder / name
    if path.is_symlink() or not path.is_file() or path.resolve().parent != folder:
        raise CatalogueRefreshError(f"{name} must be a regular file inside the catalogue folder")
    return path


def load_catalogue(folder: Path) -> tuple[dict, dict, dict]:
    """The two records and the body text for every identity, or a typed refusal."""
    folder = folder.resolve()
    specifications = json.loads(_regular_file(folder, SPECIFICATIONS_FILE).read_text(encoding="utf-8"))
    items = json.loads(_regular_file(folder, ITEMS_FILE).read_text(encoding="utf-8"))
    if not isinstance(specifications, dict) or specifications.get("record_type") != SPECIFICATIONS_RECORD_TYPE:
        raise CatalogueRefreshError("unsupported specifications record")
    if not isinstance(items, dict) or items.get("record_type") != ITEMS_RECORD_TYPE:
        raise CatalogueRefreshError("unsupported items record")
    spec_ids = [row.get("id") for row in specifications.get("specifications") or ()]
    item_ids = [row.get("reference", {}).get("identity") for row in items.get("items") or ()]
    if not spec_ids or spec_ids != item_ids or len(set(spec_ids)) != len(spec_ids):
        raise CatalogueRefreshError("both records must list the same unique identities in the same order")
    bodies_folder = folder / BODIES_FOLDER
    if bodies_folder.is_symlink() or not bodies_folder.is_dir():
        raise CatalogueRefreshError("the bodies folder is missing")
    found = sorted(path.name for path in bodies_folder.iterdir())
    if found != sorted(identity + BODY_SUFFIX for identity in spec_ids):
        raise CatalogueRefreshError("every identity needs exactly one body file and no other file may be present")
    bodies = {}
    for identity in spec_ids:
        path = bodies_folder / (identity + BODY_SUFFIX)
        if path.is_symlink() or not path.is_file():
            raise CatalogueRefreshError(f"the body of {identity} must be a regular file")
        bodies[identity] = path.read_bytes().decode("utf-8")
    return specifications, items, bodies


def measured_reference(reference: dict, body: str) -> dict:
    """The reference with its digest and size measured from the body by the engine."""
    tags = dict(reference["tags"])
    if tags.pop("record_type", None) != TAG_RECORD_TYPE:
        raise CatalogueRefreshError("tags need their current versioned record")
    draft = HarnessIntelligenceDraft(
        reference["identity"], reference["kind"], reference["purpose"], reference["source_layer"],
        reference["source_ref"], reference["license"], tuple(reference["declared_effects"]),
        tuple(reference["styles"]), reference["exposure"], reference["availability"], TagSet(tags))
    return item_from_body(draft, body).reference()


def derive(specifications: dict, items: dict, bodies: dict) -> tuple[dict, dict]:
    """Copies of both records with the text, digest, size and body path taken from the bodies."""
    new_specifications, new_items = deepcopy(specifications), deepcopy(items)
    for row, item in zip(new_specifications["specifications"], new_items["items"]):
        identity = row["id"]
        row["text"] = bodies[identity]
        item["reference"] = measured_reference(item["reference"], bodies[identity])
        item["body_path"] = f"{BODIES_FOLDER}/{identity}{BODY_SUFFIX}"
    return new_specifications, new_items


def stale_identities(specifications: dict, items: dict, bodies: dict) -> list[str]:
    """The identities whose stored derived fields differ from their body."""
    new_specifications, new_items = derive(specifications, items, bodies)
    return [row["id"] for row, new_row, item, new_item in zip(
        specifications["specifications"], new_specifications["specifications"],
        items["items"], new_items["items"]) if row != new_row or item != new_item]


def _replace(path: Path, value: dict) -> None:
    temporary = path.with_name(path.name + ".refresh")
    with temporary.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    os.replace(temporary, path)


def refresh(request: RefreshRequest) -> dict:
    """Report the stale identities and rewrite them only with explicit write authority."""
    if not isinstance(request, RefreshRequest):
        raise CatalogueRefreshError("a typed refresh request is required")
    folder = request.folder.resolve()
    specifications, items, bodies = load_catalogue(folder)
    stale = stale_identities(specifications, items, bodies)
    if stale and request.write:
        new_specifications, new_items = derive(specifications, items, bodies)
        _replace(_regular_file(folder, SPECIFICATIONS_FILE), new_specifications)
        _replace(_regular_file(folder, ITEMS_FILE), new_items)
    return {"record_type": "starter_catalogue_refresh/v1", "items": len(bodies), "stale": stale,
            "written": bool(stale and request.write), "approved": False, "published": False}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true",
                        help="Rewrite the derived fields. Without it the tool only reports.")
    arguments = parser.parse_args(argv)
    result = refresh(RefreshRequest(Path(__file__).resolve().parent, arguments.write))
    print(json.dumps(result, indent=2))
    return 0 if not result["stale"] or result["written"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
