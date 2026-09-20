"""Capability surfaces for the detection and correction family, so a run can call it.

Text conformance registered its own surface when it landed. The four
families that followed (duplicate detection, email recovery with malformed
field detection, address component extraction, and the copy that applies
corrections to a new target) were reachable only by importing their modules,
which makes them libraries with checks rather than parts of a working
system. This module registers all four as typed surfaces with declared
handshakes, so a Practitioner reaches them the same way it reaches any other
capability: by need, through the directory, with the effects declared up
front. The copy surface is the only one that writes, and it says so.

The registrations live on this side of the boundary so that core never
imports a code node package. Nothing here performs an effect at import time
and nothing here calls a model.
"""
from __future__ import annotations

from . import address_components, database_copy, duplicate_detection, field_recovery
from .text_conformance import load_packaged_catalogs, merge_layers

#: The obligations these surfaces answer, in the words a caller would use.
FAMILY_NEEDS = (
    ("duplicate_detection", "find records that describe the same entity"),
    ("field_recovery", "repair spoiled contact values and flag malformed ones"),
    ("address_components", "split an address line into its parts"),
    ("database_copy", "write a corrected and deduplicated copy of a table"),
)


def _catalogs(supplied) -> dict:
    return supplied if supplied else merge_layers([load_packaged_catalogs()])


def _field_spec(value):
    if isinstance(value, duplicate_detection.DuplicateFieldSpec):
        return value
    return duplicate_detection.DuplicateFieldSpec(**dict(value or {}))


def duplicate_detection_run_endpoint(**kw) -> dict:
    """Compare rows inside declared blocks and report every pair with its outcome."""
    policy = kw.get("policy")
    if isinstance(policy, dict):
        policy = duplicate_detection.DuplicatePolicy(**policy)
    report = duplicate_detection.find_duplicates(
        kw.get("rows") or (), _field_spec(kw.get("fields")), policy,
        catalogs=_catalogs(kw.get("catalogs")))
    return {"report": report.to_dict(), "summary": duplicate_detection.summarize(report)}


def duplicate_detection_propose_endpoint(**kw) -> dict:
    """Propose one survivor per duplicate cluster; no row is changed."""
    rows = list(kw.get("rows") or ())
    policy = kw.get("policy")
    if isinstance(policy, dict):
        policy = duplicate_detection.DuplicatePolicy(**policy)
    report = duplicate_detection.find_duplicates(
        rows, _field_spec(kw.get("fields")), policy, catalogs=_catalogs(kw.get("catalogs")))
    proposal = duplicate_detection.dedupe(
        rows, report, strategy=kw.get("strategy", duplicate_detection.STRATEGIES[0]))
    return {"report": report.to_dict(), "proposal": proposal.to_dict()}


def duplicate_detection_surface():
    """The typed surface registration for duplicate detection."""
    from ..core.capability_directory import CapabilityHandshake, Endpoint, SurfaceRegistration
    return SurfaceRegistration(CapabilityHandshake(
        "duplicate_detection", "code_node_registry",
        "fuzzy duplicate detection over names, addresses, emails, and phones: rows "
        "are compared only inside declared blocking keys, every pair carries named "
        "signals and a confidence that is the weakest named signal, clusters follow "
        "duplicate decisions only, and a dedupe is a proposal that changes no row",
        operations=("run", "compose"), accepts=("code",), returns=("code",),
        input_schema="rows_and_field_specification",
        output_schema=duplicate_detection.REPORT_RECORD_TYPE),
        (Endpoint("run", duplicate_detection_run_endpoint),
         Endpoint("compose", duplicate_detection_propose_endpoint)))


def field_recovery_run_endpoint(**kw) -> dict:
    """Recover every value of one column under the apply, hold, and escalate bands."""
    tables = kw.get("tables")
    if isinstance(tables, dict):
        tables = field_recovery.RecoveryTables(**tables)
    policy = kw.get("policy")
    if isinstance(policy, dict):
        policy = field_recovery.RecoveryPolicy(**policy)
    return field_recovery.recover_column(kw.get("values") or (), tables, policy)


