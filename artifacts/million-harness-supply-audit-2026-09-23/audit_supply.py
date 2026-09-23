"""Offline, read-only inventory of existing harness candidate and release records.

This is an audit projection, not an importer, reviewer, admission service or
source of authority. SQLite lives in a temporary directory so file and package
deduplication does not require a million Python objects in memory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sqlite3
import subprocess
import tempfile
from collections import Counter
from pathlib import Path

SHA = re.compile(r"[0-9a-f]{64}\Z")
SKILL_BATCH = "first_party_harness_candidate_batch_manifest/v1"
MIXED_BATCH = "heterogeneous_harness_candidate_file_manifest/v2"
MULTIFILE_BATCH = "first_party_multifile_manifest/v1"
PANEL = "starter_catalogue_panel_review/v1"
HISTORICAL_REVIEW = "starter_catalogue_independent_review/v1"
BUNDLE = "catalogue_release_bundle/v1"
BUNDLE_ITEM = "catalogue_bundle_item/v1"
MAX_JSON_BYTES = 32_000_000
MAX_LINE_BYTES = 65_536
ANCHOR = re.compile(rb"Written for this catalogue at revision [a-f0-9]{7,40}\.\n\Z")


class AuditError(ValueError):
    """One input cannot safely contribute to the inventory."""


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise AuditError("duplicate_json_field")
        result[key] = value
    return result


def _json(raw: bytes, *, label: str) -> dict:
    try:
        value = json.loads(
            raw,
            object_pairs_hook=_unique,
            parse_constant=lambda _value: (_ for _ in ()).throw(
                AuditError("nonfinite_json_number")
            ),
        )
    except (UnicodeError, ValueError, RecursionError) as error:
        raise AuditError(f"invalid_json:{label}:{error}") from None
    if not isinstance(value, dict):
        raise AuditError(f"not_json_object:{label}")
    return value


def _read(path: Path, *, limit: int = MAX_JSON_BYTES) -> tuple[dict, str]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise AuditError(f"input_missing_symlinked_or_oversized:{path}")
    raw = path.read_bytes()
    return _json(raw, label=str(path)), hashlib.sha256(raw).hexdigest()


def _digest(value: str) -> str:
    if not isinstance(value, str) or not SHA.fullmatch(value):
        raise AuditError("invalid_sha256")
    return value


def _body(root: Path, relative: str, digest: str, size: int) -> None:
    """Check an exact regular file, including all ancestors, without following links."""
    if not isinstance(relative, str) or not relative or relative.startswith("/"):
        raise AuditError("unsafe_relative_path")
    parts = relative.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise AuditError("unsafe_relative_path")
    if type(size) is not int or size < 0:
        raise AuditError("invalid_file_size")
    _digest(digest)
    target = root
    for part in parts:
        target = target / part
        if target.is_symlink():
            raise AuditError("symlink_in_input_path")
    if not target.is_file() or target.stat().st_size != size:
        raise AuditError(f"missing_or_resized_body:{relative}")
    check = hashlib.sha256()
    with target.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            check.update(chunk)
    if check.hexdigest() != digest:
        raise AuditError(f"changed_body:{relative}")


def _db(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        PRAGMA journal_mode=OFF;
        PRAGMA synchronous=OFF;
        PRAGMA temp_store=FILE;
        PRAGMA cache_size=-16000;
        CREATE TABLE packages (
            population TEXT NOT NULL, source TEXT NOT NULL, identity TEXT NOT NULL,
            kind TEXT NOT NULL, review_state TEXT NOT NULL, risk TEXT NOT NULL,
            host_packaged INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (population, source, identity)
        );
        CREATE TABLE files (
            population TEXT NOT NULL, source TEXT NOT NULL, identity TEXT NOT NULL,
            path TEXT NOT NULL, digest TEXT NOT NULL, bytes INTEGER NOT NULL,
            role TEXT NOT NULL,
            PRIMARY KEY (population, source, identity, path)
        );
        CREATE INDEX files_digest ON files (population, digest);
        CREATE TABLE review_events (
            identity TEXT NOT NULL, source TEXT NOT NULL, body_digest TEXT,
            outcome TEXT NOT NULL, normalized_digest TEXT,
            PRIMARY KEY (identity, source)
        );
        """
    )


