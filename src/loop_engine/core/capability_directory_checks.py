"""Offline checks for the capability directory's model use declarations.

The directory module itself sits at the module size cap, so the checks for
the September 18 placement rule live here: a tool may call a model service,
and it may embed only a small in-process model with a declared memory
ceiling; a service-sized model is never loaded inside a tool.
"""
from __future__ import annotations

from .capability_directory import (
    CapabilityHandshake, CapabilityQuery, Endpoint, HandshakeError, default_directory)
from .model_ontology import ModelProfile


def model_use_checks() -> list:
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    def refuses(action):
        try:
            action()
        except ValueError:
            return True
        return False

    small = ModelProfile(
        kind="embedding", determinism="deterministic", placement="in_process",
        size_class="in_process_small", provenance="open_weights",
        output_kinds=("vector",), memory_ceiling_mb=64)
    embedding_tool = CapabilityHandshake(
        "fixture.embedder", "static_component", "embed a small model inside the tool",
        operations=("invoke",), model_use="embeds_small", model_profile=small)
    check("a_tool_embeds_only_a_small_in_process_model",
          refuses(lambda: CapabilityHandshake(
              "fixture.embedder", "static_component", "embed a model inside the tool",
              operations=("invoke",), model_use="embeds_small",
              model_profile=ModelProfile(kind="embedding")))
          and embedding_tool.describe()["model_profile"]["memory_ceiling_mb"] == 64,
          "a service-sized model is called, never loaded, by a tool")
    check("a_tool_that_calls_a_service_declares_no_in_process_profile",
          CapabilityHandshake("fixture.caller", "static_component", "call a model service",
                              operations=("invoke",), model_use="calls_service").model_profile is None
          and refuses(lambda: CapabilityHandshake(
              "fixture.caller", "static_component", "call a model service",
              operations=("invoke",), model_use="calls_service", model_profile=small))
          and refuses(lambda: CapabilityHandshake(
              "fixture.plain", "static_component", "no model", operations=("invoke",),
              model_use="none", model_profile=small)))
    check("the_handshake_digest_covers_the_model_declaration",
          embedding_tool.describe()["model_use"] == "embeds_small"
          and CapabilityHandshake("fixture.plain", "static_component", "no model",
                                  operations=("invoke",)).describe()["model_use"] == "none")
    return tests