def field_recovery_validate_endpoint(**kw) -> dict:
    """Flag the values whose pattern differs from the column's dominant pattern."""
    share = kw.get("dominant_share", field_recovery.DEFAULT_DOMINANT_SHARE)
    return field_recovery.detect_malformed(kw.get("values") or (), dominant_share=share)


def field_recovery_surface():
    """The typed surface registration for email recovery and malformed field detection."""
    from ..core.capability_directory import CapabilityHandshake, Endpoint, SurfaceRegistration
    return SurfaceRegistration(CapabilityHandshake(
        "field_recovery", "code_node_registry",
        "email recovery from declared tables of spelled-out separators, punctuation "
        "slips, and typed domains, each correction carrying its reasons and the "
        "weakest named confidence under the same apply, hold, and escalate bands as "
        "text conformance; malformed field detection by dominant pattern margin",
        operations=("run", "validate"), accepts=("code",), returns=("code",),
        input_schema="column_values",
        output_schema=field_recovery.RECOVERY_RECORD_TYPE),
        (Endpoint("run", field_recovery_run_endpoint),
         Endpoint("validate", field_recovery_validate_endpoint)))


def address_components_run_endpoint(**kw) -> dict:
    """Split every supplied address line into its components with named reasons."""
    parser = kw.get("parser", address_components.PARSERS[0])
    extracted = [address_components.extract_components(value, parser=parser)
                 for value in kw.get("values") or ()]
    return {"parser": parser, "total": len(extracted),
            "components": [item.to_dict() for item in extracted],
            "keys": [item.key() for item in extracted],
            "available": all(item.available for item in extracted) if extracted else True}


def address_components_surface():
    """The typed surface registration for address component extraction."""
    from ..core.capability_directory import CapabilityHandshake, Endpoint, SurfaceRegistration
    return SurfaceRegistration(CapabilityHandshake(
        "address_components", "code_node_registry",
        "address component extraction into house number, street, unit, city, region, "
        "postal code, and country from declared unit keywords and postal patterns, "
        "with the reasons for what could not be placed and a confidence that is the "
        "weakest named signal; optional parsers report unavailability, never a guess",
        operations=("run",), accepts=("code",), returns=("code",),
        input_schema="address_lines", output_schema=address_components.RECORD_TYPE),
        (Endpoint("run", address_components_run_endpoint),))


def database_copy_run_endpoint(**kw) -> dict:
    """Copy a table to a new target with applied corrections and a dedupe proposal."""
    def location(value):
        if isinstance(value, database_copy.TableLocation):
            return value
        return database_copy.TableLocation(**dict(value or {}))

    corrections = []
    for item in kw.get("corrections") or ():
        if isinstance(item, database_copy.ColumnCorrection):
            corrections.append(item)
        else:
            corrections.append(database_copy.ColumnCorrection(**dict(item)))
    return database_copy.copy_table(
        location(kw.get("source")), location(kw.get("target")),
        corrections=tuple(corrections), proposal=kw.get("proposal"),
        identity_column=kw.get("identity_column", ""))


def database_copy_surface():
    """The typed surface registration for the copy that applies decisions."""
    from ..core.capability_directory import CapabilityHandshake, Endpoint, SurfaceRegistration
    return SurfaceRegistration(CapabilityHandshake(
        "database_copy", "code_node_registry",
        "copy a delimited file or a table into a new target with applied corrections "
        "and the merged identities of a dedupe proposal dropped; the target is refused "
        "when it exists or is the source, held and escalated values are copied "
        "unchanged and counted, and the manifest carries the source digest before and "
        "after the copy",
        operations=("run",), accepts=("code",), returns=("code",),
        input_schema="source_and_target_locations",
        output_schema=database_copy.MANIFEST_RECORD_TYPE,
        effects=("reads_fs", "writes_fs"), idempotency="no_overwrite"),
        (Endpoint("run", database_copy_run_endpoint),))


