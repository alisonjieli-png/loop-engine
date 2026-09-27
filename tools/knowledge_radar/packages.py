"""Package radar deliverables in the existing native harness candidate format, and nothing else.

Each brief, helper and tool becomes one `harness_candidate_batch_proposals/v2`
proposal that the existing preparation factory (`tools/prepare_harness_candidates.py`
with `tools/native_harness_candidates.py`) turns into a candidate catalogue:
`starter_catalogue_candidate_items/v3`, `candidate_intelligence_specifications/v3`
and complete package trees. The factory pins every cited repository file to
the checkout's committed revision; this module adds no second package format,
no store and no approval.

```text
deliverable                    package kind  files
brief (and data file)          skill         SKILL.md, references/brief.json, references/provenance.json,
                                             contracts/brief.schema.json, [references/<id>-table.json,
                                             contracts/<id>-table.schema.json], LICENSE
decision helper                tool          the asset's files plus the day's table at its data_file path
tool (volatile facts)          tool          the asset's files, unchanged from the repository
```
"""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

from .brief import BRIEF_SCHEMA, PROVENANCE_RECORD_TYPE, build_table, description, render_skill

PROPOSALS_RECORD_TYPE = "harness_candidate_batch_proposals/v2"
ASSET_RECORD_TYPE = "knowledge_radar_asset/v1"
REGISTRY_PATH = "tools/knowledge_radar/questions-v1.json"
CONTRACTS_PATH = "tools/knowledge_radar/source-contracts-v1.json"
BRIEF_MODULE_PATH = "tools/knowledge_radar/brief.py"
ASSETS_PATH = "tools/knowledge_radar/assets"
STYLES = ["claude", "codex", "opencode", "pi"]
PRODUCER = {"producer_identity": "Baltor knowledge radar generator (deterministic rules)", "family": "anthropic",
            "method_identity": "knowledge_radar/brief/v1"}
_ASSET_FIELDS = {"record_type", "asset_id", "asset_version", "kind", "title", "purpose", "declared_effects",
                 "dependencies", "styles", "entrypoint", "test", "data_file", "files"}
_MEDIA = {"skill_definition": "text/markdown", "skill_reference": "application/json",
          "configuration": "application/schema+json", "other": "text/plain"}


class PackagingError(ValueError):
    """A deliverable could not be packaged, with a stable code."""


def _bytes_json(value) -> bytes:
    return (json.dumps(value, indent=1, ensure_ascii=False, sort_keys=False) + "\n").encode("utf-8")


def file_record(path: str, body: bytes, role: str, media_type: "str | None" = None) -> dict:
    return {"path": path, "digest": hashlib.sha256(body).hexdigest(), "size_bytes": len(body),
            "media_type": media_type or _MEDIA[role], "role": role,
            "content_base64": base64.b64encode(body).decode("ascii")}


def compact_day(day: str) -> str:
    return day.replace("-", "")


def _tags(question) -> dict:
    return {"domain": ["knowledge_radar", question.area], "language": ["en"], "data_sensitivity": ["public"],
            "authentication": ["none"]}


def _search_tags(question, brief: dict) -> list:
    tags = ["knowledge radar", f"radar {question.id}", question.area.replace("_", " "), question.title.lower(),
            f"as of {brief['as_of']}", f"valid until {brief['valid_until']}"]
    for section in brief["sections"][:6]:
        tags.append(section["title"].lower())
    unique = []
    for tag in tags:
        tag = tag[:160]
        if tag not in unique:
            unique.append(tag)
    return unique[:20]


def files_meaning(question) -> dict:
    """The supporting files of a brief package and what each holds, as SKILL.md lists them."""
    meaning = {"references/brief.json": "this brief as a typed record (knowledge_radar_brief/v1)",
               "contracts/brief.schema.json": "the JSON Schema of the brief record",
               "references/provenance.json": "how this brief was produced: generator, registry, sources and checks"}
    if "data_file" in question.delivery:
        meaning[f"references/{question.id}-table.json"] = "the current claims as one typed table (knowledge_radar_table/v1)"
        meaning[f"contracts/{question.id}-table.schema.json"] = "the JSON Schema of that table"
    return meaning


def brief_proposal(question, brief: dict, *, licence: bytes, revision: str, registry_sha256: str,
                   contracts_sha256: str, checks: list) -> "tuple[dict, dict | None]":
    """One skill package for a question's brief, with its table when the question delivers a data file."""
    files = []
    table = schema = None
    if "data_file" in question.delivery:
        table, schema = build_table(question, brief)
    meaning = files_meaning(question)
    provenance = {"record_type": PROVENANCE_RECORD_TYPE, "question_id": question.id, "as_of": brief["as_of"],
                  "generator": brief["generator"], "source_revision": revision,
                  "registry": {"path": REGISTRY_PATH, "sha256": registry_sha256},
                  "source_contracts": {"path": CONTRACTS_PATH, "sha256": contracts_sha256},
                  "checks": checks, "model_calls": 0, "authoring": "deterministic rules over dated public metadata",
                  "review_requirement": question.review_requirement}
    skill = render_skill(question, brief, meaning).encode("utf-8")
    files.append(file_record("SKILL.md", skill, "skill_definition"))
    files.append(file_record("references/brief.json", _bytes_json(brief), "skill_reference"))
    files.append(file_record("references/provenance.json", _bytes_json(provenance), "skill_reference"))
    files.append(file_record("contracts/brief.schema.json", _bytes_json(BRIEF_SCHEMA), "configuration"))
    if table is not None:
        files.append(file_record(f"references/{question.id}-table.json", _bytes_json(table), "skill_reference"))
        files.append(file_record(f"contracts/{question.id}-table.schema.json", _bytes_json(schema), "configuration"))
    files.append(file_record("LICENSE", licence, "other"))
    identity = f"radar_{question.id}_{compact_day(brief['as_of'])}"
    proposal = {"id": identity, "title": f"{question.title} (radar brief, {brief['as_of']})",
                "purpose": " ".join(description(question, brief).split()),
                "sources": [REGISTRY_PATH, BRIEF_MODULE_PATH, CONTRACTS_PATH], "layer": "context",
                "family": "knowledge_radar_brief", "search_tags": _search_tags(question, brief), "tags": _tags(question),
                "symbols": [question.id], "declared_effects": ["reads_fs"], "kind": "skill", "styles": list(STYLES),
                "dependencies": [], "producer": dict(PRODUCER), "files": files}
    return proposal, table


