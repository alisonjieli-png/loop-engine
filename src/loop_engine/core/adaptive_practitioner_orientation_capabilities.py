"""Effect-free orientation capabilities for the adaptive Practitioner.

Environment description and intelligence search are discovery operations.
They perform no effect, expose no secret, and never grant authority. The
store search inside intelligence search runs through one Practitioner Loop;
a product capability never reaches a store directly.
"""
from __future__ import annotations

import os

from ..loop.encapsulate import as_practitioner_loop
from .adaptive_practitioner_records import (
    AdaptiveRunServices)
from .adaptive_practitioner_validation import AdaptivePractitionerError


def environment_describe_operation(services: AdaptiveRunServices) -> dict:
    """Describe the runtime environment without any effect or secret.

    Orientation discovery is effect-free: it reports which capabilities are
    admitted, the sandbox availability, configured provider names without
    secrets, and the authority grants already given to this run.
    """
    import shutil
    request = services.request
    return {
        "record_type": "environment_description/v1",
        "practitioner_mode": str(getattr(request, "mode", "unknown")),
        "interaction_mode": str(getattr(request, "interaction_mode", "")),
        "authority": {
            "allow_network_reads": bool(request.allow_network_reads),
            "allow_workspace_writes": bool(request.allow_workspace_writes),
            "allow_sandbox_commands": bool(request.allow_sandbox_commands),
            "allow_source_materialization_to_model": bool(
                request.allow_source_materialization_to_model),
        },
        "sandbox": {
            "docker_command_available": bool(shutil.which("docker")),
        },
        "providers_configured": sorted({
            name for name, value in (
                ("ollama_cloud", os.environ.get("OLLAMA_API_KEY")),
                ("openrouter", os.environ.get("OPENROUTER_API_KEY")),
                ("mistral", os.environ.get("MISTRAL_API_KEY")),
                ("opencode_go", os.environ.get("OPENCODE_GO_API_KEY")),
                ("opencode_zen", os.environ.get("OPENCODE_ZEN_API_KEY")),
            ) if value}),
        "model_execution_available": bool(
            services.dependencies.model_execution is not None),
        "deterministic_resolvers_registered": len(
            services.dependencies.deterministic_resolvers),
    }


def intelligence_search_operation(
        arguments: dict, services: AdaptiveRunServices, owner) -> dict:
    """Search the supplied portfolio or packaged Context Intelligence only.

    The operation is advisory: results are typed references and candidates
    with prior_not_proof. It never promotes, executes, or materializes.
    The store search runs inside one Practitioner Loop; the capability
    never reaches a store directly.
    """
    from .context_catalog import build_context_records
    from .store_serve import STORE_KINDS, SolverStore
    query = arguments.get("query")
    if not isinstance(query, str) or not query.strip():
        raise AdaptivePractitionerError(
            "intelligence search needs one non-empty query")
    query = query.strip()
    kinds = arguments.get("kinds", [])
    if (not isinstance(kinds, list)
            or any(not isinstance(item, str) or item not in STORE_KINDS for item in kinds)):
        raise AdaptivePractitionerError(
            "intelligence search kinds must be a list of supported record kinds")
    portfolio = services.dependencies.context_portfolio
    if portfolio is not None:
        records = _portfolio_records(portfolio)
        source_scope = "supplied_practitioner_context_portfolio"
    else:
        records = build_context_records()
        source_scope = "packaged_context_catalogue"
    if kinds:
        records = tuple(record for record in records if record.kind in kinds)

    catalog = _installed_catalog(services)
    if catalog is not None and not kinds:
        return _four_layer_search(query, catalog, services, owner)

    def _search() -> dict:
        return SolverStore(core_records=records).search(query, top_n=20)

    searched = as_practitioner_loop(
        "search selected Context Intelligence records", _search, parent=owner)
    hits = searched["value"] or {}
    rows = []
    for hit in (hits or {}).get("hits", ())[:20]:
        rows.append({
            "record_id": hit.get("record_id", ""),
            "kind": hit.get("kind", ""),
            "title": str(hit.get("title", ""))[:160],
            "version": hit.get("version", ""),
            "payload_digest": hit.get("payload_digest", ""),
            "prior_not_proof": True,
        })
    return {
        "record_type": "intelligence_search_result/v1",
        "query": query,
        "source_scope": source_scope,
        "intelligence_layers": ["context_intelligence"],
        "requested_kinds": list(kinds),
        "hit_count": len(rows),
        "hits": rows,
    }


