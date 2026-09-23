"""The release bundle an operator publishes, read with the rules the host already applies.

A bundle is a folder. `bundle.json` is a small header, `items.jsonl` holds one
item per line, and `blobs/sha256/<first two>/<digest>` holds the exact bytes of
every file, in the same layout as the body store. Nothing in a bundle is read
as one large document: the header is bounded like every host file, each item
line has its own bound, and the header states how many lines there are, how
many bytes they hold and their digest. A larger library is more lines, not a
larger limit, so an oversized, truncated, malformed or reordered bundle is
still refused.

Every item passes the checks `load_host_manifest` applies to a manifest row:
the family policy first, then the licence policy, an approval reference, and
the exact digest and size of the served body. Two checks are added. The
approval names the digest of the bytes it covers, so an approval of other
bytes is refused, and a package holding a file a harness may run must declare
the process effect, so the existing effect filter withholds it from a client
that did not declare that authority.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import stat
import os

from ..practitioner_runtime.provisioning import _item
from .catalogue_packages import (EXECUTABLE_EFFECT, FILE_BODY, CataloguePackage, VolumeBodyStore,
                                 exact_digest, sha256_hex)
from .catalogue_schema import CatalogueAttributeSchema
from .records import ServiceRuntimeError

BUNDLE_RECORD_TYPE = "catalogue_release_bundle/v1"
BUNDLE_ITEM_RECORD_TYPE = "catalogue_bundle_item/v1"
ITEM_VERSION_RECORD_TYPE = "catalogue_item_version/v1"
HEADER_FILE, ITEMS_FILE, BLOBS_FOLDER = "bundle.json", "items.jsonl", "blobs"
#: The header is a host file and has the same bound as every host file.
MAXIMUM_HEADER_BYTES = 2_000_000
MAXIMUM_ITEM_LINE_BYTES = 65_536
MAXIMUM_BUNDLE_ITEMS = 200_000
MAXIMUM_NOTE_CHARACTERS = 400
MAXIMUM_RELEASE_NOTES_CHARACTERS = 4000
MAXIMUM_APPROVAL_REFERENCE_CHARACTERS = 400


def _refuse(code, message):
    raise ServiceRuntimeError(code, message)


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def strict_json(payload, code):
    """Parse one bounded JSON object, refusing duplicate fields, non-finite numbers and deep nesting."""
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("duplicate field")
            value[key] = item
        return value
    try:
        value = json.loads(payload, object_pairs_hook=unique,
                           parse_constant=lambda _value: (_ for _ in ()).throw(ValueError("non-finite")))
    except (ValueError, UnicodeError, RecursionError):
        _refuse(code, "the bundle holds text that is not one strict JSON object")
    if not isinstance(value, dict):
        _refuse(code, "the bundle holds text that is not one strict JSON object")
    return value


def note(value, limit=MAXIMUM_NOTE_CHARACTERS):
    if not isinstance(value, str) or len(value) > limit or any(ord(character) < 32 and character not in "\n\t"
                                                                for character in value):
        _refuse("bundle_note_invalid", "a note is bounded text without control characters")
    return value


def _regular(path, code):
    try:
        info = os.lstat(path)
    except FileNotFoundError:
        _refuse(code, "a bundle file is missing")
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        _refuse("bundle_path_unsafe", "every bundle file is a regular file, never a symbolic link")
    return info


def item_version_document(item, package, approval_ref, attributes):
    """The canonical content of one item version; its digest is the version's identity."""
    return {"record_type": ITEM_VERSION_RECORD_TYPE, "reference": item.reference(),
            "package": package.to_dict(), "approval_ref": approval_ref, "attributes": attributes}


@dataclass(frozen=True)
class BundleItem:
    """One validated item version, ready to publish."""

    item: object
    package: CataloguePackage
    approval_ref: str
    attributes: dict

    @property
    def identity(self):
        return self.item.identity

    @property
    def document(self):
        return item_version_document(self.item, self.package, self.approval_ref, self.attributes)

    @property
    def version(self):
        return sha256_hex(canonical_bytes(self.document))


@dataclass(frozen=True)
class CatalogueBundle:
    """A validated bundle: its header digest, schema, notes, withdrawals and items in identity order."""

    folder: Path
    digest: str
    schema: CatalogueAttributeSchema
    notes: str
    change_notes: dict
    withdrawals: tuple
    items: tuple

    def blobs(self):
        """The bundle's own blob folder, opened read-only through the body store engine."""
        return VolumeBodyStore(str(self.folder / BLOBS_FOLDER))


