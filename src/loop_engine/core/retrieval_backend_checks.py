"""Swappable retrieval contract checks with no external engine or network.

Factories and malformed backend outputs are controlled fixtures. The real
retriever still performs admission, facet filtering, rank fusion and result
limits. These cases establish adapter behavior, not semantic search quality.
"""
from dataclasses import replace
from types import SimpleNamespace

from .capability_directory import CapabilityHandshake
from .retrieval_backends import RetrievalBackendBinding, RetrievalRankingPolicy, INPUT_SCHEMA, OUTPUT_SCHEMA
from .retrieval import Retriever, RetrievalUnavailableError, EmbeddingSpace
from .store_serve import StoreRecord


def run_self_test_checks():
    tests, calls = [], []
    def check(name, value):
        tests.append({"test": name, "passed": bool(value)})
    def refused(function):
        try:
            function()
        except (ValueError, RetrievalUnavailableError):
            return True
        return False
    handshake = CapabilityHandshake("fixture.custom", "static_component", "Fixture ranking", ("search",),
        input_schema=INPUT_SCHEMA, output_schema=OUTPUT_SCHEMA)
    def factory(records):
        calls.append(tuple(item.record_id for item in records))
        return SimpleNamespace(search=lambda query, top_n: [(item.record_id, 1.0) for item in reversed(records)][:top_n])
    binding = RetrievalBackendBinding(handshake, "lexical", factory, "Offline fixture ranking; not a semantic model")
    records = [StoreRecord("first", "context", "first"), StoreRecord("second", "context", "second")]
    check("binding_discovery_is_effect_free", not calls and binding.identity == "fixture.custom")
    retriever = Retriever(records, lexical_backend=binding.identity, backend_bindings=(binding,))
    check("host_binding_swaps_engine_without_changing_the_search_interface",
          [item["record_id"] for item in retriever.search("anything", mode="lexical", top_n=1)["hits"]] == ["second"]
          and calls == [("first", "second")])
    before = len(calls)
    network = replace(binding, handshake=replace(handshake, surface="fixture.remote", effects=("network",)))
    check("effect_authority_is_checked_before_factory_execution",
          refused(lambda: Retriever(records, lexical_backend=network.identity, backend_bindings=(network,)))
          and len(calls) == before)
    allowed = Retriever(records, lexical_backend=network.identity, backend_bindings=(network,), authority_effects=("network",))
    check("explicit_authority_allows_the_bound_adapter", bool(allowed.search("x", mode="lexical")["hits"]))
    check("unknown_protocol_and_contract_do_not_silently_downgrade",
          refused(lambda: replace(binding, handshake=replace(handshake, output_schema="unrelated/v1")))
          and refused(lambda: Retriever(records, lexical_backend=binding.identity, backend_bindings=(
              replace(binding, handshake=replace(handshake, protocol_version="unsupported")),))))
    check("built_in_identities_and_duplicate_records_cannot_be_shadowed",
          refused(lambda: replace(binding, handshake=replace(handshake, surface="fts5"))))
    check("duplicate_record_identities_refuse", refused(lambda: Retriever([records[0], records[0]])))
    for name, pool in (("unknown", [("outside", 1.0)]), ("duplicate", [("first", 1.0), ("first", 0.1)]),
                       ("nonfinite", [("first", float("nan"))]), ("boolean", [("first", True)])):
        changed = replace(binding, factory=lambda _records, pool=pool: SimpleNamespace(search=lambda _query, _count: pool))
        chosen = Retriever(records, lexical_backend=changed.identity, backend_bindings=(changed,))
        check("invalid_" + name + "_candidate_refuses", refused(lambda: chosen.search("x", mode="lexical")))
    check("vector_binding_needs_an_exact_embedding_space", refused(lambda: replace(binding, stage="vector")))
    vector = replace(binding, stage="vector", embedding_space=EmbeddingSpace("fixture-embedding", "v1", 3))
    custom = Retriever(records, vector_backend=vector.identity, backend_bindings=(vector,))
    check("vector_space_identity_and_capability_limits_survive_engine_selection",
          custom.embedding_space == vector.embedding_space
          and "not a semantic model" in custom.search("x", mode="vector")["capability_note"])
    tuned = Retriever(records, lexical_backend=binding.identity, backend_bindings=(binding,),
                      ranking_policy=RetrievalRankingPolicy(reciprocal_rank_offset=20))
    check("ranking_settings_change_the_algorithm_through_the_same_interface",
          tuned.search("x", mode="lexical")["hits"][0]["rrf"] == .05
          and retriever.search("x", mode="lexical")["hits"][0]["rrf"] == .1)
    check("invalid_ranking_settings_refuse", all(refused(action) for action in (
        lambda: RetrievalRankingPolicy(reciprocal_rank_offset=0),
        lambda: RetrievalRankingPolicy(facet_preference_weight=float("nan")),
        lambda: RetrievalRankingPolicy(candidate_pool_multiplier=True),
        lambda: RetrievalRankingPolicy(hash_similarity_floor=2))))
    return {"tests": tests, "passed": sum(item["passed"] for item in tests), "total": len(tests),
            "all_passed": all(item["passed"] for item in tests)}
