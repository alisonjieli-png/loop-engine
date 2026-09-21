"""Refresh the derived fields of the starter catalogue after a body was edited.

The files in ``bodies`` are the source of truth for the text, the digest and
the size of every item. This tool measures each body through the engine's own
``item_from_body`` function and rewrites only the committed population files
``specifications-001.json`` and the ones after it, together with ``items.json``,
in its own folder. It approves nothing, publishes nothing and grants nothing.
Every item stays a candidate.

The staging tool accepts one bounded population of at most ``POPULATION_SIZE``
rows, so the catalogue is committed as several population files that the tool
accepts as they stand. A row keeps the population file it is already in. When a
population file is full, add the next file by hand with an empty row list and
put the new rows in it; this tool never moves a row between files.

Check without writing (the default), then write with explicit authority:

    PYTHONPATH=src python examples/29_intelligence_service/starter-catalogue/refresh.py
    PYTHONPATH=src python examples/29_intelligence_service/starter-catalogue/refresh.py --write

``items.json`` also pins the exact bytes of every cited source, under the one
revision that the bodies name. When a cited file changes in the repository, the
catalogue has to be anchored again to a revision whose bytes are the ones now in
the tree. This tool does that in one command. It reads each cited file at the
named revision, refuses unless every one of them equals the file in the tree,
and only then rewrites the revision, the source reference of every item, the
measured source digests and the revision named in each body:

    PYTHONPATH=src python examples/29_intelligence_service/starter-catalogue/refresh.py \\
      --anchor REVISION --write
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from loop_engine.core.harness_intelligence import HarnessIntelligenceDraft, item_from_body
from loop_engine.core.intelligence_tagging import RECORD_TYPE as TAG_RECORD_TYPE, TagSet

SPECIFICATIONS_RECORD_TYPE = "candidate_intelligence_specifications/v1"
#: Version two of the items record. It gained ``source_digests``, which pins the exact
#: bytes of every cited source at ``source_revision``. A reader of version one would
#: ignore that field and lose the integrity claim, so it must refuse this record.
ITEMS_RECORD_TYPE = "starter_catalogue_candidate_items/v2"
#: The committed population files, named by their number. ``tools/stage_intelligence_candidates.py``
#: accepts one such file as it stands, so nothing has to be split before staging.
SPECIFICATIONS_PREFIX = "specifications-"
SPECIFICATIONS_GLOB = SPECIFICATIONS_PREFIX + "[0-9][0-9][0-9].json"
#: The bound that the staging tool states. A population file larger than this is refused there,
#: so it is refused here as well, before anything is rewritten.
POPULATION_SIZE = 50
ITEMS_FILE = "items.json"
BODIES_FOLDER = "bodies"
BODY_SUFFIX = ".md"
TEMPORARY_SUFFIX = ".refresh"
#: One full revision, and how many of its characters a body names.
REVISION = re.compile(r"[0-9a-f]{40}")
SHORT_REVISION = 7
#: The sentence that each kind of body carries, with the revision it was anchored to.
#: Anchoring again rewrites the revision inside these sentences and nothing else.
GROUNDING_SENTENCES = ("Compiled from revision {revision}.",
                       "Written for this catalogue at revision {revision}.")
#: How long the tool waits for the version control command that reads one file.
GIT_SECONDS = 30


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


@dataclass(frozen=True)
class AnchorRequest:
    """One catalogue folder, the repository it cites, the new revision and the write authority."""

    folder: Path
    repository: Path
    revision: str
    write: bool = False

    def __post_init__(self):
        if (not isinstance(self.folder, Path) or not isinstance(self.repository, Path)
                or type(self.write) is not bool):
            raise CatalogueRefreshError("anchoring needs a folder, a repository and an explicit write flag")
        if not isinstance(self.revision, str) or not REVISION.fullmatch(self.revision):
            raise CatalogueRefreshError("anchoring needs one full forty character revision")


def _regular_file(folder: Path, name: str) -> Path:
    path = folder / name
    if path.is_symlink() or not path.is_file() or path.resolve().parent != folder:
        raise CatalogueRefreshError(f"{name} must be a regular file inside the catalogue folder")
    return path


def _text(path: Path) -> str:
    try:
        return path.read_bytes().decode("utf-8")
    except UnicodeDecodeError as error:
        raise CatalogueRefreshError(f"{path.name} is not UTF-8 text; save the file as UTF-8 and run again") from error


def _record(folder: Path, name: str) -> dict:
    try:
        return json.loads(_text(_regular_file(folder, name)))
    except json.JSONDecodeError as error:
        raise CatalogueRefreshError(
            f"{name} is not valid JSON (line {error.lineno}); repair the file or restore it from the repository") from error


def population_names(folder: Path) -> list[str]:
    """The committed population file names in number order, or a typed refusal."""
    names = sorted(path.name for path in folder.glob(SPECIFICATIONS_GLOB))
    if not names:
        raise CatalogueRefreshError(
            f"no population file is present; the catalogue needs {SPECIFICATIONS_PREFIX}001.json")
    expected = [f"{SPECIFICATIONS_PREFIX}{number:03d}.json" for number in range(1, len(names) + 1)]
    if names != expected:
        raise CatalogueRefreshError(f"the population files must be numbered from one without a gap: {expected}")
    return names


def load_populations(folder: Path) -> list[tuple[str, dict]]:
    """Every committed population file with its record, in number order, or a typed refusal."""
    names = population_names(folder)
    populations = []
    for number, name in enumerate(names, start=1):
        record = _record(folder, name)
        rows = record.get("specifications") if isinstance(record, dict) else None
        if (not isinstance(record, dict) or record.get("record_type") != SPECIFICATIONS_RECORD_TYPE
                or record.get("population") != number or record.get("populations") != len(names)):
            raise CatalogueRefreshError(
                f"{name} must be a {SPECIFICATIONS_RECORD_TYPE} record that names population "
                f"{number} of {len(names)}")
        if not isinstance(rows, list) or not 1 <= len(rows) <= POPULATION_SIZE:
            raise CatalogueRefreshError(
                f"{name} holds {len(rows) if isinstance(rows, list) else 'no'} rows; the staging tool accepts "
                f"one to {POPULATION_SIZE}")
        populations.append((name, record))
    return populations


def combined(populations: list) -> dict:
    """Every population's rows in file order, under one record the staging tool would refuse."""
    return {"record_type": SPECIFICATIONS_RECORD_TYPE,
            "specifications": [row for _name, record in populations for row in record["specifications"]]}


