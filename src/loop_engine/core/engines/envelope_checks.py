"""Named checks for the envelope layers, their records and the coverage that every engine slot declares.

Each check names its known-wrong case: the input that must be refused or reported. A control whose
name starts with ``removed_`` runs the same case with one guard taken away and confirms that the check
would then fail, which is how a removed guard is shown to be noticed. Nothing here opens a network
connection, starts a process, imports an engine module or calls a model. The records live in
``envelope.py``, ``envelope_tracking.py`` and ``envelope_preflight.py``; the declarations and the
baseline are read by ``envelope_coverage.py``. Section 14 of the functional component standard cites
these check names as its enforcement.
"""
from __future__ import annotations

import ast
import os
from dataclasses import replace
from types import MappingProxyType, SimpleNamespace
from unittest.mock import patch

from . import envelope as envelope_module
from .envelope import (
    COVERAGE_LAYERS, EFFECT_DURABLE_PENDING, EFFECT_UNKNOWN, ENGINE_SOURCE, INBOUND_LAYERS,
    LAYER_ACCEPTED, LAYER_ANSWERED, LAYER_HANDSHAKE, LAYER_NOT_APPLICABLE, LAYER_REFUSED, LAYER_TRACKING,
    MAXIMUM_AUTOMATIC_ATTEMPTS, MAXIMUM_ENVELOPE_DEPTH, RECONCILE_BEFORE_RETRY, RETRY_AFTER_FIX,
    RETRY_AFTER_WAIT, RETRY_NOW_SAME_IDENTITY, EnvelopeError, EnvelopeHandshakeDeclaration,
    EnvelopeHandshakeRequest, EnvelopeHandshakeVerdict, EnvelopeRecoveryPolicy, EnvelopeRefusal, EnvelopeTrace,
    RecoveryAllowance, enter_nested, envelope_refusal, may_recover, negotiate_handshake, nesting_depths, root_frame)
from .envelope_coverage import (
    COVERAGE_RULES, FULL, NONE, NOT_APPLICABLE, PARTIAL, RECORDED_BASELINE_FLOOR, EnvelopeCoverageBaseline,
    EnvelopeLayerCoverage, EnvelopeSlotCoverage, coverage_findings, coverage_report, load_envelope_coverage,
    load_envelope_coverage_baseline)
from .envelope_preflight import (
    STEP_REPAIR_REFUSED, VERDICT_READY, VERDICT_REFUSED, VERDICT_REPAIRED, EnvelopePreflightCheck,
    EnvelopePreflightGrant, EnvelopeSelfRepair, run_preflight)
from .envelope_tracking import (
    ANSWER_FROM_FIRST_RESULT, DISPATCH, FIRST_RESULT_NOT_HELD, RECONCILE_FIRST, RESYNC_IN_SYNC, RESYNC_NOW,
    RESYNC_WAIT, EnvelopeJournalEntry, EnvelopeResyncBackoff, EnvelopeResyncObservation, journal_decision,
    journal_intent, journal_outcome, journal_reconciliation, request_identity_digest, resync_decision)
from .slot_index import current_join_sources
from .slots import load_engine_slot_catalog

#: The modules that hold the envelope layers. The structure check reads their source.
ENVELOPE_MODULES = ("envelope.py", "envelope_tracking.py", "envelope_preflight.py", "envelope_coverage.py")
#: Imports that would start, open or schedule something; an envelope module imports none of them.
_FORBIDDEN_IMPORTS = ("threading", "asyncio", "concurrent", "subprocess", "socket", "sqlite3", "urllib",
                      "http", "multiprocessing", "sched")
_AT = "2026-10-16T12:00:00Z"
_COMPONENT = "fixture_component"


def _refused(build, code: "str | None" = None) -> bool:
    """Whether building or running something raises the typed envelope refusal (with the code, if named)."""
    try:
        build()
    except EnvelopeError as error:
        return code is None or error.code == code
    return False


def _sentence_refusal(code: str, retry: str = RETRY_AFTER_FIX, **changes) -> EnvelopeRefusal:
    return envelope_refusal(code, "The fixture step could not finish what it was asked to do.",
                            "Correct the fixture request as its record names, then send it again.", retry=retry,
                            **changes)