def run_checks() -> dict:
    results: list[dict] = []

    def check(name, ok, detail=""):
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    from ..core.store_serve import SolverStore, StoreRecord
    from ..core.facets import code_facets, string_facets
    store = SolverStore(core_records=[
        StoreRecord("n.vif", "node", "compute variance inflation factor",
                    body={"kind": "node",
                          "facets": code_facets(
                              execution_mode="code_only",
                              determinism="deterministic",
                              locality="local_machine", effects=("pure",),
                              role="detect")},
                    tags=("stats", "collinearity")),
        StoreRecord("n.vif_api", "node",
                    "compute variance inflation factor via hosted stats API",
                    body={"kind": "node",
                          "facets": code_facets(
                              execution_mode="code_only",
                              determinism="deterministic",
                              locality="api_calling", effects=("network",),
                              cost_class="metered", role="detect")},
                    tags=("stats", "collinearity")),
        StoreRecord("s.warn", "context", "watch for temporal leakage",
                    body={"string_kind": "warning",
                          "facets": string_facets(
                              category="risk", subcategory="leakage",
                              job_position="risk_officer")},
                    tags=("leakage",))])
    d = default_directory(store=store)

    # 1. the practitioner KNOWS what is available, by surface kind.
    kinds = {h.surface: h.surface_kind for h in d.available()}
    check("practitioner_knows_the_available_surfaces",
          kinds.get("string_bank") == "string_store"
          and kinds.get("contract_registry") == "code_node_registry"
          and kinds.get("llm_pipeline") == "static_component"
          and kinds.get("resource_search") == "static_component",
          f"{len(kinds)} surfaces across strings / code nodes / static")

    # 2. the HANDSHAKE tells it HOW to call + WHAT is available (never assumed).
    hs = d.handshake("resource_search")
    check("handshake_declares_operations_and_search_fields",
          hs.supports("search") and "title" in hs.query_fields
          and not hs.embeddings and hs.functionality,
          "operations, query fields, ranking, and functionality are declared")

    # 3. discover: which surfaces support an operation.
    searchers = d.discover("search")
    validators = d.discover("validate", surface_kind="code_node_registry")
    check("discover_finds_surfaces_by_operation",
          "resource_search" in searchers and "string_bank" in searchers
          and validators == ["contract_registry"],
          f"search: {searchers}; validate: {validators}")

    # 4. negotiate: a supported op is ok; an unsupported one names a fallback.
    ok_neg = d.negotiate("resource_search", ["search", "get"])
    bad_neg = d.negotiate("contract_registry", ["validate", "search"])
    check("negotiate_reports_support_and_fallbacks",
          ok_neg["ok"] and not bad_neg["ok"]
          and bad_neg["missing"] == ["search"]
          and bad_neg["fallbacks"]["search"] == ("resource_search", "search"),
          "the practitioner negotiates before committing")

    # 5. a standardized CALL actually invokes the endpoint (real search).
    r = d.call("resource_search", "search", query="variance inflation collinearity")
    check("standardized_call_invokes_the_endpoint",
          r.ok and not r.used_fallback and r.value
          and any("vif" in h["record_id"] for h in r.value["hits"]),
          "call('resource_search','search',...) returns real hits")

    # 6. a missing operation follows the declared FALLBACK (a bias, not a crash).
    r2 = d.call("contract_registry", "search",
                query="temporal leakage warning")
    check("missing_operation_follows_the_declared_fallback",
          r2.ok and r2.used_fallback
          and "resource_search" in r2.note,
          "contract_registry has no search → fell back to resource_search")

    # 7. serve = the two-rail bias: no code node for a need → the LLM pipeline.
    served = d.serve("summarize")             # nothing supports 'summarize'... but
    # 'summarize' is not a standard op; discover returns [], so it asks the LLM.
    check("serve_falls_back_to_the_llm_when_no_code_node_serves",
          served.used_fallback and served.surface == "llm_pipeline"
          and served.value.get("asked_model"),
          "prefer a code node; ask the model (string rail) only when none serves")

    # 8. an unknown surface raises (no silent guessing).
    bad = False
    try:
        d.handshake("nope")
    except HandshakeError:
        bad = True
    check("unknown_surface_raises", bad, "a capability is never assumed")

    # 9. the COMPACT snapshot: versioned, by kind, and rendered for the model —
    # full awareness WITHOUT loading the catalog.
    snap = d.snapshot(gaps=("no medical-literature graph registered",))
    txt = snap.render()
    check("compact_capability_snapshot_is_versioned_and_rendered",
          snap.snapshot_id.startswith("snap.")
          and "string_bank" in snap.string_stores
          and "contract_registry" in snap.code_registries
          and "AVAILABLE CAPABILITIES" in txt and "Known gaps" in txt
          and len(txt) < 700,
          f"snapshot {snap.snapshot_id}: compact model-facing summary")

    # 10. search BY NEED (not by filename): matches keep their source surface +
    # asset class, ranked code-first (the zero-token bias).
    q = CapabilityQuery(obligation="assess redundancy",
                        desired_capability="assess feature collinearity",
                        tags=("collinearity", "stats"), preferred_class="either")
    ms = d.search_by_need(q)
    check("search_by_need_returns_matches_with_provenance",
          ms and ms[0].source_surface == "resource_search"
          and ms[0].asset_class == "code" and ms[0].resource_id,
          f"{len(ms)} match(es); first is a code node from "
          f"{ms[0].source_surface if ms else '—'}")

    # 10b. FACET BLOCKING: require locality=local_machine drops the API-calling
    # variant of the same capability — blocked by facet, never by folder.
    q_local = CapabilityQuery(
        obligation="assess redundancy",
        desired_capability="assess feature collinearity",
        tags=("collinearity", "stats"),
        require_facets={"locality": "local_machine"})
    ms_local = d.search_by_need(q_local)
    ids_local = {m.resource_id for m in ms_local}
    check("require_facet_blocks_api_calling_by_facet_not_folder",
          "n.vif" in ids_local and "n.vif_api" not in ids_local,
          f"local-only search kept {sorted(ids_local)}")

    # 10c. EXCLUDE by evidence: effects=network excluded; the pure node stays.
    q_off = CapabilityQuery(
        obligation="assess redundancy",
        desired_capability="assess feature collinearity",
        tags=("collinearity", "stats"),
        exclude_facets={"effects": "network",
                        "locality": ("api_calling", "external_resources")})
    ids_off = {m.resource_id for m in d.search_by_need(q_off)}
    check("offline_exclusion_drops_network_node_keeps_pure",
          "n.vif" in ids_off and "n.vif_api" not in ids_off,
          f"offline search kept {sorted(ids_off)}")

    # 10d. PREFER is a soft rank: preferring the metered API node reorders it
    # first WITHOUT dropping the local one.
    q_pref = CapabilityQuery(
        obligation="assess redundancy",
        desired_capability="assess feature collinearity",
        tags=("collinearity", "stats"),
        prefer_facets={"locality": "api_calling"})
    ms_pref = d.search_by_need(q_pref)
    code_hits = [m for m in ms_pref if m.asset_class == "code"]
    check("prefer_facet_reorders_without_excluding",
          {m.resource_id for m in code_hits} >= {"n.vif", "n.vif_api"}
          and code_hits[0].resource_id == "n.vif_api",
          "both nodes present; preferred one ranked first")

    # 10e. job-position lens on Context Intelligence.
    q_job = CapabilityQuery(
        obligation="warn about leakage",
        desired_capability="temporal leakage warning",
        tags=("leakage",), preferred_class="string",
        require_facets={"job_position": "risk_officer"})
    ms_job = d.search_by_need(q_job)
    check("job_position_lens_focuses_context_intelligence",
          ms_job and ms_job[0].resource_id == "s.warn"
          and ms_job[0].facets.get("job_position") == "risk_officer",
          "search focused one position's intelligence")

    # 11. the SEMANTIC fallback layer: a code registry with no such op falls
    # back to the LLM pipeline — a materially different method, labelled.
    r3 = d.call("logic_registry", "search", query="how to decide collinearity")
    check("semantic_fallback_layer_is_labelled",
          r3.used_fallback and r3.fallback_layer == "semantic",
          "code node → LLM pipeline is a semantic fallback (a new method)")

    # D-4: what the loop COULD see when it decided is part of why it decided,
    # so the snapshot belongs on the timeline.  Without a ledger the behaviour
    # is byte-identical — visibility is opt-in, never a behaviour change.
    from ..loop.recursive_loop import LoopLedger
    from ..core.run_history import to_canonical_events
    _lg = LoopLedger()
    _quiet = d.snapshot()
    _loud = d.snapshot(ledger=_lg)
    _fams = [c["type"] for c in to_canonical_events(_lg.events)]
    check("the_capability_snapshot_lands_on_the_timeline",
          _loud.snapshot_id == _quiet.snapshot_id
          and _fams == ["capability.snapshot.created"]
          and _lg.events[0]["snapshot_id"] == _loud.snapshot_id,
          f"snapshot {_loud.snapshot_id} recorded; identical without a ledger")
    static_refs = d.search_core(
        "provider neutral model routes")
    check("core_search_returns_local_loop_refs_without_calls",
          static_refs and static_refs[0].item_ref.endswith("model_gateway")
          and static_refs[0].source == "core"
          and static_refs[0].handshake.layer == "code_intelligence")
    unsafe_calls = []
    d.register(CapabilityHandshake(
        "remote_fixture_search", "static_component",
        "search a remote fixture service", operations=("search",),
        locality="api_calling", effects=("network",), cost_class="metered"),
        [Endpoint("search", lambda query: unsafe_calls.append(query) or {
            "hits": []})])
    remote_refs = d.search_core("remote fixture search")
    d.search_by_need(CapabilityQuery(
        obligation="find fixture", desired_capability="remote fixture search"))
    check("federated_discovery_never_executes_effectful_search_endpoints",
          remote_refs and not unsafe_calls
          and remote_refs[0].item_ref.endswith("remote_fixture_search"),
          "effectful capability is discoverable as a local ref, not called")

    duplicate_refused = False
    try:
        d.register(d.handshake("model_gateway"))
    except HandshakeError:
        duplicate_refused = True
    check("duplicate_static_surface_registration_is_refused",
          duplicate_refused)

    results.extend(model_use_checks())
    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "capability_directory_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