def load_catalogue(folder: Path) -> tuple[list, dict, dict]:
    """The population files, the items record and the body text for every identity, or a typed refusal."""
    folder = folder.resolve()
    populations, items = load_populations(folder), _record(folder, ITEMS_FILE)
    specifications = combined(populations)
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
        bodies[identity] = _text(path)
    return populations, items, bodies


def measured_reference(reference: dict, body: str) -> dict:
    """The reference with its digest and size measured from the body by the engine."""
    tags = dict(reference["tags"])
    if tags.pop("record_type", None) != TAG_RECORD_TYPE:
        raise CatalogueRefreshError("tags need their current versioned record")
    draft = HarnessIntelligenceDraft(
        reference["identity"], reference["kind"], reference["purpose"], reference["source_layer"],
        reference["source_ref"], reference["license"], tuple(reference["declared_effects"]),
        tuple(reference["styles"]), reference["exposure"], reference["availability"],
        tags=TagSet(tags))
    return item_from_body(draft, body).reference()


def derive(populations: list, items: dict, bodies: dict) -> tuple[list, dict]:
    """Copies of both records with the text, digest, size and body path taken from the bodies.

    A row keeps the population file it is already in, so the committed files stay
    the ones the staging tool has already accepted.
    """
    new_populations, new_items = deepcopy(populations), deepcopy(items)
    rows = [row for _name, record in new_populations for row in record["specifications"]]
    for row, item in zip(rows, new_items["items"]):
        identity = row["id"]
        row["text"] = bodies[identity]
        item["reference"] = measured_reference(item["reference"], bodies[identity])
        item["body_path"] = f"{BODIES_FOLDER}/{identity}{BODY_SUFFIX}"
    return new_populations, new_items


def stale_identities(populations: list, items: dict, bodies: dict) -> list[str]:
    """The identities whose stored derived fields differ from their body."""
    new_populations, new_items = derive(populations, items, bodies)
    old_rows = [row for _name, record in populations for row in record["specifications"]]
    new_rows = [row for _name, record in new_populations for row in record["specifications"]]
    return [row["id"] for row, new_row, item, new_item in zip(
        old_rows, new_rows, items["items"], new_items["items"]) if row != new_row or item != new_item]


