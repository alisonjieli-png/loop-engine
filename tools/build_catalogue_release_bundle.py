"""Build a catalogue release bundle from a reviewed catalogue folder.

The independent review record decides what may be served, with the same rules
`tools/build_host_catalogue_manifest.py` applies to the host manifest: the
reviewers the row's library tier requires judged the item (every named reviewer
for a verified row, one or more for a community row), no reviewer objected, the
approval names the exact digest of the bytes it covers, and the declared
licence is one the host accepts. Each bundle line names the tier of its row. This command then writes one release bundle: a small header, one
item per line, and every file stored under its own SHA-256 digest. The service
publishes it with `loop-engine service publish-catalogue`, without a new image.

A catalogue row may name its package files explicitly under `package_files`,
each with its source path, placement path, media type and role, so a skill with
scripts, references and assets, an `AGENTS.md`, a subagent definition, a hook
or a protocol server configuration travels as it is. A row without that list
is one text body placed where its kind is read. Two files with one name in
different folders stay two files, because each is stored by its own digest.

The bundle holds library bodies, so this command refuses an output folder
inside this public repository. It approves nothing, reaches no network and
grants no effect.

    PYTHONPATH=src python tools/build_catalogue_release_bundle.py \\
        --catalogue examples/29_intelligence_service/starter-catalogue \\
        --output ~/baltor-bundles/starter-1 --notes "Starter catalogue" --write
"""
from __future__ import annotations

import argparse
from dataclasses import replace
import datetime
import json
from pathlib import Path

from build_host_catalogue_manifest import (
    APPROVED, ITEMS_FILE, ITEMS_RECORD_TYPE, REVIEW_FILE, ManifestBuildError, _read_json, _review_index, row_tier,
)
from loop_engine.core.practitioner_runtime.provisioning import _item
from loop_engine.core.service_runtime.catalogue_bundle import BUNDLE_ITEM_RECORD_TYPE, read_bundle, write_bundle
from loop_engine.core.service_runtime.catalogue_packages import (
    FILE_BODY, PACKAGE_BODY, CataloguePackage, CataloguePackageFile, sha256_hex,
)
from loop_engine.core.service_runtime.catalogue_schema import MAXIMUM_KEYWORD_CHARACTERS, CatalogueAttributeSchema
from loop_engine.core.service_runtime.http_entrypoint import HostFamilyPolicy, HostLicensePolicy
from loop_engine.core.service_runtime.records import ServiceRuntimeError

REPOSITORY = Path(__file__).resolve().parents[1]
SCHEMA_FILE = "attribute-schema.json"
RESULT_RECORD_TYPE = "catalogue_release_bundle_build/v1"
#: Where a one-file item of each kind is placed, and what its file is for.
KIND_PLACEMENT = {"skill": ("SKILL.md", "skill_definition"), "instruction_file": ("AGENTS.md", "instruction_file")}
MEDIA_TYPES = {".md": "text/markdown", ".py": "text/x-python", ".sh": "text/x-shellscript", ".json": "application/json",
               ".toml": "application/toml", ".yaml": "application/yaml", ".yml": "application/yaml",
               ".txt": "text/plain", ".png": "image/png", ".svg": "image/svg+xml", ".js": "text/javascript"}


def _source(folder, relative):
    """A regular file inside the catalogue folder, never a link or a path outside it."""
    candidate = Path(relative)
    target = folder / candidate
    if (candidate.is_absolute() or ".." in candidate.parts or target.is_symlink() or target.resolve() != target
            or folder not in target.parents or not target.is_file()):
        raise ManifestBuildError("unsafe_artifact_path", f"{relative!r} must name a regular file inside the catalogue")
    return target.read_bytes()


