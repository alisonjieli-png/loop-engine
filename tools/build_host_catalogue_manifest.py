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
import re
import shutil

from loop_engine.core.practitioner_runtime.provisioning import _item
from loop_engine.core.provisioning_server import METERING_POLICIES
from loop_engine.core.service_runtime.http_entrypoint import (
    HostLicensePolicy, MANIFEST_VERSION,
)

#: The review record this command reads. A different record version is refused
#: rather than reinterpreted, so an older or newer review cannot be guessed at.
#: Version two names every catalogue item, including the ones no reviewer has
#: judged, and records whether an approval was reviewed or carried.
REVIEW_RECORD_TYPE = "starter_catalogue_independent_review/v2"
ITEMS_RECORD_TYPE = "starter_catalogue_candidate_items/v2"
REVIEW_FILE = "reviews.json"
ITEMS_FILE = "items.json"
MANIFEST_FILE = "manifest.json"
BODIES_FOLDER = "bodies"
BODY_SUFFIX = ".md"
APPROVED = "approved"
REJECTED = "rejected"
#: No reviewer has judged the item. It carries no digest, because no reviewer read any bytes.
NOT_REVIEWED = "not_reviewed"
#: The item was approved once, and then its body changed by more than the anchor line,
#: so the approval no longer covers the bytes. It is a candidate again.
CARRY_REFUSED = "carry_refused"
OUTCOMES = (APPROVED, REJECTED, NOT_REVIEWED, CARRY_REFUSED)
#: Only this outcome may be written into a host manifest.
SERVED_OUTCOME = APPROVED
#: How an approval was reached. A reader tells a carried approval from a reviewed one here.
REVIEWED_STATE, CARRIED_STATE, NO_STATE = "reviewed", "carried", "none"
APPROVAL_STATES = (REVIEWED_STATE, CARRIED_STATE, NO_STATE)
#: The carry record and the proof inside it, both versioned.
CARRY_RECORD_TYPE = "starter_catalogue_approval_carry/v1"
PROOF_RECORD_TYPE = "starter_catalogue_anchor_line_only_proof/v1"
REFUSAL_RECORD_TYPE = "starter_catalogue_approval_carry_refusal/v1"
DIGEST = re.compile(r"[0-9a-f]{64}")
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


def _judged(identity: str, row: dict, known: set) -> None:
    """Refuse unless every named reviewer decided this item and every objection has a reason."""
    decided = {decision["reviewer_id"] for decision in row["decisions"]}
    if decided != known:
        raise ManifestBuildError("review_record_inconsistent",
            f"item {identity!r} was not judged by every named reviewer")
    objections = [decision for decision in row["decisions"] if decision["decision"] != "approve"]
    if any(not decision["reason"].strip() for decision in objections):
        raise ManifestBuildError("review_record_inconsistent",
            f"item {identity!r} carries a rejection with no written reason")
    decided_outcome = REJECTED if objections else APPROVED
    if row["outcome"] == APPROVED and decided_outcome != APPROVED:
        raise ManifestBuildError("review_record_inconsistent",
            f"item {identity!r} records the outcome {row['outcome']!r} while a reviewer objected")
    if row["outcome"] == REJECTED and decided_outcome != REJECTED:
        raise ManifestBuildError("review_record_inconsistent",
            f"item {identity!r} records a rejection while every reviewer approved")


def _carried(identity: str, row: dict) -> None:
    """Refuse unless a carried approval keeps the digest it was given for and carries its proof."""
    carry = row.get("carry")
    proof = (carry or {}).get("proof")
    if not isinstance(carry, dict) or carry.get("record_type") != CARRY_RECORD_TYPE:
        raise ManifestBuildError("carry_record_unsupported",
            f"carried item {identity!r} must carry a {CARRY_RECORD_TYPE} record")
    if not isinstance(proof, dict) or proof.get("record_type") != PROOF_RECORD_TYPE:
        raise ManifestBuildError("carry_record_unsupported",
            f"carried item {identity!r} must carry a {PROOF_RECORD_TYPE} proof")
    if carry.get("carried_body_digest") != row["body_digest"] or \
            carry.get("carried_body_size_bytes") != row["body_size_bytes"]:
        raise ManifestBuildError("carry_record_inconsistent",
            f"carried item {identity!r} names one digest in its row and another in its carry record")
    if not DIGEST.fullmatch(str(carry.get("reviewed_body_digest") or "")):
        raise ManifestBuildError("carry_record_inconsistent",
            f"carried item {identity!r} does not name the digest its reviewers judged")
    if carry.get("reviewed_body_digest") == row["body_digest"]:
        raise ManifestBuildError("carry_record_inconsistent",
            f"carried item {identity!r} names the same digest before and after the carry, "
            "so nothing was carried")
    if carry.get("decisions_unchanged") is not True or carry.get("reviewed_again") is not False:
        raise ManifestBuildError("carry_record_inconsistent",
            f"carried item {identity!r} must record that its decisions are unchanged and that "
            "no reviewer read the new bytes")