def _trace(steps, *, dispatched=False, refused_by="", refusal=None) -> EnvelopeTrace:
    return EnvelopeTrace(_COMPONENT, tuple(steps), dispatched, refused_by, refusal)


def _structure_findings(sources: dict) -> list:
    """What an envelope module must never hold: a forbidden import, a file open, a Loop or Node class."""
    found = []
    for name, text in sources.items():
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                modules = [alias.name for alias in node.names] if isinstance(node, ast.Import) else [node.module or ""]
                found += [f"{name}: imports {module}" for module in modules
                          if module.split(".")[0] in _FORBIDDEN_IMPORTS]
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("open", "exec",
                                                                                                    "eval"):
                found.append(f"{name}: calls {node.func.id}")
            elif isinstance(node, ast.ClassDef) and (node.name == "Loop" or node.name.endswith("Node")):
                found.append(f"{name}: defines {node.name}")
    return found


def _module_sources() -> dict:
    folder = os.path.dirname(os.path.abspath(__file__))
    sources = {}
    for name in ENVELOPE_MODULES:
        with open(os.path.join(folder, name), encoding="utf-8") as handle:
            sources[name] = handle.read()
    return sources


def _coverage_codes(catalog, coverage, baseline, sources, rules=COVERAGE_RULES) -> set:
    return {(item.slot_id, item.code) for item in coverage_findings(catalog, coverage, baseline, sources, rules)}


def _rules_without(name):
    return tuple(rule for rule in COVERAGE_RULES if rule[0] != name)


def _declaration(slot: EnvelopeSlotCoverage, layer: str, **changes) -> EnvelopeSlotCoverage:
    layers = tuple(replace(item, **changes) if item.layer == layer else item for item in slot.layers)
    return replace(slot, layers=layers)


def _with_slot(coverage, slot: EnvelopeSlotCoverage):
    return replace(coverage, slots=tuple(slot if item.slot_id == slot.slot_id else item for item in coverage.slots))


def _ratchet_holds(catalog, coverage, baseline, sources, rules) -> bool:
    """The condition of the baseline check, for one rule set: a lowered declaration, a gap hidden as not
    applicable and a lowered baseline are each reported."""
    levels = baseline.slots
    partial = next(slot for slot in coverage.slots if any(item.coverage == PARTIAL for item in slot.layers)
                   and slot.slot_id in levels)
    layer = next(item.layer for item in partial.layers if item.coverage == PARTIAL)
    lowered = _with_slot(coverage, _declaration(partial, layer, coverage=NONE, evidence=()))
    gap = next(slot for slot in coverage.slots if any(item.coverage == NONE for item in slot.layers)
               and slot.slot_id in levels)
    gap_layer = next(item.layer for item in gap.layers if item.coverage == NONE)
    hidden = _with_slot(coverage, _declaration(gap, gap_layer, coverage=NOT_APPLICABLE,
                                               reason=next(iter(coverage.reasons)), next_step=""))
    rows = {slot_id: dict(row) for slot_id, row in levels.items()}
    rows[partial.slot_id][layer] = NONE
    lowered_baseline = EnvelopeCoverageBaseline(baseline.recorded_on, MappingProxyType(
        {slot_id: MappingProxyType(row) for slot_id, row in rows.items()}))
    return ((partial.slot_id, "coverage_fell_below_baseline") in _coverage_codes(catalog, lowered, baseline, sources,
                                                                                 rules)
            and (gap.slot_id, "coverage_fell_below_baseline") in _coverage_codes(catalog, hidden, baseline, sources,
                                                                                 rules)
            and ("", "baseline_lowered_below_its_recorded_floor") in _coverage_codes(catalog, coverage,
                                                                                     lowered_baseline, sources, rules))


def _declarations_hold(catalog, coverage, baseline, sources, rules) -> bool:
    """The condition of the declaration check: a new slot without declarations, and a declared slot the
    catalogue does not hold, are each reported."""
    first = coverage.slots[0]
    without_first = replace(coverage, slots=coverage.slots[1:])
    stray = replace(coverage, slots=coverage.slots + (replace(first, slot_id="fixture_retired_slot"),))
    return ((first.slot_id, "slot_without_envelope_declarations") in _coverage_codes(catalog, without_first, baseline,
                                                                                    sources, rules)
            and ("fixture_retired_slot", "declaration_names_an_uncatalogued_slot")
            in _coverage_codes(catalog, stray, baseline, sources, rules))


