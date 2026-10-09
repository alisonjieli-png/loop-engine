"""Line creative_originals: Baltor's own creative families, one package per item, read at a pinned commit.

```text
creative_originals (one package per item of tools/creative_originals/<family>/items/<identity>/)
├── facts: the repository's LICENSE and every item and shared file at the pinned commit, each by its
│   raw.githubusercontent.com address and SHA-256 (MIT, this repository's licence)
├── files
│   ├── the item's files and the family's shared files, verbatim copies of those facts
│   ├── component.json (the contract card), verification/native.json and preview.png, written here
│   └── LICENSE (MIT) and ATTRIBUTION.md
├── native evidence: a family with a native verifier must have a passed record for the exact item bytes
│   (tools/creative_originals/verify.py, run before this line); an item without one is refused by name
├── effects: derived with qualification's own rules (code_effects for Python, the licensed import's text
│   rules for instruction and configuration roles, spawns_process for an executable role)
└── job key: component.json job.family and job.identity, so a second package for one item is the same job
```

The line reads no network address and calls no model. A package is a candidate until qualification and the
ongoing independent review.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from creative_originals.assemble import Entry, package_entries
from creative_originals.records import (COMPONENT_NAME, EVIDENCE_PATH, FORM_KINDS, PREVIEW_PATH, CreativeRecordError,
                                        families, item_identities, read_family, read_item)

from .packaging import LICENCE_NAME, PackageFile, SupplyPackage, build
from .reading import https_address
from .records import (CREATIVE_ORIGINALS, GENERATED, GENERATED_CODE_LICENCE, LICENCE_TEXT, UPSTREAM_VERBATIM,
                      SupplyRecordError, fact_source, provenance, refusal, upstream_key)

GENERATOR_VERSION = "1.0.0"
REPOSITORY = "alisonjieli-png/loop-engine"
RAW_HOST = "raw.githubusercontent.com"
NATIVE_FORMAT = "creative_original"
FAMILIES_ROOT = Path(__file__).resolve().parents[1] / "creative_originals"
#: Files the line writes itself rather than copying from the repository.
WRITTEN = (COMPONENT_NAME, EVIDENCE_PATH, PREVIEW_PATH)
REFUSALS = {"evidence_missing": "native_evidence_missing", "evidence_stale": "native_evidence_stale",
            "native_check_failed": "native_check_failed", "preview_mismatch": "native_evidence_stale",
            "preview_unexpected": "native_evidence_stale"}


def raw_address(revision: str, path: str) -> str:
    return https_address(RAW_HOST, f"{REPOSITORY}/{revision}/{path}")


def derived_effects(kind: str, entries: list) -> list:
    """(effect, rule) pairs computed with qualification's own rules, so declared and derived effects agree."""
    from component_qualification.checks import POLICY_PATH, code_effects, is_test_file
    from licensed_import.checks import package_effects
    from loop_engine.core.service_runtime.catalogue_packages import EXECUTABLE_ROLES
    found = {}
    for entry in entries:
        if entry.path.endswith(".py") and not is_test_file(entry.path):
            for effect, line in code_effects(entry.data.decode("utf-8"), set()).items():
                found.setdefault(effect, f"python_syntax_tree {entry.path}:{line}")
    if any(entry.role in EXECUTABLE_ROLES for entry in entries):
        found.setdefault("spawns_process", "holds_an_executable_file")
    text_roles = set(json.loads(POLICY_PATH.read_text(encoding="utf-8"))["effect_text_roles"])
    _effects, rows = package_effects(kind, {entry.path: entry.data for entry in entries if entry.role in text_roles},
                                     {entry.path: entry.role for entry in entries})
    for row in rows:
        if row["effect"] != "pure":
            found.setdefault(row["effect"], f"licensed_import_rule {row['rule']}")
    return sorted(found.items())


