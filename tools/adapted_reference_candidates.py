"""Stage source-adapted reference packages without inventing original authorship.

This reader proves local snapshot and package integrity only. It does not approve
an item, certify live service behavior, execute content, or contact a source.
Review policy is selected separately and may reuse qualified transformation evidence.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from loop_engine.core.library_ingestion.licences import LicencePolicy, match_licence
from loop_engine.core.library_ingestion.provenance import read_outside_provenance
from loop_engine.core.library_ingestion.record_rules import (
    canonical_digest,
    digest_value,
    read_part,
    read_record,
    sequence,
    text_value,
)
from loop_engine.core.service_runtime.catalogue_packages import CataloguePackage
from tools import native_harness_candidates as native
from tools import prepare_harness_candidates as preparation

ADAPTED_SPECIFICATIONS = "candidate_intelligence_specifications/v4"
ADAPTATION_RECORD = "reference_adaptation/v1"
PAYLOAD_RECORD = "candidate_intelligence_specification/v4"
AUTHORING = "adapted_reference_under_permissive_licence"
FIELDS = {"id", "layer", "family", "title", "purpose", "text", "tags", "kind", "component_type", "styles",
          "dependencies", "producer", "declared_effects", "package", "package_digest", "package_root", "body_path",
          "outside_provenance", "source_blobs", "license", "adaptation"}
ADAPTATION_FIELDS = ("method_identity", "compiler_sha256", "parameters", "source_digests", "description", "target_package_digest")
PASSIVE_TYPES = frozenset({"text/plain", "text/markdown", "application/json", "application/schema+json"})
PASSIVE_ROLES = frozenset({"instruction_file", "skill_reference", "configuration", "other"})
MAX_SOURCE_BYTES = 32 * 1024 * 1024
METHOD = re.compile(r"[a-z][a-z0-9_.-]*(?:/[a-z0-9_.-]+)*/v[1-9][0-9]*\Z")


def refuse(code):
    raise ValueError(code)


def plain_root(value, code):
    if value is None:
        refuse(code)
    root = Path(value).absolute()
    if not root.is_dir() or root.resolve() != root:
        refuse(code)
    return root


def bounded_file(root, relative, maximum):
    # Reuse the current confined package-path checks; no directory traversal or links.
    path = native._confined(root, relative)
    if path.stat().st_size > maximum:
        refuse("reference_file_too_large")
    with path.open("rb") as stream:
        raw = stream.read(maximum + 1)
    if len(raw) > maximum:
        refuse("reference_file_too_large")
    return raw


def source_evidence(row, source_root, files):
    declared = row["outside_provenance"]
    if type(declared) is not list or not 1 <= len(declared) <= 20:
        refuse("outside_provenance_required")
    proofs = [read_outside_provenance(value) for value in declared]
    # This profile preserves one permissive licence expression. It does not
    # reinterpret outline-only or link-only decisions as adaptation rights.
    expression = row["license"]["expression"]
    if expression not in LicencePolicy().accepted:
        refuse("adaptation_rights_not_established")
    for proof in proofs:
        if proof.decision != "verbatim_permitted" or proof.spdx != expression:
            refuse("adaptation_rights_not_established")
    snapshots = row["source_blobs"]
    if type(snapshots) is not list or len(snapshots) != len(proofs):
        refuse("source_blob_population_invalid")
    indices = set()
    for entry in snapshots:
        read_part(entry, "source_blob", ("source_index", "snapshot_path"))
        index = entry["source_index"]
        if type(index) is not int or not 0 <= index < len(proofs) or index in indices:
            refuse("source_blob_population_invalid")
        indices.add(index)
        proof = proofs[index]
        raw = bounded_file(source_root, entry["snapshot_path"], MAX_SOURCE_BYTES)
        if len(raw) != proof.source_size_bytes or hashlib.sha256(raw).hexdigest() != proof.source_digest:
            refuse("source_blob_mismatch")
        if proof.origin == "github_repository":
            blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
            if blob != proof.git_blob_sha:
                refuse("source_blob_mismatch")
    texts = row["license"]["upstream_texts"]
    if type(texts) is not list or len(texts) != len(proofs):
        refuse("upstream_licence_population_invalid")
    indices = set()
    for entry in texts:
        read_part(entry, "upstream_licence", ("source_index", "path"))
        index = entry["source_index"]
        if type(index) is not int or not 0 <= index < len(proofs) or index in indices:
            refuse("upstream_licence_population_invalid")
        indices.add(index)
        proof = proofs[index]
        payload = files.get(entry["path"])
        expected = proof.licence_evidence["governing_file"]["sha256"]
        if payload is None or hashlib.sha256(payload).hexdigest() != expected:
            refuse("upstream_licence_bytes_missing")
        match = match_licence(payload.decode("utf-8"))
        if match.spdx != expression or match.reason != "recognized":
            refuse("upstream_licence_not_recognized")
        # Required extra notice files travel by exact digest, regardless of placement.
        carried = {hashlib.sha256(value).hexdigest() for value in files.values()}
        for notice in proof.licence_evidence["file_level_notices"]:
            if notice["kind"] == "notice_file" and notice["sha256"] not in carried:
                refuse("upstream_licence_notice_missing")
    return proofs


def compile_adapted_candidates(rows, request):
    """Return existing catalogue records after exact source and package checks."""
    root = plain_root(request.package_root, "package_root_required")
    source_root = plain_root(request.source_root, "source_root_required")
    records, identities = [], set()
    for row in rows:
        read_part(row, "adapted_reference", FIELDS)
        identity = row["id"]
        if type(identity) is not str or preparation.IDENTITY.fullmatch(identity) is None or len(identity) > 64:
            refuse("reference_identity_invalid")
        if identity in identities:
            refuse("duplicate_identity")
        identities.add(identity)
        if row["layer"] != "context" or row["kind"] != "instruction_file":
            refuse("reference_kind_invalid")
        if row["declared_effects"] != ["reads_fs"]:
            refuse("reference_effects_invalid")
        native._metadata(row)
        for key, limit in (("title", 160), ("purpose", 1024), ("family", 160), ("component_type", 160)):
            text_value(row[key], key, limit=limit)
        if type(row["text"]) is not str or not row["text"].startswith("# ") or len(row["text"]) > 65536:
            refuse("instruction_text_invalid")
        sequence(row["tags"], "tags", lambda value, name: text_value(value, name, limit=160))
        if row["package_root"] != "packages/" + identity or row["body_path"] != "bodies/" + identity + ".package.json":
            refuse("reference_package_path_invalid")
        package = CataloguePackage.from_dict(row["package"])
        if package.body_form != "package" or package.package_digest != row["package_digest"]:
            refuse("reference_package_binding_invalid")
        for entry in package.files:
            if entry.role not in PASSIVE_ROLES or entry.media_type not in PASSIVE_TYPES:
                refuse("reference_file_kind_invalid")
        native._verify_tree(root, row, package)
        folder = root / row["package_root"]
        files = {entry.path: bounded_file(folder, entry.path, entry.size_bytes) for entry in package.files}
        for payload in files.values():
            try:
                payload.decode("utf-8")
            except UnicodeError:
                refuse("reference_text_not_utf8")
        if files.get("AGENTS.md") != row["text"].encode("utf-8"):
            refuse("instruction_text_not_bound")
        licence = read_part(row["license"], "adapted_licence", ("expression", "original_text_path", "upstream_texts"))
        original = files.get(licence["original_text_path"])
        if original is None:
            refuse("original_licence_text_missing")
        matched = match_licence(original.decode("utf-8"))
        if matched.spdx != licence["expression"] or matched.reason != "recognized":
            refuse("original_licence_not_recognized")
        proofs = source_evidence(row, source_root, files)
        adaptation = read_record(row["adaptation"], ADAPTATION_RECORD, ADAPTATION_FIELDS)
        if type(adaptation["method_identity"]) is not str or METHOD.fullmatch(adaptation["method_identity"]) is None:
            refuse("adaptation_method_invalid")
        digest_value(adaptation["compiler_sha256"], "compiler_sha256")
        text_value(adaptation["description"], "description", limit=2000)
        if type(adaptation["parameters"]) is not dict or len(json.dumps(adaptation["parameters"], allow_nan=False).encode()) > 32768:
            refuse("adaptation_parameters_invalid")
        expected_sources = sorted({proof.source_digest for proof in proofs})
        if adaptation["source_digests"] != expected_sources or adaptation["target_package_digest"] != package.package_digest:
            refuse("adaptation_binding_invalid")
        payload = {**row, "record_type": PAYLOAD_RECORD, "authoring": AUTHORING, "lifecycle": "candidate",
                   "execution_available": False, "license_state": "pending_review",
                   "qualification": "not_independently_qualified", "source_snapshot_integrity": "checked",
                   "transformation_fidelity": "pending_independent_review"}
        digest = canonical_digest(payload)
        records.append({"record_id": request.namespace + "." + identity, "record_version": digest,
            "intelligence_layer": "context", "source_collection": "learned", "artifact_kind": "intelligence_record",
            "lifecycle": "candidate", "namespace": request.namespace,
            "attributes": {"family": row["family"], "tags": row["tags"], "title": row["title"],
                           "content_sha256": digest, "package_digest": package.package_digest,
                           "authoring": AUTHORING, "license_state": "pending_review"}, "payload": payload})
    return records