def _handshake_checks(check) -> None:
    request = EnvelopeHandshakeRequest(_COMPONENT, ("fixture_request/v2", "fixture_request/v1"),
                                       ("profile:rdfs",), ("traces",), ("pure",))
    declared = EnvelopeHandshakeDeclaration("fixture_engine", ("fixture_request/v1",), ("profile:rdfs",), ("pure",))
    chosen = negotiate_handshake(request, declared)
    undeclared = negotiate_handshake(request, replace(declared, supported_versions=None))
    newer_only = negotiate_handshake(replace(request, requested_versions=("2.1.0",)),
                                     replace(declared, supported_versions=("2.0.0",)))
    forged = {**chosen.to_dict(), "supported_versions": ["fixture_request/v3"]}
    forged_unknown = {**undeclared.to_dict(), "verdict": "compatible", "selected_version": "fixture_request/v1",
                      "reasons": []}
    check("an_inferred_compatibility_is_refused",
          chosen.verdict == "compatible_with_degradation" and chosen.selected_version == "fixture_request/v1"
          and undeclared.verdict == "unknown" and not undeclared.proceeds
          and newer_only.verdict == "incompatible" and "no_mutually_supported_version" in newer_only.reasons
          and _refused(lambda: EnvelopeHandshakeVerdict.from_dict(forged), "inferred_compatibility_refused")
          and _refused(lambda: EnvelopeHandshakeVerdict.from_dict(forged_unknown), "inferred_compatibility_refused")
          and EnvelopeHandshakeVerdict.from_dict(chosen.to_dict()) == chosen,
          f"undeclared {undeclared.verdict}; 2.1.0 against 2.0.0 {newer_only.verdict}")

    def lenient(*_declarations):
        # Trust what the record claims instead of recomputing it from its declarations.
        return (chosen.verdict, chosen.selected_version, chosen.reasons, chosen.degraded_behavior)
    with patch.object(envelope_module, "_judge", lenient):
        accepted_without_guard = not _refused(lambda: EnvelopeHandshakeVerdict.from_dict(forged))
    check("removed_declared_match_requirement_is_detected",
          _refused(lambda: EnvelopeHandshakeVerdict.from_dict(forged)) and accepted_without_guard,
          "without the recomputed verdict a hand-written compatible record would pass")
    effectful = negotiate_handshake(request, replace(declared, effects=("network",)))
    granted = negotiate_handshake(replace(request, granted_effects=("network",)), replace(declared, effects=("network",)))
    missing = negotiate_handshake(replace(request, required_capabilities=("blank_nodes",)), declared)
    check("a_handshake_verdict_never_grants_and_names_what_it_ignored",
          effectful.verdict == "refused_by_policy" and effectful.reasons == ("effect_not_granted:network",)
          and granted.proceeds and chosen.degraded_behavior == ("advisory_capability_ignored:traces",)
          and missing.verdict == "incompatible" and missing.reasons == ("capability_missing:blank_nodes",)
          and _refused(lambda: EnvelopeHandshakeVerdict.from_dict({**chosen.to_dict(), "degraded_behavior": []})),
          f"network without a grant: {effectful.verdict}")


