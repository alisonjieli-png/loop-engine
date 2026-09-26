"""Write a reviewed catalogue folder that the release tools accept, from review ledgers and one candidate catalogue.

The candidate catalogue is a native candidate folder from the factory
(``tools/prepare_harness_candidates.py``, version three) or a licensed import
review export (``tools/licensed_import/review_export.py``), which the panel's
imported reader and profile read (roadmap S-6.196). The review ledgers are
the panel's own (``tools/candidate_review``). The output is one new folder,
outside this public repository, that ``tools/build_catalogue_release_bundle.py``
and ``tools/build_host_catalogue_manifest.py`` read: ``items.json``
(``starter_catalogue_candidate_items/v2``), ``reviews.json``
(``starter_catalogue_independent_review/v2``), the bodies and an attribute
schema that declares the tier.

When scan records are given (``--scan-record``, written by a package safety
scanner such as SkillSpector in static mode), every item needs a passing result
there too, bound to its package digest.

The tier follows the "Library tiers" row of the decision table in AGENTS.md:

- ``verified``: at least two named reviewers from distinct families, none of
  them the family that produced the item, approve it, and every automated check
  passes;
- ``community``: one named reviewer from a family that did not produce the
  item approves it, the licence is on the allowlist, the provenance is pinned
  and every automated check passes.

A folder serves one tier and names one fixed set of reviewers, because the
release tools require every named reviewer to have judged every judged row.
An item enters the folder only when every named reviewer gave a verdict bound
to its exact package, and no other reviewer did: approved when all approve,
rejected when any rejects. An item another reviewer also judged is left out,
because that verdict must count (a rejection anywhere withholds approval), and
a folder that names both reviewers is where it belongs.
Everything else is left out and listed in the writer's report with its reason:
a named reviewer of the producer's family (no family approves its own
family's output), a missing verdict, a refusing pre-check, a licence off the
allowlist, or a verdict from a scripted fixture reviewer.

A one-file package is served as one body. The verdict names the canonical
package digest, whose document names exactly one file; the row keeps that
package digest beside the body digest, and the writer refuses a row whose
package document does not name that body digest at the placement the release
serves. A package of several files is written with its files and
``package_files``, and its served digest is the reviewed package digest itself.

    PYTHONPATH=src:tools python tools/write_reviewed_catalogue.py --repository . \\
        --catalogue CANDIDATES --ledger LEDGER --reviewer claude_code.subscription --tier community \\
        --output /home/username/baltor-library/NAME --recorded-at 2026-09-24
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
REPOSITORY = HERE.parent
for entry in (str(HERE), str(REPOSITORY / "src"), str(REPOSITORY)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from candidate_review import configuration as config  # noqa: E402
from candidate_review import engines, imported, imported_profile, native, native_profile  # noqa: E402
from candidate_review.configuration import PERMISSIVE_LICENCES  # noqa: E402
from candidate_review.ledger import ReviewLedger  # noqa: E402
from candidate_review.panel import review_key, review_key_for  # noqa: E402
from candidate_review.prechecks import PrecheckContext, run_prechecks  # noqa: E402
from candidate_review.prompt import build_prompt, member_prompt_sha256  # noqa: E402
from candidate_review.records import sha256_hex  # noqa: E402
from loop_engine.core.harness_intelligence import HarnessIntelligenceDraft, item_from_body  # noqa: E402
from loop_engine.core.intelligence_tagging import TagSet  # noqa: E402
from loop_engine.core.library_ingestion.step_functions import (  # noqa: E402
    RulesStepFunctionTagger, StepFunctionMaterial, entry_text)
from loop_engine.core.service_runtime.catalogue_attributes import (  # noqa: E402
    HARNESS_KIND_ATTRIBUTE, STEP_FUNCTIONS_ATTRIBUTE, TIER_ATTRIBUTE, declare, harness_kind_of)
from loop_engine.core.service_runtime.catalogue_packages import CataloguePackage  # noqa: E402

ITEMS_RECORD = "starter_catalogue_candidate_items/v2"
REVIEW_RECORD = "starter_catalogue_independent_review/v2"
REPORT_RECORD = "reviewed_catalogue_writer_report/v1"
TIERS = ("verified", "community")
VERIFIED, COMMUNITY = TIERS
#: The file placement the release tools give a one-file item of each kind (build_catalogue_release_bundle.py).
KIND_PLACEMENT = {"skill": ("SKILL.md", "skill_definition"), "instruction_file": ("AGENTS.md", "instruction_file")}
ORIGIN_LAYER = {"context": "context_intelligence", "code": "code_intelligence"}
FIXTURE = "fixture"
RULES = {
    VERIFIED: ("An item is approved only when every named reviewer approves it, the named reviewers come from at "
               "least two model families, none of them the family that produced the item, and every automated "
               "check passes. One written objection withholds approval. Tier: Verified."),
    COMMUNITY: ("An item is approved only when its licence allows direct copying, its provenance is pinned, every "
                "automated check passes and the one named reviewer, from a family that did not produce the item, "
                "approves it against the written criteria. One written objection withholds approval. Tier: "
                "Community; it becomes Verified only through the full review."),
}
#: Each written item carries the kinds of step it supports and the kind of file a harness picks up, as served
#: attributes (roadmap S-6.206, S-6.208). The rules engine names itself on every tag it writes.
TAGGER = RulesStepFunctionTagger()


def item_attributes(reference: dict, spec: dict, package, files, *, is_import: bool) -> tuple:
    """(attributes, attribute engines) of one item: its harness kind and, when its words name one, its step
    functions. The tagger reads the name, purpose, bounded entry text and file roles, never a licence text."""
    declared = str(spec.get("provenance", {}).get("harness_kind") or "") if is_import else ""
    roles = tuple(entry.role for entry in package.files)
    kind = harness_kind_of(reference["kind"], tuple(reference.get("styles") or ()), roles, declared)
    text = entry_text([(entry.path, entry.role, entry.media_type, file.text) for entry, file in zip(package.files, files)])
    material = StepFunctionMaterial(reference["kind"], kind, str(spec.get("title") or reference["identity"]),
                                    reference["purpose"], text, roles)
    tags = TAGGER.tag(material)
    attributes = {"harness_kind": kind, **tags.attribute_values()}
    engines = ({"step_functions": {"engine_id": tags.engine_id, "engine_version": tags.engine_version}}
               if tags.functions else {})
    return attributes, engines


class WriterError(ValueError):
    """A stable refusal code for a folder that cannot be written as declared."""


def refuse(code: str, message: str = "") -> None:
    raise WriterError(f"{code}: {message}" if message else code)


def _json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def verdicts_for(ledgers, installation, request, instructions) -> list:
    """Every stored verdict of one installation on one exact request, single or batched.

    ``ledgers`` holds (name, ledger, calls by run and sequence) for each ledger read."""
    keys = {review_key(installation, request, build_prompt(request, installation, instructions)),
            review_key_for(installation, request, member_prompt_sha256(request, installation, instructions))}
    found = []
    for name, ledger, calls in ledgers:
        for key in sorted(keys):
            verdict = ledger.verdict(key)
            if verdict is not None:
                found.append((name, verdict, calls[(verdict["run_id"], verdict["sequence"])]))
    return found


def _same_family(reviewers, producer) -> bool:
    """No family approves its own family's output. A mutant control replaces this rule."""
    return any(reviewer.family == producer.family for reviewer in reviewers)