def family_surfaces() -> tuple:
    """Every detection and correction surface, for one directory registration."""
    from .text_conformance import text_conformance_surface
    return (text_conformance_surface(), duplicate_detection_surface(),
            field_recovery_surface(), address_components_surface(),
            database_copy_surface())


def self_test() -> dict:
    """Every surface registers, answers through the directory, and declares its effects."""
    import tempfile
    from pathlib import Path
    from ..core.capability_directory import default_directory
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    surfaces = family_surfaces()
    directory = default_directory(surfaces=surfaces)
    names = [item.handshake.surface for item in surfaces]
    check("every_family_member_registers_one_named_surface_with_declared_operations",
          names == ["text_conformance", "duplicate_detection", "field_recovery",
                    "address_components", "database_copy"]
          and all(item.endpoints for item in surfaces)
          and all(endpoint.operation in item.handshake.operations
                  for item in surfaces for endpoint in item.endpoints)
          and len(FAMILY_NEEDS) == len(surfaces) - 1,
          str(names))
    rows = [{"id": "1", "company": "ACME WIDGETS INC", "email": "Sales at Acme dot example",
             "address": "12 N Main St., Ste 4", "phone": "+1 (415) 555-0100"},
            {"id": "2", "company": "Acme Widgets, Inc.", "email": "sales@acme.example",
             "address": "12 North Main Street Suite 4", "phone": "415-555-0100"},
            {"id": "3", "company": "Beta Holdings LLC", "email": "ops@gmail.con",
             "address": "9 Oak Ave", "phone": ""}]
    fields = {"name": "company", "address": "address", "email": "email",
              "phone": "phone", "identity": "id"}
    found = directory.call("duplicate_detection", "run", rows=rows, fields=fields)
    proposed = directory.call("duplicate_detection", "compose", rows=rows, fields=fields)
    check("a_caller_finds_duplicates_and_a_proposal_through_the_directory",
          found.ok and proposed.ok
          and found.value["summary"]["rows"] == 3
          and found.value["report"]["record_type"] == duplicate_detection.REPORT_RECORD_TYPE
          and proposed.value["proposal"]["rows_in"] == 3
          and proposed.value["proposal"]["rows_out"] <= 3,
          str(found.value["summary"]) if found.ok else str(found.note))
    recovered = directory.call("field_recovery", "run",
                               values=[row["email"] for row in rows])
    malformed = directory.call("field_recovery", "validate",
                               values=["2026-09-18", "2026-09-19", "18/09/2026"])
    check("a_caller_recovers_a_column_and_flags_malformed_values_through_the_directory",
          recovered.ok and malformed.ok
          and recovered.value["total"] == 3
          and sum(recovered.value["counts"].values()) == 3
          and recovered.value["rows"][0]["output"] == "sales@acme.example"
          and malformed.value["flagged"][0]["index"] == 2,
          str(recovered.value["counts"]) if recovered.ok else str(recovered.note))
    split = directory.call("address_components", "run",
                           values=[row["address"] for row in rows])
    check("a_caller_splits_address_lines_through_the_directory",
          split.ok and split.value["total"] == 3
          and split.value["components"][0]["components"]["house_number"] == "12"
          and split.value["keys"][0].startswith("12 ")
          and split.value["available"] is True,
          str(split.value["components"][0]["components"]) if split.ok else str(split.note))
    with tempfile.TemporaryDirectory(prefix="loop-family-surfaces-") as folder:
        import csv
        source = Path(folder) / "rows.csv"
        with open(source, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["id", "company", "email"])
            writer.writeheader()
            writer.writerows([{k: row[k] for k in ("id", "company", "email")} for row in rows])
        target = Path(folder) / "clean.csv"
        copied = directory.call(
            "database_copy", "run", source={"path": str(source)},
            target={"path": str(target)},
            corrections=[{"column": "email", "operation": field_recovery.recover_email}],
            identity_column="id")
        refused = directory.call(
            "database_copy", "run", source={"path": str(source)},
            target={"path": str(source)})
        check("a_caller_writes_a_corrected_copy_through_the_directory_and_a_bad_target_is_refused",
              copied.ok and copied.value["record_type"] == database_copy.MANIFEST_RECORD_TYPE
              and copied.value["rows_in"] == copied.value["rows_out"] == 3
              and copied.value["in_place"] is False and target.exists()
              and not refused.ok,
              str(copied.value["corrections"]) if copied.ok else str(copied.note))
    copy_handshake = next(item.handshake for item in surfaces
                          if item.handshake.surface == "database_copy")
    pure = [item.handshake for item in surfaces if item.handshake.surface != "database_copy"]
    check("only_the_copy_surface_declares_that_it_writes_and_the_others_declare_purity",
          copy_handshake.effects == ("reads_fs", "writes_fs")
          and copy_handshake.idempotency == "no_overwrite"
          and all(item.effects == ("pure",) for item in pure)
          and all(item.model_use == "none" for item in (copy_handshake, *pure)),
          str(copy_handshake.effects))
    unknown = directory.call("duplicate_detection", "search", rows=rows, fields=fields)
    declared = next(item.handshake for item in surfaces
                    if item.handshake.surface == "duplicate_detection")
    check("an_operation_a_surface_never_declared_is_refused_by_the_directory",
          not unknown.ok and unknown.value is None
          and "unsupported" in str(unknown.note).lower()
          and not declared.supports("search") and declared.supports("run"),
          str(unknown.note))
    from types import SimpleNamespace
    from ..core.registered_capability_call import (
        registered_capabilities, registered_capability_operation)
    from .solve_runtime import (SolveRequest, solve_capability_directory, solve_dependencies,
                                solve_intelligence_catalog)
    run_directory = solve_capability_directory()
    run_services = SimpleNamespace(
        dependencies=SimpleNamespace(capability_directory=run_directory))
    through_handle = registered_capability_operation(
        {"surface": "text_conformance", "operation": "validate",
         "arguments": {"rows": rows, "columns": ["company"]}}, run_services)
    listed = {row["surface"]: row for row in registered_capabilities(run_directory)}
    from ..core.intelligence_layers import LAYERS
    catalog_builder = solve_intelligence_catalog()
    run_catalog = catalog_builder()
    from ..templates.intake import TaskIntakeRequest, intake_task
    request = SolveRequest(intake_task(TaskIntakeRequest(text="Inspect declared family surfaces.")),
                           practitioner_mode="deterministic")
    installed = solve_dependencies(request, ())
    from ..core.model_call_collection import LearningEventCollector
    forwarded = []
    with_collector = solve_dependencies(
        request, (), LearningEventCollector(forward_to=forwarded.append))
    check("a_solve_run_installs_the_collector_that_keeps_what_its_model_calls_can_teach",
          isinstance(with_collector.progress, LearningEventCollector)
          and with_collector.progress.forward_to is not None
          and installed.progress is None,
          type(with_collector.progress).__name__)
    check("a_solve_run_is_given_the_four_layer_catalog_as_a_builder_it_pays_for_only_when_asked",
          installed.intelligence_catalog is not None
          and installed.capability_directory is not None
          and callable(catalog_builder) and set(run_catalog) == set(LAYERS)
          and sum(len(records) for records in run_catalog.values()) > 0
          and any("data_quality_surfaces" in str(getattr(record, "record_id", ""))
                  for record in run_catalog["code_intelligence"]),
          str({name: len(records) for name, records in run_catalog.items()}))
    check("a_solve_run_reaches_the_family_through_the_one_capability_handle",
          through_handle["ok"] and "profiles" in through_handle["value"]
          and set(names) <= set(listed)
          and all(listed[name]["callable_through_this_handle"] for name in names
                  if name != "database_copy")
          and listed["database_copy"]["callable_through_this_handle"] is False,
          str(sorted(listed))[:160])
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "data_quality_surfaces_test/v1", "tests": tests, "passed": passed,
            "total": len(tests), "all_passed": passed == len(tests)}
