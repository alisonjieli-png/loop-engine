"""Finite community research work on the existing reactive scheduler and canonical Loop.

The worker compiles evidence packets and component work orders, not code or
approval. It uses fenced leases and exact managed-record versions. A stopped
running activation requires reconciliation; it is not silently replayed.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from loop_engine.core.reactive_scheduler import SQLiteReactiveScheduler
from loop_engine.loop.atomic_primitives import LoopValue, LoopValueCreateRequest
from loop_engine.loop.loop_definition import LoopDefinitionRef
from loop_engine.loop.reactive_activation import (
    ActivationClaimRequest,
    ActivationStartRequest,
    ActivationStatus,
    ActivationTerminalRequest,
    ReactiveSeriesDefinition,
    TriggerEnvelope,
)
from loop_engine.loop.reactive_contracts import (
    ActivationPolicy,
    AdmissionPolicy,
    EmissionPolicy,
    ExplorationPolicy,
    InputSchedulingPolicy,
    MetricDirection,
    OutputPortDefinition,
    PersistenceMode,
    PortfolioPolicy,
    PortfolioView,
    RankingDimension,
    ReactiveLivenessPolicy,
    ReactiveLoopProfile,
    RetentionPolicy,
    ServingPolicy,
    TriggerKind,
)
from loop_engine.loop.service_loop_envelope import (
    ServiceLoopSpec,
    run_service_operation,
)

INPUT_CONTRACT = "community_research_input/v1"
OUTPUT_CONTRACT = "community_component_work_order/v1"


def work_profile():
    return ReactiveLoopProfile("community.research.compile", "1.0.0",
        ActivationPolicy((TriggerKind.PUSH_EVENT,), reactivation_enabled=True, minimum_information_delta=0.01),
        AdmissionPolicy(1000), InputSchedulingPolicy("priority_aging", 0.01), PersistenceMode.DURABLE_SERIES,
        ExplorationPolicy(), (OutputPortDefinition("result", "research_work_order", OUTPUT_CONTRACT),),
        PortfolioPolicy("community.research.evidence", "1.0.0", PortfolioView.VERIFIED_TOP_K,
                        (RankingDimension("evidence_coverage", MetricDirection.MAXIMIZE),), 20),
        EmissionPolicy(), ServingPolicy(20), RetentionPolicy(100, 100), ReactiveLivenessPolicy(30))


def open_queue(store):
    if not store.writes_allowed:
        raise PermissionError("local_write_grant_required")
    store._safe()
    scheduler = SQLiteReactiveScheduler(str(store.root / "scheduler.sqlite"), store.runtime)
    profile = work_profile()
    revision = definition_digest()
    series = ReactiveSeriesDefinition("community.compile." + revision[:16], "Compile source-linked component research work.",
        LoopDefinitionRef("community.compile", "1.0.0", revision), profile.profile_id, profile.version,
        profile.content_digest, INPUT_CONTRACT, ("result",), 2, 1)
    scheduler.register_profile(profile)
    scheduler.register_series(series)
    return scheduler, series


def definition_digest():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def queue_lead(scheduler, series, identity, version, document, now, loop_id):
    value = LoopValue.create(document, LoopValueCreateRequest(INPUT_CONTRACT, "community_lead", loop_id, "community.intake/v1"))
    digest = value.content_digest
    trigger_id = hashlib.sha256((series.series_id + ":" + digest).encode()).hexdigest()
    trigger = TriggerEnvelope("community.trigger." + trigger_id[:24], series.series_id, TriggerKind.PUSH_EVENT,
        identity + ":v" + version, value.to_ref(), loop_id, now, now, identity, 1.0,
        priority=min(100, document["data"]["priority"]))
    return scheduler.admit(trigger).created


def reconcile_definition(store, scheduler, series, now):
    """Carry saved inputs into a changed compiler definition, without editing old activations."""
    identity = "community.source.compiler"
    prior = store.get(identity)
    definition = series.loop_definition_ref.content_digest
    if prior and prior["document"]["data"].get("definition_digest") == definition:
        return {"status": "unchanged", "requeued": 0}
    leads = store.query(kind="lead", limit=1000)
    queued = 0
    for row in leads:
        queued += queue_lead(scheduler, series, row["identity"], row["version"], row["document"], now, "community.reconcile")
    for row in store.query(kind="research_brief", state="needs_research", limit=1000):
        if row["document"]["data"].get("definition_digest") != definition:
            store.put(row["identity"], "research_brief", row["document"]["source_id"], "deferred",
                      {**row["document"]["data"], "superseded_for_definition": definition}, expected=row)
    state = {"definition_digest": definition, "at": now, "requeued": queued,
             "reconciliation_limit": 1000, "coverage_complete": len(leads) < 1000}
    # A capped reconciliation stays pending instead of claiming complete coverage.
    if state["coverage_complete"]:
        store.put(identity, "source", "compiler", "recorded", state, expected=prior)
    return {"status": "reconciled" if state["coverage_complete"] else "partial", **state}


def component_work(lead):
    """Hints route investigation, never assert that a mentioned tool produced the output."""
    signals = set(lead["signals"])
    work = []
    if signals & {"geometry_and_rigging", "gameplay", "procedural_generation"}:
        work += ["geometry or scene generator with typed parameters", "scale, coordinate, topology and rig-weight checks",
                 "collision, navigation and recorded-input fixtures"]
    if signals & {"visual_design", "procedural_generation"}:
        work += ["editable composition, shader or material with dependency locks", "aspect-ratio, timing and visual regression fixtures"]
    if "audio" in signals:
        work += ["audio or MIDI transform with sample-rate and channel contracts", "loudness, clipping, duration and alignment checks"]
    if "publication" in signals:
        work += ["reproducible export and packaging recipe", "platform requirements and asset-rights checklist"]
    if "software_data" in signals:
        work += ["schema, migration or data-transform component", "idempotency, tenant isolation and malformed-input fixtures"]
    if "agent_control" in signals:
        work += ["bounded engine-control adapter with declared read and write operations"]
    return {"record_type": OUTPUT_CONTRACT, "source_url": lead["url"], "source_digest": lead["content_digest"],
            "source_title": lead.get("title", ""),
            "tools_mentioned": lead["tools_mentioned"], "linked_sources": lead["linked_sources"],
            "signal_hints": lead["signals"],
            "candidate_component_work": list(dict.fromkeys(work)),
            "research_questions": ["What exact versions, input assets and steps produced the result?",
                "Which links contain editable source and explicit reuse rights?",
                "Which claims are creator reports, independently documented facts, or reproduced results?",
                "What broke during revision, export or real-input testing?",
                "Can an existing component satisfy the task without extra context or generated code?"],
            "delivery_contract": {"discover": "compact purpose, inputs, outputs, effects and compatibility",
                "resolve": "exact version and content digest", "configure": "parameters rather than source rewrites",
                "execute": "existing Loop and authorized native engine", "check": "independent known-good and known-wrong fixtures"},
            "next_stage": "source_verification_then_candidate_factory", "reproduced": False,
            "reuse_rights": "not_established", "publication_approved": False}


def work_once(store, scheduler, series, now, *, maximum=20):
    results = []
    for _index in range(maximum):
        claim = scheduler.claim(ActivationClaimRequest("community.compiler", now, 120, series.series_id))
        if claim is None:
            break
        activation = scheduler.start(ActivationStartRequest(claim.activation.activation_id, claim.lease.lease_id,
                                                             claim.lease.fencing_token, now))
        trigger = scheduler.get_trigger(activation.trigger_id)
        identity, version = trigger.subject_ref.rsplit(":v", 1)
        held = store.get(identity, version)
        value = LoopValue.create(held["document"], LoopValueCreateRequest(INPUT_CONTRACT, "community_lead", "verify", "community.intake/v1"))
        if value.content_digest != activation.input_ref.content_digest or activation.loop_definition_ref != series.loop_definition_ref:
            raise ValueError("research_input_or_definition_mismatch")
        definition = series.loop_definition_ref.content_digest
        brief_id = "community.brief." + hashlib.sha256((value.content_digest + definition).encode()).hexdigest()

        def compile_work(active, brief_id=brief_id, held=held, definition=definition):
            if store.get(brief_id) is None:
                store.put(brief_id, "research_brief", held["document"]["source_id"], "needs_research",
                          {**component_work(held["document"]["data"]), "definition_digest": definition})
            return active.loop_id

        loop_id = run_service_operation(store.runtime, ServiceLoopSpec("community_compile_work", "practitioner.code_execution",
            INPUT_CONTRACT, OUTPUT_CONTRACT, ("reads_fs", "writes_fs"), "Compile one bounded research work order.",
            "community_work_failed"), compile_work)
        scheduler.terminal(ActivationTerminalRequest(activation.activation_id, claim.lease.lease_id,
            claim.lease.fencing_token, ActivationStatus.COMPLETED, now, loop_id, "WORK_ORDER_COMPILED",
            (brief_id,), worker_id="community.compiler"))
        results.append(brief_id)
    return results