def approval_refusal(approval, package):
    """Empty text when an approval covers exactly the bytes this item serves, otherwise the refusal code."""
    if not isinstance(approval, dict) or set(approval) != {"approval_ref", "approved_digest"}:
        return "explicit_host_review_required"
    reference = approval["approval_ref"]
    if (not isinstance(reference, str) or not reference.strip()
            or len(reference) > MAXIMUM_APPROVAL_REFERENCE_CHARACTERS or not reference.isprintable()):
        return "explicit_host_review_required"
    # The approval covers exact bytes. For a package, the served body is the
    # package document, which names the digest of every file in it.
    return "" if approval["approved_digest"] == package.served_digest else "approval_not_bound_to_bytes"


def effect_refusal(item, package):
    """Empty text unless a package holds a runnable file and its item does not declare the process effect."""
    return ("package_executable_effect_undeclared"
            if package.executable and EXECUTABLE_EFFECT not in item.declared_effects else "")


def validate_item(value, schema, *, license_policy, family_policy):
    """Apply the manifest rules and the two added rules to one bundle line."""
    if (not isinstance(value, dict)
            or set(value) != {"record_type", "reference", "package", "approval", "attributes"}
            or value["record_type"] != BUNDLE_ITEM_RECORD_TYPE):
        _refuse("bundle_item_invalid", f"each line is one {BUNDLE_ITEM_RECORD_TYPE} record and nothing else")
    try:
        item = _item(value["reference"])
    except (ValueError, TypeError, KeyError):
        _refuse("bundle_item_invalid", "an item reference is a current body-free harness item reference")
    refused = family_policy.refusal(item.family) or license_policy.refusal(item.license_name)
    if refused:
        _refuse(refused, "the host family or licence policy refuses this item before it is published")
    package = CataloguePackage.from_dict(value["package"])
    if item.digest != package.served_digest or item.size_bytes != package.served_size:
        _refuse("bundle_item_digest_mismatch", "the item reference names other bytes than its package serves")
    refused = approval_refusal(value["approval"], package) or effect_refusal(item, package)
    if refused:
        _refuse(refused, "an unapproved item, an approval of other bytes and an undeclared process effect "
                         "are never published")
    return BundleItem(item, package, value["approval"]["approval_ref"], schema.validate_values(value["attributes"]))