def _refusal_checks(check) -> None:
    good = _sentence_refusal("fixture_refused")
    check("a_refusal_without_a_next_action_is_refused",
          _refused(lambda: envelope_refusal("fixture_refused", good.message, "", retry=RETRY_AFTER_FIX),
                   "refusal_without_a_next_action")
          and _refused(lambda: envelope_refusal("fixture_refused", good.message, "Retry.", retry=RETRY_AFTER_FIX))
          and _refused(lambda: envelope_refusal("fixture_refused", "Fixture refused here, nothing more to say.",
                                                good.next_action, retry=RETRY_AFTER_FIX), "message_only_restates_the_code")
          and _refused(lambda: EnvelopeRefusal.from_dict({**good.to_dict(), "retry_statement": "Try again later."}),
                       "retry_statement_does_not_match_its_rule")
          and _refused(lambda: _sentence_refusal("fixture_refused", RETRY_AFTER_WAIT), "retry_wait_refused")
          and _sentence_refusal("fixture_refused", RETRY_AFTER_WAIT, retry_after_seconds=30).retry_after_seconds == 30
          and EnvelopeRefusal.from_dict(good.to_dict()) == good,
          good.retry_statement)
    check("an_uncertain_effect_reconciles_before_any_retry",
          all(_refused(lambda effect=effect: _sentence_refusal("fixture_refused", RETRY_NOW_SAME_IDENTITY,
                                                               effect_commitment=effect),
                       "an_uncertain_effect_reconciles_before_any_retry")
              for effect in (EFFECT_DURABLE_PENDING, EFFECT_UNKNOWN))
          and _sentence_refusal("fixture_refused", RECONCILE_BEFORE_RETRY,
                                effect_commitment=EFFECT_UNKNOWN).retry == RECONCILE_BEFORE_RETRY
          and _refused(lambda: _sentence_refusal("fixture_refused", RECONCILE_BEFORE_RETRY))
          and _refused(lambda: _sentence_refusal("fixture_refused", RETRY_NOW_SAME_IDENTITY,
                                                 effect_commitment="not_asserted", automatic_retry=True),
                       "automatic_retry_needs_no_effect"),
          "a pending or unknown effect never retries now, and only a refusal that wrote nothing retries itself")


def _recovery_checks(check) -> None:
    policy = EnvelopeRecoveryPolicy(_COMPONENT, 2, ("concurrent_update",))
    lost_race = _sentence_refusal("concurrent_update", RETRY_NOW_SAME_IDENTITY, automatic_retry=True)
    uncertain = _sentence_refusal("concurrent_update", RECONCILE_BEFORE_RETRY, effect_commitment=EFFECT_UNKNOWN)
    other = _sentence_refusal("other_failure", RETRY_NOW_SAME_IDENTITY, automatic_retry=True)
    frame = root_frame("fixture_parent", automatic_attempts=MAXIMUM_AUTOMATIC_ATTEMPTS)
    nested = enter_nested(frame, _COMPONENT)
    nested_policy = EnvelopeRecoveryPolicy("fixture_parent", 3, ("concurrent_update",))
    first, second, third = (may_recover(policy, lost_race, nested.allowance) for _ in range(3))
    parent_once = may_recover(nested_policy, lost_race, frame.allowance)
    parent_again = may_recover(nested_policy, lost_race, frame.allowance)
    check("bounded_recovery_never_repeats_an_effect_and_is_shared_by_nested_envelopes",
          first and second and not third and parent_once and not parent_again
          and nested.allowance is frame.allowance and frame.allowance.remaining == 0
          and not may_recover(policy, uncertain, RecoveryAllowance())
          and not may_recover(policy, other, RecoveryAllowance())
          and _refused(lambda: EnvelopeRecoveryPolicy(_COMPONENT, MAXIMUM_AUTOMATIC_ATTEMPTS + 1, ()))
          and _refused(lambda: EnvelopeRecoveryPolicy(_COMPONENT, 0, ("concurrent_update",))),
          f"nested two, parent one, of {MAXIMUM_AUTOMATIC_ATTEMPTS} shared attempts")


