"""Assemble one creative original package from its family, item and native evidence.

The same function builds the package a family author tests locally and the package the
creative_originals supply line stores, so a local pass and a stored package hold the same bytes
(apart from the source revision, which a local run records as "uncommitted").

```text
<package>/
├── the item's files, at their declared paths
├── the family's shared files (byte-identical in every package of the family)
├── component.json          creative_original_component/v1: the small contract card a harness reads first
├── verification/native.json the native check record, when the family has a verifier
└── preview.png             a render the verifier captured, when it captured one
```
LICENSE and ATTRIBUTION.md are added by the supply line's packaging; a local run adds the repository licence.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .media import media_type, refuse_unsupported
from .records import (COMPONENT_NAME, COMPONENT_RECORD, EVIDENCE_PATH, FORM_KINDS, PREVIEW_PATH, CreativeRecordError,
                      read_evidence, read_family, read_item)

LINE = "creative_originals"
REPOSITORY = "alisonjieli-png/loop-engine"
#: The interpreter and flags the qualification sandbox uses (tools/component_qualification/sandbox.py).
SANDBOX_PYTHON = "/usr/bin/python3"


@dataclass(frozen=True)
class SandboxEnvironment:
    """The environment a local package test run gets: a fixed search path, a UTF-8 locale and no bytecode files,
    the way the qualification sandbox starts its interpreter."""

    search_path: str = "/usr/bin:/bin"
    locale: str = "C.UTF-8"
    #: PYTHONDONTWRITEBYTECODE: any non-empty value stops the interpreter writing .pyc files into the package.
    no_bytecode_flag: str = "1"

    def variables(self, home: Path) -> dict:
        return {"PATH": self.search_path, "HOME": str(home), "LANG": self.locale,
                "PYTHONDONTWRITEBYTECODE": self.no_bytecode_flag}


LOCAL_SANDBOX_ENVIRONMENT = SandboxEnvironment()


@dataclass(frozen=True)
class Entry:
    path: str
    data: bytes
    role: str
    media_type: str


def json_bytes(value) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source_files(family_directory: Path, identity: str, family: dict, item: dict) -> list:
    """(package path, bytes, role, repository path) for the item's files, item.json and the shared files."""
    family_directory = Path(family_directory)
    base = Path("tools/creative_originals") / family["family"]
    rows = []
    for row in item["files"]:
        data = (family_directory / "items" / identity / row["path"]).read_bytes()
        rows.append((row["path"], data, row["role"], str(base / "items" / identity / row["path"])))
    for row in family["shared_files"]:
        data = (family_directory / "shared" / row["path"]).read_bytes()
        rows.append((row["path"], data, row["role"], str(base / "shared" / row["path"])))
    return rows


def item_digest(family_directory: Path, identity: str, family: "dict | None" = None, item: "dict | None" = None) -> str:
    """The digest the evidence binds: every item and shared byte, item.json and the family version."""
    family_directory = Path(family_directory)
    family = family or read_family(family_directory)
    item = item or read_item(family_directory, identity, family)
    rows = sorted((path, _digest(data)) for path, data, _role, _source in source_files(family_directory, identity,
                                                                                          family, item))
    rows.append(("item.json", _digest((family_directory / "items" / identity / "item.json").read_bytes())))
    rows.append(("family_version", family["generator_version"]))
    return _digest(json.dumps(rows, sort_keys=True).encode())


def component_card(family: dict, item: dict, files: list, evidence: "dict | None", revision: str) -> dict:
    native = {"state": "not_run", "checks": [], "engine": None}
    if evidence is not None:
        native = {"state": evidence["state"], "checks": [check["name"] for check in evidence["checks"]],
                  "engine": {key: evidence["engine"].get(key) for key in ("name", "version", "renderer")
                             if key in evidence["engine"]}, "record": EVIDENCE_PATH}
    return {"record_type": COMPONENT_RECORD, "job": {"family": family["family"], "identity": item["identity"]},
            "title": item["title"], "purpose": item["purpose"], "form": item["form"],
            "kind": FORM_KINDS[item["form"]], "asset_role": item.get("asset_role"), "dimension": item["dimension"],
            "engine": item["engine"], "tags": item["tags"], "contract": item["contract"], "limits": item["limits"],
            "related": item.get("related", []), "technique_references": item.get("technique_references", []),
            "files": [{"path": path, "role": role, "sha256": _digest(data)} for path, data, role, _ in files],
            "verification": {"native": native},
            "generator": {"line": LINE, "family": family["family"], "family_version": family["generator_version"]},
            "source": {"repository": REPOSITORY, "revision": revision,
                       "paths": sorted(source for _path, _data, _role, source in files)},
            "authoring": "original_baltor_implementation"}