def _installed_catalog(services: AdaptiveRunServices):
    """The four layer populations this run was given, built now if it was given a builder."""
    installed = getattr(services.dependencies, "intelligence_catalog", None)
    if installed is None:
        return None
    catalog = installed() if callable(installed) else installed
    if not isinstance(catalog, dict) or not catalog:
        raise AdaptivePractitionerError(
            "the installed intelligence catalog is not a mapping of layer name to records")
    return catalog


def _four_layer_search(query: str, catalog: dict, services: AdaptiveRunServices,
                       owner) -> dict:
    """Search every installed layer and return typed references, never bodies.

    A body is loaded after selection and a permission check, so the rows here
    carry identity, layer, classification, and digest and nothing else. Reuse
    evidence the run was given reorders those references; it never removes a
    record and never adds one.
    """
    from .intelligence_layers import (IntelligenceSearchContext,
                                      IntelligenceSearchRequest, query_intelligence)
    evidence = dict(getattr(services.dependencies, "reuse_evidence", None) or {})
    result = query_intelligence(
        IntelligenceSearchRequest(query, catalog, mode="lexical", top_n=20,
                                  reuse_evidence=evidence),
        IntelligenceSearchContext(parent=owner))
    query_loop = dict(result.get("query_loop") or {})
    if query_loop.get("model_calls") not in (0, None):
        raise AdaptivePractitionerError(
            "an intelligence search must not make a model call")
    rows = []
    for hit in result.get("hits", ())[:20]:
        rows.append({
            "record_id": str(hit.get("record_id", "")),
            "layer": str(hit.get("layer", "")),
            "kind": str(hit.get("classification", "") or hit.get("kind", "")),
            "title": str(hit.get("title", ""))[:160],
            "version": str(hit.get("version", "")),
            "payload_digest": str(hit.get("payload_digest", "")),
            "prior_not_proof": True,
        })
    searched_layers = [layer for layer in catalog if catalog[layer]]
    return {
        "record_type": "intelligence_search_result/v1",
        "query": query,
        "source_scope": "installed_four_layer_catalog",
        "intelligence_layers": searched_layers,
        "requested_kinds": [],
        "reuse_evidence_records": len(evidence),
        "hit_count": len(rows),
        "hits": rows,
    }


def _portfolio_records(portfolio):
    """Project the real typed portfolio fields into the existing search records."""
    from .component_contracts import component_payload_digest
    from .practitioner_context import PractitionerContextPortfolio
    from .store_serve import StoreRecord
    if not isinstance(portfolio, PractitionerContextPortfolio):
        raise AdaptivePractitionerError("intelligence search needs a typed context portfolio")
    entries = [
        (persona.persona_id, "persona", persona.to_dict(), persona.version)
        for persona in (portfolio.persona, *portfolio.perspectives)]
    entries.extend((item.record_id, "context", item.to_dict(), item.version)
                   for item in portfolio.guidance)
    entries.extend((f"core.questions.default.{item.step_id}", "question", item.to_dict(), portfolio.version)
                   for item in portfolio.steps)
    entries.extend((item.profile_id, "strategy", item.to_dict(), item.version)
                   for item in portfolio.assembly_profiles)
    if len({entry[0] for entry in entries}) != len(entries):
        raise AdaptivePractitionerError("context portfolio search identities are ambiguous")
    return tuple(StoreRecord(
        identity, kind, identity,
        body={**body, "version": version, "payload_digest": component_payload_digest(body)},
        tags=(portfolio.portfolio_id, kind), source=portfolio.portfolio_id)
        for identity, kind, body, version in entries)