def _nesting_checks(check, catalog) -> None:
    frame = root_frame("fixture_0", deadline_at=100.0)
    for index in range(1, MAXIMUM_ENVELOPE_DEPTH + 1):
        frame = enter_nested(frame, f"fixture_{index}")
    depths = nesting_depths(catalog.slots)
    chain = tuple(SimpleNamespace(slot_id=f"fixture_{index}", nested_under=(f"fixture_{index - 1}",) if index else ())
                  for index in range(MAXIMUM_ENVELOPE_DEPTH + 2))
    deep = SimpleNamespace(slots=chain)
    # Through the rules tuple, so that a rule taken out of it leaves the planted chain unreported.
    bound_rules = tuple(item for item in COVERAGE_RULES if item[0] == "nesting_bound")
    check("recursion_past_the_depth_bound_is_refused",
          frame.depth == MAXIMUM_ENVELOPE_DEPTH
          and _refused(lambda: enter_nested(frame, "fixture_deeper"), "envelope_depth_exceeded")
          and _refused(lambda: enter_nested(frame, "fixture_2"), "envelope_cycle")
          and _refused(lambda: enter_nested(root_frame("fixture_0", deadline_at=1.0), "fixture_1", now=2.0),
                       "envelope_deadline_passed")
          and frame.remaining_seconds(40.0) == 60.0
          and max(depths.values()) <= MAXIMUM_ENVELOPE_DEPTH
          and [item.code for item in coverage_findings(deep, None, None, None, bound_rules)]
          == ["nesting_deeper_than_the_envelope_bound"],
          f"deepest catalogued slot {max(depths, key=depths.get)} at depth {max(depths.values())}")


def _trace_checks(check) -> None:
    refusal = _sentence_refusal("fixture_refused")
    everything = [(layer, LAYER_ACCEPTED) for layer in INBOUND_LAYERS]
    check("the_envelope_layers_keep_their_declared_order",
          _trace(everything, dispatched=True).engine_dispatched
          and _trace([(LAYER_HANDSHAKE, LAYER_REFUSED)], refused_by=LAYER_HANDSHAKE, refusal=refusal).refused_by
          and _trace([*everything[:3], (LAYER_TRACKING, LAYER_ANSWERED)]).steps[-1][1] == LAYER_ANSWERED
          and _trace(everything, dispatched=True, refused_by=ENGINE_SOURCE, refusal=refusal).refusal is refusal
          and _refused(lambda: _trace(everything[::-1], dispatched=True), "envelope_layers_out_of_order")
          and _refused(lambda: _trace([(LAYER_HANDSHAKE, LAYER_REFUSED), everything[3]], refused_by=LAYER_HANDSHAKE,
                                      refusal=refusal), "a_refused_layer_ends_the_trace")
          and _refused(lambda: _trace([(LAYER_HANDSHAKE, LAYER_REFUSED)], dispatched=True, refused_by=LAYER_HANDSHAKE,
                                      refusal=refusal), "a_refused_request_reached_the_engine")
          and _refused(lambda: _trace(everything[:3], dispatched=True), "the_engine_ran_before_every_layer")
          and _trace([(layer, LAYER_NOT_APPLICABLE) for layer in INBOUND_LAYERS], dispatched=True).engine_dispatched,
          f"inbound order {list(INBOUND_LAYERS)}")


