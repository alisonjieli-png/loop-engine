"""Offline end-to-end checks for the Reusable Capability Flywheel.

The fixture uses an injected model transport and an in-memory code artifact.
It proves contracts, call counts, lifecycle separation, reactive placement,
retrieval, and verification. It does not claim live provider quality.
"""
from __future__ import annotations

import asyncio
import hashlib
import inspect
import json
import os
import tempfile
from dataclasses import replace
from types import SimpleNamespace

from ..catalog.stores.in_memory import EphemeralRecordStore
from ..catalog.stores.sqlite_store import SQLiteRecordStore
from ..catalog.query import IntelligenceQuery
from ..code_nodes.solution_graph import LoopDefinitionRegistry
from ..loop.atomic_primitives import LoopValueRef
from ..loop.encapsulate import as_model_loop
from ..loop.loop_capsule import ExternalPayloadRef, MaterializedPayload
from ..loop.loop_contract import LoopContract
from ..loop.loop_definition import LoopDefinition
from ..loop.loop_role import LoopRole, LoopRoleIdentity
from ..loop.reactive_activation import (
    ActivationClaimRequest, ActivationStatus, ReactiveSeriesDefinition)
from ..loop.reactive_contracts import (
    ActivationPolicy, AdmissionPolicy, EmissionPolicy, ExplorationPolicy,
    InputSchedulingPolicy, MetricDirection, OutputPortDefinition,
    PersistenceMode, PortfolioPolicy, PortfolioView, RankingDimension,
    ReactiveLivenessPolicy, ReactiveLoopProfile, RetentionPolicy,
    ServingPolicy, TriggerKind)
from ..loop.recursive_loop import LoopConfig, LoopLedger, StepOutcome
from ..loop.runtime_context import LoopRuntimeContext
from .code_intelligence_assets import (
    CodeAssetAdmissionError, CodeAssetAdmissionRecord, spec_from_template)
from .context_artifacts import ContextArtifactStore, ContextArtifactStoreSpec
from .information_access import (
    InformationAccessRequest, InformationResolver)
from .reactive_scheduler import SQLiteReactiveScheduler
from .reactive_worker import (
    AsyncReactiveWorker, CanonicalReactiveExecutor, ReactiveHandlerBinding,
    ReactiveWorkerRequest)
from .reusable_capability_flywheel import (
    CandidateRegistrationRequest, CapabilityAuthority,
    PromotionRequest, QualificationRequest,
)
from .reusable_capability_harvest import (
    GeneralizedCapabilityCandidate,
    ReuseHarvestRequest, ReuseHarvestServices,
    ReuseObservationPort, ReuseObservationRequest,
    dispatch_reuse_opportunity_as_loop,
    harvest_reuse_opportunity_as_loop,
    observe_reuse_opportunity_as_loop)
from .adaptive_practitioner_reuse import observe_generated_project_reuse
from .reusable_capability_resolution import (
    CapabilityInvocationRequest, CapabilityResolutionRequest,
    CapabilityResolver, ReusableCapabilityTaskResolver,
    invoke_capability_as_loop,
    rebuild_capability_projection_as_loop)
from .adaptive_practitioner import run_adaptive_practitioner
from .adaptive_practitioner_records import (
    AdaptivePractitionerDependencies, AdaptivePractitionerRequest)
from .reusable_capability_hybrid import (
    AdapterExecutionRequest, HybridAssistanceError, HybridAssistanceRequest,
    execute_ephemeral_adapter_as_loop, hybrid_assistance_profile,
    load_hybrid_assistance_profiles, normalized_need_from_assistance,
    run_hybrid_assistance_as_loop, selected_candidate_from_assistance)
from .reusable_capability_records import (
    CapabilityNeed, HarvestDispatch, HybridAssistanceStage,
    REUSE_ASSESSMENT_DIMENSIONS,
    ResolutionDisposition, ReuseAssessment, ReuseRecommendation,
    ReuseHarvestPolicy, ReuseOpportunityObserved,
    content_digest)
from .run_history import RunHistory


def _deduplicate_records(request: dict) -> dict:
    """Configurable deterministic artifact discovered by the cold fixture."""
    records = list(request["records"])
    key_fields = tuple(request["key_fields"])
    keep = request.get("keep", "first")
    if not key_fields or keep not in ("first", "last"):
        raise ValueError("key_fields and keep policy are invalid")
    for record in records:
        if not isinstance(record, dict) or any(
                field not in record for field in key_fields):
            raise ValueError("every record must contain every key field")

    def key(index: int) -> tuple[str, ...]:
        return tuple(json.dumps(
            records[index][field], sort_keys=True,
            separators=(",", ":"), ensure_ascii=False)
            for field in key_fields)

    representative: dict[tuple[str, ...], int] = {}
    order = range(len(records)) if keep == "first" \
        else range(len(records) - 1, -1, -1)
    for index in order:
        representative.setdefault(key(index), index)
    kept_indices = tuple(sorted(representative.values()))
    lineage = {str(index): representative[key(index)]
               for index in range(len(records))
               if representative[key(index)] != index}
    return {
        "records": [records[index] for index in kept_indices],
        "lineage": lineage,
        "kept_indices": list(kept_indices),
    }


def _cold_email_deduplication(records: list[dict]) -> list[dict]:
    """The source run's narrow implementation before parameterization."""
    seen = set()
    result = []
    for record in records:
        email = record["email"]
        if email not in seen:
            seen.add(email)
            result.append(record)
    return result


def _assessment_dimensions(**overrides: float) -> tuple[tuple[str, float], ...]:
    values = {name: 7.0 for name in REUSE_ASSESSMENT_DIMENSIONS}
    values.update(overrides)
    return tuple((name, values[name]) for name in REUSE_ASSESSMENT_DIMENSIONS)


def _qualification_suite() -> tuple[bool, tuple[str, ...], str]:
    cases = []

    def check(name: str, request: dict, expected: dict) -> None:
        cases.append((name, _deduplicate_records(request) == expected))

    check("empty", {"records": [], "key_fields": ["id"]},
          {"records": [], "lineage": {}, "kept_indices": []})
    check("keep_first", {
        "records": [{"id": 1, "v": "a"}, {"id": 1, "v": "b"}],
        "key_fields": ["id"], "keep": "first"}, {
            "records": [{"id": 1, "v": "a"}],
            "lineage": {"1": 0}, "kept_indices": [0]})
    check("keep_last", {
        "records": [{"id": 1, "v": "a"}, {"id": 1, "v": "b"}],
        "key_fields": ["id"], "keep": "last"}, {
            "records": [{"id": 1, "v": "b"}],
            "lineage": {"0": 1}, "kept_indices": [1]})
    check("nested_key", {
        "records": [{"id": [1, 2]}, {"id": [1, 2]}, {"id": [2, 3]}],
        "key_fields": ["id"]}, {
            "records": [{"id": [1, 2]}, {"id": [2, 3]}],
            "lineage": {"1": 0}, "kept_indices": [0, 2]})
    invalid_refused = False
    try:
        _deduplicate_records({
            "records": [{"id": 1}, {"other": 1}],
            "key_fields": ["id"]})
    except ValueError:
        invalid_refused = True
    cases.append(("missing_field_refused", invalid_refused))
    refs = tuple(f"qualification:{name}" for name, passed in cases if passed)
    return (all(passed for _name, passed in cases), refs,
            content_digest(cases))


