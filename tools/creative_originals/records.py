"""Strict readers for the creative original families: family.json, item.json and the evidence record.

```text
tools/creative_originals/<family>/
├── family.json            creative_original_family/v1: what the family is, its shared files, its verifier
├── shared/                files every package of the family carries, byte for byte (inspectors, test runners)
├── native.py              the family's native verifier: verify(item, workspace, engines) -> evidence checks
└── items/<identity>/
    ├── item.json          creative_original_item/v1: one distinct capability, its contract and its limits
    ├── README.md          how a harness uses it; the first line is "# " and the title
    └── the native files   shaders, scenes, scripts, generators, data
```

A reader refuses unknown keys, wrong types and inconsistent values with a closed reason code, so a
family cannot drift into an undocumented shape. Nothing here runs an engine or writes a file.
"""
from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath

FAMILY_RECORD = "creative_original_family/v1"
ITEM_RECORD = "creative_original_item/v1"
COMPONENT_RECORD = "creative_original_component/v1"
EVIDENCE_RECORD = "creative_original_native_evidence/v1"
COMPONENT_NAME = "component.json"
EVIDENCE_PATH = "verification/native.json"
PREVIEW_PATH = "preview.png"

#: The served component forms this line writes, and the harness kind each is served as
#: (catalogue_attributes.COMPONENT_FORM_KINDS). Every form here holds Python the sandbox can run.
FORM_KINDS = {"library_module": "code_module", "function": "code_module", "code_example": "code_module",
              "evaluation_set": "code_module", "template": "template", "three_d_model": "three_d_model",
              "schema": "contract_schema"}
#: Forms that must declare what a harness does with the artifact (catalogue_attributes.ASSET_ROLE_FORMS).
ASSET_ROLE_FORMS = ("template", "three_d_model", "code_example")
ASSET_ROLES = ("reference", "generation_input", "editable_source", "test_evidence")
#: The owner's taxonomy for creative work, October 9, 2026: "3D 2D 2.5D, 4D". "none" is a tool for any of them.
DIMENSIONS = ("2d", "2.5d", "3d", "4d", "none")
ENGINES = ("godot", "blender", "python", "node", "webgl2_browser", "any_gltf_viewer")
#: Package file roles (catalogue_packages.FILE_ROLES) an item may declare.
FILE_ROLES = ("instruction_file", "skill_reference", "skill_asset", "executable_tool", "configuration", "other")
EVIDENCE_STATES = ("passed", "failed")

_IDENTITY = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
_TAG = re.compile(r"^[a-z0-9][a-z0-9 .+#/-]{0,39}$")
_VERSION = re.compile(r"^\d+(\.\d+){0,2}$")
_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
#: Paths an item may not use: the files the line writes itself.
RESERVED_PATHS = (COMPONENT_NAME, EVIDENCE_PATH, PREVIEW_PATH, "LICENSE", "UPSTREAM-LICENSE", "ATTRIBUTION.md")
MAXIMUM_ITEM_FILES = 40
MAXIMUM_TITLE, MAXIMUM_PURPOSE, MAXIMUM_LIMITS = 90, 320, 900

FAMILY_KEYS = {"record_type", "family", "title", "description", "engine", "shared_files", "native_verifier",
               "generator_version", "default_dimension"}
ITEM_KEYS = {"record_type", "identity", "title", "purpose", "form", "asset_role", "dimension", "engine", "tags",
             "files", "contract", "limits", "related", "technique_references", "native_checks"}
ENGINE_KEYS = {"name", "minimum_version", "notes"}


class CreativeRecordError(ValueError):
    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason, self.detail = reason, detail


def _strict_json(path: Path) -> dict:
    def pairs(items):
        keys = [key for key, _value in items]
        if len(keys) != len(set(keys)):
            raise CreativeRecordError("duplicate_key", str(path))
        return dict(items)

    def constant(name):
        raise CreativeRecordError("non_finite_number", f"{path}: {name}")

    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs, parse_constant=constant)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CreativeRecordError("record_unreadable", f"{path}: {type(error).__name__}") from None
    if not isinstance(value, dict):
        raise CreativeRecordError("record_not_object", str(path))
    return value