def _journal_checks(check) -> None:
    identity = request_identity_digest("fixture-request-1")
    intent = journal_intent((), component=_COMPONENT, request_identity=identity, repeatable=False, at=_AT)
    done = journal_outcome((intent,), component=_COMPONENT, request_identity=identity, request_outcome="answered",
                           task_outcome="completed", effect_state="confirmed", result_digest="b" * 64, at=_AT)
    lost = journal_outcome((intent,), component=_COMPONENT, request_identity=identity,
                           request_outcome="deadline_exceeded", task_outcome="unknown", effect_state="unknown", at=_AT)
    nothing = journal_outcome((intent,), component=_COMPONENT, request_identity=identity, request_outcome="refused",
                              task_outcome="failed", effect_state="none", at=_AT)
    observed = journal_reconciliation((intent, lost), component=_COMPONENT, request_identity=identity,
                                      observed_effect_state="confirmed", result_digest="c" * 64, at=_AT)
    edited = {**done.to_dict(), "result_digest": "d" * 64}
    check("a_retry_of_a_confirmed_effect_is_answered_from_the_first_result",
          journal_decision((), identity).decision == DISPATCH
          and journal_decision((intent, done), identity).decision == ANSWER_FROM_FIRST_RESULT
          and journal_decision((intent, done), identity).result_digest == "b" * 64
          and journal_decision((intent,), identity).decision == RECONCILE_FIRST
          and journal_decision((intent, lost), identity).decision == RECONCILE_FIRST
          and journal_decision((intent, lost, observed), identity).decision == ANSWER_FROM_FIRST_RESULT
          and journal_decision((intent, nothing), identity).decision == DISPATCH
          and journal_decision((intent, nothing), identity).attempt == 2
          and _refused(lambda: journal_intent((intent, lost), component=_COMPONENT, request_identity=identity,
                                              repeatable=False, at=_AT), "dispatch_refused_by_the_journal")
          and _refused(lambda: EnvelopeJournalEntry.from_dict(edited), "journal_entry_digest_mismatch")
          and _refused(lambda: journal_reconciliation((intent, lost), component=_COMPONENT, request_identity=identity,
                                                      observed_effect_state="unknown", at=_AT),
                       "reconciliation_needs_an_observation")
          and _refused(lambda: journal_decision((done,), identity), "journal_chain_broken")
          and EnvelopeJournalEntry.from_dict(done.to_dict()) == done,
          "confirmed answers the first result; pending, unknown and interrupted reconcile first")
    no_bytes = journal_outcome((intent,), component=_COMPONENT, request_identity=identity, request_outcome="answered",
                               task_outcome="completed", effect_state="confirmed", at=_AT)
    repeatable = journal_intent((), component=_COMPONENT, request_identity=identity, repeatable=True, at=_AT)
    check("a_confirmed_effect_is_never_repeated_even_without_its_answer",
          journal_decision((intent, no_bytes), identity).decision == FIRST_RESULT_NOT_HELD
          and journal_decision((repeatable,), identity).decision == DISPATCH
          and journal_decision((repeatable,), identity).attempt == 2
          and _refused(lambda: request_identity_digest(" ")),
          "an answer that is gone is refused, never recomputed by running the effect again")
    backoff = EnvelopeResyncBackoff(60, 3600)
    check("an_unchanged_rejected_desired_state_waits_for_its_backoff",
          resync_decision(EnvelopeResyncObservation("release-b", "release-b"), backoff) == RESYNC_IN_SYNC
          and resync_decision(EnvelopeResyncObservation("release-b", "release-a", "release-b", 1, 5.0), backoff)
          == RESYNC_WAIT
          and resync_decision(EnvelopeResyncObservation("release-b", "release-a", "release-b", 1, 60.0), backoff)
          == RESYNC_NOW
          and resync_decision(EnvelopeResyncObservation("release-b", "release-a", "release-b", 9, 3599.0), backoff)
          == RESYNC_WAIT
          and resync_decision(EnvelopeResyncObservation("release-c", "release-a", "release-b", 9, 0.0), backoff)
          == RESYNC_NOW
          and _refused(lambda: resync_decision(EnvelopeResyncObservation("release-b", "release-a"),
                                               EnvelopeResyncBackoff(0, 10))),
          "three checks of one rejected release build once, and a changed release builds at once")