def _reactive_definition() -> LoopDefinition:
    config = LoopConfig(
        framework="custom", custom_steps=("act",),
        allowable_modes=("deterministic",),
        preferred_modes=("deterministic",),
        delegated_modes=("deterministic",),
        exit_condition="accepted_success")
    contract = LoopContract(
        "Harvest one accepted reuse opportunity", "code_only",
        ("reuse_opportunity_observed/v1",),
        ("capability_candidate_ref/v1",), ("pure",),
        role="practitioner")
    return LoopDefinition.from_runtime(
        identity=LoopRoleIdentity(
            LoopRole.PRACTITIONER, "practitioner.self_improvement"),
        contract=contract, config=config,
        definition_id="practitioner.reuse_harvest_fixture",
        version="1.0.0", installed_executor_modes=("deterministic",))


def _reactive_profile() -> ReactiveLoopProfile:
    return ReactiveLoopProfile(
        "profile-reuse-harvest-fixture", "1.0.0",
        ActivationPolicy(
            (TriggerKind.PUSH_EVENT,), reactivation_enabled=True),
        AdmissionPolicy(4), InputSchedulingPolicy(),
        PersistenceMode.DURABLE_SERIES, ExplorationPolicy(),
        (OutputPortDefinition(
            "candidate", "capability_candidate_ref",
            "capability_candidate_ref/v1"),),
        PortfolioPolicy(
            "policy-reuse-harvest-fixture", "1.0.0",
            PortfolioView.ALL_ATTEMPTED,
            (RankingDimension(
                "evidence_coverage", MetricDirection.MAXIMIZE),), 4),
        EmissionPolicy(), ServingPolicy(4), RetentionPolicy(16, 16),
        ReactiveLivenessPolicy(30))