def _package(db, population, source, identity, kind, state, risk, hosted=0):
    if not isinstance(identity, str) or not identity:
        raise AuditError("package_identity_missing")
    try:
        db.execute(
            "INSERT INTO packages VALUES (?,?,?,?,?,?,?)",
            (population, source, identity, kind, state, risk, int(hosted)),
        )
    except sqlite3.IntegrityError:
        raise AuditError(f"duplicate_package_identity:{source}:{identity}") from None


def _file(db, population, source, identity, path, digest, size, role):
    _digest(digest)
    if type(size) is not int or size < 0:
        raise AuditError("invalid_file_size")
    try:
        db.execute(
            "INSERT INTO files VALUES (?,?,?,?,?,?,?)",
            (population, source, identity, path, digest, size, role),
        )
    except sqlite3.IntegrityError:
        raise AuditError(f"duplicate_package_file:{source}:{identity}:{path}") from None


def _event(db, identity, source, digest, outcome, normalized_digest=None):
    if digest is not None:
        _digest(digest)
    if normalized_digest is not None:
        _digest(normalized_digest)
    try:
        db.execute(
            "INSERT INTO review_events VALUES (?,?,?,?,?)",
            (identity, source, digest, outcome, normalized_digest),
        )
    except sqlite3.IntegrityError:
        raise AuditError(f"duplicate_review_event:{source}:{identity}") from None


def _starter(db, folder: Path, inputs: list[dict]) -> int:
    items, items_sha = _read(folder / "items.json")
    reviews, reviews_sha = _read(folder / "reviews.json")
    host, host_sha = _read(folder / "host-release/manifest.json")
    inputs.extend(
        [
            {"path": str(folder / "items.json"), "sha256": items_sha},
            {"path": str(folder / "reviews.json"), "sha256": reviews_sha},
            {"path": str(folder / "host-release/manifest.json"), "sha256": host_sha},
        ]
    )
    if (
        items.get("record_type") != "starter_catalogue_candidate_items/v2"
        or reviews.get("record_type") != "starter_catalogue_independent_review/v2"
        or host.get("record_type") != "host_attested_intelligence_manifest/v1"
    ):
        raise AuditError("starter_record_type_mismatch")
    if items.get("source_revision") != reviews.get("catalogue_source_revision"):
        raise AuditError("starter_review_revision_mismatch")
    review_rows = {}
    for row in reviews["rows"]:
        identity = row["identity"]
        if identity in review_rows:
            raise AuditError("duplicate_starter_review")
        review_rows[identity] = row
    hosted = {}
    for row in host["items"]:
        identity = row["reference"]["identity"]
        if identity in hosted:
            raise AuditError("duplicate_host_identity")
        hosted[identity] = row
    source_refs = set()
    seen = set()
    for row in items["items"]:
        reference = row["reference"]
        identity = reference["identity"]
        if identity in seen or identity not in review_rows:
            raise AuditError("starter_item_or_review_missing")
        seen.add(identity)
        source_refs.add(reference["source_ref"])
        digest, size = reference["digest"], reference["size_bytes"]
        _body(folder, row["body_path"], digest, size)
        review = review_rows[identity]
        state = review["outcome"]
        if state not in ("approved", "rejected", "not_reviewed", "carry_refused"):
            raise AuditError("starter_review_outcome_unknown")
        # A rejection can describe historical bytes. Re-anchoring changed the
        # current body without turning that old rejection into an approval.
        if state == "approved" and review["body_digest"] != digest:
            raise AuditError("starter_review_digest_mismatch")
        if state == "approved" and (
            not review.get("approval_ref")
            or not all(
                decision.get("decision") == "approve"
                for decision in review["decisions"]
            )
        ):
            raise AuditError("starter_approval_inconsistent")
        if identity in hosted:
            host_row = hosted[identity]
            if (
                state != "approved"
                or host_row["reference"]["digest"] != digest
                or host_row["approval_ref"] != review["approval_ref"]
            ):
                raise AuditError("host_item_not_reviewed_exactly")
            _body(folder / "host-release", host_row["body_path"], digest, size)
        _package(
            db,
            "local",
            "starter",
            identity,
            reference["kind"],
            state,
            "instruction",
            identity in hosted,
        )
        _file(
            db,
            "local",
            "starter",
            identity,
            row["body_path"],
            digest,
            size,
            "single_markdown_body",
        )
        _event(db, identity, "starter/reviews.json", review["body_digest"], state)
    if seen != set(review_rows) or not set(hosted) <= seen:
        raise AuditError("starter_population_mismatch")
    return len(source_refs)