def read_bundle(folder, *, license_policy, family_policy, verify_blobs=True):
    """Read and validate one bundle folder without writing anything."""
    root = Path(folder) if isinstance(folder, (str, Path)) else None
    if root is None or not root.is_absolute() or root.resolve() != root or not root.is_dir():
        _refuse("bundle_folder_invalid", "a bundle is an existing absolute folder without symbolic links")
    info = _regular(root / HEADER_FILE, "bundle_header_missing")
    if info.st_size > MAXIMUM_HEADER_BYTES:
        _refuse("bundle_header_too_large", "the bundle header is larger than a host file may be")
    raw_header = (root / HEADER_FILE).read_bytes()
    header = strict_json(raw_header, "bundle_header_invalid")
    fields = {"record_type", "items", "items_bytes", "items_digest", "schema", "notes", "change_notes", "withdrawals"}
    if set(header) != fields or header["record_type"] != BUNDLE_RECORD_TYPE:
        _refuse("bundle_header_invalid", f"this release reads {BUNDLE_RECORD_TYPE} only, with its exact fields")
    count, size = header["items"], header["items_bytes"]
    if (type(count) is not int or not 1 <= count <= MAXIMUM_BUNDLE_ITEMS or type(size) is not int
            or not count <= size <= count * (MAXIMUM_ITEM_LINE_BYTES + 1)):
        _refuse("bundle_header_invalid", f"a bundle holds one to {MAXIMUM_BUNDLE_ITEMS} bounded item lines")
    exact_digest(header["items_digest"], "bundle_header_invalid")
    schema = CatalogueAttributeSchema.from_dict(header["schema"])
    notes = note(header["notes"], MAXIMUM_RELEASE_NOTES_CHARACTERS)
    change_notes = header["change_notes"]
    if not isinstance(change_notes, dict) or len(change_notes) > count:
        _refuse("bundle_header_invalid", "change notes map an item identity to a short note")
    change_notes = {str(key): note(value) for key, value in change_notes.items()}
    withdrawals = header["withdrawals"]
    if not isinstance(withdrawals, list) or len(withdrawals) > MAXIMUM_BUNDLE_ITEMS or any(
            not isinstance(row, dict) or set(row) != {"identity", "note"} or not isinstance(row["identity"], str)
            or not row["identity"] for row in withdrawals):
        _refuse("bundle_header_invalid", "a withdrawal names an item identity and a note")
    withdrawals = tuple(sorted(({"identity": row["identity"], "note": note(row["note"])} for row in withdrawals),
                               key=lambda row: row["identity"]))
    if len({row["identity"] for row in withdrawals}) != len(withdrawals):
        _refuse("bundle_header_invalid", "an identity is withdrawn once in one bundle")
    items_info = _regular(root / ITEMS_FILE, "bundle_items_missing")
    if items_info.st_size != size:
        _refuse("bundle_items_changed", "the item file holds another number of bytes than the header states")
    checksum, items, seen, lines = hashlib.sha256(), [], set(), 0
    with open(root / ITEMS_FILE, "rb") as stream:
        while True:
            line = stream.readline(MAXIMUM_ITEM_LINE_BYTES + 2)
            if not line:
                break
            checksum.update(line)
            lines += 1
            if len(line) > MAXIMUM_ITEM_LINE_BYTES + 1 or not line.endswith(b"\n") or lines > count:
                _refuse("bundle_item_line_invalid", "each item line is bounded and ends with one newline")
            bundle_item = validate_item(strict_json(line[:-1], "bundle_item_invalid"), schema,
                                        license_policy=license_policy, family_policy=family_policy)
            if bundle_item.identity in seen:
                _refuse("duplicate_item_identity", "one identity appears twice in one bundle")
            seen.add(bundle_item.identity)
            items.append(bundle_item)
    if lines != count or checksum.hexdigest() != header["items_digest"]:
        _refuse("bundle_items_changed", "the item file differs from the count and digest the header states")
    if set(change_notes) - seen - {row["identity"] for row in withdrawals}:
        _refuse("bundle_header_invalid", "a change note names an item the bundle neither lists nor withdraws")
    bundle = CatalogueBundle(root, sha256_hex(raw_header), schema, notes, change_notes, withdrawals,
                             tuple(sorted(items, key=lambda entry: entry.identity)))
    if verify_blobs:
        blobs = bundle.blobs()
        for entry in bundle.items:
            for payload, _file in bundle_payloads(blobs, entry):
                pass
    return bundle


def bundle_payloads(blobs, entry):
    """Yield the verified bytes of every file of one bundle item, in path order."""
    for file in entry.package.files:
        payload = blobs.read(file.digest, file.size_bytes)
        if entry.package.body_form == FILE_BODY:
            try:
                payload.decode("utf-8")
            except UnicodeDecodeError:
                _refuse("package_file_not_text", "the file body form serves UTF-8 text only")
        yield payload, file


def write_bundle(folder, *, schema, lines, payloads, notes="", change_notes=None, withdrawals=()):
    """Write one bundle folder from validated parts and return its header digest.

    `lines` are bundle item records; `payloads` are the bytes of every file,
    stored under their own digest. The folder must not exist yet, so a bundle
    is never merged into an older one.
    """
    root = Path(folder)
    if not root.is_absolute() or root.exists():
        _refuse("bundle_folder_invalid", "a new bundle is written into a new absolute folder")
    (root / BLOBS_FOLDER).mkdir(parents=True)
    blobs = VolumeBodyStore(str((root / BLOBS_FOLDER).resolve()), writes_authorized=True)
    for payload in payloads:
        blobs.put(payload)
    rendered = b"".join(canonical_bytes(line) + b"\n"
                        for line in sorted(lines, key=lambda line: line["reference"]["identity"]))
    (root / ITEMS_FILE).write_bytes(rendered)
    header = {"record_type": BUNDLE_RECORD_TYPE, "items": len(lines), "items_bytes": len(rendered),
              "items_digest": sha256_hex(rendered), "schema": schema.to_dict(), "notes": notes,
              "change_notes": dict(change_notes or {}), "withdrawals": list(withdrawals)}
    encoded = json.dumps(header, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    (root / HEADER_FILE).write_bytes(encoded)
    return sha256_hex(encoded)
