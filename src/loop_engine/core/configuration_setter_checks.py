"""Offline setting-resolution and atomic-application controls.

Includes a fixture gateway invocation to check actual field propagation.
No real provider, native harness configuration, or task quality is tested.
"""
from dataclasses import dataclass, replace
from datetime import datetime, timezone
import json

from .configuration_capabilities import (
    ConfigurationCapabilityError, ConfigurationFact, ConfigurationSettingSpec,
    ConfigurationTargetSpec, describe_configuration, digest)
from .configuration_setters import (
    ConfigurationSetterContext, ConfigurationSettingChange, ConfigurationUpdateRequest,
    ConfigurationValueCandidate, ConfigurationWriteAuthority, apply_configuration_as_loop)
from .parameter_resolution import (
    ParameterDefinition, ParameterInput, ParameterIntelligenceProposal,
    ParameterSource, ParameterSourceKind)

NOW = datetime(2026, 9, 13, tzinfo=timezone.utc)


def fact(state, **changes):
    return replace(ConfigurationFact(state, "offline-contract-fixture@1.0.0", digest(state)), **changes)


def setting(name, semantic_type="number", **changes):
    parameter = ParameterDefinition(name, name, "Offline setting fixture", semantic_type,
        "fixture-owner@1.0.0", "request", nullable=True,
        intelligence_allowed=True, minimum_intelligence_confidence=0.0)
    base = ConfigurationSettingSpec.from_parameter(parameter, name,
        support=fact("supported"), availability=fact("available"), qualification=fact("qualified"),
        writable=True, phases=("before_initialization", "per_request"))
    return replace(base, **changes)


def target(*settings):
    return ConfigurationTargetSpec("fixture-request@1.0.0", settings,
                                    "fixture-owner@1.0.0", digest("fixture-owner"), "local")


def authority(spec, kind=ParameterSourceKind.LOOP_PROFILE, **changes):
    return replace(ConfigurationWriteAuthority(spec.target_ref,
        tuple(s.parameter_id for s in spec.settings), kind, "fixture-source@1.0.0", "1.0.0"), **changes)


def proposal(value, **changes):
    return replace(ParameterIntelligenceProposal(ParameterInput.from_value(value), 0.0,
        ("fixture-evidence@1.0.0",), (), (), (), False, "", "fixture-validator@1.0.0",
        "intelligence.context.frame@1.0.0", "offline-proposal@1.0.0",
        "fixture-prompt@1.0.0", digest("fixture-context")), **changes)


def request(spec, current, changes, **overrides):
    view = describe_configuration(spec, current, at=NOW)
    return replace(ConfigurationUpdateRequest(view["target_digest"], view["values_digest"],
        tuple(ConfigurationSettingChange(name, tuple(ConfigurationValueCandidate(ParameterInput.from_value(v))
                                                     for v in values))
              for name, values in changes), "per_request", "non_deterministic"), **overrides)