def _skill_batch(db, folder: Path, manifest: dict) -> None:
    if (
        manifest.get("approval_state") != "none"
        or manifest.get("rights_state") != "pending_independent_review"
    ):
        raise AuditError("candidate_manifest_claims_approval")
    entries = manifest["entries"]
    if manifest["package_count"] != len(entries):
        raise AuditError("skill_batch_count_mismatch")
    source = folder.name
    for row in entries:
        identity = row["name"]
        _body(folder, row["package_path"], row["package_sha256"], row["package_bytes"])
        _body(
            folder,
            row["review_note_path"],
            row["review_note_sha256"],
            row["review_note_bytes"],
        )
        _package(
            db,
            "local",
            source,
            identity,
            "agent_skill",
            "candidate_only",
            "instruction",
        )
        _file(
            db,
            "local",
            source,
            identity,
            row["package_path"],
            row["package_sha256"],
            row["package_bytes"],
            "skill_definition",
        )


def _mixed_batch(
    db, folder: Path, manifest: dict, inputs: list[dict]
) -> tuple[int, int]:
    catalogue, digest = _read(folder / "candidate-items.json")
    inputs.append({"path": str(folder / "candidate-items.json"), "sha256": digest})
    if (
        manifest.get("approval_state") != "none"
        or manifest.get("rights_state") != "pending_independent_review"
        or catalogue.get("approval_state") != "none"
        or catalogue.get("record_type") != "heterogeneous_harness_candidate_catalog/v1"
    ):
        raise AuditError("mixed_candidate_state_mismatch")
    inventory = {}
    for row in manifest["entries"]:
        path = row["path"]
        if path in inventory:
            raise AuditError("mixed_manifest_duplicate_path")
        _body(folder, path, row["sha256"], row["bytes"])
        inventory[path] = row
    used = set()
    variant_count = 0
    bindings = 0
    for item in catalogue["items"]:
        identity, kind = item["id"], item["kind"]
        risk = (
            "executable_or_connection"
            if kind in ("skill_with_python_tool", "local_protocol_server_connection")
            else "instruction"
        )
        _package(db, "local", folder.name, identity, kind, "candidate_only", risk)
        paths = set()
        for client, files in item["delivery_variants"].items():
            if not isinstance(client, str) or not client or not files:
                raise AuditError("empty_client_variant")
            variant_count += 1
            bindings += len(files)
            paths.update(files)
        for path in sorted(paths):
            row = inventory.get(path)
            if row is None or row["file_role"] != "delivery_payload" or path in used:
                raise AuditError("mixed_delivery_untracked_or_shared_between_methods")
            used.add(path)
            _file(
                db,
                "local",
                folder.name,
                identity,
                path,
                row["sha256"],
                row["bytes"],
                kind,
            )
    if used != {
        path
        for path, row in inventory.items()
        if row["file_role"] == "delivery_payload"
    }:
        raise AuditError("mixed_delivery_unassigned")
    if len(used) != manifest["delivery_payload_file_count"]:
        raise AuditError("mixed_delivery_count_mismatch")
    return variant_count, bindings


