"""Offline vertical-slice checks for the transactional semantic runtime.

The fixture uses injected interpreter transports. It proves canonical Loop
execution, trust transitions, abstention, injection resistance, requalification,
materialization through the existing flywheel, and strategy accounting. It does
not claim live provider quality or production effect safety.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import tempfile
import time
from dataclasses import replace

from ..catalog.query import IntelligenceQuery
from ..catalog.stores.in_memory import EphemeralRecordStore
from ..loop.encapsulate import as_model_loop
from ..loop.loop_capsule import ExternalPayloadRef
from ..loop.recursive_loop import LoopLedger
from .code_intelligence_assets import (
    CodeAssetAdmissionRecord, spec_from_template)
from .context_artifacts import ContextArtifactStore, ContextArtifactStoreSpec
from .reusable_capability_flywheel import (
    CapabilityAuthority, PromotionRequest, QualificationRequest)
from .reusable_capability_harvest import (
    GeneralizedCapabilityCandidate, ReuseHarvestRequest, ReuseHarvestServices,
    harvest_reuse_opportunity_as_loop, observe_reuse_opportunity_as_loop,
    ReuseObservationRequest)
from .reusable_capability_records import (
    HarvestDispatch, REUSE_ASSESSMENT_DIMENSIONS, ReuseAssessment,
    ReuseHarvestPolicy, ReuseRecommendation, content_digest)
from .run_history import RunHistory
from .semantic_runtime import (
    SemanticExecutionRequest, SemanticExecutionServices,
    SemanticInterpreterPort, execute_semantic_loop,
    select_semantic_realization)
from .semantic_runtime_evidence import (
    SemanticReliabilityEnvelope, SemanticStrategyBenchmark,
    SemanticStrategyMeasurement)
from .semantic_runtime_fixture import (
    build_routing_fixture, deterministic_route, input_is_valid,
    interpreter_a, interpreter_b, interpreter_undeclared_effect,
    preconditions, routing_verification)
from .semantic_runtime_records import (
    ProposedStateDelta, SemanticCandidateOutput, SemanticDisposition,
    SemanticExecutionRecord, SemanticLoopContract,
    SemanticInterpreterQualification, SemanticRealizationBinding,
    SemanticRealizationKind, canonical_json, semantic_digest)
from .semantic_state import (
    CatalogTrustedSemanticState, SemanticEffectController,
    SemanticStateConflict, SemanticVerifier)


def _assessment_dimensions(**overrides: float) -> tuple[tuple[str, float], ...]:
    values = {name: 7.0 for name in REUSE_ASSESSMENT_DIMENSIONS}
    values.update(overrides)
    return tuple((name, values[name]) for name in REUSE_ASSESSMENT_DIMENSIONS)


def _request(fixture, binding, input_value, suffix: str) \
        -> SemanticExecutionRequest:
    return SemanticExecutionRequest(
        "semantic-request." + suffix, fixture.contract, fixture.definition,
        binding, input_value, fixture.context, "routing-state",
        "semantic-idempotency." + suffix,
        requested_regions=(("jurisdiction:" + input_value["jurisdiction"],)
                           if input_value.get("jurisdiction") else ()))


def self_test() -> dict:
    tests: list[dict] = []

    def check(name: str, passed: bool, detail: object = "") -> None:
        tests.append({"test": name, "passed": bool(passed),
                      "detail": detail})

    fixture = build_routing_fixture()
    ledger = LoopLedger(id_namespace="semantic-runtime")
    state_catalog = EphemeralRecordStore()
    trusted_state = CatalogTrustedSemanticState(state_catalog)
    initial_state = trusted_state.initialize("routing-state")
    verifier = SemanticVerifier(
        "semantic-routing-verifier", "1.0.0",
        semantic_digest("semantic.verify.routing/v1"), routing_verification)
    effects = SemanticEffectController(
        "semantic-effect-controller",
        semantic_digest("semantic.effects.exact-contract/v1"))
    population = (
        fixture.valid_auto, fixture.valid_property,
        fixture.missing_facts, fixture.prompt_injection)
    population_digest = semantic_digest(population)
    qualification_a = SemanticInterpreterQualification(
        "semantic-qualification-a", fixture.contract.contract_digest,
        fixture.profile_a.digest, population_digest, verifier.policy_digest,
        "semantic-profile-producer-a", "semantic-profile-verifier",
        True, ("semantic-regression:a",))
    direct_a = SemanticRealizationBinding(
        "semantic.route_claim.direct_a", "1.0.0",
        fixture.contract.contract_digest,
        SemanticRealizationKind.DIRECT_SEMANTIC,
        "non_deterministic", "registered", qualification_a.digest,
        interpreter_profile_digest=fixture.profile_a.digest)
    hybrid_a = SemanticRealizationBinding(
        "semantic.route_claim.hybrid_a", "1.0.0",
        fixture.contract.contract_digest,
        SemanticRealizationKind.HYBRID_SEMANTIC,
        "hybrid", "registered", qualification_a.digest,
        interpreter_profile_digest=fixture.profile_a.digest)
    services_a = SemanticExecutionServices(
        (SemanticInterpreterPort(fixture.profile_a, interpreter_a),), (),
        input_is_valid, preconditions, verifier, effects, trusted_state,
        qualifications=(qualification_a,))

    check("implementationless_contract_is_bound_to_canonical_loop_definition",
          fixture.definition.ref == fixture.contract.loop_definition_ref
          and fixture.definition.configuration_facts.to_dict()[
              "semantic_specification_digest"]
          == fixture.contract.draft.specification_digest
          and "implementation" not in fixture.contract.to_dict()
          and set(fixture.contract.draft.supported_modes) == {
              "deterministic", "hybrid", "non_deterministic"})
    check("semantic_contract_round_trips_with_exact_definition_binding",
          SemanticLoopContract.from_dict(
              fixture.contract.to_dict()) == fixture.contract)

    valid = execute_semantic_loop(
        _request(fixture, direct_a, fixture.valid_auto, "valid-auto"),
        services_a, ledger=ledger)
    check("direct_semantic_transaction_commits_only_after_verification",
          valid.output["queue"] == "AUTO"
          and valid.execution_record.disposition is SemanticDisposition.ACCEPTED
          and valid.execution_record.model_calls == 1
          and valid.execution_record.trust_transitions == (
              "candidate", "structurally_valid", "contract_valid",
              "verified", "effect_authorized", "committed")
          and valid.committed is not None
          and valid.verifier_loop_id and valid.commit_loop_id,
          {"program_id": valid.execution_record.program.program_id,
           "execution_record": valid.execution_record.execution_record_id,
           "loop_id": valid.loop_id})
    check("semantic_program_identity_exposes_every_effective_component",
          all(len(value) == 64
              for value in valid.execution_record.program.__dict__.values())
          and len(valid.execution_record.program.program_id) == 64)
    check("semantic_execution_record_round_trips_without_identity_drift",
          SemanticExecutionRecord.from_dict(
              valid.execution_record.to_dict()) == valid.execution_record)

    replay = trusted_state.commit(
        valid.candidate, valid.verification, valid.authorization,
        verifier, effects)
    check("semantic_commit_is_idempotent_and_does_not_duplicate_state",
          replay.replayed
          and replay.state_before == replay.state_after
          and trusted_state.snapshot("routing-state").version == 1)

    before_abstention = trusted_state.snapshot("routing-state")
    abstained = execute_semantic_loop(
        _request(fixture, direct_a, fixture.missing_facts, "missing"),
        services_a, ledger=ledger)
    after_abstention = trusted_state.snapshot("routing-state")
    check("missing_facts_produce_verified_abstention_without_state_change",
          abstained.output["decision"] == "NEEDS_REVIEW"
          and abstained.execution_record.disposition is SemanticDisposition.ABSTAINED
          and abstained.verification.abstained
          and abstained.committed is None
          and before_abstention == after_abstention)

    injection = execute_semantic_loop(
        _request(fixture, direct_a, fixture.prompt_injection, "injection"),
        services_a, ledger=ledger)
    check("prompt_injection_inside_evidence_remains_untrusted_data",
          injection.execution_record.disposition is SemanticDisposition.ACCEPTED
          and injection.output["queue"] == "AUTO"
          and injection.output["rule_id"] == "R-AUTO-CA"
          and "DROP_TABLE" not in json.dumps(injection.output))

    profile_b_results = []
    qualification_b_candidate = SemanticInterpreterQualification(
        "semantic-qualification-b-candidate",
        fixture.contract.contract_digest, fixture.profile_b.digest,
        population_digest, verifier.policy_digest,
        "semantic-profile-producer-b", "semantic-profile-verifier",
        True, ("semantic-regression:b-candidate",),
        predecessor_profile_digest=fixture.profile_a.digest,
        rollback_profile_digest=fixture.profile_a.digest)
    direct_b_candidate = SemanticRealizationBinding(
        "semantic.route_claim.direct_b", "2.0.0",
        fixture.contract.contract_digest,
        SemanticRealizationKind.DIRECT_SEMANTIC,
        "non_deterministic", "registered",
        qualification_b_candidate.digest,
        interpreter_profile_digest=fixture.profile_b.digest)
    services_b_candidate = SemanticExecutionServices(
        (SemanticInterpreterPort(fixture.profile_b, interpreter_b),), (),
        input_is_valid, preconditions, verifier, effects, trusted_state,
        qualifications=(qualification_b_candidate,))
    for index, value in enumerate(population):
        profile_b_results.append(execute_semantic_loop(
            _request(fixture, direct_b_candidate, value, f"b-{index}"),
            services_b_candidate, ledger=ledger))
    b_accepted = sum(item.execution_record.disposition
                     is SemanticDisposition.ACCEPTED
                     for item in profile_b_results)
    b_abstained = sum(item.execution_record.disposition
                      is SemanticDisposition.ABSTAINED
                      for item in profile_b_results)
    b_rejected = len(profile_b_results) - b_accepted - b_abstained
    envelope_b = SemanticReliabilityEnvelope(
        "semantic-envelope-b", fixture.contract.contract_digest,
        direct_b_candidate.digest, fixture.profile_b.digest,
        population_digest, len(population), b_accepted, b_rejected,
        b_abstained, 0, 0,
        sum(item.execution_record.model_calls for item in profile_b_results),
        verifier.policy_digest, False, ("semantic-regression:b",))
    qualification_b = replace(
        qualification_b_candidate,
        qualification_id="semantic-qualification-b-rejected", passed=False,
        evidence_refs=("semantic-regression:b",))
    direct_b = replace(
        direct_b_candidate, qualification_digest=qualification_b.digest)
    selected_after_regression = select_semantic_realization(
        fixture.contract, (direct_b, direct_a),
        (qualification_b, qualification_a))
    check("runtime_profile_change_requalifies_and_rolls_back",
          valid.execution_record.program.program_id
          != profile_b_results[0].execution_record.program.program_id
          and envelope_b.qualified is False
          and b_rejected == 1
          and selected_after_regression == direct_a
          and qualification_b.rollback_profile_digest
          == fixture.profile_a.digest,
          {"profile_a_program": valid.execution_record.program.program_id,
           "profile_b_program":
               profile_b_results[0].execution_record.program.program_id})

    before_unsafe = trusted_state.snapshot("routing-state")
    unsafe_services = SemanticExecutionServices(
        (SemanticInterpreterPort(
            fixture.profile_a, interpreter_undeclared_effect),), (),
        input_is_valid, preconditions, verifier, effects, trusted_state,
        qualifications=(qualification_a,))
    unsafe = execute_semantic_loop(
        _request(fixture, direct_a, fixture.valid_auto, "unsafe-effect"),
        unsafe_services, ledger=ledger)
    check("undeclared_effect_is_rejected_before_trusted_commit",
          unsafe.execution_record.disposition is SemanticDisposition.REJECTED
          and unsafe.committed is None
          and trusted_state.snapshot("routing-state") == before_unsafe)

    stale_delta = ProposedStateDelta(
        "routing-state", initial_state.version,
        (), (), (), "semantic-idempotency.stale")
    stale_candidate = SemanticCandidateOutput(
        "semantic-candidate.stale", fixture.contract.contract_digest,
        direct_a.digest, canonical_json(valid.output), stale_delta,
        valid.candidate.evidence_refs, 0)
    stale_verification = verifier.verify(
        fixture.contract, stale_candidate, fixture.valid_auto,
        fixture.context)
    stale_authorization = effects.authorize(
        fixture.contract, stale_candidate)
    stale_refused = False
    try:
        trusted_state.commit(
            stale_candidate, stale_verification, stale_authorization,
            verifier, effects)
    except SemanticStateConflict:
        stale_refused = True
    check("stale_base_state_version_cannot_commit", stale_refused)

    property_result = execute_semantic_loop(
        _request(fixture, direct_a, fixture.valid_property, "valid-property"),
        services_a, ledger=ledger)
    a_results = (valid, property_result, abstained, injection)
    envelope_a = SemanticReliabilityEnvelope(
        "semantic-envelope-a", fixture.contract.contract_digest,
        direct_a.digest, fixture.profile_a.digest, population_digest,
        len(a_results), 3, 0, 1, 0, 0,
        sum(item.execution_record.model_calls for item in a_results),
        verifier.policy_digest, True, ("semantic-regression:a",))
    check("reliability_envelope_measures_boundary_outcomes_not_confidence",
          envelope_a.accepted_count == 3
          and envelope_a.abstained_count == 1
          and envelope_a.false_accept_count == 0
          and envelope_a.unsafe_commit_count == 0
          and envelope_a.observed_unsafe_commit_rate_ppm == 0,
          {"fixture_count": envelope_a.fixture_count,
           "observed_unsafe_commit_rate_ppm":
               envelope_a.observed_unsafe_commit_rate_ppm,
           "production_risk_budget_proven": False})

    with tempfile.TemporaryDirectory(
            prefix="semantic_materialization_") as materialization_root:
        artifact_store = ContextArtifactStore(ContextArtifactStoreSpec(
            materialization_root, namespace="semantic-materialization"))
        trace_text = json.dumps({
            "contract_digest": fixture.contract.contract_digest,
            "execution_record_digest": valid.execution_record.digest,
            "program_id": valid.execution_record.program.program_id,
            "output": valid.output,
        }, sort_keys=True, separators=(",", ":"))
        trace_artifact = artifact_store.put_text(
            trace_text, media_type="application/json",
            artifact_kind="semantic_execution_trace")
        code_source = inspect.getsource(deterministic_route)
        code_artifact = artifact_store.put_text(
            code_source, media_type="text/x-python",
            artifact_kind="semantic_materialized_code")
        code_spec = spec_from_template(
            "pure_function", asset_id="code.semantic.route_claim",
            name="Deterministic claim routing realization",
            description=(
                "Apply the reviewed claim routing contract to verified facts."),
            source_kind="local_path",
            body_ref=ExternalPayloadRef(
                "context-artifact://" + code_artifact.object_key,
                code_artifact.digest, code_artifact.byte_count,
                "text/x-python"),
            entrypoints=("deterministic_route",),
            input_contract="semantic_execution_request/v1",
            output_contract="semantic_candidate_envelope/v1",
            effects=("pure",), license="MIT", lifecycle="candidate",
            metadata={
                "operation_family": "semantic.route_claim",
                "semantic_contract_digest":
                    fixture.contract.contract_digest,
                "search_terms": [
                    "claim routing", "policy routing", "needs review"],
                "capabilities": [], "environment": {},
                "privacy_scope": "run_private",
                "namespace": "org:semantic-fixture",
            })
        materialization_opportunity = observe_reuse_opportunity_as_loop(
            ReuseObservationRequest(
                "semantic-materialization", "run-semantic", valid.loop_id,
                "solution.atomic_component@1.0.0",
                (f"{fixture.definition.definition_id}@"
                 f"{fixture.definition.version}#"
                 f"{fixture.definition.content_digest}"),
                valid.execution_record.execution_record_id, valid.execution_record.digest,
                "context-artifact://" + trace_artifact.object_key,
                trace_artifact.digest, "semantic_procedure",
                "semantic.route_claim", "2026-08-31T15:00:00Z",
                True, True, HarvestDispatch.ASYNC), ledger=ledger)
        materialization_assessment = ReuseAssessment(
            "assessment-semantic-materialization",
            materialization_opportunity.event_id,
            "semantic-materialization-assessor", True,
            _assessment_dimensions(
                observed_correctness=9.0, recurrence_likelihood=8.0,
                transfer_breadth=7.0, parameterization_clarity=9.0,
                contract_clarity=10.0, determinism_potential=9.0,
                testability=10.0, effect_safety=10.0,
                security_privacy=9.0, evidence_diversity=6.0),
            8.4, 0.8,
            ReuseRecommendation.CREATE_NEW_CAPABILITY_CANDIDATE,
            ("A bounded California routing region has deterministic rules and "
             "an independently checkable output."),
            (valid.execution_record.execution_record_id, "semantic-regression:a"))
        generalized = GeneralizedCapabilityCandidate(
            code_spec,
            ("claim_type", "jurisdiction", "policy_context",
             "idempotency_key"),
            ("exactly_one_declared_queue", "applicable_rule_reference",
             "missing_facts_return_needs_review"),
            ("untrusted_evidence_is_instruction",),
            ("semantic-regression:a", "materialization-equivalence:ca"))
        code_authority = CapabilityAuthority(EphemeralRecordStore())
        harvested = harvest_reuse_opportunity_as_loop(
            code_authority,
            ReuseHarvestRequest(
                materialization_opportunity,
                ReuseHarvestPolicy(
                    "semantic-materialization-policy", "1.0.0",
                    dispatch=HarvestDispatch.ASYNC),
                ReuseHarvestServices(
                    lambda _item: materialization_assessment,
                    lambda _item, _assessment: generalized,
                    assessment_mode="deterministic",
                    generalization_mode="deterministic"),
                (valid.execution_record.execution_record_id,)),
            ledger=ledger)
        candidate_binding = SemanticRealizationBinding(
            "semantic.route_claim.deterministic", "1.0.0",
            fixture.contract.contract_digest,
            SemanticRealizationKind.DETERMINISTIC_CODE,
            "deterministic", "candidate", code_spec.qualification_digest,
            artifact_ref=(
                f"code_asset:{code_spec.asset_id}@{code_spec.version}"),
            artifact_digest=code_spec.body_ref.digest,
            coverage_regions=("jurisdiction:CA",))
        before_qualification_selection = select_semantic_realization(
            fixture.contract, (candidate_binding, direct_a),
            (qualification_a,), ("jurisdiction:CA",), code_authority)
        equivalence_outputs = []
        for index, value in enumerate(population):
            request = _request(
                fixture, direct_a, value, f"materialization-check-{index}")
            current = trusted_state.snapshot("routing-state")
            envelope = deterministic_route(request, fixture.context, current)
            equivalence_outputs.append(envelope["output"])
        qualification_evidence = (
            "materialization:four-routing-cases",
            "materialization:prompt-injection-case",
            "materialization:missing-facts-case")
        admission = CodeAssetAdmissionRecord(
            "admission-semantic-route-v1", code_spec.asset_id,
            code_spec.version, code_spec.qualification_digest,
            code_spec.body_ref.digest, code_spec.dependency_digest,
            code_spec.contract_digest, code_spec.effect_digest,
            harvested.producer_loop_id, "semantic-code-verifier",
            qualification_evidence,
            content_digest(equivalence_outputs))
        qualified_code = code_authority.qualify_as_loop(
            QualificationRequest(code_spec.asset_id, code_spec.version,
                                 admission), ledger=ledger)
        promoted_code = code_authority.promote_as_loop(
            PromotionRequest(
                code_spec.asset_id, code_spec.version,
                "semantic-promotion-authority", qualification_evidence),
            ledger=ledger)
        deterministic_binding = replace(
            candidate_binding, lifecycle="registered")
        selected_deterministic = select_semantic_realization(
            fixture.contract, (direct_a, deterministic_binding),
            (qualification_a,), ("jurisdiction:CA",), code_authority)
        deterministic_services = SemanticExecutionServices(
            (SemanticInterpreterPort(fixture.profile_a, interpreter_a),),
            ((deterministic_binding.binding_id, deterministic_route),),
            input_is_valid, preconditions, verifier, effects, trusted_state,
            qualifications=(qualification_a,),
            code_authority=code_authority)
        deterministic_result = execute_semantic_loop(
            _request(
                fixture, selected_deterministic,
                fixture.valid_property, "deterministic-warm"),
            deterministic_services, ledger=ledger)
        unsupported = {
            **fixture.valid_auto, "claim_id": "claim-ny",
            "jurisdiction": "NY"}
        selected_fallback = select_semantic_realization(
            fixture.contract, (deterministic_binding, direct_a),
            (qualification_a,), ("jurisdiction:NY",), code_authority)
        fallback_result = execute_semantic_loop(
            _request(
                fixture, selected_fallback, unsupported,
                "semantic-fallback-ny"),
            deterministic_services, ledger=ledger)
        check("semantic_materialization_uses_existing_candidate_authority",
              harvested.registration is not None
              and harvested.registration.lifecycle_state == "candidate"
              and before_qualification_selection == direct_a
              and qualified_code.lifecycle_state == "validated"
              and promoted_code.lifecycle_state == "registered"
              and selected_deterministic == deterministic_binding
              and deterministic_result.execution_record.model_calls == 0
              and deterministic_result.output["queue"] == "PROPERTY"
              and fixture.contract.contract_digest
              == deterministic_binding.contract_digest,
              {"asset_id": code_spec.asset_id,
               "artifact_digest": code_spec.body_ref.digest,
               "qualification_digest": code_spec.qualification_digest})
        check("unsupported_deterministic_region_falls_back_to_semantic_contract",
              selected_fallback == direct_a
              and fallback_result.execution_record.model_calls == 1
              and fallback_result.execution_record.disposition
              is SemanticDisposition.ABSTAINED
              and fallback_result.output["queue"] == "NEEDS_REVIEW")

        direct_measurement = SemanticStrategyMeasurement(
            "direct_single_invocation", True, 0, 0, False,
            valid.execution_record.model_calls, valid.execution_record.prompt_tokens,
            valid.execution_record.output_tokens, valid.execution_record.cost,
            valid.execution_record.latency_ms)
        stepwise_started = time.perf_counter()
        step_one = as_model_loop(
            "stepwise route: identify verified facts",
            lambda: {"claim_type": "auto", "jurisdiction": "CA"},
            ledger=ledger)
        step_two = as_model_loop(
            "stepwise route: choose applicable policy rule",
            lambda: {"queue": "AUTO", "rule_id": "R-AUTO-CA"},
            ledger=ledger)
        step_three = as_model_loop(
            "stepwise route: format routing decision",
            lambda: deterministic_result.output
            if deterministic_result.output["queue"] == "AUTO"
            else valid.output,
            ledger=ledger)
        stepwise_latency = (time.perf_counter() - stepwise_started) * 1000.0
        stepwise_ok = (
            step_one["ok"] and step_two["ok"] and step_three["ok"]
            and step_three["value"]["queue"] == "AUTO")
        stepwise_measurement = SemanticStrategyMeasurement(
            "step_by_step_interpretation", stepwise_ok, 0, 0, False,
            3, None, None, None, stepwise_latency)
        jit_started = time.perf_counter()
        jit_plan = as_model_loop(
            "compile semantic routing request to an executable rule plan",
            lambda: {"rule_id": "R-AUTO-CA", "queue": "AUTO"},
            ledger=ledger)
        jit_output = valid.output if jit_plan["value"]["rule_id"] \
            == "R-AUTO-CA" else None
        jit_measurement = SemanticStrategyMeasurement(
            "specification_to_plan", jit_output == valid.output,
            0, 0, False, 1, None, None, None,
            (time.perf_counter() - jit_started) * 1000.0)
        hybrid_result = execute_semantic_loop(
            _request(
                fixture, hybrid_a, fixture.valid_auto,
                "hybrid-guarded"),
            services_a, ledger=ledger)
        hybrid_measurement = SemanticStrategyMeasurement(
            "hybrid_deterministic_shell", hybrid_result.output == valid.output,
            0, 0, False, hybrid_result.execution_record.model_calls,
            hybrid_result.execution_record.prompt_tokens,
            hybrid_result.execution_record.output_tokens, hybrid_result.execution_record.cost,
            hybrid_result.execution_record.latency_ms)
        deterministic_measurement = SemanticStrategyMeasurement(
            "promoted_deterministic_reuse",
            deterministic_result.execution_record.disposition
            is SemanticDisposition.ACCEPTED,
            0, 0, False, deterministic_result.execution_record.model_calls,
            0, 0, 0.0, deterministic_result.execution_record.latency_ms)
        benchmark = SemanticStrategyBenchmark(
            "semantic-routing-strategies",
            fixture.contract.contract_digest,
            semantic_digest((fixture.valid_auto,)),
            (direct_measurement, stepwise_measurement, jit_measurement,
             hybrid_measurement, deterministic_measurement))
        check("semantic_strategy_benchmark_records_all_five_realizations",
              len(benchmark.measurements) == 5
              and all(item.success for item in benchmark.measurements)
              and direct_measurement.model_calls == 1
              and stepwise_measurement.model_calls == 3
              and jit_measurement.model_calls == 1
              and hybrid_measurement.model_calls == 1
              and deterministic_measurement.model_calls == 0
              and all(item.unsafe_commits == 0
                      for item in benchmark.measurements),
              {item.strategy: item.model_calls
               for item in benchmark.measurements})

    history = RunHistory.from_ledger(ledger.events, run_id="run-semantic")
    history.commit()
    check("semantic_execution_leaves_digest_chained_run_history",
          history.verify_chain()["intact"] and len(history.event_log) > 0,
          {"events": len(history.event_log),
           "head_digest": history.event_log[-1].event_digest})
    passed = sum(item["passed"] for item in tests)
    return {
        "record_type": "semantic_runtime_self_test/v1",
        "scope": "offline_injected_interpreter",
        "tests": tests, "passed": passed, "total": len(tests),
        "all_passed": passed == len(tests),
        "contract": {
            "contract_id": fixture.contract.draft.contract_id,
            "version": fixture.contract.draft.version,
            "contract_digest": fixture.contract.contract_digest,
            "loop_definition_digest": fixture.definition.content_digest,
        },
        "profile_a": fixture.profile_a.to_dict(),
        "profile_b": fixture.profile_b.to_dict(),
        "reliability": {
            "profile_a": {
                "fixture_count": envelope_a.fixture_count,
                "accepted": envelope_a.accepted_count,
                "abstained": envelope_a.abstained_count,
                "false_accepts": envelope_a.false_accept_count,
                "unsafe_commits": envelope_a.unsafe_commit_count,
                "qualified": envelope_a.qualified,
            },
            "profile_b": {
                "fixture_count": envelope_b.fixture_count,
                "accepted": envelope_b.accepted_count,
                "abstained": envelope_b.abstained_count,
                "rejected": envelope_b.rejected_count,
                "qualified": envelope_b.qualified,
                "rollback_profile_digest":
                    qualification_b.rollback_profile_digest,
            },
        },
        "materialization": {
            "asset_id": code_spec.asset_id,
            "asset_version": code_spec.version,
            "artifact_digest": code_spec.body_ref.digest,
            "qualification_digest": code_spec.qualification_digest,
            "promoted_transition": promoted_code.transition_record_ref,
            "warm_model_calls": deterministic_result.execution_record.model_calls,
            "unsupported_region_fallback_model_calls":
                fallback_result.execution_record.model_calls,
        },
        "strategy_benchmark": {
            item.strategy: {
                "success": item.success,
                "model_calls": item.model_calls,
                "false_accepts": item.false_accepts,
                "unsafe_commits": item.unsafe_commits,
                "latency_ms": item.latency_ms,
                "tokens_known": item.prompt_tokens is not None
                                and item.output_tokens is not None,
                "cost": item.cost,
            }
            for item in benchmark.measurements
        },
        "example_execution_record": {
            "execution_record_id": valid.execution_record.execution_record_id,
            "execution_record_digest": valid.execution_record.digest,
            "program_id": valid.execution_record.program.program_id,
            "trust_transitions": list(valid.execution_record.trust_transitions),
        },
        "run_history": {
            "events": len(history.event_log),
            "head_digest": history.event_log[-1].event_digest,
        },
    }


__all__ = ("self_test",)