def _prepare(path: Path, value: dict, created: list) -> Path:
    """Write the new content beside the record. Exclusive creation never follows a planted link."""
    temporary = path.with_name(path.name + TEMPORARY_SUFFIX)
    try:
        stream = temporary.open("x", encoding="utf-8")
    except FileExistsError as error:
        raise CatalogueRefreshError(
            f"{temporary.name} is left from an interrupted write; check that {path.name} is intact, "
            f"remove {temporary.name} and run again") from error
    created.append(temporary)
    with stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    return temporary


def _replace_both(replacements: list) -> None:
    """Prepare every new file before replacing any record; remove what this run created on failure."""
    created: list = []
    try:
        prepared = [(_prepare(path, value, created), path) for path, value in replacements]
        for temporary, path in prepared:
            os.replace(temporary, path)
    except OSError as error:
        raise CatalogueRefreshError(f"the write failed: {error}; run the tool again to see what is stale") from error
    finally:
        for temporary in created:
            temporary.unlink(missing_ok=True)


def refresh(request: RefreshRequest) -> dict:
    """Report the stale identities and rewrite them only with explicit write authority."""
    if not isinstance(request, RefreshRequest):
        raise CatalogueRefreshError("a typed refresh request is required")
    folder = request.folder.resolve()
    populations, items, bodies = load_catalogue(folder)
    stale = stale_identities(populations, items, bodies)
    if stale and request.write:
        new_populations, new_items = derive(populations, items, bodies)
        _replace_both([(_regular_file(folder, name), record) for name, record in new_populations]
                      + [(_regular_file(folder, ITEMS_FILE), new_items)])
    return {"record_type": "starter_catalogue_refresh/v1", "items": len(bodies),
            "populations": [name for name, _record in populations], "stale": stale,
            "written": bool(stale and request.write), "approved": False, "published": False}


def cited_sources(populations: list) -> list:
    """Every repository path that any row cites, once, in path order."""
    return sorted({source for _name, record in populations
                   for row in record["specifications"] for source in row["sources"]})


def _confined(repository: Path, relative: str) -> Path:
    """One cited path inside the repository, refusing traversal, a hidden part and a link."""
    parts = Path(relative).parts
    path = repository / relative
    if (Path(relative).is_absolute() or ".." in parts or any(part.startswith(".") for part in parts)
            or any(repository.joinpath(*parts[:index]).is_symlink() for index in range(1, len(parts) + 1))
            or repository not in path.resolve().parents or not path.is_file()):
        raise CatalogueRefreshError(f"{relative} must be a confined visible repository file")
    return path


def measure_sources(repository: Path, sources: list) -> dict:
    """The digest of every cited source as it stands in the tree, which is what the staging tool hashes."""
    return {relative: hashlib.sha256(_confined(repository, relative).read_bytes()).hexdigest()
            for relative in sources}


def _bytes_at_revision(repository: Path, revision: str, relative: str) -> bytes:
    """The committed bytes of one cited file at one revision, or a typed refusal."""
    try:
        finished = subprocess.run(["git", "-C", str(repository), "show", f"{revision}:{relative}"],
                                  capture_output=True, timeout=GIT_SECONDS, check=False)
    except (OSError, subprocess.SubprocessError) as error:
        raise CatalogueRefreshError(f"the repository history could not be read: {error}") from error
    if finished.returncode != 0:
        raise CatalogueRefreshError(f"{relative} is not in the repository at revision {revision[:SHORT_REVISION]}")
    return finished.stdout


def drifted_sources(repository: Path, revision: str, sources: list) -> list:
    """The cited files whose bytes at the revision are not the bytes in the tree."""
    return [relative for relative in sources
            if _bytes_at_revision(repository, revision, relative)
            != _confined(repository, relative).read_bytes()]


