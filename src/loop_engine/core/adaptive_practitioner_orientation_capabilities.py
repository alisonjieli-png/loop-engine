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
    AdaptivePractitionerError, AdaptiveRunServices)


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

    passed = sum(item["passed"] for item in tests)
    return {"record_type": "orientation_capabilities_test/v1",
            "tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}


__all__ = (
    "environment_describe_operation", "intelligence_search_operation")