def _preflight_checks(check) -> None:
    def diagnosis(context):
        if context.get("ready"):
            return None
        return _sentence_refusal("fixture_not_ready", RETRY_NOW_SAME_IDENTITY)
    calls = []

    def mark_ready(context):
        calls.append(1)
        return {**context, "ready": True}
    readiness = EnvelopePreflightCheck("fixture_ready", ("fixture_not_ready",), diagnosis)
    pure = EnvelopeSelfRepair("fixture_recompute", ("fixture_not_ready",), ("pure",), 1, mark_ready)
    writing = EnvelopeSelfRepair("fixture_write_marker", ("fixture_not_ready",), ("writes_fs",), 1, mark_ready)
    ready = run_preflight(_COMPONENT, (readiness,), (pure,), {"ready": True})
    repaired = run_preflight(_COMPONENT, (readiness,), (pure,), {"ready": False})
    before = len(calls)
    refused = run_preflight(_COMPONENT, (readiness,), (writing,), {"ready": False})
    not_called = len(calls) == before
    granted = run_preflight(_COMPONENT, (readiness,), (writing,), {"ready": False},
                            EnvelopePreflightGrant(("writes_fs",)))
    check("a_repair_that_declares_an_effect_without_authority_is_refused",
          ready.verdict == VERDICT_READY and repaired.verdict == VERDICT_REPAIRED and repaired.context["ready"]
          and refused.verdict == VERDICT_REFUSED and not_called
          and refused.steps[0].outcome == STEP_REPAIR_REFUSED and refused.refusal.code == "fixture_not_ready"
          and granted.verdict == VERDICT_REPAIRED,
          refused.steps[0].detail)
    stubborn = EnvelopeSelfRepair("fixture_noop", ("fixture_not_ready",), ("pure",), 1, lambda context: context)
    stays = run_preflight(_COMPONENT, (readiness,), (stubborn,), {"ready": False})
    undeclared = EnvelopePreflightCheck("fixture_other", ("fixture_other_code",), diagnosis)
    check("a_self_repair_is_declared_bounded_and_checked_again",
          stays.verdict == VERDICT_REFUSED and stays.steps[0].detail == "still_failing_after_repair"
          and _refused(lambda: run_preflight(_COMPONENT, (undeclared,), (), {}), "undeclared_diagnosis")
          and _refused(lambda: EnvelopeSelfRepair("fixture_bad", ("fixture_not_ready",), ("pure", "network"), 1,
                                                  mark_ready), "repair_declaration_incomplete")
          and _refused(lambda: EnvelopeSelfRepair("fixture_bad", ("fixture_not_ready",), ("pure",), 3, mark_ready))
          and _refused(lambda: run_preflight(_COMPONENT, (readiness,), (pure, writing), {}),
                       "two_repairs_for_one_diagnosis"),
          "a repair that does not fix its check ends the preflight with the check's refusal")


def _coverage_checks(check, catalog) -> None:
    coverage, baseline, sources = load_envelope_coverage(), load_envelope_coverage_baseline(), current_join_sources()
    report = coverage_report(catalog, coverage, baseline, sources)
    check("every_engine_slot_declares_every_envelope_layer",
          report["valid"] and report["slot_count"] == len(catalog.slots)
          and [slot.slot_id for slot in coverage.slots] == [slot.slot_id for slot in catalog.slots]
          and _declarations_hold(catalog, coverage, baseline, sources, COVERAGE_RULES)
          and _refused(lambda: EnvelopeSlotCoverage("fixture_slot", coverage.slots[0].layers[:-1]),
                       "layer_declaration_missing"),
          f"{report['slot_count']} slots; totals {report['totals']}; findings {report['findings'][:3]}")
    check("removed_declaration_join_is_detected",
          _declarations_hold(catalog, coverage, baseline, sources, COVERAGE_RULES)
          and not _declarations_hold(catalog, coverage, baseline, sources, _rules_without("declarations_join")),
          "without the join a new slot with no declarations would pass")
    check("envelope_layer_coverage_never_falls_below_its_baseline",
          _ratchet_holds(catalog, coverage, baseline, sources, COVERAGE_RULES)
          and all(baseline.totals()[name] >= floor for name, floor in RECORDED_BASELINE_FLOOR.items()),
          f"baseline {baseline.recorded_on} totals {baseline.totals()}; floor {dict(RECORDED_BASELINE_FLOOR)}")
    check("removed_baseline_ratchet_is_detected",
          _ratchet_holds(catalog, coverage, baseline, sources, COVERAGE_RULES)
          and not _ratchet_holds(catalog, coverage, baseline, sources, _rules_without("baseline_ratchet")),
          "without the ratchet a lowered declaration would pass")
    slot = next(item for item in coverage.slots if any(layer.coverage == PARTIAL for layer in item.layers))
    layer = next(item.layer for item in slot.layers if item.coverage == PARTIAL)
    ghost = _with_slot(coverage, _declaration(slot, layer, evidence=("core.no_such_module.NoSuchSymbol",)))
    unchecked_full = _with_slot(coverage, _declaration(slot, layer, coverage=FULL, next_step="",
                                                       evidence=("core.engines.envelope.envelope_refusal",)))
    parent = next(item for item in coverage.slots if item.layer(COVERAGE_LAYERS[-1]).coverage == NONE)
    hidden_parent = _with_slot(coverage, _declaration(parent, COVERAGE_LAYERS[-1], coverage=NOT_APPLICABLE,
                                                      reason="no_nested_slot", next_step=""))
    run_time = next(item for item in coverage.slots if not next(
        record for record in catalog.slots if record.slot_id == item.slot_id).is_release_time)
    released = _with_slot(coverage, _declaration(run_time, "carrier", coverage=NOT_APPLICABLE, evidence=(),
                                                 reason="release_time_slot", next_step=""))
    check("covered_layers_name_evidence_that_resolves_and_reasons_that_hold",
          (slot.slot_id, "evidence_does_not_resolve") in _coverage_codes(catalog, ghost, baseline, sources)
          and (slot.slot_id, "full_coverage_names_no_check") in _coverage_codes(catalog, unchecked_full, baseline,
                                                                                sources)
          and (parent.slot_id, "reason_contradicts_the_catalogue") in _coverage_codes(catalog, hidden_parent,
                                                                                      baseline, sources)
          and (run_time.slot_id, "reason_contradicts_the_catalogue") in _coverage_codes(catalog, released, baseline,
                                                                                        sources)
          and _refused(lambda: EnvelopeLayerCoverage("carrier", PARTIAL), "coverage_without_evidence")
          and _refused(lambda: EnvelopeLayerCoverage("carrier", NOT_APPLICABLE), "not_applicable_needs_a_reason")
          and _refused(lambda: EnvelopeLayerCoverage("courtesy", NONE), "unknown_envelope_layer"),
          f"{len(coverage.reasons)} named reasons")
    rows = {slot_id: row for slot_id, row in baseline.slots.items() if slot_id != slot.slot_id}
    without_row = EnvelopeCoverageBaseline(baseline.recorded_on, MappingProxyType(rows))
    gaps = [item for item in slot.layers if item.coverage == NONE]
    named = _with_slot(coverage, replace(slot, layers=tuple(replace(item, next_step="S-6.30")
                                                            if item.coverage == NONE else item
                                                            for item in slot.layers)))
    check("a_new_slot_names_the_step_that_closes_each_gap",
          (not gaps or (slot.slot_id, "new_slot_gap_names_no_next_step")
           in _coverage_codes(catalog, coverage, without_row, sources))
          and (slot.slot_id, "new_slot_gap_names_no_next_step") not in _coverage_codes(catalog, named, without_row,
                                                                                       sources)
          and _refused(lambda: EnvelopeLayerCoverage("carrier", FULL, ("core.engines.envelope",), "", "S-6.30"),
                       "invalid_next_step"),
          f"{slot.slot_id} as a new slot has {len(gaps)} gaps")