def _review_index(folder: Path):
    """Return each judged identity with the outcome its reviewers' decisions carry.

    Approval is read from the decisions themselves, never from the summary
    field beside them, so an edited summary cannot approve an item that a
    reviewer rejected. The two must agree or the record is refused. An item with
    no verdict, and an item whose approval was returned to candidate state
    because its body changed, both carry no digest and no approval reference.
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
        if row["outcome"] not in OUTCOMES or row.get("approval_state") not in APPROVAL_STATES:
            raise ManifestBuildError("review_record_unsupported",
                f"item {identity!r} records the outcome {row['outcome']!r} and the approval state "
                f"{row.get('approval_state')!r}; this command reads {list(OUTCOMES)} and "
                f"{list(APPROVAL_STATES)}")
        if row["outcome"] != NOT_REVIEWED:
            _judged(identity, row, known)
        if row["outcome"] == CARRY_REFUSED \
                and any(decision["decision"] != "approve" for decision in row["decisions"]):
            raise ManifestBuildError("review_record_inconsistent",
                f"item {identity!r} returned from an approval its reviewers did not give")
        if row["outcome"] == APPROVED:
            if not row["approval_ref"].strip():
                raise ManifestBuildError("approval_ref_missing",
                    f"approved item {identity!r} carries no approval reference")
            if not DIGEST.fullmatch(str(row["body_digest"] or "")):
                raise ManifestBuildError("review_record_inconsistent",
                    f"approved item {identity!r} does not name the digest of the bytes it covers")
            if row["approval_state"] == CARRIED_STATE:
                _carried(identity, row)
            elif row["approval_state"] != REVIEWED_STATE:
                raise ManifestBuildError("review_record_inconsistent",
                    f"approved item {identity!r} must record whether its approval was reviewed or carried")
            elif "carry" in row:
                raise ManifestBuildError("carry_record_inconsistent",
                    f"item {identity!r} records a reviewed approval beside a carry record")
        else:
            if row["approval_ref"].strip():
                raise ManifestBuildError("review_record_inconsistent",
                    f"item {identity!r} is not approved and carries an approval reference")
            if row["approval_state"] != NO_STATE:
                raise ManifestBuildError("review_record_inconsistent",
                    f"item {identity!r} is not approved and records the approval state "
                    f"{row['approval_state']!r}")
            if row["outcome"] == REJECTED and not DIGEST.fullmatch(str(row["body_digest"] or "")):
                raise ManifestBuildError("review_record_inconsistent",
                    f"rejected item {identity!r} does not name the digest of the bytes its reviewers read")
            if row["outcome"] != REJECTED \
                    and (row["body_digest"] is not None or row["body_size_bytes"] is not None):
                raise ManifestBuildError("review_record_inconsistent",
                    f"item {identity!r} has no standing verdict, so it names no digest a reviewer judged")
        if row["outcome"] == CARRY_REFUSED:
            refusal = row.get("carry_refusal")
            if not isinstance(refusal, dict) or refusal.get("record_type") != REFUSAL_RECORD_TYPE \
                    or not str(refusal.get("reason") or "").strip():
                raise ManifestBuildError("carry_record_inconsistent",
                    f"item {identity!r} returned to candidate state with no written reason")
        if row["outcome"] == NOT_REVIEWED and row["decisions"]:
            raise ManifestBuildError("review_record_inconsistent",
                f"item {identity!r} records no verdict beside reviewer decisions")
        index[identity] = row
    counted = {outcome: sum(1 for row in record["rows"] if row["outcome"] == outcome) for outcome in OUTCOMES}
    stated = record["totals"]
    if any(stated.get(outcome) != count for outcome, count in counted.items()) \
            or stated.get("items_in_catalogue") != len(record["rows"]):
        raise ManifestBuildError("review_record_inconsistent",
            f"the totals say {stated} while the rows say {counted} over {len(record['rows'])} items")
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