def _text(value, field: str, limit: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit or value != value.strip():
        raise CreativeRecordError("field_invalid", f"{field} must be trimmed text of at most {limit} characters")
    return value


def _engine(value, field: str) -> dict:
    if not isinstance(value, dict) or set(value) - ENGINE_KEYS or "name" not in value:
        raise CreativeRecordError("engine_invalid", f"{field} has keys {sorted(ENGINE_KEYS)}")
    if value["name"] not in ENGINES:
        raise CreativeRecordError("engine_invalid", f"{field}.name is one of {ENGINES}")
    if "minimum_version" in value and not (isinstance(value["minimum_version"], str)
                                           and _VERSION.match(value["minimum_version"])):
        raise CreativeRecordError("engine_invalid", f"{field}.minimum_version is like 4.3 or 3.10")
    if "notes" in value:
        _text(value["notes"], f"{field}.notes", 300)
    return value


def safe_relative(path, field: str = "path") -> str:
    if not isinstance(path, str) or not path or path.startswith("/") or "\\" in path or "\x00" in path:
        raise CreativeRecordError("path_invalid", f"{field}: {path!r}")
    parts = PurePosixPath(path).parts
    if any(part in ("", ".", "..") or part.startswith(".git") for part in parts) or len(parts) > 6 or len(path) > 160:
        raise CreativeRecordError("path_invalid", f"{field}: {path!r}")
    return path


def read_family(directory: Path) -> dict:
    directory = Path(directory)
    record = _strict_json(directory / "family.json")
    if set(record) != FAMILY_KEYS:
        raise CreativeRecordError("family_keys_invalid", f"expected {sorted(FAMILY_KEYS)}, got {sorted(record)}")
    if record["record_type"] != FAMILY_RECORD:
        raise CreativeRecordError("record_type_invalid", record["record_type"])
    if record["family"] != directory.name or not _IDENTITY.match(record["family"]):
        raise CreativeRecordError("family_name_invalid", f"{record['family']} in folder {directory.name}")
    _text(record["title"], "title", MAXIMUM_TITLE)
    _text(record["description"], "description", 2000)
    _engine(record["engine"], "engine")
    if not isinstance(record["generator_version"], str) or not _SEMVER.match(record["generator_version"]):
        raise CreativeRecordError("field_invalid", "generator_version is semantic, like 1.0.0")
    if record["default_dimension"] not in DIMENSIONS:
        raise CreativeRecordError("field_invalid", f"default_dimension is one of {DIMENSIONS}")
    if record["native_verifier"] is not None:
        verifier = safe_relative(record["native_verifier"], "native_verifier")
        if not (directory / verifier).is_file():
            raise CreativeRecordError("native_verifier_missing", verifier)
    shared = record["shared_files"]
    if not isinstance(shared, list):
        raise CreativeRecordError("field_invalid", "shared_files is a list")
    seen = set()
    for row in shared:
        if not isinstance(row, dict) or set(row) != {"path", "role"}:
            raise CreativeRecordError("shared_file_invalid", "each shared file has path and role")
        path = safe_relative(row["path"], "shared_files.path")
        if row["role"] not in FILE_ROLES or path in seen or path in RESERVED_PATHS:
            raise CreativeRecordError("shared_file_invalid", path)
        if not (directory / "shared" / path).is_file():
            raise CreativeRecordError("shared_file_missing", path)
        seen.add(path)
    return record


def read_item(family_directory: Path, identity: str, family: "dict | None" = None) -> dict:
    family_directory = Path(family_directory)
    family = family or read_family(family_directory)
    directory = family_directory / "items" / identity
    record = _strict_json(directory / "item.json")
    missing = {"record_type", "identity", "title", "purpose", "form", "dimension", "engine", "tags", "files",
               "contract", "limits"} - set(record)
    if missing or set(record) - ITEM_KEYS:
        raise CreativeRecordError("item_keys_invalid", f"missing {sorted(missing)}, unknown {sorted(set(record) - ITEM_KEYS)}")
    if record["record_type"] != ITEM_RECORD:
        raise CreativeRecordError("record_type_invalid", record["record_type"])
    if record["identity"] != identity or not _IDENTITY.match(identity):
        raise CreativeRecordError("identity_invalid", f"{record['identity']} in folder {identity}")
    _text(record["title"], "title", MAXIMUM_TITLE)
    _text(record["purpose"], "purpose", MAXIMUM_PURPOSE)
    _text(record["limits"], "limits", MAXIMUM_LIMITS)
    if record["form"] not in FORM_KINDS:
        raise CreativeRecordError("form_invalid", f"form is one of {sorted(FORM_KINDS)}")
    role = record.get("asset_role")
    if record["form"] in ASSET_ROLE_FORMS and role not in ASSET_ROLES:
        raise CreativeRecordError("asset_role_required", f"a {record['form']} declares one of {ASSET_ROLES}")
    if role is not None and role not in ASSET_ROLES:
        raise CreativeRecordError("asset_role_invalid", str(role))
    if record["dimension"] not in DIMENSIONS:
        raise CreativeRecordError("dimension_invalid", f"dimension is one of {DIMENSIONS}")
    _engine(record["engine"], "engine")
    tags = record["tags"]
    if (not isinstance(tags, list) or not 2 <= len(tags) <= 16 or len(set(tags)) != len(tags)
            or not all(isinstance(tag, str) and _TAG.match(tag) for tag in tags)):
        raise CreativeRecordError("tags_invalid", "2 to 16 distinct lower-case tags")
    if not isinstance(record["contract"], dict) or not record["contract"]:
        raise CreativeRecordError("contract_invalid", "contract is a non-empty object")
    for key in ("related", "technique_references", "native_checks"):
        value = record.get(key, [])
        if not isinstance(value, list) or not all(isinstance(entry, str) and entry for entry in value):
            raise CreativeRecordError("field_invalid", f"{key} is a list of strings")
    if any(not _IDENTITY.match(entry) for entry in record.get("related", [])):
        raise CreativeRecordError("related_invalid", "related names item identities")
    files = record["files"]
    if not isinstance(files, list) or not 1 <= len(files) <= MAXIMUM_ITEM_FILES:
        raise CreativeRecordError("files_invalid", f"1 to {MAXIMUM_ITEM_FILES} files")
    shared = {row["path"] for row in family["shared_files"]}
    paths = set()
    for row in files:
        if not isinstance(row, dict) or set(row) != {"path", "role"}:
            raise CreativeRecordError("file_invalid", "each file has path and role")
        path = safe_relative(row["path"])
        if row["role"] not in FILE_ROLES:
            raise CreativeRecordError("file_role_invalid", f"{path}: role is one of {FILE_ROLES}")
        if path in paths or path in shared or path in RESERVED_PATHS or path == "item.json":
            raise CreativeRecordError("file_path_conflict", path)
        if not (directory / path).is_file():
            raise CreativeRecordError("file_missing", path)
        paths.add(path)
    if "README.md" not in paths:
        raise CreativeRecordError("readme_missing", identity)
    readme = (directory / "README.md").read_text(encoding="utf-8")
    if not readme.startswith("# " + record["title"] + "\n"):
        raise CreativeRecordError("readme_title_invalid", "README.md starts with '# ' and the item title")
    present = {str(path.relative_to(directory)).replace("\\", "/") for path in directory.rglob("*")
               if path.is_file() and "__pycache__" not in path.parts}
    undeclared = sorted(present - paths - {"item.json"})
    if undeclared:
        raise CreativeRecordError("file_undeclared", ", ".join(undeclared[:5]))
    return record


def item_identities(family_directory: Path) -> list:
    root = Path(family_directory) / "items"
    return sorted(path.name for path in root.iterdir() if path.is_dir() and (path / "item.json").is_file()) \
        if root.is_dir() else []


def families(root: Path) -> list:
    root = Path(root)
    return sorted(path.name for path in root.iterdir() if (path / "family.json").is_file())


def read_evidence(data: bytes, family: str, identity: str, item_digest: str) -> dict:
    """An evidence record, checked against the item it claims to describe."""
    try:
        record = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise CreativeRecordError("evidence_unreadable") from None
    expected = {"record_type", "family", "identity", "item_digest", "engine", "checks", "state", "preview"}
    if not isinstance(record, dict) or set(record) != expected or record["record_type"] != EVIDENCE_RECORD:
        raise CreativeRecordError("evidence_invalid", "record shape")
    if (record["family"], record["identity"], record["item_digest"]) != (family, identity, item_digest):
        raise CreativeRecordError("evidence_stale", f"{family}/{identity} evidence describes other bytes")
    if record["state"] not in EVIDENCE_STATES or not isinstance(record["checks"], list) or not record["checks"]:
        raise CreativeRecordError("evidence_invalid", "state and checks")
    for check in record["checks"]:
        if not isinstance(check, dict) or set(check) != {"name", "state", "detail"} \
                or check["state"] not in EVIDENCE_STATES:
            raise CreativeRecordError("evidence_invalid", "each check has name, state and detail")
    if record["state"] == "passed" and any(check["state"] != "passed" for check in record["checks"]):
        raise CreativeRecordError("evidence_invalid", "a passed record holds only passed checks")
    return record


__all__ = ["FAMILY_RECORD", "ITEM_RECORD", "COMPONENT_RECORD", "EVIDENCE_RECORD", "COMPONENT_NAME", "EVIDENCE_PATH",
           "PREVIEW_PATH", "FORM_KINDS", "ASSET_ROLE_FORMS", "ASSET_ROLES", "DIMENSIONS", "ENGINES", "FILE_ROLES",
           "CreativeRecordError", "read_family", "read_item", "read_evidence", "item_identities", "families",
           "safe_relative"]
