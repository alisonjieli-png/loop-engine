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
    """Search persistent intelligence and prior runs through retrieval.

    The operation is advisory: results are typed references and candidates
    with prior_not_proof. It never promotes, executes, or materializes.
    The store search runs inside one Practitioner Loop; the capability
    never reaches a store directly.
    """
    from .context_catalog import build_context_records
    from .store_serve import SolverStore
    query = str(arguments.get("query") or "").strip()
    if not query:
        raise AdaptivePractitionerError(
            "intelligence search needs one non-empty query")
    kinds = arguments.get("kinds") or []
    if (not isinstance(kinds, list)
            or any(not isinstance(item, str) for item in kinds)):
        raise AdaptivePractitionerError(
            "intelligence search kinds must be a list of text")
    portfolio = services.dependencies.context_portfolio
    if portfolio is not None:
        records = tuple(portfolio.records)
    else:
        records = build_context_records()

    def _search() -> dict:
        return SolverStore(core_records=records).search(query, kind=None)

    searched = as_practitioner_loop(
        "search persistent intelligence records", _search, parent=owner)
    hits = searched["value"] or {}
    rows = []
    for hit in (hits or {}).get("hits", ())[:20]:
        rows.append({
            "record_id": hit.get("record_id", ""),
            "kind": hit.get("kind", ""),
            "title": str(hit.get("title", ""))[:160],
            "prior_not_proof": True,
        })
    return {
        "record_type": "intelligence_search_result/v1",
        "query": query,
        "hit_count": len(rows),
        "hits": rows,
    }


def self_test() -> dict:
    """Prove orientation capabilities are effect-free and advisory."""
    from types import SimpleNamespace
    import tempfile
    from pathlib import Path

    tests = []

    def check(name: str, passed: bool) -> None:
        tests.append({"test": name, "passed": bool(passed)})

    services = SimpleNamespace(
        request=SimpleNamespace(
            mode="non_deterministic", interaction_mode="autonomous",
            allow_network_reads=False, allow_workspace_writes=True,
            allow_sandbox_commands=False,
            allow_source_materialization_to_model=True),
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

    passed = sum(item["passed"] for item in tests)
    return {"record_type": "orientation_capabilities_test/v1",
            "tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}


__all__ = (
    "environment_describe_operation", "intelligence_search_operation")