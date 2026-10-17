"""The JavaScript member adapter of the engine_api_cards line: one release of a package of javascript_packages.json a
run (lodash's functions, Express's application, request and response).

```text
read_package(reader, workspace, identity)
├── facts: the npm registry's record of the release (its tarball, SHA-512 integrity and gitHead); the tag's commit,
│   which must be that gitHead; the tarball streamed once, its integrity checked, its files unpacked inside one
│   folder (node_modules/<package>); every pinned dependency the same way, at the path its lock names
├── licence: GitHub's licence interface and the licence file agree at the tag, the package's own license field names
│   the same licence, and the package's licence file is the tag's, byte for byte
├── source identity: every file a card reads is the tag's blob at the same path, else its members are refused
├── surface: the JSDoc-documented public members of the package's rules (tools/engine_api_cards/jsdoc_members.py)
└── native check: Node requires the published module once for every card (tools/engine_api_cards/node_members.py)
```

The line calls no model. A package is a candidate until qualification and the ongoing independent review.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from engine_api_cards import cards, jsdoc_members, jsdoc_reference, node_members, node_native
from engine_api_cards.godot_native import NativeError, evidence_bytes

from .engine_api_cards import (INTEGRITY_PREFIX, LICENCE_AT_THE_TAG, MAXIMUM_PACKAGE_BYTES, REGISTRY_HOST, EngineSources,
                               LineStopped, _package_files, tag_licence)
from .reading import RAW_HOST, https_address, pinned_files
from .records import ENGINE_API_CARDS, GENERATED_CODE_LICENCE, refusal

SOURCES_FILE = Path(__file__).resolve().parents[1] / "engine_api_cards" / "javascript_packages.json"
SOURCES_RECORD = "javascript_api_card_sources/v1"
HOSTS = (RAW_HOST, REGISTRY_HOST)
#: Where a package and its dependencies are unpacked in the workspace, so Node resolves each require.
INSTALL_FOLDER, MODULES_FOLDER = "install", "node_modules"
LIMITS = ("The surface is what the JSDoc of the package's own published source files declares public (lodash's "
          "@memberOf _, Express's @public), each member confirmed by requiring the published module in Node: a member "
          "the library builds at run time without a JSDoc block (Express's app.get and the other HTTP method "
          "shortcuts) is not listed, and the types are the JSDoc's own claims, which a running module cannot confirm. "
          "The text is that JSDoc, with its examples; references to other members are names, not links. Nothing here "
          "was loaded by a harness.")


def read_sources(path: Path = SOURCES_FILE) -> dict:
    record = json.loads(Path(path).read_text(encoding="utf-8"))
    if record.get("record_type") != SOURCES_RECORD:
        raise ValueError(f"expected {SOURCES_RECORD}")
    return record


def package_row(record: dict, identity: str) -> dict:
    for row in record["packages"]:
        if row["identity"] == identity:
            return row
    raise LookupError(f"no package row {identity!r} in {SOURCES_FILE.name}")


def _install(reader, tarball: str, integrity: str, folder: Path, marker: str) -> object:
    """Stream one npm tarball, check its integrity and unpack it into folder; raises LineStopped."""
    digested = reader.digest(tarball, published={"integrity": integrity}, maximum_bytes=MAXIMUM_PACKAGE_BYTES,
                             inspect=lambda path: _package_files(path, folder),
                             use_cache=(folder / marker).is_file())
    if not digested.ok or (digested.inspected or {}).get("integrity") != integrity:
        raise LineStopped("engine_binary_unverified", f"{tarball}: the download does not match its integrity")
    return digested


def read_package(reader, workspace: Path, identity: str, *, record: "dict | None" = None, only=()) -> EngineSources:
    """Read one pinned JavaScript package release and its documented members; raises LineStopped."""
    record = record or read_sources()
    row = package_row(record, identity)
    name, version, repository, tag = row["package"], row["version"], row["repository"], row["tag"]
    address = https_address(REGISTRY_HOST, f"{name}/{version}")
    answer = reader.get(address)
    if answer.status != 200:
        raise LineStopped("source_unreadable", f"{name}@{version}: the registry did not answer")
    document = json.loads(answer.body)
    distribution = document.get("dist") or {}
    head = reader.github(f"repos/{repository}/commits/{tag}")
    if head.status != 200:
        raise LineStopped("source_unreadable", f"the tag {tag} has no readable commit")
    commit = json.loads(head.body)["sha"]
    if document.get("gitHead") != commit:
        raise LineStopped("engine_binary_unverified", f"{name}@{version} was built from {document.get('gitHead')}, "
                                                      f"not the tag's {commit[:12]}")
    root = Path(workspace) / INSTALL_FOLDER
    folder = root / MODULES_FOLDER / name
    tarball = distribution.get("tarball", "")
    digested = _install(reader, tarball, distribution.get("integrity"), folder, row["module"])
    for dependency in row.get("dependencies", ()):
        # A pinned dependency (a lock's path and version): its own registry record names its tarball and integrity.
        path, pinned_version = dependency["path"], dependency["version"]
        if not path.startswith(MODULES_FOLDER + "/") or ".." in path.split("/"):
            raise LineStopped("engine_binary_unverified", f"a dependency path {path[:80]} is refused")
        dependency_name = path.rsplit(MODULES_FOLDER + "/", 1)[1]
        found = reader.get(https_address(REGISTRY_HOST, f"{dependency_name}/{pinned_version}"))
        if found.status != 200:
            raise LineStopped("source_unreadable", f"{dependency_name}@{pinned_version}: the registry did not answer")
        dist = json.loads(found.body).get("dist") or {}
        _install(reader, dist.get("tarball", ""), dist.get("integrity"), root / path, "package.json")
    tree = reader.github(f"repos/{repository}/git/trees/{commit}?recursive=1")
    if tree.status != 200 or json.loads(tree.body).get("truncated"):
        raise LineStopped("source_unreadable", f"no complete tree at {commit[:12]}")
    blobs = {entry["path"]: entry["sha"] for entry in json.loads(tree.body).get("tree", []) if entry.get("type") == "blob"}
    found = reader.licence_text(repository, commit)
    if found is None:
        raise LineStopped("licence_unknown", f"{repository} at {commit[:12]}: no licence file")
    licence_path = found[0]
    pinned_licence, missing = pinned_files(reader, repository, commit, [licence_path])
    if missing:
        raise LineStopped("source_unreadable", licence_path)
    decision, licence_basis = tag_licence(reader, repository, commit, pinned_licence[licence_path])
    if not decision.allowed:
        raise LineStopped(decision.reason, f"{repository} at {commit[:12]}: {decision.evidence()}")
    package_licence = json.loads((folder / "package.json").read_text(encoding="utf-8")).get("license")
    shipped_licence = folder / licence_path
    if package_licence != decision.spdx or not shipped_licence.is_file() or \
            shipped_licence.read_bytes() != pinned_licence[licence_path]["bytes"]:
        raise LineStopped("licence_signals_disagree", f"the package names {package_licence}; its {licence_path} must "
                                                      "be the tag's")
    from loop_engine.core.library_ingestion.record_rules import git_blob_identity
    rules = row["rules"]
    files, refusals = {}, []
    for path in sorted(str(item.relative_to(folder)) for item in folder.rglob("*.js") if item.is_file()):
        if not any(re.fullmatch(rule["files"], path) and not re.fullmatch(rule.get("exclude", "(?!)"), path)
                   for rule in rules):
            continue
        data = (folder / path).read_bytes()
        if blobs.get(path) != git_blob_identity(data):
            refusals.append(refusal(ENGINE_API_CARDS, "published_source_differs", path, f"{name}@{version}"))
            continue
        files[path] = data
    units, problems = jsdoc_members.units({path: data.decode("utf-8") for path, data in files.items()}, rules,
                                          prefix=row.get("prefix", ""))
    refusals += [refusal(ENGINE_API_CARDS, reason, subject, detail) for subject, reason, detail in problems]
    if only:
        units = {key: unit for key, unit in units.items() if key in only}
    pinned, reference_paths, dump = {}, {}, {}
    for key, unit in sorted(units.items()):
        data = files[unit.file]
        if unit.file not in pinned:
            pinned[unit.file] = {"url": https_address(RAW_HOST, f"{repository}/{commit}/{unit.file}"), "bytes": data,
                                 "sha256": hashlib.sha256(data).hexdigest(), "blob": blobs[unit.file],
                                 "retrieved_at": digested.retrieved_at}
        reference_paths[key] = unit.file
        dump[key] = (unit.file, hashlib.sha256(data).hexdigest())
    module_file = folder / row["module"]
    code = cards.card_module().code
    major, minor = version.split(".")[:2]
    release = cards.EngineRelease(
        name=name, title=row["title"], release=tag, version=version, api_version=f"{major}.{minor}",
        repository=repository, commit=commit, binary_name=Path(tarball).name, binary_sha256=digested.sha256,
        binary_version=version, docs_address="", syntax=cards.card_module().JAVASCRIPT_SYNTAX,
        surface_source=(f"read from the JSDoc of `{name}@{version}` (`{Path(tarball).name}`, SHA-256 "
                        f"`{digested.sha256}`), each member confirmed by requiring its `{row['module']}` in Node"),
        surface_phrase="the surface the package's own JSDoc declares and its published module confirms",
        text_format="JSDoc", licence=decision.spdx, text_phrase="the library's own JSDoc")
    licence = dict(pinned_licence[licence_path], evidence=decision.evidence(), basis=licence_basis)
    metadata = {"url": address, "bytes": answer.body, "sha256": answer.sha256, "retrieved_at": answer.retrieved_at}
    asset = {"url": tarball, "sha256": digested.sha256, "size_bytes": digested.size_bytes,
             "retrieved_at": digested.retrieved_at, "member": row["module"]}
    references = {key: unit.reference for key, unit in units.items()}
    summary = {"package": f"{name}@{version}", "surface_engine": "jsdoc_public", "verifier_engine": "node_require",
               "files_read": len(files), "dependencies": len(row.get("dependencies", ())),
               "units": {kind: sum(1 for unit in units.values() if unit.reference.kind.value == kind)
                         for kind in ("function", "object", "method", "property")}}
    try:
        engine = node_native.locate(row["module"], hashlib.sha256(module_file.read_bytes()).hexdigest())
    except NativeError as error:
        raise LineStopped("engine_binary_unverified", str(error)) from None
    return EngineSources(
        release, dump, references, dict(references), reference_paths, pinned, licence, None, {}, None, asset, refusals,
        summary, text_for=lambda key: jsdoc_reference.JsDocText(code), licence_path=licence_path,
        text_basis=LICENCE_AT_THE_TAG, limits=LIMITS, state_scope=row["state_scope"], metadata=metadata,
        licence_expression=GENERATED_CODE_LICENCE if decision.spdx == GENERATED_CODE_LICENCE else
        f"{GENERATED_CODE_LICENCE} AND {decision.spdx}",
        chains={key: [] for key in units}, children={key: [] for key in units},
        locations={key: unit.path for key, unit in units.items()}, native=(engine, module_file))


def package_evidence(sources: EngineSources, prepared: dict, workspace: Path, folder: "Path | None" = None) -> dict:
    """{card: evidence bytes} from one Node run over every prepared card; a run that cannot happen gives no evidence,
    so every card is refused by name (native_evidence_missing)."""
    engine, module_file = sources.native
    try:
        answers = node_members.verify(engine, module_file, [card.api for card in prepared.values()],
                                      sources.locations, Path(workspace) / "verify")
    except NativeError as error:
        sources.summary["native_check_error"] = str(error)[:300]
        return {}
    records = {}
    for key, card in prepared.items():
        data = evidence_bytes(node_members.evidence(engine, card.api, answers.get(key), card.digest))
        records[key] = data
        if folder is not None:
            target = Path(folder) / card.api["engine"]["name"] / f"{re.sub(r'[^A-Za-z0-9_.-]', '_', key)}.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    return records


__all__ = ["read_sources", "package_row", "read_package", "package_evidence", "HOSTS", "LIMITS", "SOURCES_FILE",
           "INTEGRITY_PREFIX"]