def _multifile_batch(db, folder: Path, manifest: dict, inputs: list[dict]) -> None:
    catalogue, digest = _read(folder / "candidate-items.json")
    inputs.append({"path": str(folder / "candidate-items.json"), "sha256": digest})
    if (
        manifest.get("approval_state") != "candidate_only"
        or catalogue.get("approval_state") != "candidate_only"
    ):
        raise AuditError("multifile_candidate_state_mismatch")
    inventory = {}
    for row in manifest["file_inventory"]:
        path = row["path"]
        if path in inventory:
            raise AuditError("multifile_duplicate_path")
        _body(folder, path, row["sha256"], row["bytes"])
        inventory[path] = row
    declared = {item["id"]: item for item in catalogue["items"]}
    if len(declared) != len(catalogue["items"]) or set(declared) != set(
        manifest["package_trees"]
    ):
        raise AuditError("multifile_identity_mismatch")
    used = set()
    for identity, tree in manifest["package_trees"].items():
        item = declared[identity]
        if {row["path"] for row in tree} != set(item["delivery_files"]):
            raise AuditError("multifile_delivery_mismatch")
        _package(
            db,
            "local",
            folder.name,
            identity,
            "agent_skill_with_scripts",
            "candidate_only",
            "executable_or_connection",
        )
        for row in tree:
            path = row["path"]
            if path in used or inventory.get(path) != row:
                raise AuditError("multifile_delivery_untracked_or_shared")
            used.add(path)
            _file(
                db,
                "local",
                folder.name,
                identity,
                path,
                row["sha256"],
                row["bytes"],
                row["role"],
            )
    if (
        len(used) != manifest["physical_delivery_paths"]
        or len(declared) != manifest["logical_packages"]
    ):
        raise AuditError("multifile_count_mismatch")


def _overlay_body_digest(folder: Path, row: dict, expected: str | None) -> str | None:
    """Compare bytes only when this checkout still holds the reviewed version."""
    if expected is None or not row.get("body_path"):
        return None
    try:
        _body(folder, row["body_path"], expected, row["body_size_bytes"])
    except (AuditError, KeyError):
        return None
    raw = (folder / row["body_path"]).read_bytes()
    normalized = ANCHOR.sub(
        b"Written for this catalogue at revision <revision>.\n", raw
    )
    return hashlib.sha256(normalized).hexdigest()


def _panels(db, paths: list[Path], inputs: list[dict]) -> list[dict]:
    results = []
    for path in paths:
        record, digest = _read(path)
        kind = record.get("record_type")
        if kind not in (PANEL, HISTORICAL_REVIEW):
            raise AuditError("review_overlay_type_mismatch")
        source = f"{'panel' if kind == PANEL else 'historical'}/{digest}"
        outcomes = Counter()
        exact_bodies = 0
        for row in record["rows"]:
            identity, outcome = row["identity"], row["outcome"]
            if not db.execute(
                "SELECT 1 FROM packages WHERE population='local' AND identity=?",
                (identity,),
            ).fetchone():
                raise AuditError("panel_identity_absent_from_local_catalogue")
            if outcome not in (
                "approved",
                "rejected",
                "refused_before_review",
                "panel_incomplete",
                "not_started",
            ):
                raise AuditError("panel_outcome_unknown")
            body_digest = row.get("body_sha256") or row.get("body_digest")
            normalized = _overlay_body_digest(path.parent, row, body_digest)
            exact_bodies += normalized is not None
            _event(db, identity, source, body_digest, outcome, normalized)
            outcomes[outcome] += 1
        inputs.append({"path": str(path), "sha256": digest})
        results.append(
            {
                "sha256": digest,
                "record_type": kind,
                "recorded_outcomes": dict(sorted(outcomes.items())),
                "exact_bodies_still_present": exact_bodies,
                "bodies_changed_or_missing": len(record["rows"]) - exact_bodies,
                "within_panel_disagreements": record.get("totals", {}).get(
                    "disagreements"
                ),
                "promotion_authority": False,
            }
        )
    return results


def _ingestion_reports(paths: list[Path], inputs: list[dict]) -> list[dict]:
    """Count outside source leads separately; they are not package approvals."""
    results = []
    for path in paths:
        record, digest = _read(path)
        if record.get("record_type") != "library_ingestion_run_report/v1":
            raise AuditError("ingestion_report_type_mismatch")
        counts = record["counts"]
        if (
            record.get("approved") is not False
            or record.get("hosted_publication") is not False
            or counts["discovered"] != counts["candidates"] + counts["batch_refusals"]
            or not 0 <= counts["staged_rows"] <= counts["candidates"]
        ):
            raise AuditError("ingestion_report_state_or_counts_mismatch")
        results.append(
            {
                "sha256": digest,
                "source_rows": len(record["sources"]),
                "discovered": counts["discovered"],
                "candidate_refs": counts["candidates"],
                "staged_rows": counts["staged_rows"],
                "staged_by_kind": counts["staged_by_kind"],
                "approved_package_credit": 0,
                "distinct_native_file_count": None,
                "integration_state": "external_run_evidence_only",
            }
        )
        inputs.append({"path": str(path), "sha256": digest})
    return results