def build_item(family_directory: Path, family: dict, identity: str, *, code_revision: str, licence_text: bytes,
               generated_on: str, retrieved_at: str, evidence_root: "Path | None") -> tuple:
    item = read_item(family_directory, identity, family)
    evidence = preview = None
    if family["native_verifier"] is not None and evidence_root is not None:
        record = Path(evidence_root) / family["family"] / f"{identity}.json"
        if record.is_file():
            evidence = record.read_bytes()
            image = record.with_suffix(".png")
            preview = image.read_bytes() if image.is_file() else None
    entries = package_entries(family_directory, identity, evidence=evidence, preview=preview, revision=code_revision)
    base = f"tools/creative_originals/{family['family']}"
    sources = {row["path"]: f"{base}/items/{identity}/{row['path']}" for row in item["files"]}
    sources.update({row["path"]: f"{base}/shared/{row['path']}" for row in family["shared_files"]})
    files, facts = [], [fact_source(raw_address(code_revision, LICENCE_NAME), retrieved_at,
                                    hashlib.sha256(licence_text).hexdigest(), len(licence_text), "licence_text",
                                    spdx=GENERATED_CODE_LICENCE, basis="repository_licence_at_the_pinned_commit")]
    for entry in entries:
        if entry.path in WRITTEN:
            files.append(PackageFile(entry.path, entry.data, entry.role, GENERATED, media_type=entry.media_type))
            continue
        digest = hashlib.sha256(entry.data).hexdigest()
        address = raw_address(code_revision, sources[entry.path])
        files.append(PackageFile(entry.path, entry.data, entry.role, UPSTREAM_VERBATIM,
                                 {"url": address, "sha256": digest}, media_type=entry.media_type))
        facts.append(fact_source(address, retrieved_at, digest, len(entry.data), "release",
                                 spdx=GENERATED_CODE_LICENCE, basis="repository_licence_at_the_pinned_commit"))
    files.append(PackageFile(LICENCE_NAME, licence_text, "other", LICENCE_TEXT))
    kind = FORM_KINDS[item["form"]]
    key = upstream_key(CREATIVE_ORIGINALS, f"{family['family']}/{identity}")
    tests = sorted(entry.path for entry in entries if "/" not in entry.path and entry.path.startswith("test_")
                   and entry.path.endswith(".py"))
    native = "not_applicable" if family["native_verifier"] is None else "passed"
    supply = SupplyPackage(
        line=CREATIVE_ORIGINALS, identity=f"{family['family']}/{identity}", key=key, kind=kind,
        native_format=NATIVE_FORMAT, form=item["form"], name=item["title"],
        description=f"{item['purpose']} Limits: {item['limits']}",
        files=files, licence_expression=GENERATED_CODE_LICENCE,
        provenance=provenance("github_repository", REPOSITORY, f"{base}/items/{identity}", code_revision, facts,
                              {"identity": "creative_originals", "version": GENERATOR_VERSION,
                               "code_revision": code_revision}),
        placements=[{"harness": "reference", "path": f"baltor/{family['family']}/{identity}/",
                     "basis": "documented_layout", "scope": "project", "support": "unverified"}],
        effects=derived_effects(kind, [Entry(row.path, row.data, row.role, row.media_type or "") for row in files]),
        credentials=[],
        tests={"files": tests, "command": "python -m unittest " + " ".join(name[:-3] for name in tests),
               "network": False, "native": native, "native_record": EVIDENCE_PATH if native == "passed" else None},
        repository={"name": REPOSITORY, "revision": code_revision, "family": family["family"], "identity": identity,
                    "dimension": item["dimension"], "engine": item["engine"], "asset_role": item.get("asset_role"),
                    "tags": item["tags"], "family_version": family["generator_version"]},
        generated_on=generated_on, comparison_text=f"{family['family']}/{identity}")
    return build(supply)


def generate(*, code_revision: str, licence_text: bytes, generated_on: str, retrieved_at: str,
             evidence_root: "Path | None", only_families=None, only_items=None, root: Path = FAMILIES_ROOT) -> tuple:
    """(built, refusals, facts, summary) for every item of the selected families."""
    built, refused, summary = [], [], {}
    for name in families(root):
        if only_families and name not in only_families:
            continue
        family_directory = Path(root) / name
        try:
            family = read_family(family_directory)
        except CreativeRecordError as error:
            refused.append(refusal(CREATIVE_ORIGINALS, "family_invalid", name, f"{error.reason}: {error.detail}"))
            continue
        counts = {"items": 0, "built": 0, "refused": 0}
        for identity in item_identities(family_directory):
            if only_items and identity not in only_items:
                continue
            counts["items"] += 1
            try:
                built.append(build_item(family_directory, family, identity, code_revision=code_revision,
                                        licence_text=licence_text, generated_on=generated_on,
                                        retrieved_at=retrieved_at, evidence_root=evidence_root))
                counts["built"] += 1
            except CreativeRecordError as error:
                refused.append(refusal(CREATIVE_ORIGINALS, REFUSALS.get(error.reason, "item_invalid"),
                                       f"{name}/{identity}", f"{error.reason}: {error.detail}"))
                counts["refused"] += 1
            except SupplyRecordError as error:
                reason = error.args[0].split(":", 1)[0] if error.args else "item_invalid"
                refused.append(refusal(CREATIVE_ORIGINALS, reason if reason in PACKAGE_REASONS else "item_invalid",
                                       f"{name}/{identity}", str(error)[:300]))
                counts["refused"] += 1
        summary[name] = counts
    return built, refused, {}, summary


#: Refusal reasons the shared packaging may raise for one item (records.REFUSAL_REASONS lists them for the line).
PACKAGE_REASONS = ("blocked_by_static_check", "package_above_review_bound", "package_path_invalid")

__all__ = ["GENERATOR_VERSION", "REPOSITORY", "NATIVE_FORMAT", "FAMILIES_ROOT", "raw_address", "derived_effects",
           "build_item", "generate"]