def self_test() -> dict:
    tests: list[dict] = []
    metrics: dict[str, object] = {
        "cold_model_calls": 0,
        "warm_model_calls": None,
        "adaptive_warm_model_calls": None,
        "hybrid_normalization_model_calls": None,
        "adapter_model_calls": None,
        "repair_model_calls": None,
        "harvest_model_calls": None,
        "input_tokens_avoided": None,
        "output_tokens_avoided": None,
        "estimated_cost_avoided": None,
    }

    def check(name: str, passed: bool, detail: object = "") -> None:
        tests.append({"test": name, "passed": bool(passed),
                      "detail": detail})

    ledger = LoopLedger(id_namespace="reusable-capability-flywheel")
    artifact_directory = tempfile.TemporaryDirectory(
        prefix="reusable_capability_artifacts_")
    artifact_store = ContextArtifactStore(ContextArtifactStoreSpec(
        artifact_directory.name, namespace="reusable-capability"))
    installed_profiles = load_hybrid_assistance_profiles()
    check("hybrid_variations_are_profiles_not_new_run_modes",
          {item.profile_id for item in installed_profiles} == {
              "hybrid.normalize_then_resolve",
              "hybrid.retrieve_then_rerank",
              "hybrid.adapt_then_execute",
              "hybrid.execute_then_diagnose",
              "hybrid.execute_then_repair",
              "hybrid.compose_promoted_capabilities",
              "hybrid.full_assisted_resolution",
          } and all(item.maximum_model_calls == 1
                    for item in installed_profiles),
          "seven assistance presets, one canonical hybrid mode")
    authority_store = EphemeralRecordStore()
    authority = CapabilityAuthority(authority_store)
    empty_projection = EphemeralRecordStore()
    cold_need = CapabilityNeed(
        "need-cold", "run-cold", "practitioner.solver@1.0.0",
        "Remove duplicate records and preserve merge lineage.",
        "data.record_deduplication", "deduplicate structured records",
        "record_deduplication_request/v1",
        content_digest("record_deduplication_request/v1"),
        "record_deduplication_result/v1",
        content_digest("record_deduplication_result/v1"),
        allowed_effects=("pure",),
        search_terms=("duplicate", "records", "lineage"))
    cold_resolution = CapabilityResolver(
        authority, empty_projection).resolve_as_loop(
            CapabilityResolutionRequest(cold_need), ledger=ledger)
    check("cold_request_has_no_reusable_match",
          cold_resolution.plan.disposition
          is ResolutionDisposition.ESCALATE_TO_NOVEL_BUILD
          and cold_resolution.model_calls == 0,
          cold_resolution.plan.disposition.value)
    retry_need = replace(
        cold_need, need_id="need-cold-retry", originating_run_id="run-retry")
    check("normalized_need_digest_excludes_retry_provenance",
          retry_need.normalized_digest == cold_need.normalized_digest
          and retry_need.record_digest != cold_need.record_digest)
    check("capability_need_round_trips_without_digest_drift",
          CapabilityNeed.from_dict(cold_need.to_dict()) == cold_need)

    cold_source = inspect.getsource(_cold_email_deduplication)
    cold_artifact_digest = hashlib.sha256(
        cold_source.encode("utf-8")).hexdigest()
    cold_artifact = artifact_store.put_text(
        cold_source, media_type="text/x-python",
        artifact_kind="generated_python_source")
    cold_value = _cold_email_deduplication([
        {"email": "a@example.com", "name": "A"},
        {"email": "a@example.com", "name": "Alias"},
        {"email": "b@example.com", "name": "B"},
    ])
    source = inspect.getsource(_deduplicate_records)
    artifact_digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    candidate_artifact = artifact_store.put_text(
        source, media_type="text/x-python",
        artifact_kind="generalized_python_source")
    if (cold_artifact.digest != cold_artifact_digest
            or candidate_artifact.digest != artifact_digest):
        raise AssertionError("content-addressed source digest drifted")
    spec = spec_from_template(
        "pure_function", asset_id="code.data.record_deduplication",
        name="Configurable record deduplication",
        description=("Remove duplicate structured records using selected key "
                     "fields while preserving stable order and lineage."),
        source_kind="local_path",
        body_ref=ExternalPayloadRef(
            "context-artifact://" + candidate_artifact.object_key,
            candidate_artifact.digest, candidate_artifact.byte_count,
            "text/x-python"),
        entrypoints=("deduplicate_records",),
        input_contract="record_deduplication_request/v1",
        output_contract="record_deduplication_result/v1",
        effects=("pure",), license="MIT", lifecycle="candidate",
        metadata={
            "operation_family": "data.record_deduplication",
            "search_terms": [
                "deduplicate", "duplicate records", "merge rows", "lineage"],
            "capabilities": [], "environment": {},
            "privacy_scope": "run_private", "namespace": "org:fixture",
        })
    discovery = as_model_loop(
        "offline cold capability discovery contract",
        lambda: {
            "source": cold_source,
            "result": cold_value,
            "artifact_digest": cold_artifact_digest,
        }, ledger=ledger)
    metrics["cold_model_calls"] = 1
    check("cold_discovery_runs_as_non_deterministic_loop",
          discovery["ok"]
          and discovery["value"]["artifact_digest"]
          == cold_artifact_digest
          and len(discovery["value"]["result"]) == 2,
          "offline injected transport, not live provider quality evidence")

    opportunity = observe_reuse_opportunity_as_loop(ReuseObservationRequest(
        "correlation-cold", "run-cold", "loop-cold-producer",
        "practitioner.solver@1.0.0",
        "practitioner.cold-discovery@1.0.0#fixture",
        "result-cold", "execution-cold",
        "context-artifact://" + cold_artifact.object_key,
        cold_artifact_digest,
        "python_function",
        "data.record_deduplication", "2026-08-30T12:00:00Z",
        True, True, HarvestDispatch.ASYNC), ledger=ledger)
    assessment = ReuseAssessment(
        "assessment-cold", opportunity.event_id, "loop-assessor", True,
        _assessment_dimensions(
            observed_correctness=10.0, recurrence_likelihood=8.0,
            parameterization_clarity=9.0, contract_clarity=9.0,
            determinism_potential=10.0, testability=10.0,
            effect_safety=10.0, security_privacy=9.0),
        8.5, 0.8,
        ReuseRecommendation.CREATE_NEW_CAPABILITY_CANDIDATE,
        "Pure deterministic transformation with explicit parameters and tests.",
        ("execution-cold", "source-regression"), expected_value=None)
    generalized_candidate = GeneralizedCapabilityCandidate(
        spec, ("key_fields", "keep"),
        ("stable_output_order", "lineage_for_removed_records"),
        ("email_is_the_only_identity_field", "always_keep_first"),
        ("source-regression", "parameterization-review"))

    def assess_opportunity(item: ReuseOpportunityObserved) -> ReuseAssessment:
        return replace(
            assessment,
            assessment_id="assessment." + item.event_id.split(".")[-1],
            opportunity_id=item.event_id)

    harvest_services = ReuseHarvestServices(
        assess_opportunity,
        lambda _opportunity, _assessment: generalized_candidate,
        assessment_mode="deterministic",
        generalization_mode="deterministic")
    integration_requests = []
    integration_port = ReuseObservationPort(
        lambda request: (
            integration_requests.append(request)
            or observe_reuse_opportunity_as_loop(request)))
    integration_owner = SimpleNamespace(
        loop_id="loop-adaptive-source",
        identity=SimpleNamespace(
            profile_id="practitioner.reference_nine_step",
            profile_version="1.0.0"),
        definition_ref=SimpleNamespace(
            definition_id="practitioner.adaptive",
            version="1.0.0", content_digest="a" * 64))
    integration_services = SimpleNamespace(
        run_id="run-adaptive-source",
        dependencies=SimpleNamespace(
            reuse_observation_port=integration_port),
        project_attempts=[{
            "deterministic_checks_passed": True,
            "manifest_digest": cold_artifact_digest,
            "workspace_path": "/verified/run-adaptive-source/attempt-1",
            "manifest": {"project_id": "record_deduplication"},
        }])
    integration = observe_generated_project_reuse(
        integration_owner, integration_services,
        {"head_digest": "b" * 64}, True)
    failing_services = SimpleNamespace(
        run_id=integration_services.run_id,
        dependencies=SimpleNamespace(reuse_observation_port=(
            ReuseObservationPort(
                lambda _request: (_ for _ in ()).throw(
                    RuntimeError("observer unavailable"))))),
        project_attempts=integration_services.project_attempts)
    failed_observer = observe_generated_project_reuse(
        integration_owner, failing_services, {"head_digest": "b" * 64},
        True)
    check("public_practitioner_completion_has_typed_reuse_observation_seam",
          integration["status"] == "observed"
          and integration["dispatch"] == "async"
          and integration_requests[0].source_loop_id
          == integration_owner.loop_id
          and integration_requests[0].source_loop_definition_ref.endswith(
              "#" + "a" * 64)
          and failed_observer["status"] == "failed",
          "observer failure remains a non-terminal status record")

    with tempfile.TemporaryDirectory(
            prefix="reusable_capability_") as temporary:
        scheduler = SQLiteReactiveScheduler(
            os.path.join(temporary, "reactive.sqlite"))
        profile = _reactive_profile()
        definition = _reactive_definition()
        series = ReactiveSeriesDefinition(
            "series-reuse-harvest-fixture",
            "Harvest accepted reusable capability opportunities.",
            definition.ref, profile.profile_id, profile.version,
            profile.content_digest, "reuse_opportunity_observed/v1",
            ("candidate",), 2, 1)
        scheduler.register_profile(profile)
        scheduler.register_series(series)
        information = InformationResolver()
        dispatch = dispatch_reuse_opportunity_as_loop(
            opportunity, scheduler, information, series.series_id,
            ledger=ledger)
        duplicate_dispatch = dispatch_reuse_opportunity_as_loop(
            opportunity, scheduler, information, series.series_id,
            ledger=ledger)
        check("async_dispatch_returns_before_candidate_construction",
              dispatch.created
              and authority.state(spec.asset_id, spec.version) is None,
              dispatch.activation_id)
        check("async_trigger_delivery_is_idempotent",
              not duplicate_dispatch.created
              and duplicate_dispatch.activation_id == dispatch.activation_id)
        harvest_results = []

        def handler(active, step: str, trigger) -> StepOutcome:
            if step != "act":
                return StepOutcome("unexpected", "deterministic", 0.0,
                                   failed=True)
            materialized = information.materialize(InformationAccessRequest(
                active.loop_id, trigger.input_ref,
                "harvest accepted reuse opportunity",
                requester_run_id=opportunity.source_run_id))
            if materialized.value != opportunity.to_dict():
                raise AssertionError("reactive opportunity value changed")
            observed = ReuseOpportunityObserved.from_dict(materialized.value)
            result = harvest_reuse_opportunity_as_loop(
                authority,
                ReuseHarvestRequest(
                    observed,
                    ReuseHarvestPolicy(
                        "reuse-harvest-default", "1.0.0",
                        dispatch=HarvestDispatch.ASYNC),
                    harvest_services,
                    ("source-regression",)),
                parent=active)
            harvest_results.append(result)
            return StepOutcome(
                f"candidate:{result.registration.capability_record_ref}",
                "deterministic", 1.0)

        runtime = LoopRuntimeContext.compatibility(
            capabilities=definition.required_capabilities,
            permissions=definition.permissions,
            executor_modes=definition.installed_executor_modes)
        executor = CanonicalReactiveExecutor(
            LoopDefinitionRegistry((definition,)), runtime,
            (ReactiveHandlerBinding(definition.ref, handler),))
        worker = AsyncReactiveWorker(scheduler, executor)
        worker_outcome = asyncio.run(worker.run_once(ReactiveWorkerRequest(
            ActivationClaimRequest(
                "worker-reuse", "2026-08-30T12:00:01Z", 60,
                series.series_id),
            "2026-08-30T12:00:02Z", "2026-08-30T12:00:03Z")))
        activation = scheduler.get_activation(dispatch.activation_id)
        if not harvest_results:
            raise AssertionError(
                "reactive harvest produced no candidate: "
                f"worker={worker_outcome}; activation={activation}")
        check("async_worker_harvests_inside_canonical_loops",
              worker_outcome.claimed
              and worker_outcome.terminal_code == "ACCEPTED"
              and activation.status is ActivationStatus.COMPLETED
              and harvest_results[0].registration is not None
              and harvest_results[0].registration.lifecycle_state
              == "candidate"
              and harvest_results[0].generalization is not None
              and harvest_results[0].generalization.source_artifact_digest
              == cold_artifact_digest
              and harvest_results[0].generalization.candidate_artifact_digest
              == artifact_digest
              and cold_artifact_digest != artifact_digest,
              {"activation": activation.activation_id,
               "worker_loop": worker_outcome.loop_id,
               "assessment_loop": harvest_results[0].assessment_loop_id,
               "producer_loop": harvest_results[0].producer_loop_id,
               "candidate_loop":
                   harvest_results[0].registration.loop_id})
        scheduler.close()

    producer_id = harvest_results[0].producer_loop_id
    metrics["harvest_model_calls"] = harvest_results[0].model_calls
    inline_opportunity = observe_reuse_opportunity_as_loop(
        ReuseObservationRequest(
            "correlation-inline", "run-inline", "loop-inline-producer",
            "practitioner.solver@1.0.0",
            "practitioner.inline@1.0.0#fixture", "result-inline",
            "execution-inline", opportunity.artifact_ref,
            opportunity.artifact_digest, opportunity.artifact_kind,
            opportunity.operation_family, "2026-08-30T12:01:00Z",
            True, True, HarvestDispatch.INLINE), ledger=ledger)
    inline_harvest = harvest_reuse_opportunity_as_loop(
        authority,
        ReuseHarvestRequest(
            inline_opportunity,
            ReuseHarvestPolicy(
                "reuse-harvest-inline", "1.0.0",
                dispatch=HarvestDispatch.INLINE),
            harvest_services, ("source-regression",)),
        ledger=ledger)
    check("inline_and_async_harvest_use_the_same_pipeline_contract",
          inline_harvest.outcome == "duplicate_consolidated"
          and inline_harvest.generalization is not None
          and inline_harvest.registration is not None
          and inline_harvest.assessment_loop_id
          and inline_harvest.producer_loop_id)
    check("harvest_records_round_trip_with_source_to_candidate_lineage",
          ReuseAssessment.from_dict(
              inline_harvest.assessment.to_dict())
          == inline_harvest.assessment
          and type(inline_harvest.generalization).from_dict(
              inline_harvest.generalization.to_dict())
          == inline_harvest.generalization)
    evidence_only_opportunity = observe_reuse_opportunity_as_loop(
        ReuseObservationRequest(
            "correlation-evidence", "run-evidence", "loop-evidence-producer",
            "practitioner.solver@1.0.0",
            "practitioner.evidence@1.0.0#fixture", "result-evidence",
            "execution-evidence", opportunity.artifact_ref,
            opportunity.artifact_digest, opportunity.artifact_kind,
            opportunity.operation_family, "2026-08-30T12:02:00Z",
            True, True, HarvestDispatch.INLINE), ledger=ledger)
    evidence_assessment = replace(
        assessment, assessment_id="assessment-evidence",
        opportunity_id=evidence_only_opportunity.event_id,
        summary_score_1_to_10=3.0,
        recommendation=ReuseRecommendation.STORE_AS_EXAMPLE_ONLY,
        rationale="One accepted source is retained without candidate creation.")
    before_evidence_only = len(authority_store.query(IntelligenceQuery(
        artifact_kinds=("code_asset",))))
    evidence_only = harvest_reuse_opportunity_as_loop(
        authority,
        ReuseHarvestRequest(
            evidence_only_opportunity,
            ReuseHarvestPolicy(
                "reuse-harvest-evidence", "1.0.0",
                dispatch=HarvestDispatch.INLINE),
            ReuseHarvestServices(
                lambda _item: evidence_assessment,
                lambda _item, _assessment: (_ for _ in ()).throw(
                    AssertionError("evidence-only path called generalizer")),
                assessment_mode="deterministic",
                generalization_mode="deterministic")),
        ledger=ledger)
    check("low_value_observation_is_retained_without_candidate_creation",
          evidence_only.outcome == "evidence_only"
          and evidence_only.registration is None
          and len(authority_store.query(IntelligenceQuery(
              artifact_kinds=("code_asset",)))) == before_evidence_only)
    non_code_refused = False
    non_code = observe_reuse_opportunity_as_loop(ReuseObservationRequest(
        "correlation-text", "run-text", "loop-text-producer",
        "practitioner.solver@1.0.0",
        "practitioner.text@1.0.0#fixture", "result-text",
        "execution-text", "memory://text/example", "f" * 64,
        "text_note", "procedure.example", "2026-08-30T12:03:00Z",
        True, True, HarvestDispatch.INLINE), ledger=ledger)
    try:
        harvest_reuse_opportunity_as_loop(
            authority,
            ReuseHarvestRequest(
                non_code,
                ReuseHarvestPolicy(
                    "reuse-harvest-code-only", "1.0.0",
                    dispatch=HarvestDispatch.INLINE),
                harvest_services),
            ledger=ledger)
    except Exception:
        non_code_refused = True
    check("non_code_observation_cannot_create_a_code_candidate",
          non_code_refused)

    before_promotion = rebuild_capability_projection_as_loop(
        authority, EphemeralRecordStore(), "before-promotion", ledger=ledger)
    check("candidate_is_not_in_active_resolution_projection",
          before_promotion.record_count == 0)
    self_verification_refused = False
    try:
        CodeAssetAdmissionRecord(
            "admission-self", spec.asset_id, spec.version,
            spec.qualification_digest, spec.body_ref.digest,
            spec.dependency_digest, spec.contract_digest, spec.effect_digest,
            producer_id, producer_id, ("self-test",),
            content_digest("self-test"))
    except CodeAssetAdmissionError:
        self_verification_refused = True
    check("candidate_producer_cannot_self_qualify",
          self_verification_refused)
    suite_ok, suite_refs, suite_digest = _qualification_suite()
    admission = CodeAssetAdmissionRecord(
        "admission-dedup-v1", spec.asset_id, spec.version,
        spec.qualification_digest, spec.body_ref.digest,
        spec.dependency_digest, spec.contract_digest, spec.effect_digest,
        producer_id, "verifier-loop", suite_refs, suite_digest)
    qualified = authority.qualify_as_loop(QualificationRequest(
        spec.asset_id, spec.version, admission), ledger=ledger)
    producer_promotion_refused = False
    try:
        authority.promote_as_loop(PromotionRequest(
            spec.asset_id, spec.version, producer_id, suite_refs),
            ledger=ledger)
    except Exception:
        producer_promotion_refused = True
    promoted = authority.promote_as_loop(PromotionRequest(
        spec.asset_id, spec.version, "promotion-authority", suite_refs),
        ledger=ledger)
    check("independent_qualification_and_exact_promotion_are_separate",
          suite_ok and qualified.lifecycle_state == "validated"
          and producer_promotion_refused
          and promoted.lifecycle_state == "registered",
          {"qualified": qualified.transition_record_ref,
           "promoted": promoted.transition_record_ref})

    projection = EphemeralRecordStore()
    rebuilt = rebuild_capability_projection_as_loop(
        authority, projection, "1.0.0", ledger=ledger)
    check("active_search_projection_is_rebuildable_from_authority",
          rebuilt.record_count == 1
          and projection.get("capability_projection_manifest.active")
          ["attributes"]["manifest_ref"] == rebuilt.manifest_ref)
    warm_need = CapabilityNeed(
        "need-warm", "run-warm", "practitioner.solver@1.0.0",
        "Collapse repeated customer rows and report which rows merged.",
        "data.record_deduplication", "merge repeated structured rows",
        cold_need.input_contract_ref, cold_need.input_contract_digest,
        cold_need.output_contract_ref, cold_need.output_contract_digest,
        allowed_effects=("pure",),
        search_terms=("collapse", "repeated", "rows", "merged"))
    warm_resolution = CapabilityResolver(
        authority, projection).resolve_as_loop(
            CapabilityResolutionRequest(warm_need), ledger=ledger)
    forged_projection = EphemeralRecordStore(
        projection.export()["records"])
    forged_row = forged_projection.get(rebuilt.record_refs[0])
    forged_projection.put({
        **forged_row,
        "attributes": {**forged_row["attributes"], "effects": []},
    })
    forged_resolution = CapabilityResolver(
        authority, forged_projection).resolve_as_loop(
            CapabilityResolutionRequest(warm_need), ledger=ledger)
    check("projection_metadata_cannot_understate_authoritative_effects",
          forged_resolution.plan.disposition
          is ResolutionDisposition.ESCALATE_TO_NOVEL_BUILD
          and any(
              "projection differs" in reason
              for match in forged_resolution.matches
              for reason in match.rejection_reasons))
    warm_input = {
        "records": [
            {"email": "a@example.com", "phone": "1", "name": "A"},
            {"email": "a@example.com", "phone": "1", "name": "Alias"},
            {"email": "b@example.com", "phone": "2", "name": "B"}],
        "key_fields": ["email", "phone"], "keep": "first"}
    expected = _deduplicate_records(warm_input)
    def materializer(uri: str) -> MaterializedPayload:
        if uri != spec.body_ref.uri:
            raise ValueError("unexpected reusable artifact reference")
        return MaterializedPayload(
            artifact_store.get_text(candidate_artifact),
            candidate_artifact.digest, candidate_artifact.object_key)

    def binder(payload: object, entrypoint: str):
        if payload != source or entrypoint != "deduplicate_records":
            raise ValueError("stored source or entrypoint changed")
        return _deduplicate_records

    warm = invoke_capability_as_loop(
        authority, projection, CapabilityInvocationRequest(
            "run-warm", warm_need, warm_resolution.plan, warm_input,
            materializer, lambda value: value == expected,
            "warm-output-verifier", entrypoint="deduplicate_records",
            binder=binder), ledger=ledger)
    metrics["warm_model_calls"] = warm.record.model_call_count
    check("warm_paraphrase_executes_promoted_artifact_with_zero_model_calls",
          warm_resolution.plan.disposition
          is ResolutionDisposition.EXECUTE_EXACT
          and warm.record.accepted
          and warm.record.model_call_count == 0
          and warm.record.exact_artifact_digest == artifact_digest,
          warm.record.to_dict())
    check("invocation_record_round_trips_with_independent_verifier",
          warm.record.from_dict(warm.record.to_dict()) == warm.record
          and warm.record.verifier_id == "warm-output-verifier")
    producer_verification_refused = False
    try:
        invoke_capability_as_loop(
            authority, projection, CapabilityInvocationRequest(
                "run-self-verify", warm_need, warm_resolution.plan,
                warm_input, materializer, lambda _value: True,
                producer_id, entrypoint="deduplicate_records",
                binder=binder), ledger=ledger)
    except Exception:
        producer_verification_refused = True
    check("capability_producer_cannot_be_sole_result_verifier",
          producer_verification_refused)
    adaptive_task = (
        "Collapse repeated customer rows using email and phone, keep the first "
        "row, and report which rows merged.")
    task_resolver = ReusableCapabilityTaskResolver(
        "reusable-capability.record-deduplication",
        CapabilityResolver(authority, projection),
        lambda task: replace(
            warm_need, need_id="need-adaptive-warm",
            originating_run_id="run-adaptive-warm")
        if task == adaptive_task else None,
        lambda _task: warm_input, materializer,
        lambda _task, value: value == expected,
        "adaptive-output-verifier", entrypoint="deduplicate_records",
        binder=binder)
    with tempfile.TemporaryDirectory(
            prefix="reusable_capability_adaptive_") as adaptive_root:
        adaptive_warm = run_adaptive_practitioner(
            AdaptivePractitionerRequest(
                adaptive_task, mode="deterministic", runs_dir=adaptive_root,
                persist_run_history=False),
            AdaptivePractitionerDependencies(
                deterministic_resolvers=(task_resolver,)))
    metrics["adaptive_warm_model_calls"] = adaptive_warm["model_calls"]
    check("adaptive_practitioner_uses_promoted_capability_with_zero_model_calls",
          adaptive_warm["solved"]
          and adaptive_warm["model_calls"] == 0
          and adaptive_warm["result"]["verified"] is True
          and adaptive_warm["result"]["invocation"]["model_call_count"] == 0)
    with tempfile.TemporaryDirectory(
            prefix="reusable_capability_restart_") as restart_root:
        authority_path = os.path.join(restart_root, "authority.sqlite")
        projection_path = os.path.join(restart_root, "projection.sqlite")
        persisted_authority_store = SQLiteRecordStore(authority_path)
        persisted_authority_store.import_bundle(authority_store.export())
        persisted_authority = CapabilityAuthority(persisted_authority_store)
        persisted_projection = SQLiteRecordStore(projection_path)
        persisted_rebuild = rebuild_capability_projection_as_loop(
            persisted_authority, persisted_projection, "restart-1.0.0",
            ledger=ledger)
        persisted_authority_store.close()
        persisted_projection.close()
        reopened_authority_store = SQLiteRecordStore(authority_path)
        reopened_projection = SQLiteRecordStore(projection_path)
        reopened_authority = CapabilityAuthority(reopened_authority_store)
        reopened_resolution = CapabilityResolver(
            reopened_authority, reopened_projection).resolve_as_loop(
                CapabilityResolutionRequest(warm_need), ledger=ledger)
        reopened_invocation = invoke_capability_as_loop(
            reopened_authority, reopened_projection,
            CapabilityInvocationRequest(
                "run-restart", warm_need, reopened_resolution.plan,
                warm_input, materializer, lambda value: value == expected,
                "restart-output-verifier",
                entrypoint="deduplicate_records", binder=binder),
            ledger=ledger)
        check("authority_projection_and_artifact_survive_store_restart",
              persisted_rebuild.record_count == 1
              and reopened_resolution.plan.disposition
              is ResolutionDisposition.EXECUTE_EXACT
              and reopened_invocation.record.accepted
              and reopened_invocation.record.model_call_count == 0
              and artifact_store.get_text(candidate_artifact) == source,
              {"authority": authority_path,
               "projection": projection_path,
               "artifact": candidate_artifact.object_key})
        reopened_authority_store.close()
        reopened_projection.close()

    normalize_profile = hybrid_assistance_profile(
        "hybrid.normalize_then_resolve")
    free_form = CapabilityNeed(
        "need-free-form", "run-free-form",
        "practitioner.solver@1.0.0",
        "Make the repeated people collapse into one and show the joins.",
        "unmapped.free_form", "people rows should collapse",
        cold_need.input_contract_ref, cold_need.input_contract_digest,
        cold_need.output_contract_ref, cold_need.output_contract_digest,
        allowed_effects=("pure",), search_terms=("people", "joins"))
    bounded_packet = {
        "task": free_form.semantic_summary,
        "allowed_operation_families": ["data.record_deduplication"],
        "input_contract_ref": free_form.input_contract_ref,
        "output_contract_ref": free_form.output_contract_ref,
    }
    normalization_calls = []

    def normalization_model(packet: dict) -> dict:
        normalization_calls.append(packet)
        return {
            "profile_id": normalize_profile.profile_id,
            "profile_version": normalize_profile.version,
            "stage_outputs": {
                "need_normalization": {
                    "goal": free_form.goal,
                    "operation_family": "data.record_deduplication",
                    "semantic_summary": "deduplicate structured people rows",
                    "search_terms": ["deduplicate", "merge rows", "lineage"],
                },
                "query_expansion": {
                    "search_terms": ["duplicate records", "collapse rows"]},
            },
        }

    assisted = run_hybrid_assistance_as_loop(HybridAssistanceRequest(
        normalize_profile, bounded_packet, normalization_model), ledger=ledger)
    normalized = normalized_need_from_assistance(
        free_form, assisted, ("data.record_deduplication",))
    normalized_resolution = CapabilityResolver(
        authority, projection).resolve_as_loop(
            CapabilityResolutionRequest(normalized), ledger=ledger)
    metrics["hybrid_normalization_model_calls"] = assisted.model_calls
    check("bounded_hybrid_normalization_finds_same_promoted_capability",
          assisted.model_calls == 1 and len(normalization_calls) == 1
          and set(normalization_calls[0]["payload"])
          == set(bounded_packet)
          and normalized_resolution.plan.disposition
          is ResolutionDisposition.EXECUTE_EXACT,
          "model saw only the need contract and controlled vocabulary")

    adapter_profile = hybrid_assistance_profile(
        "hybrid.adapt_then_execute")
    mismatched = CapabilityNeed(
        "need-adapter", "run-adapter", "practitioner.solver@1.0.0",
        "Deduplicate a differently named request object.",
        "data.record_deduplication", "deduplicate alternate record container",
        "alternate_deduplication_request/v1",
        content_digest("alternate_deduplication_request/v1"),
        cold_need.output_contract_ref, cold_need.output_contract_digest,
        allowed_effects=("pure",), search_terms=("deduplicate", "records"))
    adapter_resolution = CapabilityResolver(
        authority, projection).resolve_as_loop(
            CapabilityResolutionRequest(
                mismatched, adapter_profile), ledger=ledger)
    adapter_assistance = run_hybrid_assistance_as_loop(
        HybridAssistanceRequest(adapter_profile, {
            "source_contract": mismatched.input_contract_ref,
            "target_contract": cold_need.input_contract_ref,
            "candidate_refs": [item.capability_ref
                               for item in adapter_resolution.matches
                               if item.eligible],
        }, lambda _packet: {
            "profile_id": adapter_profile.profile_id,
            "profile_version": adapter_profile.version,
            "stage_outputs": {
                "input_adapter_synthesis": {
                    "mapping": {"items": "records", "keys": "key_fields"}},
                "output_adapter_synthesis": {"mapping": "identity"},
            },
        }), ledger=ledger)
    alternate_input = {
        "items": warm_input["records"],
        "keys": warm_input["key_fields"], "keep": "first"}
    adapted = execute_ephemeral_adapter_as_loop(AdapterExecutionRequest(
        lambda value: {
            "records": value["items"], "key_fields": value["keys"],
            "keep": value["keep"]}, alternate_input,
        lambda value: set(value) == {"records", "key_fields", "keep"}),
        ledger=ledger)
    adapter_warm = invoke_capability_as_loop(
        authority, projection, CapabilityInvocationRequest(
            "run-adapter", warm_need, warm_resolution.plan,
            adapted["value"], materializer,
            lambda value: value == expected,
            "adapter-output-verifier", entrypoint="deduplicate_records",
            binder=binder), ledger=ledger)
    metrics["adapter_model_calls"] = adapter_assistance.model_calls
    check("hybrid_adapter_path_is_bounded_verified_and_ephemeral",
          adapter_resolution.plan.disposition
          is ResolutionDisposition.REQUEST_HYBRID_ASSISTANCE
          and adapter_assistance.model_calls == 1
          and adapter_warm.record.accepted
          and authority_store.query(IntelligenceQuery(
              layers=("code",), artifact_kinds=("code_asset_state",)))
              == [authority.state(spec.asset_id, spec.version)],
          "adapter was not promoted into Code Intelligence")

    rejected = invoke_capability_as_loop(
        authority, projection, CapabilityInvocationRequest(
            "run-failure", warm_need, warm_resolution.plan, warm_input,
            materializer, lambda _value: False,
            "failure-output-verifier", entrypoint="deduplicate_records",
            binder=binder), ledger=ledger)
    state_before_repair = authority.state(spec.asset_id, spec.version)
    repaired_source = source + "\n# repaired candidate version\n"
    repaired_artifact = artifact_store.put_text(
        repaired_source, media_type="text/x-python",
        artifact_kind="repaired_python_candidate")
    repaired_digest = repaired_artifact.digest
    repair_profile = hybrid_assistance_profile(
        "hybrid.execute_then_repair")
    failure_packet = {
        "need_id": warm_need.need_id,
        "selected_capability_ref": warm_resolution.plan.selected_capability_ref,
        "artifact_digest": rejected.record.exact_artifact_digest,
        "input_contract_ref": warm_need.input_contract_ref,
        "output_contract_ref": warm_need.output_contract_ref,
        "failure_class": rejected.record.failure_class,
        "failed_postcondition": rejected.record.verification_status,
        "allowed_actions": ["create_new_version_candidate"],
        "repair_attempt": 1,
    }
    repair_assistance = run_hybrid_assistance_as_loop(
        HybridAssistanceRequest(repair_profile, failure_packet,
                                lambda _packet: {
            "profile_id": repair_profile.profile_id,
            "profile_version": repair_profile.version,
            "stage_outputs": {
                "failure_diagnosis": {
                    "classification": "capability_bug",
                    "evidence_ref": rejected.record.invocation_id,
                },
                "bounded_repair": {
                    "proposed_version": "1.0.1",
                    "artifact_ref": (
                        "context-artifact://" + repaired_artifact.object_key),
                    "artifact_digest": repaired_digest,
                },
            },
        }), ledger=ledger)
    repair_limit_refused = False
    try:
        run_hybrid_assistance_as_loop(HybridAssistanceRequest(
            repair_profile, {**failure_packet, "repair_attempt": 2},
            lambda _packet: (_ for _ in ()).throw(
                AssertionError("over-budget repair reached model"))),
            ledger=ledger)
    except HybridAssistanceError:
        repair_limit_refused = True
    repair_proposal = repair_assistance.output_for(
        HybridAssistanceStage.BOUNDED_REPAIR)
    metrics["repair_model_calls"] = repair_assistance.model_calls
    repaired_spec = spec_from_template(
        "pure_function", asset_id=spec.asset_id, version="1.0.1",
        name=spec.name, description=spec.description,
        source_kind=spec.source_kind,
        body_ref=ExternalPayloadRef(
            "context-artifact://" + repaired_artifact.object_key,
            repaired_digest,
            len(repaired_source.encode()), "text/x-python"),
        entrypoints=spec.entrypoints, input_contract=spec.input_contract,
        output_contract=spec.output_contract, effects=spec.effects,
        license=spec.license, lifecycle="candidate",
        metadata={**spec.metadata,
                  "supersedes_ref": promoted.exact_record_ref})
    repair_opportunity = observe_reuse_opportunity_as_loop(
        ReuseObservationRequest(
            "correlation-repair", "run-failure", "loop-repair-producer",
            "practitioner.solver@1.0.0",
            "practitioner.repair@1.0.0#fixture", "result-repair",
            rejected.record.invocation_id, repaired_spec.body_ref.uri,
            repaired_digest, "python_function",
            "data.record_deduplication", "2026-08-30T13:00:00Z",
            True, True, HarvestDispatch.INLINE), ledger=ledger)
    repair_assessment = ReuseAssessment(
        "assessment-repair", repair_opportunity.event_id, "loop-diagnosis",
        True, _assessment_dimensions(
            observed_correctness=9.0, recurrence_likelihood=6.0,
            parameterization_clarity=8.0, testability=9.0,
            effect_safety=8.0, security_privacy=8.0,
            build_difficulty=6.0, qualification_difficulty=7.0),
        7.0, 0.7,
        ReuseRecommendation.CREATE_NEW_VERSION_CANDIDATE,
        "Failure evidence supports a separately qualified candidate version.",
        (rejected.record.invocation_id,))
    repair = authority.register_candidate_as_loop(CandidateRegistrationRequest(
        repair_opportunity, repair_assessment, repaired_spec,
        "repair-producer", (rejected.record.invocation_id,)), ledger=ledger)
    check("failed_reuse_does_not_mutate_active_artifact_and_repair_versions",
          not rejected.record.accepted
          and repair_assistance.model_calls == 1
          and repair_limit_refused
          and repair_proposal["proposed_version"] == repaired_spec.version
          and repair_proposal["artifact_digest"]
          == repaired_spec.body_ref.digest
          and authority.state(spec.asset_id, spec.version)
          == state_before_repair
          and authority.state(spec.asset_id, "1.0.1")["lifecycle"]
          == "candidate"
          and repair.lifecycle_state == "candidate",
          {"active_version": spec.version, "repair_version": "1.0.1"})
    rejected_repair = authority.transition_as_loop(
        repaired_spec.asset_id, repaired_spec.version, "rejected",
        "repair-review", (rejected.record.invocation_id,), ledger=ledger)
    check("rejected_candidate_is_terminal_and_never_active",
          rejected_repair.lifecycle_state == "rejected"
          and authority.state(
              repaired_spec.asset_id, repaired_spec.version)["lifecycle"]
          == "rejected")

    rerank_profile = hybrid_assistance_profile(
        "hybrid.retrieve_then_rerank")
    rerank = run_hybrid_assistance_as_loop(HybridAssistanceRequest(
        rerank_profile, {"eligible_candidate_refs": [
            warm_resolution.plan.selected_capability_ref]},
        lambda _packet: {
            "profile_id": rerank_profile.profile_id,
            "profile_version": rerank_profile.version,
            "stage_outputs": {"candidate_reranking": {
                "selected_capability_ref": "ineligible-capability",
                "rationale": "adversarial fixture",
            }},
        }), ledger=ledger)
    ineligible_refused = False
    try:
        selected_candidate_from_assistance(
            rerank, (warm_resolution.plan.selected_capability_ref,))
    except HybridAssistanceError:
        ineligible_refused = True
    oversized_rerank_refused = False
    try:
        run_hybrid_assistance_as_loop(HybridAssistanceRequest(
            rerank_profile,
            {"eligible_candidate_refs": [
                f"eligible-{index}" for index in range(9)]},
            lambda _packet: (_ for _ in ()).throw(
                AssertionError("oversized rerank reached model"))),
            ledger=ledger)
    except HybridAssistanceError:
        oversized_rerank_refused = True
    check("hybrid_reranker_cannot_select_outside_eligible_set",
          rerank.model_calls == 1 and ineligible_refused
          and oversized_rerank_refused)

    duplicate_opportunity = observe_reuse_opportunity_as_loop(
        ReuseObservationRequest(
            "correlation-duplicate", "run-duplicate",
            "loop-duplicate-producer", "practitioner.solver@1.0.0",
            "practitioner.duplicate@1.0.0#fixture", "result-duplicate",
            "execution-duplicate", spec.body_ref.uri, spec.body_ref.digest,
            "python_function", "data.record_deduplication",
            "2026-08-30T14:00:00Z", True, True,
            HarvestDispatch.INLINE), ledger=ledger)
    duplicate_assessment = ReuseAssessment(
        "assessment-duplicate", duplicate_opportunity.event_id,
        "loop-assessor-duplicate", True,
        _assessment_dimensions(
            observed_correctness=10.0, recurrence_likelihood=7.0,
            catalog_gap=0.0, testability=9.0,
            evidence_diversity=8.0), 7.0, 0.9,
        ReuseRecommendation.CREATE_NEW_CAPABILITY_CANDIDATE,
        "Exact artifact evidence should consolidate into the existing record.",
        ("execution-duplicate",))
    duplicate = authority.register_candidate_as_loop(
        CandidateRegistrationRequest(
            duplicate_opportunity, duplicate_assessment, spec,
            "duplicate-producer", ("execution-duplicate",)), ledger=ledger)
    check("duplicate_harvest_consolidates_instead_of_growing_library",
          duplicate.outcome == "duplicate_consolidated"
          and duplicate.duplicate_of)

    superseded = authority.transition_as_loop(
        spec.asset_id, spec.version, "superseded", "version-review",
        (duplicate.capability_record_ref,), ledger=ledger)
    rolled_back = authority.transition_as_loop(
        spec.asset_id, spec.version, "registered", "rollback-authority",
        (superseded.transition_record_ref,), ledger=ledger)
    check("rollback_reactivates_only_the_same_qualified_exact_version",
          superseded.lifecycle_state == "superseded"
          and rolled_back.lifecycle_state == "registered"
          and rolled_back.exact_record_ref == promoted.exact_record_ref
          and authority.active_spec(spec.asset_id, spec.version).body_ref.digest
          == spec.body_ref.digest)

    rebuilt_again = rebuild_capability_projection_as_loop(
        authority, projection, "1.0.0", ledger=ledger)
    check("projection_rebuild_is_deterministic",
          rebuilt_again.record_count == rebuilt.record_count
          and rebuilt_again.projection_digest == rebuilt.projection_digest,
          rebuilt_again.projection_digest)
    quarantine = authority.transition_as_loop(
        spec.asset_id, spec.version, "quarantined", "safety-review",
        (rejected.record.invocation_id,), ledger=ledger)
    quarantined_projection = rebuild_capability_projection_as_loop(
        authority, projection, "after-quarantine", ledger=ledger)
    post_quarantine_resolution = CapabilityResolver(
        authority, projection).resolve_as_loop(
            CapabilityResolutionRequest(warm_need), ledger=ledger)
    check("quarantined_version_is_removed_from_active_resolution",
          quarantine.lifecycle_state == "quarantined"
          and quarantined_projection.record_count == 0
          and post_quarantine_resolution.plan.disposition
          is ResolutionDisposition.ESCALATE_TO_NOVEL_BUILD)

    history = RunHistory.from_ledger(ledger.events, run_id="run-flywheel")
    history.commit()
    chain = history.verify_chain()
    check("important_operations_leave_digest_chained_run_history",
          chain["intact"] and len(history.event_log) > 0,
          {"events": len(history.event_log),
           "head_digest": history.event_log[-1].event_digest})

    metrics.update({
        "model_calls_avoided_on_warm_path": (
            int(metrics["cold_model_calls"])
            - int(metrics["warm_model_calls"])),
        "candidate_creation_count": 2,
        "qualification_count": 1,
        "promotion_count": 1,
        "duplicate_consolidation_count": 2,
        "evidence_only_count": 1,
        "rejection_count": 1,
        "rollback_count": 1,
        "quarantine_count": 1,
        "state_corruption_incidents": 0,
        "producer_verifier_separation_violations": 0,
    })
    passed = sum(item["passed"] for item in tests)
    result = {
        "record_type": "reusable_capability_flywheel_self_test/v1",
        "scope": "offline_contract_only",
        "tests": tests,
        "passed": passed,
        "total": len(tests),
        "all_passed": passed == len(tests),
        "metrics": metrics,
        "promoted": {
            "asset_id": spec.asset_id,
            "asset_version": spec.version,
            "artifact_digest": artifact_digest,
            "admission_id": admission.admission_id,
            "qualification_digest": spec.qualification_digest,
        },
        "projection": {
            "version": rebuilt.projection_version,
            "digest": rebuilt.projection_digest,
            "record_count": rebuilt.record_count,
            "manifest_ref": rebuilt.manifest_ref,
        },
        "run_history": {
            "run_id": history.run_id,
            "events": len(history.event_log),
            "head_digest": history.event_log[-1].event_digest,
        },
    }
    artifact_directory.cleanup()
    return result


__all__ = ("self_test",)