def package_entries(family_directory: Path, identity: str, *, evidence: "bytes | None" = None,
                    preview: "bytes | None" = None, revision: str = "uncommitted") -> list:
    """Every file of the package except LICENSE and ATTRIBUTION.md, in path order."""
    family_directory = Path(family_directory)
    family = read_family(family_directory)
    item = read_item(family_directory, identity, family)
    files = source_files(family_directory, identity, family, item)
    for path, _data, _role, _source in files:
        refuse_unsupported(path)
    record = None
    if family["native_verifier"] is not None:
        if evidence is None:
            raise CreativeRecordError("evidence_missing", f"{family['family']}/{identity} has a native verifier")
        record = read_evidence(evidence, family["family"], identity, item_digest(family_directory, identity, family, item))
        if record["state"] != "passed":
            raise CreativeRecordError("native_check_failed", f"{family['family']}/{identity}")
        expected = record["preview"]
        if expected is None and preview is not None:
            raise CreativeRecordError("preview_unexpected", identity)
        if expected is not None and (preview is None or _digest(preview) != expected["sha256"]):
            raise CreativeRecordError("preview_mismatch", identity)
    entries = [Entry(path, data, role, media_type(path)) for path, data, role, _source in files]
    entries.append(Entry(COMPONENT_NAME, json_bytes(component_card(family, item, files, record, revision)), "other",
                         "application/json"))
    if record is not None:
        entries.append(Entry(EVIDENCE_PATH, evidence, "other", "application/json"))
        if preview is not None:
            entries.append(Entry(PREVIEW_PATH, preview, "skill_asset", "image/png"))
    paths = [entry.path for entry in entries]
    lowered = [path.lower() for path in paths]
    if len(set(lowered)) != len(lowered):
        raise CreativeRecordError("file_path_conflict", "two package paths differ only in case")
    return sorted(entries, key=lambda entry: entry.path)


def write_package(directory: Path, entries: list, licence: "bytes | None" = None) -> Path:
    """Write the entries into a new, empty folder (refused when it exists)."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    for entry in entries:
        target = directory / PurePosixPath(entry.path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(entry.data)
    if licence is not None:
        (directory / "LICENSE").write_bytes(licence)
    return directory


def run_package_tests(directory: Path, *, timeout: int = 300, python: str = SANDBOX_PYTHON,
                      settings: SandboxEnvironment = LOCAL_SANDBOX_ENVIRONMENT) -> dict:
    """Run the package's root test_*.py modules the way the sandbox does: isolated interpreter, package root as cwd.

    This is not the sandbox (no namespace, network or resource isolation); it shows a family author whether the
    tests the sandbox will run pass on the exact package bytes."""
    directory = Path(directory)
    tests = sorted(path.stem for path in directory.glob("test_*.py"))
    if not tests:
        return {"state": "failed", "reason": "no_root_test_modules", "tests": []}
    environment = settings.variables(directory)
    try:
        completed = subprocess.run([python, "-E", "-s", "-B", "-m", "unittest", "-v", *tests], cwd=directory,
                                   env=environment, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"state": "failed", "reason": "tests_timed_out", "tests": tests}
    return {"state": "passed" if completed.returncode == 0 else "failed", "returncode": completed.returncode,
            "tests": tests, "output_tail": completed.stderr[-4000:]}


def assemble_and_test(family_directory: Path, identity: str, destination: Path, *, evidence: "bytes | None" = None,
                      preview: "bytes | None" = None, licence: "bytes | None" = None) -> dict:
    """Write one package into ``destination`` / identity and run its tests; the folder is replaced each time."""
    target = Path(destination) / identity
    if target.exists():
        shutil.rmtree(target)
    entries = package_entries(family_directory, identity, evidence=evidence, preview=preview)
    write_package(target, entries, licence)
    result = run_package_tests(target)
    result["files"] = len(entries)
    result["bytes"] = sum(len(entry.data) for entry in entries)
    return result


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def repository_licence() -> bytes:
    return (repository_root() / "LICENSE").read_bytes()


__all__ = ["Entry", "LINE", "REPOSITORY", "json_bytes", "source_files", "item_digest", "component_card",
           "package_entries", "write_package", "run_package_tests", "assemble_and_test", "repository_root",
           "repository_licence"]