def _bundle_lines(db, folders: list[Path], inputs: list[dict]) -> list[dict]:
    """Stream prospective release metadata. Do not call it active or verify blobs."""
    results = []
    for folder in folders:
        header, digest = _read(folder / "bundle.json", limit=2_000_000)
        if header.get("record_type") != BUNDLE:
            raise AuditError("bundle_record_type_mismatch")
        count = header.get("items")
        if type(count) is not int or not 1 <= count <= 200_000:
            raise AuditError("bundle_item_count_invalid")
        item_path = folder / "items.jsonl"
        if (
            item_path.is_symlink()
            or not item_path.is_file()
            or item_path.stat().st_size != header.get("items_bytes")
        ):
            raise AuditError("bundle_lines_missing_or_changed")
        source = f"bundle/{digest}"
        checksum = hashlib.sha256()
        read_count = 0
        with item_path.open("rb") as stream:
            while line := stream.readline(MAX_LINE_BYTES + 2):
                if len(line) > MAX_LINE_BYTES + 1 or not line.endswith(b"\n"):
                    raise AuditError("bundle_line_unbounded")
                checksum.update(line)
                read_count += 1
                if read_count > count:
                    raise AuditError("bundle_extra_item")
                row = _json(line[:-1], label=str(item_path))
                if row.get("record_type") != BUNDLE_ITEM:
                    raise AuditError("bundle_item_record_type_mismatch")
                reference = row["reference"]
                identity = reference["identity"]
                files = row["package"]["files"]
                if not isinstance(files, list) or not 1 <= len(files) <= 64:
                    raise AuditError("bundle_file_count_invalid")
                _package(
                    db,
                    "prospective_bundle",
                    source,
                    identity,
                    reference["kind"],
                    "approval_claim_in_bundle_unverified",
                    "not_assessed",
                )
                for entry in files:
                    _file(
                        db,
                        "prospective_bundle",
                        source,
                        identity,
                        entry["path"],
                        entry["digest"],
                        entry["size_bytes"],
                        entry["role"],
                    )
        if read_count != count or checksum.hexdigest() != header.get("items_digest"):
            raise AuditError("bundle_lines_digest_or_count_mismatch")
        inputs.append({"path": str(folder / "bundle.json"), "sha256": digest})
        inputs.append({"path": str(item_path), "sha256": checksum.hexdigest()})
        results.append(
            {
                "header_sha256": digest,
                "items": count,
                "blobs_verified": False,
                "active_release_proven": False,
            }
        )
    return results