def run_checks():
    tests = []
    def check(name, passed):
        tests.append({"name": name, "passed": bool(passed)})
    def refuses(name, fn):
        try:
            fn()
        except (ValueError, TypeError):
            check(name, True)
        else:
            check(name, False)

    @dataclass(frozen=True)
    class Values:
        temperature: float = 0.7
        enabled: bool = True
        optional: object = "value"
        resources: tuple = ("initial",)

    current = Values()
    spec = target(setting("temperature"), setting("enabled", "boolean"),
                  setting("optional", "any"), setting("resources", "text_sequence", value_codec="tuple"))
    def apply(req, chosen=spec, current=current, grant=None, prior=()):
        return apply_configuration_as_loop(req, ConfigurationSetterContext(chosen, current,
            grant or authority(chosen), NOW, prior))

    initial = request(spec, current, (("temperature", (0,)), ("enabled", (False,)),
                                      ("optional", (None,)), ("resources", ([],))))
    result, run = apply(initial)
    check("configuration_setter_uses_canonical_loop", run["loop_id"].startswith("loop")
          and run["loop_definition_id"] and run["model_calls"] == 0)
    check("zero_false_null_and_empty_are_not_omitted", result.configuration == Values(0, False, None, ()))
    check("original_configuration_is_not_mutated", current == Values())
    check("configuration_change_is_not_an_execution_or_approval", result.report["status"] == "applied_in_memory"
          and result.report["qualification_invalidated"] and not result.report["dispatch_performed"]
          and not result.report["effect_authority_granted"] and not result.report["native_harness_reconfigured"])
    unchanged, _ = apply(request(spec, current, (("temperature", (0.7,)),)))
    check("unchanged_setting_does_not_invalidate_qualification", unchanged.report["status"] == "unchanged"
          and not unchanged.report["qualification_invalidated"])
    for name, modified in (("stale_values", replace(initial, expected_values_digest=digest("stale"))),
                           ("different_target", replace(initial, expected_target_digest=digest("other")))):
        rejected, _ = apply(modified)
        check(name + "_refuses_atomically", rejected.configuration is current
              and rejected.report["rejections"][0]["reason"] == "stale_or_different_target")
    incomplete, _ = apply(initial, grant=authority(spec, allowed_parameter_ids=("temperature",)))
    check("one_unauthorized_field_prevents_partial_application", incomplete.configuration is current
          and incomplete.report["status"] == "rejected")
    unknown, _ = apply(request(spec, current, (("not_a_setting", (1,)),)))
    check("unknown_fields_cannot_create_settings", unknown.report["rejections"][0]["reason"] == "unknown_setting")
    for name, modified in (
        ("unsupported", replace(spec.settings[0], support=fact("unsupported"))),
        ("unknown_support", replace(spec.settings[0], support=ConfigurationFact())),
        ("unavailable", replace(spec.settings[0], availability=fact("unavailable"))),
        ("unqualified", replace(spec.settings[0], qualification=fact("unqualified"))),
        ("expired", replace(spec.settings[0], availability=fact("available", expires_at="2026-09-12T00:00:00Z"))),
        ("read_only", replace(spec.settings[0], writable=False)),
        ("authority_bearing", replace(spec.settings[0], authority_bearing=True)),
        ("wrong_phase", replace(spec.settings[0], phases=("before_initialization",))),
        ("wrong_mode", replace(spec.settings[0], run_modes=("deterministic",)))):
        constrained = replace(spec, settings=(modified, *spec.settings[1:]))
        rejected, _ = apply(request(constrained, current, (("temperature", (0,)),)), chosen=constrained)
        check(name + "_is_refused", rejected.configuration is current and rejected.report["status"] == "rejected")
    experimental = replace(spec, settings=(replace(spec.settings[0], qualification=ConfigurationFact(),
                                                  availability=ConfigurationFact()), *spec.settings[1:]))
    changed, _ = apply(request(experimental, current, (("temperature", (0.1,)),)), chosen=experimental,
                      grant=authority(experimental, allow_unqualified=True, allow_unavailable=True))
    check("explicit_experiment_can_stage_an_unqualified_unavailable_setting",
          changed.report["status"] == "applied_in_memory" and not changed.report["dispatch_performed"])
    parameter = replace(spec.settings[0].parameter(), constraints={"minimum": 0, "maximum": 1},
                        default_input=ParameterInput.from_value(0.5))
    constrained = replace(spec, settings=(ConfigurationSettingSpec.from_parameter(parameter, "temperature",
        support=fact("supported"), availability=fact("available"), qualification=fact("qualified"),
        writable=True, phases=("per_request",)), *spec.settings[1:]))
    fallback = request(constrained, current, (("temperature", (4, 0.2)),))
    changed, _ = apply(fallback, chosen=constrained)
    check("ordered_alternative_is_tried_before_repository_default", changed.configuration.temperature == 0.2
          and len(changed.report["attempts"]) == 2)
    rejected, _ = apply(fallback, chosen=constrained,
                        grant=authority(constrained, ParameterSourceKind.EXPLICIT_INVOCATION))
    check("invalid_explicit_pin_cannot_fallback", rejected.configuration is current
          and len(rejected.report["attempts"]) == 1)
    pinned = ParameterSource(ParameterSourceKind.EXPLICIT_INVOCATION,
        "fixture-explicit-pin@1.0.0", "1.0.0", ParameterInput.from_value(0.9))
    changed, _ = apply(fallback, chosen=constrained, prior=(("temperature", pinned),))
    check("higher_priority_explicit_pin_wins", changed.configuration.temperature == 0.9)
    intelligent = ConfigurationValueCandidate(ParameterInput.from_value(0.1), proposal(0.1))
    inferred = replace(initial, changes=(ConfigurationSettingChange("temperature", (intelligent,)),))
    changed, inferred_run = apply(inferred, grant=authority(spec, ParameterSourceKind.INTELLIGENCE_PROPOSAL))
    check("explicit_zero_confidence_threshold_is_preserved", changed.configuration.temperature == 0.1
          and inferred_run["model_calls"] == 0)
    changed, _ = apply(inferred, grant=authority(spec, ParameterSourceKind.INTELLIGENCE_PROPOSAL),
                       prior=(("temperature", pinned),))
    check("agent_proposal_cannot_override_user_pin", changed.configuration.temperature == 0.9)
    default_request = replace(inferred, expected_target_digest=constrained.content_digest)
    changed, _ = apply(default_request, chosen=constrained,
                       grant=authority(constrained, ParameterSourceKind.INTELLIGENCE_PROPOSAL))
    check("repository_default_keeps_precedence_over_agent_proposal", changed.configuration.temperature == 0.5)
    rejected, _ = apply(initial, grant=authority(spec, ParameterSourceKind.INTELLIGENCE_PROPOSAL))
    check("agent_proposal_source_cannot_use_an_untyped_value", rejected.report["status"] == "rejected")
    raw = ["selected"]
    candidate = ConfigurationValueCandidate(ParameterInput.from_value(raw))
    raw.append("not-selected")
    alias_request = replace(initial, changes=(ConfigurationSettingChange("resources", (candidate,)),))
    changed, _ = apply(alias_request)
    check("candidate_values_are_frozen_at_construction", changed.configuration.resources == ("selected",))
    sensitive = replace(spec, settings=(ConfigurationSettingSpec.from_parameter(
        replace(spec.settings[2].parameter(), sensitivity="sensitive"), "optional",
        support=fact("supported"), availability=fact("available"), qualification=fact("qualified"),
        writable=True, phases=("per_request",)),))
    private = replace(current, optional="private-existing-value")
    changed, _ = apply(request(sensitive, private, (("optional", ("private-new-value",)),)),
                       chosen=sensitive, current=private)
    safe = json.dumps(changed.report)
    check("sensitive_values_are_absent_from_change_reports",
          "private-existing-value" not in safe and "private-new-value" not in safe)
    for name, invalid in (("nan", float("nan")), ("infinity", float("inf")), ("opaque", object())):
        refuses("non_json_or_nonfinite_candidate_refused_" + name,
                lambda invalid=invalid: ConfigurationValueCandidate(ParameterInput.from_value(invalid)))
    refuses("fact_axes_are_not_interchangeable", lambda: replace(spec.settings[0], support=fact("available")))
    refuses("unknown_fact_state_is_not_inferred", lambda: ConfigurationFact("probably_supported"))
    refuses("known_fact_needs_a_source", lambda: ConfigurationFact("supported"))
    refuses("naive_fact_time_refused", lambda: fact("available").current_state(datetime(2026, 9, 13)))
    refuses("dataclass_type_is_not_a_configuration", lambda: describe_configuration(spec, Values, at=NOW))
    _invocation_checks(check)
    _review_checks(check, refuses, spec, current, apply, Values)
    return {"tests": tests, "passed": sum(t["passed"] for t in tests), "total": len(tests),
            "all_passed": all(t["passed"] for t in tests)}


