"""Adversarial checks for Loop definitions and runtime contexts.

These deterministic checks cover forged profiles, changed digests, missing
services, role conflicts, strict starts, and semantic executor refusal.
"""
from __future__ import annotations

from .loop_contract import LoopContract
from .loop_definition import (LoopDefinition, LoopDefinitionError,
                              LoopStartRequest)
from .loop_role import LoopRelationship, LoopRole, LoopRoleIdentity
from .recursive_loop import (Loop, LoopConfig, LoopExecutorUnavailableError,
                             LoopLedger, StepOutcome)
from .runtime_context import (IntelligenceSearchRetrievalPort,
                              InternalRuntimeBinding,
                              InternalRuntimeMechanics,
                              LoopRuntimeContext)


def _definition(*, profile_id="practitioner.reference_nine_step",
                role=LoopRole.PRACTITIONER,
                modes=("deterministic",), installed=("deterministic",),
                contract_role="") -> LoopDefinition:
    execution_mode = (
        "model_led" if "non_deterministic" in modes
        else "hybrid" if "hybrid" in modes else "code_only")
    config = LoopConfig(
        allowable_modes=modes, preferred_modes=modes,
        llm_thinking_power=("medium" if execution_mode != "code_only" else ""))
    return LoopDefinition.from_runtime(
        identity=LoopRoleIdentity(role, profile_id),
        contract=LoopContract(
            name="check one definition", execution_mode=execution_mode,
            input_roles=("request",), output_roles=("result",),
            role=contract_role or role.value),
        config=config, installed_executor_modes=installed)


def _strict_context(definition: LoopDefinition) -> LoopRuntimeContext:
    binding = InternalRuntimeBinding(
        "definition_check", object(), definition.required_capabilities)
    return LoopRuntimeContext(internal=InternalRuntimeMechanics(
        bindings=(binding,), permissions=definition.permissions,
        executor_modes=definition.installed_executor_modes))


def self_test() -> dict:
    tests: list[dict] = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    definition = _definition()
    restored = LoopDefinition.from_dict(definition.to_dict())
    check("definition_roundtrip_preserves_exact_digest",
          restored == definition and restored.ref == definition.ref)

    tampered = definition.to_dict()
    tampered["configuration_facts"]["max_depth"] = 99
    digest_refused = False
    try:
        LoopDefinition.from_dict(tampered)
    except LoopDefinitionError:
        digest_refused = True
    check("definition_digest_mismatch_is_refused", digest_refused)

    forged_profile = False
    try:
        _definition(profile_id="practitioner.forged")
    except LoopDefinitionError:
        forged_profile = True
    check("forged_profile_is_refused", forged_profile)

    abstract_profile = False
    try:
        _definition(profile_id="practitioner")
    except LoopDefinitionError:
        abstract_profile = True
    check("abstract_profile_cannot_define_a_runnable_loop", abstract_profile)

    role_mismatch = False
    try:
        _definition(contract_role="solution")
    except LoopDefinitionError:
        role_mismatch = True
    check("role_and_contract_mismatch_is_refused", role_mismatch)

    intelligence_definition = LoopDefinition.from_runtime(
        identity=LoopRoleIdentity(
            LoopRole.INTELLIGENCE, "intelligence.context.serve"),
        contract=LoopContract(
            name="serve selected context", execution_mode="code_only",
            input_roles=("intelligence_reference",),
            output_roles=("context_intelligence",), role="intelligence"),
        config=LoopConfig(
            framework="custom", custom_steps=("serve",),
            allowable_modes=("deterministic",),
            preferred_modes=("deterministic",),
            exit_condition="accepted_success"),
        installed_executor_modes=("deterministic",))
    missing_service = False
    try:
        LoopStartRequest(
            "serve selected context", intelligence_definition,
            LoopRelationship.starting(), LoopRuntimeContext(), LoopLedger())
    except LoopDefinitionError:
        missing_service = True
    check("missing_required_service_fails_before_execution", missing_service)

    intelligence_context = LoopRuntimeContext(
        intelligence_search_retrieval=IntelligenceSearchRetrievalPort(
            "check_intelligence", object(),
            intelligence_definition.required_capabilities),
        internal=InternalRuntimeMechanics(
            executor_modes=("deterministic",)))
    intelligence_loop = Loop(LoopStartRequest(
        "serve selected context", intelligence_definition,
        LoopRelationship.starting(), intelligence_context, LoopLedger()))
    intelligence_loop.run(handler=lambda loop, step, context: StepOutcome(
        "served", mode="deterministic"))
    check("strict_context_starts_role_correct_intelligence_loop",
          intelligence_loop.identity.role is LoopRole.INTELLIGENCE
          and intelligence_loop.definition_ref == intelligence_definition.ref)

    semantic_definition = _definition(
        modes=("non_deterministic",), installed=("non_deterministic",))
    semantic_loop = Loop(LoopStartRequest(
        "interpret an open question", semantic_definition,
        LoopRelationship.starting(), _strict_context(semantic_definition),
        LoopLedger()))
    executor_missing = False
    try:
        semantic_loop.run()
    except LoopExecutorUnavailableError:
        executor_missing = True
    check("semantic_mode_never_uses_the_structural_handler", executor_missing)

    public_keys = set(intelligence_context.public_static_architecture())
    check("runtime_context_has_exactly_three_public_service_ports",
          public_keys == {"intelligence_search_retrieval", "web_research",
                          "custom_plugins"})

    strict_loop = Loop(LoopStartRequest(
        "strict deterministic work", definition,
        LoopRelationship.starting(), _strict_context(definition), LoopLedger()))
    strict_loop.run()
    check("every_runtime_event_carries_the_definition_reference",
          all(event.get("loop_definition_id") == definition.definition_id
              and event.get("loop_definition_version") == definition.version
              and event.get("loop_definition_digest") == definition.content_digest
              for event in strict_loop.ledger.events
              if event.get("loop_id") == strict_loop.loop_id))

    spawned = strict_loop.spawn(
        "bounded verification", definition=definition)
    check("spawned_loop_receives_a_derived_runtime_context",
          spawned.runtime_context is not strict_loop.runtime_context
          and spawned.runtime_context.available_capabilities
          == frozenset(definition.required_capabilities)
          and spawned.runtime_context.internal.permissions
          == tuple(definition.permissions))

    passed = sum(1 for test in tests if test["passed"])
    return {"record_type": "loop_definition_checks/v1", "tests": tests,
            "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}


if __name__ == "__main__":
    result = self_test()
    print(f"{result['passed']}/{result['total']} checks passed")
    raise SystemExit(0 if result["all_passed"] else 1)
