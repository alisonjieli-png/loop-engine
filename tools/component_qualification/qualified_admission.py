"""Admit qualified generated components with independent review ongoing after publication.

The owner, October 5, 2026: "Can you streamline or even completely remove the independent review, independent
review should be an ongoing processes, not something that stops publications." This route admits every
qualified component of every generator version that is not held. Deterministic qualification stays blocking;
the sampled independent review becomes the ongoing audit (``audit.py``), which withdraws what it rejects and
holds a generator version whose recorded defect rate reaches the tolerance.

```text
admit-qualified (deterministic; reads, never calls a model)
├── read  the qualification run, the decision ledger (read only and exact) and the held-versions file
├── hold  a generator version (supply line and version) whose recorded defect rate in the ledger is at or
│         above the tolerance, or that the held-versions file names (``line/version`` or ``line/*``)
├── leave out  a component a reviewer rejected (ledger, by identity or package digest), a component of a held
│              version, a component qualification refused
└── write  items.json, reviews.json, the exact files, the attribute schema, admission-report.json and
           decided.txt, into a new folder that appears only when complete
```

Each row is a community row with the approval state ``qualified`` and the rule
``deterministic_qualification_independent_review_ongoing``: its one decision is
the deterministic qualification participant's, bound to the exact package
digest and to the evidence it read. No row is recorded as reviewed, and the
release tools refuse a qualified row that names the verified tier.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil

from . import decisions, sampling
from .admission import _revision, reference_for
from .components import StoreReader

HELD_RECORD = "generated_held_generator_versions/v1"
HELD_FIELDS = ("record_type", "held")
HELD_ENTRY_FIELDS = ("generator", "reason", "held_at", "held_by")
REPORT_RECORD = "generated_qualified_admission_report/v1"
PARTICIPANT = "generated_component_qualification/v1"
#: The canonical held-versions file the lead controls, beside the decision ledger.
HELD_VERSIONS_PATH = "/home/username/baltor-library/generated-admission/held-generator-versions.json"
DECISION_RULE = ("A generated component is admitted to the community tier when a qualification process separate "
                 "from its generator checked its exact package digest (manifest, licence and pinned provenance, "
                 "parse, schema, declared effects, safety and secret scans, and duplicates, with known-wrong "
                 "controls), its generator version is not held, and no reviewer rejected it. No model reviewer has "
                 "approved it: independent review is ongoing after publication (the owner, October 5, 2026). The "
                 "audit samples each published batch with a calibrated reviewer of a family that did not write the "
                 "generator, a rejected component is withdrawn, and a generator version whose recorded defect rate "
                 "reaches the tolerance is held, so nothing more of it is admitted.")


class QualifiedAdmissionError(ValueError):
    """A stable refusal code and an operator message; nothing was written."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def _refuse(code: str, message: str):
    raise QualifiedAdmissionError(code, message)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def _file_sha256(path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_held(path) -> dict:
    """Generator (``line/version``) or line pattern (``line/*``) to its hold entry, read exactly."""
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        _refuse("held_versions_missing", f"no held-versions file at {path}; the lead keeps it beside the ledger")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        _refuse("held_versions_unreadable", f"{path} is not JSON")
    if type(value) is not dict or set(value) != set(HELD_FIELDS) or value["record_type"] != HELD_RECORD \
            or type(value["held"]) is not list:
        _refuse("held_versions_unreadable", f"{path} is not a {HELD_RECORD} record")
    held = {}
    for entry in value["held"]:
        if type(entry) is not dict or set(entry) != set(HELD_ENTRY_FIELDS) or not all(
                type(entry[name]) is str and entry[name].strip() for name in HELD_ENTRY_FIELDS):
            _refuse("held_versions_unreadable", f"each hold names exactly {list(HELD_ENTRY_FIELDS)}")
        line, separator, version = entry["generator"].partition("/")
        if not line or separator != "/" or not version or "@" in version or entry["generator"] in held:
            _refuse("held_versions_unreadable", f"{entry['generator']!r} is not one line/version or line/*")
        held[entry["generator"]] = entry
    return held


def held_generators(ledger, held_file: dict, generators, policy=sampling.SamplingPolicy()) -> dict:
    """Each held generator of ``generators`` with the reason: a listed hold, or a recorded rate at the tolerance."""
    rows = ledger.history_rows()
    held = {}
    for generator in sorted(set(generators)):
        line = generator.split("/", 1)[0]
        entry = held_file.get(generator) or held_file.get(f"{line}/*")
        if entry is not None:
            held[generator] = f"held by the held-versions file: {entry['reason']} (held {entry['held_at']} by " \
                              f"{entry['held_by']})"
            continue
        history = sampling.GeneratorHistory.from_decisions(generator, rows)
        rate = history.observed_rate(policy)
        if rate is not None and rate >= policy.tolerance_defect_rate:
            held[generator] = (f"recorded defect rate {history.defective} of {history.sampled} "
                               f"({rate:.3f}) is at or above the tolerance {policy.tolerance_defect_rate}")
    return held


def _participant(basis: dict) -> dict:
    return {"reviewer_id": PARTICIPANT + "." + _sha(basis),
            "label": "Deterministic qualification of the exact package bytes; independent review ongoing",
            "family": "deterministic_process", "model": "none", "engine_kind": "deterministic_qualification",
            "installation_sha256": _sha(basis), "lens": "deterministic_qualification",
            "produced_any_item_under_review": False}


def admit_qualified(qualification_folder: Path, store_root: "Path | None", decisions_path: Path, held_path: Path,
                    output: Path, recorded_at: str, root: Path, *, lines=(), batches=(),
                    producer_family: str = "anthropic", components: "dict | None" = None) -> dict:
    """Write the admission folder. ``components`` (identity to component) replaces the store for checks."""
    from tools.build_host_catalogue_manifest import QUALIFICATION_RULE, QUALIFIED_STATE
    from tools.write_reviewed_catalogue import (COMPONENT_FORM_ATTRIBUTE, FACET_ATTRIBUTES, HARNESS_KIND_ATTRIBUTE,
                                                STEP_FUNCTIONS_ATTRIBUTE, TIER_ATTRIBUTE, declare, item_attributes)
    from tools.candidate_review.native import NativeReviewFile
    from tools.candidate_review.verdicts import APPROVE
    output = Path(output)
    if output.exists():
        _refuse("output_exists", f"{output} exists; an admission folder is written once")
    ledger = decisions.DecisionLedger.open(decisions_path, for_append=False)
    held_file = read_held(held_path)
    qualification_path = Path(qualification_folder) / "qualification.jsonl"
    records = []
    with open(qualification_path, encoding="utf-8") as stream:
        for line in stream:
            record = json.loads(line)
            if record.get("outcome") != "qualified":
                continue
            if (lines and record.get("line") not in lines) or (batches and record.get("batch") not in batches):
                continue
            records.append(record)
    generators = {sampling.generator_of(record["batch"]) for record in records}
    held = held_generators(ledger, held_file, generators)
    basis = {"qualification_run": str(qualification_folder), "qualification_sha256": _file_sha256(qualification_path),
             "decision_ledger": str(decisions_path), "decision_ledger_sha256": ledger.sha256,
             "held_versions": str(held_path), "held_versions_sha256": _file_sha256(held_path),
             "lines": sorted(lines), "batches": sorted(batches),
             "tolerance_defect_rate": sampling.SamplingPolicy().tolerance_defect_rate}
    participant = _participant(basis)
    partial = output.with_name(output.name + f".partial-{os.getpid()}")
    if partial.exists():
        shutil.rmtree(partial)
    reader = StoreReader(store_root) if components is None else None
    items, rows, counts, report_batches, left_out = [], [], Counter(), {}, Counter()
    try:
        for record in sorted(records, key=lambda value: value["identity"]):
            identity, batch = record["identity"], record["batch"]
            generator = sampling.generator_of(batch)
            summary = report_batches.setdefault(batch, {"generator": generator, "qualified": 0, "admitted": 0,
                                                        "held": held.get(generator), "rejected_by_a_reviewer": 0})
            summary["qualified"] += 1
            if generator in held:
                left_out["generator_version_held"] += 1
                continue
            if ledger.rejected(identity, record["package_digest"]):
                summary["rejected_by_a_reviewer"] += 1
                left_out["rejected_by_a_reviewer"] += 1
                continue
            if record["qualifier"].get("uncommitted_changes", True):
                _refuse("qualifier_uncommitted", f"{identity}: its qualifier's code was not committed")
            component = components[identity] if components is not None else reader.component(reader.row(identity))
            from .checks import require_declared_producer_family
            require_declared_producer_family(component, producer_family)
            if component.record_version != record["record_version"]:
                _refuse("store_changed", f"{identity}: the stored metadata differs from the qualified store version")
            if component.package.package_digest != record["package_digest"]:
                _refuse("store_changed", f"{identity}: the stored package differs from the qualified package")
            reference = reference_for(component)
            files = tuple(NativeReviewFile(file, component.payloads[file.path]) for file in component.package.files)
            spec = {"title": component.candidate.get("name") or identity, "component_form": component.form,
                    "provenance": {"harness_kind": component.kind}}
            attributes, engines = item_attributes(reference, spec, component.package, files, is_import=True)
            body_path = f"bodies/{identity}.md"
            declared = []
            for file in component.package.files:
                source = f"packages/{identity}/{file.path}"
                target = partial / source
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(component.payloads[file.path])
                declared.append({"source": source, "path": file.path, "media_type": file.media_type,
                                 "role": file.role})
            (partial / "bodies").mkdir(parents=True, exist_ok=True)
            (partial / body_path).write_bytes(component.package.document())
            provenance = {"authoring": component.candidate.get("authoring"), "line": component.line,
                          "component_form": component.form, "generator": component.generator,
                          "facts": (component.candidate.get("provenance") or {}).get("facts", []),
                          "license": component.candidate.get("licence"),
                          "reviewed_package_digest": record["package_digest"],
                          "qualification": {"vetting": record["vetting"], "qualifier": record["qualifier"],
                                            "self_test_sha256": record["self_test_sha256"]}}
            items.append({"reference": reference, "body_path": body_path, "package_files": declared,
                          "lifecycle": "candidate", "license_state": "declared", "tier": "community",
                          "provenance": provenance, "attributes": attributes,
                          **({"attribute_engines": engines} if engines else {})})
            decision = {"reviewer_id": participant["reviewer_id"], "decision": APPROVE, "reason": "", "findings": [],
                        "body_sha256": record["package_digest"], "call_ref": "",
                        "basis": {"qualification_ref": f"qualification.jsonl#{identity}",
                                  "qualification_record_sha256": _sha(record), "batch": batch,
                                  "generator": generator}}
            rows.append({"identity": identity, "body_path": body_path, "body_digest": component.package.served_digest,
                         "body_size_bytes": component.package.served_size,
                         "declared_license": component.licence_expression, "source_layer": "code_intelligence",
                         "decisions": [decision], "outcome": "approved", "approval_state": QUALIFIED_STATE,
                         "rule_applied": QUALIFICATION_RULE, "independent_review": "ongoing",
                         "approval_ref": f"reviews.json#{identity}", "tier": "community",
                         "producer": {"producer_identity": f"library_supply_generator:{batch}",
                                      "family": producer_family},
                         "reviewed_package": {"package_digest": record["package_digest"],
                                              "files": [{"path": file.path, "digest": file.digest}
                                                        for file in component.package.files]},
                         "prechecks": "passed"})
            summary["admitted"] += 1
            counts[(component.line, component.form, attributes.get("harness_kind"))] += 1
    except BaseException:
        if reader is not None:
            reader.close()
        shutil.rmtree(partial, ignore_errors=True)
        raise
    if reader is not None:
        reader.close()
    if not rows:
        shutil.rmtree(partial, ignore_errors=True)
        _refuse("nothing_admitted", "no qualified component of an unheld generator version was found")
    revision = _revision(root)
    record = {"record_type": "starter_catalogue_independent_review/v2", "recorded_at": recorded_at,
              "catalogue_folder": str(output), "catalogue_items_file": "items.json",
              "catalogue_items_record_type": "starter_catalogue_candidate_items/v2",
              "catalogue_source_revision": revision, "approval_ref_prefix": "reviews.json#",
              "tier": "community", "approval_basis": QUALIFIED_STATE, "decision_rule": DECISION_RULE,
              "what_an_approval_permits": ("An approved row may be named by a release bundle and served, labelled "
                                           "community, by a host whose licence policy accepts its licence. Approval "
                                           "grants no effect, network access, spending or model authority, and "
                                           "states no model review: independent review is ongoing."),
              "what_a_rejection_records": ("This folder holds no rejection. A component the ongoing audit rejects is "
                                           "withdrawn after publication and left out of later admissions."),
              "reviewers": [participant], "admission_basis": basis, "ledgers": [],
              "totals": {"items_in_catalogue": len(rows), "items_reviewed": 0, "items_qualified": len(rows),
                         "approved": len(rows), "approved_as_reviewed": 0, "approved_by_carry": 0,
                         "approved_by_qualification": len(rows), "rejected": 0, "carry_refused": 0,
                         "not_reviewed": 0},
              "rows": rows}
    items_record = {"record_type": "starter_catalogue_candidate_items/v2", "source_revision": revision,
                    "previous_source_revisions": [], "source_digests": {}, "publication": "not_published",
                    "items": items}
    schema = declare(json.loads((root / "examples/29_intelligence_service/starter-catalogue/attribute-schema.json")
                                .read_text(encoding="utf-8")),
                     TIER_ATTRIBUTE, HARNESS_KIND_ATTRIBUTE, STEP_FUNCTIONS_ATTRIBUTE, COMPONENT_FORM_ATTRIBUTE,
                     *FACET_ATTRIBUTES)
    (partial / "items.json").write_text(json.dumps(items_record, indent=1, sort_keys=True) + "\n")
    (partial / "reviews.json").write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
    (partial / "attribute-schema.json").write_text(json.dumps(schema, indent=2) + "\n")
    report = {"record_type": REPORT_RECORD, "written_at": _now(), "output": str(output), "approval_basis": QUALIFIED_STATE,
              "admitted": len(rows), "left_out": dict(left_out), "held_generators": held, "batches": report_batches,
              "licences": dict(Counter(row["declared_license"] for row in rows)),
              "by_line_form_kind": [{"line": line, "form": form, "harness_kind": kind, "count": count}
                                    for (line, form, kind), count in sorted(counts.items())],
              "decision_ledger_sha256": ledger.sha256}
    (partial / "admission-report.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    (partial / "decided.txt").write_text("".join(f"{row['identity']} admitted_by_qualification {recorded_at}\n"
                                                 for row in rows))
    os.rename(partial, output)
    return {"output": str(output), "admitted": len(rows), "left_out": dict(left_out),
            "held_generators": sorted(held), "by_line": dict(Counter(line for (line, _f, _k) in counts.elements()))}


def command(options, root: Path) -> dict:
    return admit_qualified(options.qualification, options.store_root, options.decisions, options.held_versions,
                           options.output, options.recorded_at, root, lines=tuple(options.line),
                           batches=tuple(options.batch), producer_family=options.producer_family)