def self_test() -> dict:
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": str(detail)[:400]})

    catalog = load_engine_slot_catalog()
    _trace_checks(check)
    _handshake_checks(check)
    _refusal_checks(check)
    _recovery_checks(check)
    _nesting_checks(check, catalog)
    _journal_checks(check)
    _preflight_checks(check)
    _coverage_checks(check, catalog)
    planted = {"planted.py": "import threading\nclass StepNode:\n    pass\nopen('x')\n"}
    found = _structure_findings(_module_sources())
    check("the_envelope_modules_start_nothing_and_keep_no_registry",
          not found and len(_structure_findings(planted)) == 3
          and all(not hasattr(envelope_module, name) for name in ("REGISTRY", "ENGINES", "SCHEDULER")),
          f"findings {found}; planted {_structure_findings(planted)}")
    extra = {**_sentence_refusal("fixture_refused").to_dict(), "hint": "x"}
    newer = {**_sentence_refusal("fixture_refused").to_dict(), "record_type": "envelope_refusal/v2"}
    check("the_envelope_records_refuse_unknown_keys_and_other_versions",
          _refused(lambda: EnvelopeRefusal.from_dict(extra), "unknown_record_fields")
          and _refused(lambda: EnvelopeRefusal.from_dict(newer), "unsupported_record_version")
          and _refused(lambda: EnvelopeHandshakeVerdict.from_dict({"record_type": "envelope_handshake_verdict/v2"}),
                       "unsupported_record_version")
          and _refused(lambda: EnvelopeJournalEntry.from_dict({"record_type": "envelope_journal_entry/v1"}),
                       "missing_record_fields"),
          "another version or an unknown field is refused before anything is built")
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "envelope_checks/v1", "tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