def _package(folder, row, kind):
    """The package of one catalogue row and the bytes of each of its files."""
    declared = row.get("package_files")
    if declared is None:
        if kind not in KIND_PLACEMENT:
            raise ManifestBuildError("package_files_required",
                                     f"an item of kind {kind!r} names its package files; no placement is assumed")
        path, role = KIND_PLACEMENT[kind]
        declared = [{"source": row["body_path"], "path": path, "role": role,
                     "media_type": MEDIA_TYPES.get(Path(row["body_path"]).suffix, "application/octet-stream")}]
    files, payloads = [], []
    for entry in declared:
        if not isinstance(entry, dict) or set(entry) != {"source", "path", "media_type", "role"}:
            raise ManifestBuildError("package_files_invalid", "a package file names source, path, media type and role")
        payload = _source(folder, entry["source"])
        files.append(CataloguePackageFile(entry["path"], sha256_hex(payload), len(payload), entry["media_type"],
                                          entry["role"]))
        payloads.append(payload)
    single = len(files) == 1 and files[0].media_type.startswith("text/")
    if single:
        try:
            payloads[0].decode("utf-8")
        except UnicodeDecodeError:
            single = False
    return CataloguePackage(tuple(files), FILE_BODY if single else PACKAGE_BODY), payloads


#: The longest keyword a release schema accepts.
KEYWORD_LIMIT = MAXIMUM_KEYWORD_CHARACTERS


def cited_source(source_ref: str) -> str:
    """The file an item cites, without its revision; a path longer than a keyword keeps its last whole parts."""
    path = source_ref.split("@", 1)[0]
    if len(path) <= KEYWORD_LIMIT:
        return path
    parts = path.split("/")
    kept = parts[-1:]
    for part in reversed(parts[:-1]):
        if len("/".join([part, *kept])) > KEYWORD_LIMIT:
            break
        kept.insert(0, part)
    return "/".join(kept)[-KEYWORD_LIMIT:]


def _attributes(row, review, recorded_at, batch, schema):
    # A combined snapshot keeps each row's own review date; a row without one takes the record's date.
    catalogued_on = datetime.date.fromisoformat(str(review.get("catalogued_on", recorded_at))[:10]).isoformat()
    values = {"cited_source": cited_source(row["reference"]["source_ref"]), "origin_layer": review["source_layer"],
              "catalogued_on": catalogued_on, "batch": batch}
    if "tier" in review and any(item.name == "tier" for item in schema.attributes):
        # The library tier of the decision table (Verified or Community) always travels in the line's approval. It is
        # also a served attribute, shown and filtered on, when the release schema declares one named tier.
        values["tier"] = review["tier"]
    # An item's own attributes (the harness kind and the step functions the writer tagged it with) join the line.
    # They never restate one of the builder's: that would let a row relabel its tier or its review date.
    own = row.get("attributes") or {}
    if not isinstance(own, dict):
        raise ManifestBuildError("item_attributes_invalid", "an item's attributes are a mapping")
    if set(own) & set(values):
        raise ManifestBuildError("item_attribute_reserved",
                                 "an item's own attributes never restate the builder's: " + ", ".join(sorted(set(own) & set(values))))
    values.update(own)
    return values