def read_asset(repository: Path, asset_id: str) -> "tuple[dict, dict]":
    """An asset's declaration and the exact bytes of every file it lists, read from the repository."""
    folder = Path(repository) / ASSETS_PATH / asset_id
    try:
        declaration = json.loads((folder / "asset.json").read_bytes())
    except (OSError, ValueError) as error:
        raise PackagingError(f"radar_asset_unreadable: {asset_id}: {type(error).__name__}") from None
    if (type(declaration) is not dict or set(declaration) != _ASSET_FIELDS
            or declaration["record_type"] != ASSET_RECORD_TYPE or declaration["asset_id"] != asset_id):
        raise PackagingError(f"radar_asset_invalid: {asset_id} is not a knowledge_radar_asset/v1 declaration")
    bodies = {}
    listed = {entry["path"] for entry in declaration["files"]}
    found = {path.relative_to(folder).as_posix() for path in folder.rglob("*")
             if path.is_file() and path.name != "asset.json" and "__pycache__" not in path.parts}
    if found != listed:
        raise PackagingError(f"radar_asset_inventory_mismatch: {asset_id} lists {sorted(listed ^ found)[:5]} wrongly")
    for entry in declaration["files"]:
        path = folder / entry["path"]
        if path.is_symlink() or not path.is_file():
            raise PackagingError(f"radar_asset_file_invalid: {asset_id}/{entry['path']}")
        bodies[entry["path"]] = path.read_bytes()
    return declaration, bodies


def asset_sources(declaration: dict) -> list:
    base = f"{ASSETS_PATH}/{declaration['asset_id']}"
    return [f"{base}/asset.json", f"{base}/{declaration['entrypoint']}"]


def asset_proposal(repository: Path, asset_id: str, *, as_of: str, table: "dict | None" = None,
                   question=None) -> dict:
    """A helper or tool package from the repository asset; a helper receives the day's table at its data path."""
    declaration, bodies = read_asset(repository, asset_id)
    files = []
    for entry in declaration["files"]:
        files.append(file_record(entry["path"], bodies[entry["path"]], entry["role"], entry["media_type"]))
    if declaration["kind"] == "decision_helper":
        if table is None or not declaration["data_file"]:
            raise PackagingError(f"radar_helper_without_table: {asset_id} needs the day's table")
        files.append(file_record(declaration["data_file"], _bytes_json(table), "skill_reference"))
        identity = f"radar_helper_{asset_id}_{compact_day(as_of)}"
        title = f"{declaration['title']} (radar helper, data as of {as_of})"
    else:
        major = declaration["asset_version"].split(".")[0]
        identity = f"radar_tool_{asset_id}_v{major}"
        title = f"{declaration['title']} (radar tool, version {declaration['asset_version']})"
    area = question.area if question is not None else "tools"
    tags = ["knowledge radar", f"radar {asset_id}", declaration["kind"].replace("_", " "), declaration["title"].lower()]
    if question is not None:
        tags.append(f"radar {question.id}")
    return {"id": identity, "title": title[:160], "purpose": " ".join(declaration["purpose"].split()),
            "sources": asset_sources(declaration), "layer": "code",
            "family": "knowledge_radar_" + ("helper" if declaration["kind"] == "decision_helper" else "tool"),
            "search_tags": tags, "tags": {"domain": ["knowledge_radar", area], "language": ["en"],
                                          "data_sensitivity": ["public"], "authentication": ["none"]},
            "symbols": [asset_id], "declared_effects": list(declaration["declared_effects"]), "kind": "tool",
            "styles": list(declaration["styles"]), "dependencies": list(declaration["dependencies"]),
            "producer": {**PRODUCER, "method_identity": f"knowledge_radar/{declaration['kind']}/v1"}, "files": files}


def proposals_record(repository: Path, revision: str, proposals: list) -> dict:
    """The factory's input: every cited repository file with its digest at the committed revision."""
    root = Path(repository)
    cited = sorted({path for proposal in proposals for path in proposal["sources"]})
    sources = {path: hashlib.sha256((root / path).read_bytes()).hexdigest() for path in cited}
    licence = hashlib.sha256((root / "LICENSE").read_bytes()).hexdigest()
    return {"record_type": PROPOSALS_RECORD_TYPE, "source_revision": revision,
            "license": {"expression": "MIT", "path": "LICENSE", "sha256": licence},
            "sources": sources, "proposals": proposals}