def audit(
    root: Path, out_dir: Path, *, panel_paths=(), ingestion_paths=(), bundle_folders=()
) -> dict:
    root = root.resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="harness-supply-audit-") as scratch:
        db = sqlite3.connect(Path(scratch) / "inventory.sqlite")
        try:
            _db(db)
            inputs = []
            source_refs = _starter(
                db, root / "examples/29_intelligence_service/starter-catalogue", inputs
            )
            variants = bindings = 0
            for path in sorted((root / "artifacts").glob("*/manifest.json")):
                manifest, digest = _read(path)
                kind = manifest.get("record_type") or manifest.get("schema")
                if kind not in (SKILL_BATCH, MIXED_BATCH, MULTIFILE_BATCH):
                    continue
                inputs.append({"path": str(path), "sha256": digest})
                if kind == SKILL_BATCH:
                    _skill_batch(db, path.parent, manifest)
                elif kind == MIXED_BATCH:
                    new_variants, new_bindings = _mixed_batch(
                        db, path.parent, manifest, inputs
                    )
                    variants += new_variants
                    bindings += new_bindings
                else:
                    _multifile_batch(db, path.parent, manifest, inputs)
            panels = _panels(db, list(panel_paths), inputs)
            ingestions = _ingestion_reports(list(ingestion_paths), inputs)
            bundles = _bundle_lines(db, list(bundle_folders), inputs)
            db.commit()
            local = db.execute(
                "SELECT count(*) FROM packages WHERE population='local'"
            ).fetchone()[0]
            approved = db.execute(
                "SELECT count(*) FROM packages WHERE population='local' AND review_state='approved'"
            ).fetchone()[0]
            hosted = db.execute(
                "SELECT count(*) FROM packages WHERE population='local' AND host_packaged=1"
            ).fetchone()[0]
            payload_paths, unique_bytes = db.execute(
                "SELECT count(*), count(DISTINCT digest) FROM files WHERE population='local'"
            ).fetchone()
            queue_path = Path(scratch) / "review-queue.jsonl"
            queue_count = 0
            queue_sha = hashlib.sha256()
            gate_counts = Counter()
            with queue_path.open("xb") as output:
                for source, identity, kind, state, risk, file_count in db.execute(
                    """SELECT p.source,p.identity,p.kind,p.review_state,p.risk,count(f.path)
                       FROM packages p JOIN files f USING(population,source,identity)
                       WHERE p.population='local' AND p.review_state!='approved'
                       GROUP BY p.source,p.identity ORDER BY p.source,p.identity"""
                ):
                    outcomes = [
                        row[0]
                        for row in db.execute(
                            "SELECT outcome FROM review_events WHERE identity=? AND (source LIKE 'panel/%' OR source LIKE 'historical/%') ORDER BY source",
                            (identity,),
                        )
                    ]
                    conflict = "approved" in outcomes and (
                        "rejected" in outcomes or state == "rejected"
                    )
                    if conflict:
                        gate = "adjudicate_conflicting_review_records"
                    elif "rejected" in outcomes or state == "rejected":
                        gate = "repair_then_independent_rereview"
                    elif "approved" in outcomes:
                        gate = "historical_or_unmerged_approval_requires_authoritative_admission"
                    elif risk == "executable_or_connection":
                        gate = "rights_effects_sandbox_and_independent_tree_review"
                    else:
                        gate = "rights_distinctness_and_independent_review"
                    row = {
                        "source": source,
                        "identity": identity,
                        "kind": kind,
                        "current_review_state": state,
                        "panel_outcomes": outcomes,
                        "delivery_files": file_count,
                        "risk": risk,
                        "next_gate": gate,
                        "approval_ready": False,
                    }
                    encoded = (
                        json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n"
                    ).encode("utf-8")
                    output.write(encoded)
                    queue_sha.update(encoded)
                    queue_count += 1
                    gate_counts[gate] += 1
            conflict_sql = (
                "SELECT identity FROM review_events "
                "GROUP BY identity HAVING sum(outcome='approved')>0 AND sum(outcome='rejected')>0"
            )
            review_conflict_count = db.execute(
                f"SELECT count(*) FROM ({conflict_sql})"
            ).fetchone()[0]
            review_conflicts_first = [
                row[0]
                for row in db.execute(conflict_sql + " ORDER BY identity LIMIT 25")
            ]
            normalized_conflict_sql = (
                "SELECT identity FROM review_events WHERE normalized_digest IS NOT NULL "
                "GROUP BY identity,normalized_digest "
                "HAVING sum(outcome='approved')>0 AND sum(outcome='rejected')>0"
            )
            normalized_conflict_count = db.execute(
                f"SELECT count(DISTINCT identity) FROM ({normalized_conflict_sql})"
            ).fetchone()[0]
            hosted_review_conflicts = db.execute(
                """SELECT count(*) FROM packages p WHERE p.population='local' AND p.host_packaged=1
                   AND p.identity IN (SELECT identity FROM review_events GROUP BY identity
                     HAVING sum(outcome='approved')>0 AND sum(outcome='rejected')>0)"""
            ).fetchone()[0]
            duplicate_groups = [
                {
                    "sha256": digest,
                    "physical_paths": count,
                    "logical_packages": packages,
                }
                for digest, count, packages in db.execute(
                    """SELECT digest,count(*),count(DISTINCT source||char(0)||identity)
                       FROM files WHERE population='local' GROUP BY digest HAVING count(*)>1
                       ORDER BY count(*) DESC,digest LIMIT 25"""
                )
            ]
            source_counts = [
                {"source": source, "logical_packages": packages, "payload_paths": files}
                for source, packages, files in db.execute(
                    """SELECT p.source,count(DISTINCT p.identity),count(f.path)
                       FROM packages p JOIN files f USING(population,source,identity)
                       WHERE p.population='local' GROUP BY p.source ORDER BY p.source"""
                )
            ]
            states = dict(
                db.execute(
                    "SELECT review_state,count(*) FROM packages WHERE population='local' GROUP BY review_state"
                )
            )
            roles = dict(
                db.execute(
                    "SELECT role,count(*) FROM files WHERE population='local' GROUP BY role"
                )
            )
            bundle_packages, bundle_paths, bundle_unique = db.execute(
                """SELECT (SELECT count(*) FROM packages WHERE population='prospective_bundle'),
                          count(*),count(DISTINCT digest) FROM files WHERE population='prospective_bundle'"""
            ).fetchone()
            try:
                revision = subprocess.check_output(
                    ["git", "-C", str(root), "rev-parse", "HEAD"],
                    text=True,
                    stderr=subprocess.DEVNULL,
                ).strip()
            except (OSError, subprocess.CalledProcessError):
                revision = None
            report = {
                "record_type": "harness_supply_offline_audit/v1",
                "repository_revision": revision,
                "inputs": sorted(inputs, key=lambda row: row["path"]),
                "local": {
                    "logical_package_records": local,
                    "recorded_approved": approved,
                    "packaged_host_items": hosted,
                    "not_approved_review_queue": queue_count,
                    "physical_payload_paths": payload_paths,
                    "distinct_payload_body_sha256": unique_bytes,
                    "starter_distinct_source_references": source_refs,
                    "client_specific_variants": variants,
                    "variant_file_bindings": bindings,
                    "review_states": states,
                    "file_roles": roles,
                    "sources": source_counts,
                    "exact_duplicate_body_groups_first_25": duplicate_groups,
                },
                "panels": {
                    "unmerged_evidence": panels,
                    "conflicting_identity_count": review_conflict_count,
                    "same_body_after_closing_anchor_conflict_count": normalized_conflict_count,
                    "conflicting_identities_first_25": review_conflicts_first,
                    "host_packaged_identity_conflicts": hosted_review_conflicts,
                    "approval_credit_from_panels": 0,
                },
                "outside_ingestion_reports": ingestions,
                "prospective_bundles": {
                    "inputs": bundles,
                    "logical_records": bundle_packages,
                    "physical_file_paths": bundle_paths,
                    "distinct_file_sha256": bundle_unique,
                    "active_release_credit": 0,
                },
                "live_active_count": None,
                "limitations": [
                    "Local review records and package digests are inventoried, not independently re-adjudicated.",
                    "A packaged host manifest is not proof that a live account can fetch or use an item.",
                    "Exact byte deduplication does not establish semantic distinctness or rights.",
                    "A prospective bundle line is not a published active release, and its blobs are not checked here.",
                    "An unmerged panel verdict cannot increase approved supply; conflicting verdicts require adjudication.",
                ],
            }
            out_dir.mkdir(parents=True, exist_ok=False)
            shutil.copyfile(queue_path, out_dir / "review-queue.jsonl")
            report["review_queue"] = {
                "path": "review-queue.jsonl",
                "sha256": queue_sha.hexdigest(),
                "rows": queue_count,
                "next_gates": dict(sorted(gate_counts.items())),
            }
            (out_dir / "report.json").write_text(
                json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            return report
        finally:
            db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument(
        "--out-dir",
        type=Path,
        required=True,
        help="new receipt folder; never overwrites a prior report",
    )
    parser.add_argument("--panel-record", action="append", type=Path, default=[])
    parser.add_argument("--ingestion-report", action="append", type=Path, default=[])
    parser.add_argument("--bundle-dir", action="append", type=Path, default=[])
    args = parser.parse_args()
    report = audit(
        args.repo,
        args.out_dir,
        panel_paths=args.panel_record,
        ingestion_paths=args.ingestion_report,
        bundle_folders=args.bundle_dir,
    )
    print(
        json.dumps(
            {
                "report": str(args.out_dir / "report.json"),
                "local_package_records": report["local"]["logical_package_records"],
                "recorded_approved": report["local"]["recorded_approved"],
                "packaged_host_items": report["local"]["packaged_host_items"],
                "payload_paths": report["local"]["physical_payload_paths"],
                "distinct_body_digests": report["local"][
                    "distinct_payload_body_sha256"
                ],
                "review_queue_rows": report["review_queue"]["rows"],
                "review_conflicts": report["panels"]["conflicting_identity_count"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