def build(folder, *, accepted_licenses, schema_path=None, include=(), batch="starter-catalogue"):
    """Return the bundle lines and file payloads of every approved item, or raise the first refusal."""
    policy = HostLicensePolicy(accepted_licenses=tuple(accepted_licenses))
    family = HostFamilyPolicy()
    catalogue = _read_json(folder / ITEMS_FILE, "the candidate item file")
    if not isinstance(catalogue, dict) or catalogue.get("record_type") != ITEMS_RECORD_TYPE:
        raise ManifestBuildError("catalogue_record_unsupported", f"this command reads {ITEMS_RECORD_TYPE} only")
    record, reviewed = _review_index(folder)
    if record["catalogue_source_revision"] != catalogue["source_revision"]:
        raise ManifestBuildError("review_covers_another_revision", "the review and the items name other revisions")
    schema = CatalogueAttributeSchema.from_dict(_read_json(schema_path or folder / SCHEMA_FILE, "the attribute schema"))
    recorded_at = datetime.date.fromisoformat(str(record["recorded_at"])[:10]).isoformat()
    rows = {row["reference"]["identity"]: row for row in catalogue["items"]}
    selected = sorted(include) if include else sorted(identity for identity in rows
                                                      if reviewed.get(identity, {}).get("outcome") == APPROVED)
    lines, payloads = [], []
    for identity in selected:
        if identity not in rows or reviewed.get(identity, {}).get("outcome") != APPROVED:
            raise ManifestBuildError("item_not_approved", f"item {identity!r} is not approved; it is never bundled")
        row, review = rows[identity], reviewed[identity]
        item = _item(row["reference"])
        refused = family.refusal(item.family) or policy.refusal(item.license_name)
        if refused:
            raise ManifestBuildError(refused, f"item {identity!r} is refused by the host family or licence policy")
        package, files = _package(folder, row, item.kind)
        if review["body_digest"] != package.served_digest:
            raise ManifestBuildError("body_changed_after_review",
                                     f"item {identity!r} serves other bytes than its reviewers approved")
        exact = replace(item, digest=package.served_digest, size_bytes=package.served_size)
        lines.append({"record_type": BUNDLE_ITEM_RECORD_TYPE, "reference": exact.reference(),
                      "package": package.to_dict(),
                      # The review record approved these bytes under the tier its row names.
                      "approval": {"tier": row_tier(identity, review), "approval_ref": review["approval_ref"],
                                   "approved_digest": review["body_digest"]},
                      "attributes": schema.validate_values(_attributes(row, review, recorded_at, batch, schema))})
        payloads.extend(files)
    if not lines:
        raise ManifestBuildError("no_approved_items", "no item is approved, so there is nothing to bundle")
    return schema, lines, payloads


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--catalogue", type=Path, required=True, help="The reviewed candidate catalogue folder.")
    parser.add_argument("--output", type=Path, required=True, help="A new bundle folder outside this repository.")
    parser.add_argument("--schema", type=Path, help="The attribute schema; defaults to the catalogue's own file.")
    parser.add_argument("--accept-license", action="append", default=[], help="Repeat for each accepted licence.")
    parser.add_argument("--include", action="append", default=[], help="Name one identity; omit for every approved.")
    parser.add_argument("--notes", default="", help="Release notes a customer can read.")
    parser.add_argument("--withdraw", action="append", default=[],
                        help="IDENTITY=NOTE: withdraw one item of the active release durably with this release.")
    parser.add_argument("--batch", default="starter-catalogue", help="The internal batch name kept with each item.")
    parser.add_argument("--write", action="store_true", help="Write the bundle; without it the build is only checked.")
    options = parser.parse_args(argv)
    try:
        output = options.output.expanduser().resolve()
        if output == REPOSITORY or REPOSITORY in output.parents:
            raise ManifestBuildError("bundle_inside_repository",
                                     "library bodies never go into this public repository; write the bundle elsewhere")
        withdrawals = []
        for value in options.withdraw:
            identity, separator, note = value.partition("=")
            if not separator or not identity:
                raise ManifestBuildError("invalid_withdrawal", "a withdrawal is written IDENTITY=NOTE")
            withdrawals.append({"identity": identity, "note": note})
        schema, lines, payloads = build(options.catalogue.resolve(),
                                        accepted_licenses=tuple(options.accept_license) or ("MIT",),
                                        schema_path=options.schema, include=tuple(options.include),
                                        batch=options.batch)
        digest = None
        if options.write:
            digest = write_bundle(output, schema=schema, lines=lines, payloads=payloads, notes=options.notes,
                                  withdrawals=withdrawals)
            read_bundle(output, license_policy=HostLicensePolicy(tuple(options.accept_license) or ("MIT",)),
                        family_policy=HostFamilyPolicy())
    except (ManifestBuildError, ServiceRuntimeError) as error:
        print(json.dumps({"record_type": RESULT_RECORD_TYPE, "refused": True, "code": error.code,
                          "message": str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps({"record_type": RESULT_RECORD_TYPE, "refused": False,
                      "state": "written" if digest else "checked", "items": len(lines),
                      "files": len(payloads), "bytes": sum(len(value) for value in payloads),
                      "schema_digest": schema.digest, "bundle_digest": digest, "output": str(output)},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
