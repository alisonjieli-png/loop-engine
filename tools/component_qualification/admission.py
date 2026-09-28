"""Write the qualified components of accepted batches as a reviewed folder for the existing release path.

```text
Admission folder (the format tools/write_reviewed_catalogue.py writes; read by combine and the bundle builder)
├── items.json    starter_catalogue_candidate_items/v2: one row per admitted or rejected component, with its
│                 package files, harness kind and facet attributes, and its generated provenance
├── reviews.json  starter_catalogue_independent_review/v2, tier community, two named reviewers:
│   ├── generated_batch_admission/v1: the deterministic qualification of the exact package digest and the
│   │   accepted batch decision (sample size, acceptance number, defects found, controls rejected)
│   └── the sampling reviewer: its own decision and ledger call, for sampled components only
├── bodies/<identity>.md and packages/<identity>/<path>: the exact bytes
├── attribute-schema.json, admission-report.json (counts by line, form and harness kind; withheld batches)
```

Rules: a component is admitted only when its qualification record says qualified for the exact package
digest, its batch decision says accepted, and (when sampled) its reviewer approved it. A sampled component
the reviewer rejected is written as rejected with the reviewer's reason and is never bundled. A withheld
batch writes nothing but its line in the report. Nothing here calls a model or grants an effect.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from .components import StoreReader

ADMISSION_REVIEWER = "generated_batch_admission/v1"
ADMISSION_RECORD = "generated_component_admission_report/v1"
DECISION_RULE = ("A generated component is approved for the community scope only when a qualification process "
                 "separate from its generator checked its exact package digest (manifest, licence and pinned "
                 "provenance, parse, schema, declared effects, safety and secret scans, duplicates, and its own "
                 "tests and entry points in a sandbox without network, every check with known-wrong controls), "
                 "and its generator batch was accepted by the written sampling rule: a random sample reviewed "
                 "by one calibrated reviewer from a model family that did not write the generator, with planted "
                 "known-wrong controls in every call, found no more defective components than the plan's "
                 "acceptance number. A sampled component the reviewer rejected is never approved. Feedback "
                 "withdraws an item after publication.")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def reference_for(component) -> dict:
    """The served reference, built the way the licensed import builds its own."""
    from loop_engine.core.harness_intelligence import HarnessIntelligenceItem
    from loop_engine.core.intelligence_tagging import TagSet
    from tools.licensed_import.review_export import REFERENCE_KINDS
    record, package = component.candidate, component.package
    source = record.get("provenance") or {}
    origin = "/".join(str(source.get(key) or "") for key in ("origin_host", "repository", "path")).strip("/")
    item = HarnessIntelligenceItem(
        identity=component.identity, kind=REFERENCE_KINDS[record["kind"]],
        purpose=(record.get("description") or f"{record['kind']} {record.get('name', '')}")[:1024],
        digest=package.served_digest, size_bytes=package.served_size, source_layer="harness_local",
        source_ref=f"{origin}@{source.get('immutable_revision') or source.get('generator', {}).get('code_revision')}",
        license_name=component.licence_expression, declared_effects=tuple(record["declared_effects"]),
        styles=(record["kind"], record.get("native_format") or component.form),
        tags=TagSet({"lifecycle": ["candidate"], "data_sensitivity": ["public"]}))
    return item.reference()


def _reviewer_entries(root: Path, reviewer: str, basis: dict) -> list:
    from tools.candidate_review import configuration as config
    panel = config.PanelConfiguration.from_dict(json.loads(
        (root / "tools/candidate_review/resources/panel.json").read_text(encoding="utf-8")))
    installation = panel.installation(reviewer)
    return [{"reviewer_id": ADMISSION_REVIEWER,
             "label": "Independent test-based qualification and the accepted batch sampling decision",
             "family": "deterministic_process", "model": "none", "engine_kind": "qualification_and_batch_sampling",
             "installation_sha256": _sha(basis), "lens": "qualification_and_batch_acceptance",
             "produced_any_item_under_review": False},
            {"reviewer_id": installation.installation_id, "label": f"{installation.model} ({installation.family})",
             "family": installation.family, "model": installation.model, "engine_kind": installation.engine_kind,
             "installation_sha256": installation.sha256, "lens": installation.lens,
             "produced_any_item_under_review": False}]


def admit(qualification_folder: Path, review_path: Path, store_root: "Path | None", output: Path, recorded_at: str,
          root: Path, *, components: "dict | None" = None) -> dict:
    """Write the admission folder. ``components`` (identity to component) replaces the store for checks."""
    from tools.write_reviewed_catalogue import (FACET_ATTRIBUTES, HARNESS_KIND_ATTRIBUTE, STEP_FUNCTIONS_ATTRIBUTE,
                                                TIER_ATTRIBUTE, declare, item_attributes)
    from tools.candidate_review.native import NativeReviewFile
    qualification = {}
    with open(Path(qualification_folder) / "qualification.jsonl", encoding="utf-8") as stream:
        for line in stream:
            record = json.loads(line)
            qualification[record["identity"]] = record
    review = json.loads(Path(review_path).read_text(encoding="utf-8"))
    if review.get("admissible") is not True:
        raise ValueError("the sampled review is not admissible: " + "; ".join(review.get("admissibility_reasons")
                                                                              or ["no admissibility record"]))
    output = Path(output)
    if output.exists():
        raise FileExistsError(f"{output} exists; an admission folder is written once")
    basis = {"qualification_run": str(qualification_folder),
             "qualification_sha256": hashlib.sha256((Path(qualification_folder) / "qualification.jsonl")
                                                    .read_bytes()).hexdigest(),
             "sampled_review": str(review_path), "sampled_review_sha256": hashlib.sha256(
                 Path(review_path).read_bytes()).hexdigest(), "sampling_policy": review["policy"]}
    reader = StoreReader(store_root) if components is None else None
    rows_by_id = {row["record_id"]: row for row in reader.rows()} if reader is not None else {}

    def load(identity):
        return components[identity] if components is not None else reader.component(rows_by_id[identity])

    items, rows, bodies, report_batches, counts = [], [], {}, {}, Counter()
    for batch, entry in sorted(review["batches"].items()):
        decision = entry.get("decision") or {}
        frame = sorted(identity for identity, record in qualification.items()
                       if record["batch"] == batch and record["outcome"] == "qualified")
        verdicts = {row["identity"]: row for row in entry.get("verdicts", [])}
        report_batches[batch] = {"outcome": decision.get("outcome"), "reasons": decision.get("reasons", []),
                                 "frame": len(frame), "sampled": decision.get("sampled"),
                                 "defective": decision.get("defective")}
        if decision.get("outcome") != "accepted":
            continue
        if len(frame) != entry["plan"]["batch_size"]:
            raise ValueError(f"{batch}: the qualification frame ({len(frame)}) differs from the sampled batch "
                             f"({entry['plan']['batch_size']})")
        batch_ref = f"sampled-review.json#{batch}"
        for identity in frame:
            record = qualification[identity]
            component = load(identity)
            if component.package.package_digest != record["package_digest"]:
                raise ValueError(f"{identity}: the stored package differs from the qualified package")
            sampled = verdicts.get(identity)
            admission = {"reviewer_id": ADMISSION_REVIEWER, "decision": "approve", "reason": "", "findings": [],
                         "body_sha256": record["package_digest"], "call_ref": "",
                         "basis": {"qualification_ref": f"qualification.jsonl#{identity}",
                                   "qualification_record_sha256": _sha(record), "batch": batch,
                                   "batch_decision_ref": batch_ref,
                                   "sample_size": decision["sampled"],
                                   "acceptance_number": decision["acceptance_number"],
                                   "defective_in_sample": decision["defective"],
                                   "controls_planted": decision["controls_planted"],
                                   "controls_rejected": decision.get("controls_rejected"),
                                   "in_sample": sampled is not None}}
            decisions = [admission]
            if sampled is not None:
                reviewer_decision = {"reviewer_id": review["reviewer"], "decision": sampled["decision"],
                                     "reason": sampled["reason"] if sampled["decision"] != "approve" else "",
                                     "findings": [{"criterion_id": criterion} for criterion in sampled["criteria"]],
                                     "body_sha256": sampled.get("body_sha256"), "call_ref": sampled["call_ref"]}
                if sampled["decision"] != "approve" and not reviewer_decision["reason"].strip():
                    reviewer_decision["reason"] = "rejected under the written native criteria"
                decisions.append(reviewer_decision)
            rejected = any(item["decision"] != "approve" for item in decisions)
            if rejected:
                admission["decision"] = "reject"
                admission["reason"] = "the sampling reviewer rejected this component"
            reference = reference_for(component)
            files = tuple(NativeReviewFile(file, component.payloads[file.path]) for file in component.package.files)
            spec = {"title": component.candidate.get("name") or identity,
                    "provenance": {"harness_kind": component.kind}}
            attributes, engines = item_attributes(reference, spec, component.package, files, is_import=True)
            body_path = f"bodies/{identity}.md"
            declared = []
            for file in component.package.files:
                source = f"packages/{identity}/{file.path}"
                bodies[source] = component.payloads[file.path]
                declared.append({"source": source, "path": file.path, "media_type": file.media_type,
                                 "role": file.role})
            bodies[body_path] = component.package.document()
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
            rows.append({"identity": identity, "body_path": body_path, "body_digest": component.package.served_digest,
                         "body_size_bytes": component.package.served_size,
                         "declared_license": component.licence_expression, "source_layer": "code_intelligence",
                         "decisions": decisions, "outcome": "rejected" if rejected else "approved",
                         "approval_state": "none" if rejected else "reviewed",
                         "rule_applied": ("one_written_objection_withholds_approval" if rejected
                                          else "generated_batch_admission_rule"),
                         "approval_ref": "" if rejected else f"reviews.json#{identity}", "tier": "community",
                         "producer": {"producer_identity": f"library_supply_generator:{component.batch}",
                                      "family": review["producer_family"]},
                         "reviewed_package": {"package_digest": record["package_digest"],
                                              "files": [{"path": file.path, "digest": file.digest}
                                                        for file in component.package.files]},
                         "prechecks": "passed"})
            counts[(component.line, component.form, attributes.get("harness_kind"),
                    "rejected" if rejected else "approved")] += 1
    if reader is not None:
        reader.close()
    approved = sum(1 for row in rows if row["outcome"] == "approved")
    rejected_count = len(rows) - approved
    reviewers = _reviewer_entries(root, review["reviewer"], basis)
    record = {"record_type": "starter_catalogue_independent_review/v2", "recorded_at": recorded_at,
              "catalogue_folder": str(output), "catalogue_items_file": "items.json",
              "catalogue_items_record_type": "starter_catalogue_candidate_items/v2",
              "catalogue_source_revision": _revision(root), "approval_ref_prefix": "reviews.json#",
              "tier": "community", "decision_rule": DECISION_RULE,
              "what_an_approval_permits": ("An approved row may be named by a release bundle and served by a host "
                                           "whose licence policy accepts its licence. Approval grants no effect, "
                                           "network access, spending or model authority."),
              "what_a_rejection_records": ("A rejected row stays a candidate with the reviewer's reason. It is never "
                                           "bundled; a repaired generator produces new bytes and a new review."),
              "reviewers": reviewers, "admission_basis": basis,
              "ledgers": [{"name": "sampled_review", "path": review.get("ledger", "")}],
              "totals": {"items_in_catalogue": len(rows), "items_reviewed": len(rows), "approved": approved,
                         "approved_as_reviewed": approved, "approved_by_carry": 0, "rejected": rejected_count,
                         "carry_refused": 0, "not_reviewed": 0},
              "rows": rows}
    items_record = {"record_type": "starter_catalogue_candidate_items/v2", "source_revision": _revision(root),
                    "previous_source_revisions": [], "source_digests": {}, "publication": "not_published",
                    "items": items}
    schema = declare(json.loads((root / "examples/29_intelligence_service/starter-catalogue/attribute-schema.json")
                                .read_text(encoding="utf-8")),
                     TIER_ATTRIBUTE, HARNESS_KIND_ATTRIBUTE, STEP_FUNCTIONS_ATTRIBUTE, *FACET_ATTRIBUTES)
    output.mkdir(parents=True)
    for relative, payload in sorted(bodies.items()):
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    (output / "items.json").write_text(json.dumps(items_record, indent=1, sort_keys=True) + "\n")
    (output / "reviews.json").write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
    (output / "attribute-schema.json").write_text(json.dumps(schema, indent=2) + "\n")
    report = {"record_type": ADMISSION_RECORD, "written_at": _now(), "output": str(output),
              "approved": approved, "rejected": rejected_count, "batches": report_batches,
              "licences": dict(Counter(row["declared_license"] for row in rows if row["outcome"] == "approved")),
              "by_line_form_kind": [{"line": line, "form": form, "harness_kind": kind, "outcome": outcome,
                                     "count": count} for (line, form, kind, outcome), count in sorted(counts.items())]}
    (output / "admission-report.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    # Every identity a decision settled: admitted and rejected rows, and each member of a withheld batch's
    # frame, so no later run samples the same components again until the generator changes (new bytes, new
    # identities). Sampling a withheld batch again until it passes would defeat the rule.
    decided = [f"{row['identity']} {row['outcome']} {recorded_at}" for row in rows]
    for batch, entry in sorted(review["batches"].items()):
        if (entry.get("decision") or {}).get("outcome") == "withheld":
            decided += [f"{identity} withheld {recorded_at}" for identity, record in sorted(qualification.items())
                        if record["batch"] == batch and record["outcome"] == "qualified"]
    (output / "decided.txt").write_text("\n".join(decided) + ("\n" if decided else ""))
    return {key: report[key] for key in ("output", "approved", "rejected", "licences")} | {
        "batches": {batch: value["outcome"] for batch, value in report_batches.items()}}


def _revision(root: Path) -> str:
    import subprocess
    return subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True,
                          check=False).stdout.strip()


def command(options, root: Path) -> dict:
    return admit(options.qualification, options.review, options.store_root, options.output, options.recorded_at,
                 root)