def self_test() -> dict:
    """Prove orientation capabilities are effect-free and advisory."""
    from types import SimpleNamespace
    import tempfile
    from pathlib import Path
    from dataclasses import replace
    from .practitioner_context import load_practitioner_context, PractitionerPersona

    tests = []

    def check(name: str, passed: bool) -> None:
        tests.append({"test": name, "passed": bool(passed)})

    services = SimpleNamespace(
        request=SimpleNamespace(
            mode="non_deterministic", interaction_mode="autonomous",
            allow_network_reads=False, allow_workspace_writes=True,
            allow_sandbox_commands=False,
            allow_source_materialization_to_model=True, source_refs=()),
        dependencies=SimpleNamespace(
            model_execution=None, deterministic_resolvers=(),
            context_portfolio=None))
    described = environment_describe_operation(services)
    check("environment_description_is_effect_free_and_secret_free",
          described["record_type"] == "environment_description/v1"
          and isinstance(
              described["sandbox"]["docker_command_available"], bool)
          and "OLLAMA_API_KEY" not in str(described)
          and described["authority"]["allow_workspace_writes"] is True)

    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / "source"
        source.mkdir()
        (source / "notes.md").write_text(
            "churn retention baseline notes", encoding="utf-8")
        search_services = SimpleNamespace(
            request=services.request,
            dependencies=SimpleNamespace(
                model_execution=None, deterministic_resolvers=(),
                context_portfolio=None))
        try:
            searched = intelligence_search_operation(
                {"query": "churn retention baseline",
                 "kinds": ["question"]}, search_services, owner=None)
            ok = (searched["record_type"]
                  == "intelligence_search_result/v1"
                  and all(row["prior_not_proof"] is True
                          for row in searched["hits"]))
        except Exception:
            ok = False
        check("intelligence_search_returns_advisory_references", ok)
        refused = False
        try:
            intelligence_search_operation(
                {"query": "  "}, search_services, owner=None)
        except AdaptivePractitionerError:
            refused = True
        check("empty_intelligence_query_is_refused", refused)

    advertised = lambda: {item["capability_ref"] for item in AdaptiveRunServices.available_capabilities(services)}
    check("effect_free_registered_orientation_capabilities_are_advertised",
          {"core.environment.describe", "core.intelligence.search"} <= advertised()
          and "core.source.profile" not in advertised())
    services.request.source_refs = ("fixture.csv",)
    check("source_profile_and_inspection_share_the_existing_source_read_grant",
          {"core.source.inspect", "core.source.profile"} <= advertised())
    services.request.allow_source_materialization_to_model = False
    check("source_profile_and_inspection_are_withheld_without_source_authority",
          not {"core.source.inspect", "core.source.profile"} & advertised())
    from .capability_directory import default_directory
    services.dependencies.capability_directory = default_directory()
    check("registered_code_handle_is_advertised_when_its_directory_is_installed",
          "core.capability.call" in advertised())
    services.dependencies.capability_directory = None
    check("registered_code_handle_is_withheld_without_its_binding",
          "core.capability.call" not in advertised())
    services.request.allow_workspace_writes = True
    services.request.allow_sandbox_commands = True
    services.request.verifier_path = ""
    check("every_declared_workspace_capability_is_advertised_under_its_authority",
          {"core.generated_project", "core.verify.differential", "core.workspace.read"} <= advertised()
          and "core.verifier.execute" not in advertised())
    views = AdaptiveRunServices.available_capabilities(services)
    selected = next(item for item in views if item["capability_ref"] == "core.generated_project")
    original = selected["purpose"]
    selected["purpose"] = "changed by a discovery consumer"
    selected["required_permissions"].clear()
    selected["purpose_resource"]["render_digest"] = "changed"
    fresh = next(item for item in AdaptiveRunServices.available_capabilities(services)
                 if item["capability_ref"] == "core.generated_project")
    check("discovery_consumers_cannot_mutate_instructions_permissions_or_resource_identity",
          fresh["purpose"] == original and fresh["required_permissions"]
          and fresh["purpose_resource"]["render_digest"] != "changed")
    default = load_practitioner_context()
    custom = replace(default, guidance=(replace(default.guidance[0], content="filtermarker unique guidance"),),
                     perspectives=tuple(PractitionerPersona(
                         f"fixture.filtermarker.{index}", "1.0.0", "filtermarker persona") for index in range(25)))
    services.dependencies.context_portfolio = custom
    selected = intelligence_search_operation({"query": "filtermarker", "kinds": ["context"]}, services, None)
    check("real_portfolio_projection_and_kind_filter_precede_pagination",
          selected["source_scope"] == "supplied_practitioner_context_portfolio"
          and selected["intelligence_layers"] == ["context_intelligence"]
          and selected["hit_count"] == 1
          and selected["hits"][0]["record_id"] == default.guidance[0].record_id
          and len(selected["hits"][0]["payload_digest"]) == 64)
    personas = intelligence_search_operation({"query": "filtermarker", "kinds": ["persona"]}, services, None)
    check("portfolio_search_is_bounded_and_does_not_materialize_bodies",
          personas["hit_count"] == 20 and all(hit["kind"] == "persona" for hit in personas["hits"])
          and "instruction" not in str(personas["hits"]))
    check("unrelated_queries_and_nonmatching_supported_kinds_return_empty",
          intelligence_search_operation({"query": "unrelatedzzzz"}, services, None)["hits"] == []
          and intelligence_search_operation({"query": "filtermarker", "kinds": ["strategy"]}, services, None)["hits"] == [])
    bad_requests = [{"query": []}, {"query": "x", "kinds": "context"},
                    {"query": "x", "kinds": None}, {"query": "x", "kinds": ["unknown"]}]
    rejected = 0
    for arguments in bad_requests:
        try:
            intelligence_search_operation(arguments, services, None)
        except AdaptivePractitionerError:
            rejected += 1
    check("malformed_queries_and_unsupported_kind_filters_refuse", rejected == len(bad_requests))
    services.dependencies.context_portfolio = replace(custom, guidance=(replace(
        custom.guidance[0], record_id=custom.persona.persona_id),))
    try:
        intelligence_search_operation({"query": "filtermarker"}, services, None)
        ambiguous_refused = False
    except AdaptivePractitionerError:
        ambiguous_refused = True
    check("ambiguous_portfolio_record_identities_refuse", ambiguous_refused)

    # A run given the four layer populations searches all of them, and reuse
    # evidence reorders what comes back without changing which records are
    # considered. The fixture is small and typed so the check is about the
    # wiring, not about any particular record in the repository.
    from .store_serve import StoreRecord as _StoreRecord

    def _layer_record(identity, text):
        return _StoreRecord(identity, "context", identity,
                            body={"title": text, "text": text, "version": "1.0.0",
                                  "payload_digest": "d" * 64},
                            tags=("fixture",), source="fixture")

    catalog = {
        "context_intelligence": (_layer_record("ctx.alpha", "invoice totals reconcile"),),
        "code_intelligence": (_layer_record("code.alpha", "invoice totals parser"),),
        "runtime_history_solution_intelligence": (
            _layer_record("run.alpha", "invoice totals run"),),
        "user_feedback_intelligence": (),
    }
    layered_services = SimpleNamespace(
        request=services.request,
        dependencies=SimpleNamespace(
            model_execution=None, deterministic_resolvers=(), context_portfolio=None,
            intelligence_catalog=catalog, reuse_evidence=None))
    layered = intelligence_search_operation({"query": "invoice totals"}, layered_services, None)
    layers_hit = {row["layer"] for row in layered["hits"]}
    check("a_run_with_the_four_layer_catalog_searches_every_populated_layer_and_returns_references",
          layered["source_scope"] == "installed_four_layer_catalog"
          and len(layers_hit) == 3
          and "user_feedback_intelligence" not in layered["intelligence_layers"]
          and all(row["prior_not_proof"] is True for row in layered["hits"])
          and all("body" not in row and "text" not in row for row in layered["hits"])
          and layered["reuse_evidence_records"] == 0)
    plain_order = [row["record_id"] for row in layered["hits"]]
    discredited = plain_order[0]
    evidence_services = SimpleNamespace(
        request=services.request,
        dependencies=SimpleNamespace(
            model_execution=None, deterministic_resolvers=(), context_portfolio=None,
            intelligence_catalog=lambda: catalog,
            reuse_evidence={discredited: {"label": "discredited", "posterior": 0.1}}))
    reordered = intelligence_search_operation(
        {"query": "invoice totals"}, evidence_services, None)
    reordered_ids = [row["record_id"] for row in reordered["hits"]]
    check("reuse_evidence_reorders_the_references_and_removes_none",
          sorted(reordered_ids) == sorted(plain_order)
          and reordered_ids[-1] == discredited and plain_order[-1] != discredited
          and reordered["reuse_evidence_records"] == 1)
    refused_catalog = False
    try:
        intelligence_search_operation(
            {"query": "invoice totals"},
            SimpleNamespace(request=services.request, dependencies=SimpleNamespace(
                model_execution=None, deterministic_resolvers=(), context_portfolio=None,
                intelligence_catalog=lambda: ["not a mapping"], reuse_evidence=None)),
            None)
    except AdaptivePractitionerError:
        refused_catalog = True
    packaged_services = SimpleNamespace(
        request=services.request,
        dependencies=SimpleNamespace(
            model_execution=None, deterministic_resolvers=(), context_portfolio=None,
            intelligence_catalog=None, reuse_evidence=None))
    packaged = intelligence_search_operation(
        {"query": "data quality"}, packaged_services, None)
    check("a_catalog_that_is_not_a_mapping_is_refused_and_a_run_without_one_still_searches_context",
          refused_catalog
          and packaged["source_scope"] == "packaged_context_catalogue"
          and packaged["intelligence_layers"] == ["context_intelligence"])
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "orientation_capabilities_test/v1",
            "tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}


__all__ = (
    "environment_describe_operation", "intelligence_search_operation")