def _invocation_checks(check):
    from ..code_nodes.solution_model_port import ModelExecution, ModelInvocationRequest
    from ..loop.recursive_loop import Loop
    from .model_capabilities import ModelOutputCapability
    from .model_gateway import ModelGateway, ModelGatewayConfig, ProviderSpec
    from .model_routes import ModelRoute, RoutePolicy
    from .ollama_client import ChatResult
    captured = []
    class Adapter:
        DEFAULT_MODEL = "configuration-fixture-model"
        @staticmethod
        def output_capability_for(model=""):
            return ModelOutputCapability(64, "offline configuration fixture contract")
        @staticmethod
        def chat_maxout(prompt, **kwargs):
            captured.append(kwargs)
            return ChatResult("fixture response", Adapter.DEFAULT_MODEL, prompt_tokens=2, eval_tokens=3, ok=True)
        @staticmethod
        def verify(model=""):
            return {"ok": True}
        @staticmethod
        def live_models():
            return [Adapter.DEFAULT_MODEL]
    original = ModelInvocationRequest("Public fixture prompt", temperature=0.7)
    spec = target(setting("temperature"))
    req = request(spec, original, (("temperature", (0.0,)),))
    changed, _ = apply_configuration_as_loop(req, ConfigurationSetterContext(spec, original, authority(spec), NOW))
    gateway = ModelGateway(providers=(ProviderSpec("configuration-fixture", Adapter,
        "offline_fixture", "not_required", locality="local"),), routes=(ModelRoute(
            "configuration.fixture", "configuration-fixture", Adapter.DEFAULT_MODEL, "local",
            purposes=("counted_generation",)),), policy=RoutePolicy(allow_local_counted_generation=True))
    execution = ModelExecution(gateway, ModelGatewayConfig(route_names=("configuration.fixture",),
        allowed_localities=("local",), allow_failover=False), max_model_calls=1)
    answer = execution.start_session().invoke(changed.configuration, Loop("offline setter invocation"))
    check("resolved_setting_reaches_existing_gateway_invocation", answer == "fixture response"
          and len(captured) == 1 and captured[0]["temperature"] == 0.0 and original.temperature == 0.7)
    # The target constructor remains authoritative even when a generic
    # parameter definition accidentally permits a bad value.
    invalid = request(spec, original, (("temperature", (None,)),))
    refused, _ = apply_configuration_as_loop(invalid, ConfigurationSetterContext(spec, original, authority(spec), NOW))
    check("target_constructor_can_refuse_without_partial_change", refused.configuration is original
          and refused.report["rejections"][0]["reason"] == "target_constructor_refused_configuration")