def served_form(package, files) -> dict:
    """What the release serves for one package, and the proof that it is the reviewed package."""
    if len(package.files) == 1 and package.files[0].media_type.startswith("text/"):
        entry = package.files[0]
        return {"single": True, "body": files[0].payload, "digest": entry.digest, "size": entry.size_bytes,
                "path": entry.path, "role": entry.role}
    served = CataloguePackage(package.files, "package")
    if served.package_digest != package.package_digest:
        refuse("served_package_differs", "the served package would not be the reviewed package")
    return {"single": False, "digest": package.package_digest, "size": len(package.document())}


def write(options) -> dict:
    repository = Path(options.repository).resolve()
    output = Path(options.output).resolve()
    if output == repository or repository in output.parents or output == REPOSITORY or REPOSITORY in output.parents:
        refuse("folder_inside_repository", "library bodies never go into this public repository")
    if output.exists():
        refuse("output_exists", "the reviewed catalogue folder is written once, into a new folder")
    if options.tier not in TIERS:
        refuse("tier_unknown", f"a tier is one of {list(TIERS)}")
    panel = config.PanelConfiguration.from_dict(_json(options.panel))
    reviewers = [panel.installation(name) for name in options.reviewer]
    families = {reviewer.family for reviewer in reviewers}
    if len(set(options.reviewer)) != len(options.reviewer) or len(families) != len(reviewers):
        refuse("reviewer_set_invalid", "each named reviewer is its own family")
    if options.tier == COMMUNITY and len(reviewers) != 1:
        refuse("reviewer_set_invalid", "a Community folder names exactly one reviewing family")
    if options.tier == VERIFIED and len(reviewers) < 2:
        refuse("reviewer_set_invalid", "a Verified folder names at least two reviewing families")
    # A licensed import export is read with the imported reader and judged under the imported profile; an
    # original catalogue with the original ones. Each profile's verdicts are keyed by its own request.
    is_import = imported.is_imported_catalogue(Path(options.catalogue))
    reader, profile = (imported.ImportedCatalogue, imported_profile) if is_import else (native.NativeCatalogue, native_profile)
    catalogue = reader.load(Path(options.catalogue).resolve(), repository)
    configuration = profile.configuration(panel, population_size=len(catalogue.identities()))
    criteria, instructions = profile.resources()
    checks = engines.build_precheck_engines(configuration)
    context = PrecheckContext(configuration.policy, catalogue.population_bodies())
    ledgers = []
    for path in options.ledger:
        ledger = ReviewLedger(Path(path))
        ledgers.append((Path(path).name, ledger, {(row["run_id"], row["sequence"]): row
                                                  for row in ledger.calls() + ledger.batch_calls()}))
    rows, items, bodies, left_out = [], [], {}, []
    scans = None
    if options.scan_record:
        scans = {}
        for path in options.scan_record:
            record = _json(Path(path))
            if record.get("record_type") != "package_safety_scan/v1":
                refuse("scan_record_unsupported", "a scan record is package_safety_scan/v1")
            scans.update(record["packages"])
    selected = list(catalogue.identities())
    identities_file = getattr(options, "identities_file", None)
    if identities_file:
        named = [line.strip() for line in Path(identities_file).read_text().splitlines() if line.strip()]
        unknown = sorted(set(named) - set(selected))
        if unknown:
            refuse("identity_unknown", f"the identities file names items absent from the catalogue: {unknown[:5]}")
        selected = [identity for identity in selected if identity in set(named)]
    for identity in selected:
        request = catalogue.request(identity, catalogue.producer_for(identity), criteria, instructions.sha256)
        producer = request.producer
        reference = request.item["reference"]
        if _same_family(reviewers, producer):
            left_out.append({"identity": identity, "reason": f"a named reviewer is of the producer family "
                                                             f"{producer.family}"})
            continue
        if reference["license"] not in PERMISSIVE_LICENCES:
            left_out.append({"identity": identity, "reason": "the licence is not on the allowlist"})
            continue
        prechecks = run_prechecks(request, checks, context)
        if prechecks.refused:
            left_out.append({"identity": identity, "reason": "refused by a pre-check: " + ", ".join(prechecks.reasons)})
            continue
        if scans is not None:
            scan = scans.get(reference["digest"])
            if scan is None:
                left_out.append({"identity": identity, "reason": "the declared safety scanner has no result for it"})
                continue
            if scan["refused"]:
                left_out.append({"identity": identity, "reason": "refused by the safety scanner: "
                                                                 + ", ".join(scan["refusals"])})
                continue
        decisions, missing, scripted = [], [], False
        for reviewer in reviewers:
            found = verdicts_for(ledgers, reviewer, request, instructions)
            if not found:
                missing.append(reviewer.installation_id)
                continue
            scripted = scripted or any(call["engine_kind"] == FIXTURE for _name, _verdict, call in found)
            # Any stored rejection of this exact request by this reviewer stands.
            name, verdict, call = next(((n, v, c) for n, v, c in found if v["decision"] == "reject"), found[0])
            if verdict["body_sha256"] != request.body_sha256 or verdict["reported_model"] != reviewer.model:
                refuse("verdict_binding_invalid", f"a verdict on {identity} names other bytes or another model")
            decisions.append({"reviewer_id": reviewer.installation_id, "decision": verdict["decision"],
                              "reason": verdict["reasons"] if verdict["decision"] == "reject" else "",
                              "findings": verdict["findings"], "approved_digest": verdict["body_sha256"],
                              "reported_model": verdict["reported_model"],
                              "call_ref": f"{name}#{verdict['run_id']}#{verdict['sequence']}",
                              "verdicts_on_record": len(found)})
        if missing:
            left_out.append({"identity": identity, "reason": "no verdict yet from " + ", ".join(missing)})
            continue
        # A verdict from a reviewer this folder does not name must not be lost: a rejection there withholds
        # approval, and an approval there belongs to a folder that names both families.
        outside = sorted({verdict["installation_id"] for other in panel.installations
                          if other.installation_id not in {reviewer.installation_id for reviewer in reviewers}
                          for _name, verdict, _call in verdicts_for(ledgers, other, request, instructions)})
        if outside:
            left_out.append({"identity": identity, "reason": "also judged by " + ", ".join(outside)
                                                             + ", which this folder does not name"})
            continue
        if scripted and not options.allow_fixture:
            left_out.append({"identity": identity, "reason": "a verdict came from a scripted fixture reviewer"})
            continue
        package, files = catalogue._payloads[identity]
        form = served_form(package, files)
        rejected = any(decision["decision"] != "approve" for decision in decisions)
        spec = catalogue._specifications[identity]
        body_path = f"bodies/{identity}.md"
        provenance = {"producer": dict(catalogue.item(identity)["producer"]),
                      "source_revision": catalogue.source_revision, "sources": spec["sources"],
                      "reviewed_package_digest": package.package_digest}
        if is_import:
            # The upstream facts the reviewers judged travel with the row: repository, revision, path, the
            # licence texts and attribution inside the package, and the licence decision.
            outside = spec["provenance"]["outside_provenance"]
            provenance.update({"authoring": spec["provenance"]["authoring"], "license": spec["provenance"]["license"],
                               "upstream": {key: outside[key] for key in ("origin", "origin_host", "repository", "path",
                                                                           "immutable_revision", "source_digest")},
                               "licence_decision": outside["licence_evidence"]["decision"],
                               "harness_kind": spec["provenance"]["harness_kind"]})
        else:
            provenance["authoring"] = "original_model_authored"
        attributes, attribute_engines = item_attributes(reference, spec, package, files, is_import=is_import)
        row_item = {"lifecycle": "candidate", "license_state": "declared", "tier": options.tier,
                    "provenance": provenance, "attributes": attributes,
                    **({"attribute_engines": attribute_engines} if attribute_engines else {})}
        if form["single"]:
            placement = KIND_PLACEMENT.get(reference["kind"])
            if placement is None or placement != (form["path"], form["role"]):
                left_out.append({"identity": identity, "reason": "the release has no one-file placement for this "
                                                                 "kind and path"})
                continue
            tags = TagSet({key: value for key, value in reference["tags"].items() if key != "record_type"})
            draft = HarnessIntelligenceDraft(identity, reference["kind"], reference["purpose"], "harness_local",
                                             reference["source_ref"], reference["license"],
                                             tuple(reference["declared_effects"]), tuple(reference["styles"]),
                                             tags=tags)
            item = item_from_body(draft, form["body"].decode("utf-8"))
            if item.digest != form["digest"] or sha256_hex(form["body"]) != form["digest"]:
                refuse("served_body_mismatch", f"the body of {identity} is not the reviewed package's file")
            bodies[body_path] = form["body"]
            items.append({"reference": item.reference(), "body_path": body_path, **row_item})
        else:
            declared = []
            for entry, file in zip(package.files, files):
                source = f"packages/{identity}/{entry.path}"
                bodies[source] = file.payload
                declared.append({"source": source, "path": entry.path, "media_type": entry.media_type,
                                 "role": entry.role})
            bodies[body_path] = package.document()
            items.append({"reference": dict(reference), "body_path": body_path, "package_files": declared,
                          **row_item})
        outcome = "rejected" if rejected else "approved"
        rows.append({"identity": identity, "body_path": body_path, "body_digest": form["digest"],
                     "body_size_bytes": form["size"], "declared_license": reference["license"],
                     "source_layer": ORIGIN_LAYER.get(spec["layer"], "context_intelligence"),
                     "decisions": decisions, "outcome": outcome,
                     "approval_state": "none" if rejected else "reviewed",
                     "rule_applied": ("one_written_objection_withholds_approval" if rejected
                                      else f"{options.tier}_tier_rule"),
                     "approval_ref": "" if rejected else f"reviews.json#{identity}", "tier": options.tier,
                     "producer": {"producer_identity": producer.producer_identity, "family": producer.family},
                     "reviewed_package": {"package_digest": package.package_digest,
                                          "request_sha256": request.request_sha256,
                                          "files": [{"path": entry.path, "digest": entry.digest}
                                                    for entry in package.files]},
                     "prechecks": "passed"})
    if not rows:
        refuse("no_judged_items", "no item has a verdict from every named reviewer")
    counted = {outcome: sum(1 for row in rows if row["outcome"] == outcome) for outcome in ("approved", "rejected")}
    review = {
        "record_type": REVIEW_RECORD, "recorded_at": options.recorded_at, "catalogue_folder": str(output),
        "catalogue_items_file": "items.json", "catalogue_items_record_type": ITEMS_RECORD,
        "catalogue_source_revision": catalogue.source_revision, "approval_ref_prefix": "reviews.json#",
        "tier": options.tier, "decision_rule": RULES[options.tier],
        "what_an_approval_permits": ("An approved row may be named by a release bundle and served, labelled with "
                                     "its tier, by a host whose licence policy accepts its licence. Approval "
                                     "grants no effect, network access, spending or model authority."),
        "what_a_rejection_records": ("A rejected row stays a candidate with each objection's reason and findings. "
                                     "It is never bundled and may be repaired, which is new bytes and a new review."),
        "reviewers": [{"reviewer_id": reviewer.installation_id, "label": f"{reviewer.model} ({reviewer.family})",
                       "family": reviewer.family, "model": reviewer.model, "engine_kind": reviewer.engine_kind,
                       "installation_sha256": reviewer.sha256, "lens": reviewer.lens,
                       "produced_any_item_under_review": False} for reviewer in reviewers],
        "ledgers": [{"name": name, "path": str(path)} for (name, _ledger, _calls), path in zip(ledgers, options.ledger)],
        "totals": {"items_in_catalogue": len(rows), "items_reviewed": len(rows), "approved": counted["approved"],
                   "approved_as_reviewed": counted["approved"], "approved_by_carry": 0,
                   "rejected": counted["rejected"], "carry_refused": 0, "not_reviewed": 0},
        "rows": rows}
    items_record = {"record_type": ITEMS_RECORD, "source_revision": catalogue.source_revision,
                    "previous_source_revisions": [], "source_digests": dict(catalogue.source_digests),
                    "publication": "not_published", "items": items}
    schema = declare(_json(REPOSITORY / "examples/29_intelligence_service/starter-catalogue/attribute-schema.json"),
                     TIER_ATTRIBUTE, HARNESS_KIND_ATTRIBUTE, STEP_FUNCTIONS_ATTRIBUTE)
    output.mkdir(parents=True)
    for relative, payload in sorted(bodies.items()):
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    (output / "items.json").write_text(json.dumps(items_record, indent=1, sort_keys=True) + "\n")
    (output / "reviews.json").write_text(json.dumps(review, indent=1, sort_keys=True) + "\n")
    (output / "attribute-schema.json").write_text(json.dumps(schema, indent=2) + "\n")
    tagged = [item["attributes"] for item in items]
    report = {"record_type": REPORT_RECORD, "output": str(output), "tier": options.tier,
              "reviewers": options.reviewer, "approved": counted["approved"], "rejected": counted["rejected"],
              "left_out": left_out,
              "harness_kinds": dict(sorted(Counter(values["harness_kind"] for values in tagged).items())),
              "step_functions": dict(sorted(Counter(function for values in tagged
                                                    for function in values.get("step_functions", ())).items())),
              "untagged": sum(1 for values in tagged if not values.get("step_functions"))}
    (output / "writer-report.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    return {key: report[key] for key in ("output", "tier", "approved", "rejected")} | {"left_out": len(left_out)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repository", type=Path, default=REPOSITORY)
    parser.add_argument("--panel", type=Path, default=HERE / "candidate_review/resources/panel.json",
                        help="The panel whose installations the named reviewers are.")
    parser.add_argument("--catalogue", type=Path, required=True)
    parser.add_argument("--ledger", action="append", default=[], required=True)
    parser.add_argument("--reviewer", action="append", default=[], required=True)
    parser.add_argument("--tier", required=True, choices=TIERS)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--recorded-at", required=True)
    parser.add_argument("--scan-record", action="append", default=[],
                        help="A package safety scan record; when given, every item needs a passing result in one.")
    parser.add_argument("--allow-fixture", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--identities-file", type=Path,
                        help="Write only the catalogue items this file names, one identity a line; the rest are "
                             "neither judged nor listed.")
    options = parser.parse_args(argv)
    try:
        summary = write(options)
    except (WriterError, KeyError) as error:
        print(json.dumps({"record_type": REPORT_RECORD, "refused": True, "message": str(error)}))
        return 2
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
