"""Generate the host manifest and the release bodies for an approved catalogue.

The independent review record decides what may be served. This command reads
that record, refuses every item that any reviewer rejected, measures each body
file for its digest and size, checks the declared licence against the host
licence policy that the running host will apply, and writes one release folder
that holds the manifest and only the approved bodies. Nothing here approves an
item, reaches a network, or grants an effect.

The release folder is the exact content that goes into the service image. The
default run checks the folder already in the repository and writes nothing, so
a drift between the review record, the bodies and the release folder fails:

    PYTHONPATH=src python tools/build_host_catalogue_manifest.py \
        --catalogue examples/29_intelligence_service/starter-catalogue \
        --output examples/29_intelligence_service/starter-catalogue/host-release \
        --artifact-root /opt/baltor/catalogue \
        --accept-license MIT --grant pilot-owner:bodies:required

Add --write to replace the release folder with the generated content.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shutil

from loop_engine.core.practitioner_runtime.provisioning import _item
from loop_engine.core.provisioning_server import METERING_POLICIES
from loop_engine.core.service_runtime.http_entrypoint import (
    HostLicensePolicy, MANIFEST_VERSION,
)

#: The review record this command reads. A different record version is refused
#: rather than reinterpreted, so an older or newer review cannot be guessed at.
REVIEW_RECORD_TYPE = "starter_catalogue_independent_review/v1"
ITEMS_RECORD_TYPE = "starter_catalogue_candidate_items/v1"
REVIEW_FILE = "reviews.json"
ITEMS_FILE = "items.json"
MANIFEST_FILE = "manifest.json"
BODIES_FOLDER = "bodies"
BODY_SUFFIX = ".md"
APPROVED = "approved"
REJECTED = "rejected"
GRANT_BODY_CHOICES = {"bodies": True, "metadata": False}

#: The three states a run reports, and the two that mean the release folder on
#: disk is the one the review record and the bodies produce. A drift reports
#: DIFFERS and fails, so a check run cannot pass while the folder is stale.
WRITTEN = "written"
UNCHANGED = "unchanged"
DIFFERS = "differs"
ACCEPTED_STATES = (WRITTEN, UNCHANGED)


class ManifestBuildError(ValueError):
    """A stable refusal code and an operator message, with no item body."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def _read_json(path: Path, label: str):
    if path.is_symlink() or not path.is_file():
        raise ManifestBuildError("catalogue_file_missing", f"{label} must be a regular file at {path}")
    try:
        return json.loads(path.read_bytes().decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ManifestBuildError("catalogue_file_unreadable", f"{label} is not readable UTF-8 JSON: {error}") from None


def _body_path(folder: Path, relative: str) -> Path:
    """Return the body file inside the catalogue folder, or refuse the path.

    The same shape the running host applies is applied here, so a path that the
    host would refuse never reaches a generated manifest.
    """
    candidate = Path(relative)
    target = folder / candidate
    if (candidate.is_absolute() or ".." in candidate.parts or candidate.suffix != BODY_SUFFIX
            or target.resolve() != target or folder not in target.parents or target.is_symlink()
            or not target.is_file()):
        raise ManifestBuildError("unsafe_artifact_path",
            f"body path {relative!r} must name a regular {BODY_SUFFIX} file inside the catalogue folder")
    return target


def _grant(value: str) -> dict:
    parts = value.split(":")
    if len(parts) != 3 or not parts[0].strip() or parts[1] not in GRANT_BODY_CHOICES or parts[2] not in METERING_POLICIES:
        raise ManifestBuildError("invalid_grant_request",
            f"a grant is written TENANT:{'|'.join(sorted(GRANT_BODY_CHOICES))}:{'|'.join(METERING_POLICIES)}, not {value!r}")
    return {"tenant_id": parts[0], "body_allowed": GRANT_BODY_CHOICES[parts[1]], "metering": parts[2]}


def _review_index(folder: Path):
    """Return each reviewed identity with the outcome its reviewers' decisions carry.

    Approval is read from the decisions themselves, never from the summary
    field beside them, so an edited summary cannot approve an item that a
    reviewer rejected. The two must agree or the record is refused.
    """
    record = _read_json(folder / REVIEW_FILE, "the independent review record")
    if not isinstance(record, dict) or record.get("record_type") != REVIEW_RECORD_TYPE:
        raise ManifestBuildError("review_record_unsupported",
            f"this command reads the review record {REVIEW_RECORD_TYPE} only")
    known = {row["reviewer_id"] for row in record["reviewers"]}
    if not known or len(known) != len(record["reviewers"]):
        raise ManifestBuildError("review_record_unsupported", "the review record names no distinct reviewers")
    index = {}
    for row in record["rows"]:
        identity = row["identity"]
        if identity in index:
            raise ManifestBuildError("review_record_inconsistent", f"item {identity!r} is reviewed twice")
        decided = {decision["reviewer_id"] for decision in row["decisions"]}
        if decided != known:
            raise ManifestBuildError("review_record_inconsistent",
                f"item {identity!r} was not judged by every named reviewer")
        objections = [decision for decision in row["decisions"] if decision["decision"] != "approve"]
        if any(not decision["reason"].strip() for decision in objections):
            raise ManifestBuildError("review_record_inconsistent",
                f"item {identity!r} carries a rejection with no written reason")
        outcome = REJECTED if objections else APPROVED
        if row["outcome"] != outcome:
            raise ManifestBuildError("review_record_inconsistent",
                f"item {identity!r} records the outcome {row['outcome']!r} while its reviewers decided {outcome!r}")
        if outcome == APPROVED and not row["approval_ref"].strip():
            raise ManifestBuildError("approval_ref_missing", f"approved item {identity!r} carries no approval reference")
        if outcome == REJECTED and row["approval_ref"].strip():
            raise ManifestBuildError("review_record_inconsistent",
                f"rejected item {identity!r} carries an approval reference")
        index[identity] = row
    return record, index


def build(folder: Path, *, artifact_root: str, accepted_licenses, grants, include=()):
    """Return the manifest and the approved bodies, or raise the first refusal."""
    policy = HostLicensePolicy(accepted_licenses=tuple(accepted_licenses))
    catalogue = _read_json(folder / ITEMS_FILE, "the candidate item file")
    if not isinstance(catalogue, dict) or catalogue.get("record_type") != ITEMS_RECORD_TYPE:
        raise ManifestBuildError("catalogue_record_unsupported",
            f"this command reads the candidate item file {ITEMS_RECORD_TYPE} only")
    record, reviewed = _review_index(folder)
    if record["catalogue_source_revision"] != catalogue["source_revision"]:
        raise ManifestBuildError("review_covers_another_revision",
            "the review record and the candidate item file name different catalogue revisions")
    rows = {row["reference"]["identity"]: row for row in catalogue["items"]}
    if len(rows) != len(catalogue["items"]):
        raise ManifestBuildError("duplicate_item_identity", "one identity appears twice in the candidate item file")
    if set(rows) != set(reviewed):
        raise ManifestBuildError("review_does_not_cover_catalogue",
            f"reviewed but absent: {sorted(set(reviewed) - set(rows))}; "
            f"present but unreviewed: {sorted(set(rows) - set(reviewed))}")
    selected = sorted(include) if include else sorted(
        identity for identity in rows if reviewed[identity]["outcome"] == APPROVED)
    if not selected:
        raise ManifestBuildError("no_approved_items", "no item is approved, so there is nothing to serve")
    root = Path(artifact_root)
    if not root.is_absolute() or ".." in root.parts:
        raise ManifestBuildError("invalid_artifact_root", "the artifact root is one absolute path without ..")
    items, bodies = [], {}
    for identity in selected:
        if identity not in rows:
            raise ManifestBuildError("unknown_item_identity", f"item {identity!r} is not in the candidate item file")
        review = reviewed[identity]
        if review["outcome"] != APPROVED:
            objections = [decision["reviewer_id"] for decision in review["decisions"]
                          if decision["decision"] != "approve"]
            raise ManifestBuildError("item_not_approved",
                f"item {identity!r} was rejected by {objections}; a rejected candidate is never written "
                "into a host manifest, and this command does not overturn a review")
        row = rows[identity]
        target = _body_path(folder, row["body_path"])
        payload = target.read_bytes()
        item = _item(row["reference"])
        if item.identity != identity:
            raise ManifestBuildError("catalogue_record_unsupported",
                f"the reference under {identity!r} names the identity {item.identity!r}")
        measured = hashlib.sha256(payload).hexdigest()
        if measured != review["body_digest"] or len(payload) != review["body_size_bytes"]:
            raise ManifestBuildError("body_changed_after_review",
                f"body {row['body_path']!r} no longer matches the bytes the reviewers judged; "
                "review the changed body again before it is served")
        refused = policy.refusal(item.license_name)
        if refused:
            raise ManifestBuildError(refused,
                f"item {identity!r} declares the licence {item.license_name!r} and this host accepts "
                f"{list(policy.accepted_licenses)}, so it is never written into a manifest it could not be served from")
        exact = replace(item, digest=measured, size_bytes=len(payload))
        relative = f"{BODIES_FOLDER}/{Path(row['body_path']).name}"
        items.append({"reference": exact.reference(), "body_path": relative,
                      "approval_ref": review["approval_ref"], "grants": list(grants)})
        bodies[relative] = payload
    manifest = {"record_type": MANIFEST_VERSION, "artifact_root": str(root), "items": items}
    return manifest, bodies


def _rendered(manifest) -> bytes:
    return (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _existing(output: Path):
    """Return the release folder's current bytes, so a check compares content, not timestamps."""
    held = {}
    if not output.is_dir():
        return None
    for path in sorted(output.rglob("*")):
        if path.is_symlink():
            raise ManifestBuildError("unsafe_release_folder", f"{path} is a symbolic link")
        if path.is_file():
            held[str(path.relative_to(output))] = path.read_bytes()
        elif not path.is_dir():
            raise ManifestBuildError("unsafe_release_folder", f"{path} is not a regular file or folder")
    return held


def write(output: Path, manifest, bodies):
    generated = {MANIFEST_FILE: _rendered(manifest), **bodies}
    if output.exists():
        if not output.is_dir() or output.is_symlink():
            raise ManifestBuildError("unsafe_release_folder", f"{output} is not a folder this command owns")
        shutil.rmtree(output)
    for name, payload in generated.items():
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    return generated


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--catalogue", type=Path, required=True, help="The reviewed candidate catalogue folder.")
    parser.add_argument("--output", type=Path, required=True, help="The release folder this command owns and rewrites.")
    parser.add_argument("--artifact-root", required=True,
                        help="The absolute path the release folder is mounted at inside the service image.")
    parser.add_argument("--accept-license", action="append", default=[],
                        help="Repeat for each exact licence identifier the host accepts. Defaults to MIT.")
    parser.add_argument("--grant", action="append", default=[],
                        help="Repeat as TENANT:bodies|metadata:required|unmetered.")
    parser.add_argument("--include", action="append", default=[],
                        help="Name one identity to consider. Omit to take every approved item.")
    parser.add_argument("--write", action="store_true", help="Replace the release folder instead of checking it.")
    options = parser.parse_args(argv)
    try:
        grants = [_grant(value) for value in options.grant]
        if len({grant["tenant_id"] for grant in grants}) != len(grants):
            raise ManifestBuildError("duplicate_grant_request", "one tenant is granted the same item twice")
        manifest, bodies = build(options.catalogue.resolve(),
            artifact_root=options.artifact_root,
            accepted_licenses=tuple(options.accept_license) or ("MIT",),
            grants=grants, include=tuple(options.include))
        output = options.output.resolve()
        generated = {MANIFEST_FILE: _rendered(manifest), **bodies}
        if options.write:
            write(output, manifest, bodies)
            state = WRITTEN
        else:
            state = UNCHANGED if _existing(output) == generated else DIFFERS
    except ManifestBuildError as error:
        print(json.dumps({"record_type": "host_catalogue_manifest_build/v1", "refused": True,
                          "code": error.code, "message": str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps({"record_type": "host_catalogue_manifest_build/v1", "refused": False, "state": state,
                      "items": len(manifest["items"]), "artifact_root": manifest["artifact_root"],
                      "tenants_granted": sorted(grant["tenant_id"] for grant in grants),
                      "output": str(output), "bytes": sum(len(value) for value in generated.values())},
                     ensure_ascii=False))
    return 0 if state in ACCEPTED_STATES else 1


if __name__ == "__main__":
    raise SystemExit(main())