def anchored(populations: list, items: dict, bodies: dict, digests: dict, revision: str) -> tuple:
    """Copies of the records and the bodies with one new anchor revision written into them."""
    new_items, new_bodies = deepcopy(items), dict(bodies)
    old = str(items.get("source_revision") or "")
    earlier = [value for value in new_items.get("previous_source_revisions") or () if value != revision]
    if old and old != revision and old not in earlier:
        earlier.append(old)
    new_items["source_revision"] = revision
    new_items["previous_source_revisions"] = earlier
    new_items["source_digests"] = dict(sorted(digests.items()))
    rows = [row for _name, record in populations for row in record["specifications"]]
    for row, item in zip(rows, new_items["items"]):
        item["reference"]["source_ref"] = f"{row['sources'][0]}@{revision}"
        text = new_bodies[row["id"]]
        for sentence in GROUNDING_SENTENCES:
            text = text.replace(sentence.format(revision=old[:SHORT_REVISION]),
                                sentence.format(revision=revision[:SHORT_REVISION]))
        new_bodies[row["id"]] = text
    return new_items, new_bodies


def anchor(request: AnchorRequest) -> dict:
    """Pin the catalogue to a revision whose cited bytes are the bytes in the tree."""
    if not isinstance(request, AnchorRequest):
        raise CatalogueRefreshError("a typed anchor request is required")
    folder, repository = request.folder.resolve(), request.repository.resolve()
    populations, items, bodies = load_catalogue(folder)
    sources = cited_sources(populations)
    drifted = drifted_sources(repository, request.revision, sources)
    if drifted:
        raise CatalogueRefreshError(
            f"{len(drifted)} cited files differ between revision {request.revision[:SHORT_REVISION]} and the "
            f"tree, so that revision does not name the bytes the catalogue uses: {drifted}")
    digests = measure_sources(repository, sources)
    new_items, new_bodies = anchored(populations, items, bodies, digests, request.revision)
    changed = sorted([identity for identity, text in bodies.items() if new_bodies[identity] != text])
    moved = new_items != items or bool(changed)
    if moved and request.write:
        bodies_folder = folder / BODIES_FOLDER
        _replace_texts([(_regular_body(bodies_folder, identity), new_bodies[identity]) for identity in changed])
        _replace_both([(_regular_file(folder, ITEMS_FILE), new_items)])
        refresh(RefreshRequest(folder, True))
    return {"record_type": "starter_catalogue_anchor/v1", "revision": request.revision, "sources": len(sources),
            "bodies_rewritten": changed if moved else [], "written": bool(moved and request.write),
            "approved": False, "published": False}


def _regular_body(bodies_folder: Path, identity: str) -> Path:
    """One body inside the bodies folder, refusing a planted link or a path that leaves the folder."""
    path = bodies_folder / (identity + BODY_SUFFIX)
    if path.is_symlink() or not path.is_file() or path.resolve().parent != bodies_folder.resolve():
        raise CatalogueRefreshError(f"the body of {identity} must be a regular file inside the bodies folder")
    return path


def _replace_texts(replacements: list) -> None:
    """Prepare every new body before replacing any of them; remove what this run created on failure."""
    created: list = []
    try:
        prepared = []
        for path, text in replacements:
            temporary = path.with_name(path.name + TEMPORARY_SUFFIX)
            try:
                stream = temporary.open("x", encoding="utf-8")
            except FileExistsError as error:
                raise CatalogueRefreshError(
                    f"{temporary.name} is left from an interrupted write; check that {path.name} is intact, "
                    f"remove {temporary.name} and run again") from error
            created.append(temporary)
            with stream:
                stream.write(text)
            prepared.append((temporary, path))
        for temporary, path in prepared:
            os.replace(temporary, path)
    except OSError as error:
        raise CatalogueRefreshError(f"the write failed: {error}; run the tool again to see what is stale") from error
    finally:
        for temporary in created:
            temporary.unlink(missing_ok=True)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true",
                        help="Rewrite the derived fields. Without it the tool only reports.")
    parser.add_argument("--anchor", metavar="REVISION",
                        help="Pin the catalogue to this full revision, after checking that every cited "
                             "file at it equals the file in the tree.")
    arguments = parser.parse_args(argv)
    folder = Path(__file__).resolve().parent
    if arguments.anchor:
        result = anchor(AnchorRequest(folder, folder.parents[2], arguments.anchor, arguments.write))
        print(json.dumps(result, indent=2))
        return 0 if not result["bodies_rewritten"] or result["written"] else 1
    result = refresh(RefreshRequest(folder, arguments.write))
    print(json.dumps(result, indent=2))
    return 0 if not result["stale"] or result["written"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