def _review_checks(check, refuses, spec, current, apply, Values):
    """Checks added after the 2026-09-13 review: abstentions change nothing,
    a change governed by a higher source says so, constructors that coerce
    or raise are typed refusals, records are portable, and facts are typed."""
    import json
    agent = authority(spec, ParameterSourceKind.INTELLIGENCE_PROPOSAL)
    abstained = ConfigurationValueCandidate(ParameterInput.from_value(0.1),
        proposal(0.1, abstained=True, rejection_reason="no evidence for this task"))
    abstention = replace(request(spec, current, (("temperature", (0.1,)),)),
                         changes=(ConfigurationSettingChange("temperature", (abstained,)),))
    refused, _ = apply(abstention, grant=agent)
    check("an_abstained_proposal_changes_nothing",
          refused.configuration is current and refused.report["status"] == "rejected"
          and refused.report["rejections"][0]["reason"] == "proposal_abstained"
          and refused.report["attempts"] == [])
    pinned = ParameterSource(ParameterSourceKind.EXPLICIT_INVOCATION,
        "fixture-explicit-pin@1.0.0", "1.0.0", ParameterInput.from_value(0.9))
    proposed = replace(request(spec, current, (("temperature", (0.1,)),)),
                       changes=(ConfigurationSettingChange("temperature", (ConfigurationValueCandidate(
                           ParameterInput.from_value(0.1), proposal(0.1)),)),))
    governed, _ = apply(proposed, grant=agent, prior=(("temperature", pinned),))
    check("a_change_governed_by_a_higher_source_is_reported_as_such",
          governed.configuration.temperature == 0.9
          and governed.report["status"] == "applied_by_precedence"
          and governed.report["governing_sources"] == {"temperature": "explicit_invocation"}
          and governed.report["requester_candidate_selected"] is False
          and governed.report["attempts"][0]["proposal_supplied"] is True)
    own, _ = apply(proposed, grant=agent)
    check("a_requesters_own_candidate_is_reported_as_applied",
          own.configuration.temperature == 0.1 and own.report["status"] == "applied_in_memory"
          and own.report["governing_sources"] == {"temperature": "intelligence_proposal"}
          and own.report["requester_candidate_selected"] is True
          and own.report["model_call_performed_by_boundary"] is False
          and own.report["changed_settings"] == ["temperature"])

    @dataclass(frozen=True)
    class Clamping(Values):
        def __post_init__(self):
            if self.temperature > 1:
                object.__setattr__(self, "temperature", 1.0)
    clamped = Clamping()
    coerced, _ = apply(request(spec, clamped, (("temperature", (4,)),)), current=clamped)
    check("a_constructor_that_coerces_the_value_is_refused",
          coerced.configuration is clamped and coerced.report["status"] == "rejected"
          and coerced.report["rejections"][0]["reason"] == "constructor_coerced_value")

    @dataclass(frozen=True)
    class Hot(Values):
        def __post_init__(self):
            if self.temperature > 1:
                raise RuntimeError("too hot")
    hot = Hot()
    raised, _ = apply(request(spec, hot, (("temperature", (4,)),)), current=hot)
    check("a_constructor_exception_of_any_class_is_a_typed_refusal",
          raised.configuration is hot
          and raised.report["rejections"][0] == {"reason": "target_constructor_refused_configuration",
                                                 "exception_type": "RuntimeError"})

    @dataclass(frozen=True)
    class Partial:
        temperature: float = 0.7
    absent, _ = apply(replace(request(spec, current, (("temperature", (0.2,)),))), current=Partial())
    check("a_declared_field_absent_from_the_instance_is_a_typed_refusal",
          absent.report["status"] == "rejected" and absent.report["rejections"][0]["reason"] == "target_field_absent")
    unflagged = replace(spec, settings=(ConfigurationSettingSpec.from_parameter(
        replace(spec.settings[0].parameter(), affects_qualification=False), "temperature",
        support=fact("supported"), availability=fact("available"), qualification=fact("qualified"),
        writable=True, phases=("per_request",)), *spec.settings[1:]))
    quiet, _ = apply(request(unflagged, current, (("temperature", (0.2,)),)), chosen=unflagged)
    check("qualification_invalidation_honours_the_parameter_flag",
          quiet.report["status"] == "applied_in_memory" and quiet.report["qualification_invalidated"] is False
          and quiet.report["invalidated_settings"] == [] and quiet.report["changed_settings"] == ["temperature"])
    for name, constraints in (("string_minimum", {"minimum": "0"}), ("integer_allowed_values", {"allowed_values": 3}),
                              ("text_non_empty", {"non_empty": "yes"}), ("boolean_maximum", {"maximum": True})):
        refuses(f"a_{name}_constraint_is_refused_at_spec_construction",
                lambda constraints=constraints: ConfigurationSettingSpec.from_parameter(
                    replace(spec.settings[0].parameter(), constraints=constraints), "temperature"))
    same = ConfigurationFact("available", "fixture-source@1.0.0", digest("x"), "2026-09-13T20:00:00Z")
    check("an_expiry_is_normalized_so_one_instant_has_one_spelling",
          same == ConfigurationFact("available", "fixture-source@1.0.0", digest("x"), "2026-09-13T20:00:00+00:00")
          and same.expires_at == "2026-09-13T20:00:00+00:00")
    refuses("a_non_text_expiry_is_refused", lambda: ConfigurationFact("available", "s@1.0.0", digest("x"), 5))
    refuses("a_malformed_expiry_is_refused", lambda: ConfigurationFact("available", "s@1.0.0", digest("x"), "soon"))
    refuses("non_text_fact_references_are_refused", lambda: ConfigurationFact("unknown", 123, object()))
    check("setting_and_target_records_are_json_plain",
          json.loads(json.dumps(spec.to_dict())) == spec.to_dict())
