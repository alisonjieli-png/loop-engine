"""Complete original native packages behind the existing preparation/staging tools.

No execution, installation, network, model call, review or promotion occurs.
CataloguePackage owns file roles, path rules and canonical package identity.
The existing authoritative catalogue stores the resulting candidate metadata.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import re
import stat
from pathlib import Path

from loop_engine.core.facets import EFFECTS
from loop_engine.core.harness_intelligence import KINDS, HarnessIntelligenceItem
from loop_engine.core.intelligence_tagging import TagSet
from loop_engine.core.model_call_records import default_secret_patterns
from loop_engine.core.service_runtime.catalogue_packages import (
    EXECUTABLE_EFFECT,
    MAXIMUM_PACKAGE_FILES,
    CataloguePackage,
    CataloguePackageFile,
    placement_path,
)
from loop_engine.core.service_runtime.records import ServiceRuntimeError
from tools import prepare_harness_candidates as preparation

NATIVE_SPECIFICATIONS = "candidate_intelligence_specifications/v3"
NATIVE_ITEMS = "starter_catalogue_candidate_items/v3"
NATIVE_REPORT = "harness_candidate_preparation_report/v2"
NATIVE_FIELDS = (preparation.REQUIRED_PROPOSAL_FIELDS - {"body"}) | {
    "symbols", "declared_effects", "kind", "styles", "dependencies", "producer", "files"}
SPEC_FIELDS = {"id", "layer", "family", "title", "tags", "text", "sources", "symbols", "kind",
               "purpose", "styles", "dependencies", "producer", "declared_effects", "package",
               "package_digest", "package_root", "body_path", "provenance"}
PROVENANCE_FIELDS = {"authoring", "source_revision", "source_digests", "license"}
FILE_FIELDS = {"path", "digest", "size_bytes", "media_type", "role", "content_base64"}


def _refuse(code):
    preparation._refuse(code)


def _strings(value, name, maximum=64):
    return preparation._string_list(value, name, maximum=maximum, may_be_empty=True)


def _metadata(row):
    producer = row["producer"]
    if (type(producer) is not dict or set(producer) != {"producer_identity", "family", "method_identity"}
            or any(type(value) is not str or not value.strip() or len(value) > 160
                   or any(ord(char) < 32 for char in value) for value in producer.values())):
        _refuse("native_producer_invalid")
    if re.fullmatch(r"[a-z][a-z0-9_.-]*(?:/[a-z0-9_.-]+)*/v[1-9][0-9]*", producer["method_identity"]) is None:
        _refuse("native_producer_invalid")
    _strings(row["dependencies"], "native_dependencies_invalid")
    _strings(row["styles"], "native_styles_invalid", 20)
    effects = _strings(row["declared_effects"], "native_effects_invalid", 20)
    if any(effect not in EFFECTS for effect in effects) or ("pure" in effects and len(effects) > 1):
        _refuse("native_effects_invalid")
    preparation._text(row["purpose"], "native_purpose_invalid", maximum=1024, one_line=True)
    if row["kind"] not in KINDS or row["kind"] == "reusable_code":
        _refuse("native_kind_invalid")


def _package(value, effects):
    try:
        package = CataloguePackage.from_dict(value)
    except (ServiceRuntimeError, TypeError, ValueError):
        _refuse("native_package_invalid")
    if package.body_form != "package":
        _refuse("native_package_body_form_required")
    folded = {entry.path.casefold() for entry in package.files}
    if any("/".join(path.split("/")[:index]) in folded for path in folded
           for index in range(1, len(path.split("/")))):
        _refuse("native_package_path_collision")
    if package.executable and EXECUTABLE_EFFECT not in effects:
        _refuse("package_executable_effect_undeclared")
    return package


def _files(values, effects):
    if not isinstance(values, list) or not 1 <= len(values) <= MAXIMUM_PACKAGE_FILES:
        _refuse("native_files_required")
    metadata, bodies = [], {}
    for value in values:
        if type(value) is not dict or set(value) != FILE_FIELDS:
            _refuse("native_file_invalid")
        try:
            entry = CataloguePackageFile.from_dict({key: value[key] for key in FILE_FIELDS - {"content_base64"}})
            body = base64.b64decode(value["content_base64"], validate=True)
        except (ServiceRuntimeError, TypeError, ValueError, binascii.Error):
            _refuse("native_file_invalid")
        if len(body) != entry.size_bytes or hashlib.sha256(body).hexdigest() != entry.digest:
            _refuse("native_file_bytes_mismatch")
        if any(re.search(pattern, body.decode("utf-8", "replace")) for pattern in default_secret_patterns()):
            _refuse("native_secret_pattern_refused")
        metadata.append(entry.to_dict())
        bodies[entry.path] = body
    package = _package({"body_form": "package", "files": metadata}, effects)
    return package, bodies


def _proposal_metadata(record):
    """Reuse existing source, tag, identity and effect validation without inventing another item."""
    proposals = record["proposals"]
    if not isinstance(proposals, list) or not 1 <= len(proposals) <= preparation.MAXIMUM_CANDIDATES:
        _refuse("candidate_population_out_of_bounds")
    normalized = []
    for row in proposals:
        if type(row) is not dict or set(row) != NATIVE_FIELDS:
            _refuse("invalid_native_candidate_fields")
        _metadata(row)
        copied = {key: row[key] for key in preparation.PROPOSAL_FIELDS - {"body"}}
        copied["body"] = f"# {row['title']}\n\n{row['purpose']}\n"
        normalized.append(copied)
    return {**record, "proposals": normalized}


def prepare_native(request, record, raw, revision, source_digests, license_name):
    """Materialize exact complete trees and canonical documents in a new candidate folder."""
    normalized = _proposal_metadata(record)
    _bodies, metadata, _items = preparation._compile(normalized, revision, source_digests, license_name)
    documents, specifications, item_rows, digests = {}, [], [], set()
    payload_count, unique_files = 0, set()
    for proposal, meta in zip(record["proposals"], metadata):
        package, files = _files(proposal["files"], proposal["declared_effects"])
        if package.package_digest in digests:
            _refuse("duplicate_native_package")
        digests.add(package.package_digest)
        identity = proposal["id"]
        package_root, body_path = f"packages/{identity}", f"bodies/{identity}.package.json"
        for relative, body in files.items():
            documents[f"{package_root}/{relative}"] = body
        documents[body_path] = package.document()
        payload_count += len(package.files)
        unique_files.update(entry.digest for entry in package.files)
        item = HarnessIntelligenceItem(
            identity=identity, kind=proposal["kind"], purpose=proposal["purpose"],
            digest=package.served_digest, size_bytes=package.served_size, source_layer="harness_local",
            source_ref=f"{proposal['sources'][0]}@{revision}", license_name=license_name,
            declared_effects=tuple(proposal["declared_effects"]), styles=tuple(proposal["styles"]),
            tags=TagSet({**proposal["tags"], "lifecycle": ["candidate"]}))
        provenance = {"authoring": "original_assistant_authored", "source_revision": revision,
                      "source_digests": {key: source_digests[key] for key in proposal["sources"]},
                      "license": record["license"]}
        specifications.append({**meta, "kind": proposal["kind"], "purpose": proposal["purpose"],
            "styles": proposal["styles"], "dependencies": proposal["dependencies"],
            "producer": proposal["producer"], "declared_effects": proposal["declared_effects"],
            "package": package.to_dict(), "package_digest": package.package_digest,
            "package_root": package_root, "body_path": body_path, "provenance": provenance})
        item_rows.append({"reference": item.reference(), "body_path": body_path,
                          "package": package.to_dict(), "package_root": package_root,
                          "producer": proposal["producer"], "dependencies": proposal["dependencies"]})
    # Recheck sources after all payload compilation and before the first write.
    if preparation._git(request.repository, "rev-parse", "HEAD").decode().strip() != revision:
        _refuse("revision_mismatch")
    for relative, digest in source_digests.items():
        preparation._checked_source(request.repository, revision, relative, digest)
    count = (len(specifications) + preparation.POPULATION_SIZE - 1) // preparation.POPULATION_SIZE
    names = [f"specifications-{number:03d}.json" for number in range(1, count + 1)]
    for number, name in enumerate(names):
        start = number * preparation.POPULATION_SIZE
        documents[name] = preparation._json_bytes({"record_type": NATIVE_SPECIFICATIONS,
            "population": number + 1, "populations": count,
            "specifications": specifications[start:start + preparation.POPULATION_SIZE]})
    documents["items.json"] = preparation._json_bytes({"record_type": NATIVE_ITEMS,
        "source_revision": revision, "source_digests": source_digests,
        "publication": "not_published", "items": item_rows})
    report = {"record_type": NATIVE_REPORT, "complete": True, "candidates": len(specifications),
        "payload_files": payload_count, "unique_payload_digests": len(unique_files),
        "population_files": names, "source_revision": revision,
        "input_sha256": hashlib.sha256(raw).hexdigest(), "approved": False,
        "hosted_publication": False, "semantic_grounding_verified": False,
        "limits": "Original candidate declarations and exact package bytes only; dependency resolution, native loading, rights, safety and usefulness require independent review."}
    documents["preparation-report.json"] = preparation._json_bytes(report)
    output = preparation._output_path(request.output)
    output.mkdir(mode=0o700)
    for relative, body in documents.items():
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with target.open("xb") as stream:
            stream.write(body)
    return report


def _confined(root, relative, *, directory=False):
    try:
        placement_path(relative)
    except ServiceRuntimeError:
        _refuse("native_package_path_invalid")
    target = root
    for segment in relative.split("/"):
        target = target / segment
        if target.is_symlink():
            _refuse("native_package_not_regular")
    try:
        mode = target.lstat().st_mode
    except OSError:
        _refuse("native_package_inventory_mismatch")
    if not (stat.S_ISDIR(mode) if directory else stat.S_ISREG(mode)):
        _refuse("native_package_not_regular")
    return target


def _verify_tree(root, row, package):
    folder = _confined(root, row["package_root"], directory=True)
    expected = {entry.path for entry in package.files}
    found = set()
    for current, dirs, files in os.walk(folder, followlinks=False):
        for name in dirs + files:
            path = Path(current) / name
            mode = path.lstat().st_mode
            if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
                _refuse("native_package_not_regular")
            if stat.S_ISREG(mode):
                found.add(path.relative_to(folder).as_posix())
    if found != expected:
        _refuse("native_package_inventory_mismatch")
    for entry in package.files:
        file = _confined(folder, entry.path)
        if file.stat().st_size != entry.size_bytes:
            _refuse("native_file_bytes_mismatch")
        payload = file.read_bytes()
        if hashlib.sha256(payload).hexdigest() != entry.digest:
            _refuse("native_file_bytes_mismatch")
    body = _confined(root, row["body_path"])
    if body.stat().st_size != len(package.document()) or body.read_bytes() != package.document():
        _refuse("native_package_document_mismatch")


def compile_native_candidates(rows, request):
    """Validate complete candidate trees, then return records for the existing atomic stage."""
    if request.package_root is None:
        _refuse("package_root_required")
    root = Path(request.package_root).absolute()
    if not root.is_dir() or root.resolve() != root:
        _refuse("native_package_root_invalid")
    records, identities = [], set()
    for row in rows:
        if type(row) is not dict or set(row) != SPEC_FIELDS:
            _refuse("native_specification_invalid")
        _metadata(row)
        provenance = row["provenance"]
        if (type(provenance) is not dict or set(provenance) != PROVENANCE_FIELDS
                or provenance["authoring"] != "original_assistant_authored"):
            _refuse("native_provenance_invalid")
        # Existing local source compiler owns classification and local source confinement.
        from tools.stage_intelligence_candidates import compile_candidates
        local = {key: row[key] for key in preparation.PROPOSAL_FIELDS if key in ("id", "layer", "family", "title", "tags", "symbols")}
        local.update(text=row["text"], sources=row["sources"])
        base = compile_candidates({"record_type": "candidate_intelligence_specifications/v1",
                                   "specifications": [local]}, request)[0]
        if row["id"] in identities:
            _refuse("duplicate_identity")
        identities.add(row["id"])
        revision = provenance["source_revision"]
        if not isinstance(revision, str) or preparation.REVISION.fullmatch(revision) is None:
            _refuse("native_provenance_invalid")
        if (type(provenance["source_digests"]) is not dict
                or set(provenance["source_digests"]) != set(row["sources"]) - {"LICENSE"}):
            _refuse("native_provenance_invalid")
        licence = provenance["license"]
        preparation._object(licence, {"expression", "path", "sha256"}, "unknown_license")
        if licence["expression"] != "MIT" or licence["path"] != "LICENSE":
            _refuse("unknown_license")
        for relative, digest in {**provenance["source_digests"], "LICENSE": licence["sha256"]}.items():
            preparation._checked_source(request.repository, revision, relative, digest)
        package = _package(row["package"], row["declared_effects"])
        if row["package_digest"] != package.package_digest:
            _refuse("native_package_digest_mismatch")
        if row["package_root"] != f"packages/{row['id']}" or row["body_path"] != f"bodies/{row['id']}.package.json":
            _refuse("native_package_path_invalid")
        _verify_tree(root, row, package)
        payload = {**base["payload"], "record_type": "candidate_intelligence_specification/v3",
            "kind": row["kind"], "purpose": row["purpose"], "package": package.to_dict(),
            "package_digest": package.package_digest, "package_root": row["package_root"],
            "body_path": row["body_path"], "dependencies": row["dependencies"], "styles": row["styles"],
            "producer": row["producer"], "declared_effects": row["declared_effects"], "provenance": provenance}
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        version = hashlib.sha256(json.dumps({"payload": payload, "layer": row["layer"], "tags": row["tags"]},
                                           sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        records.append({**base, "record_version": version, "payload": payload,
                        "attributes": {**base["attributes"], "content_sha256": digest}})
    return records
