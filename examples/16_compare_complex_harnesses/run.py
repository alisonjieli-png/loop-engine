"""Validate source-backed harness evidence inside one deterministic Loop."""

import json

from loop_engine import (
    CustomPluginsPort,
    InternalRuntimeBinding,
    InternalRuntimeMechanics,
    Loop,
    LoopConfig,
    LoopContract,
    LoopDefinition,
    LoopLedger,
    LoopRelationship,
    LoopRoleIdentity,
    LoopRuntimeContext,
    LoopStartRequest,
    StepOutcome,
)
from loop_engine.code_nodes.complex_task_benchmark import (
    default_published_catalog_path,
    load_published_evidence,
)


def main():
    config = LoopConfig(
        framework="custom",
        custom_steps=("validate_catalog",),
        allowable_modes=("deterministic",),
        preferred_modes=("deterministic",),
        delegated_modes=("deterministic",),
        power="light",
        exit_condition="accepted_success",
    )
    identity = LoopRoleIdentity(
        "practitioner", "practitioner.verifier")
    contract = LoopContract(
        name="validate published harness evidence",
        execution_mode="code_only",
        input_roles=("published_evidence_path/v1",),
        output_roles=("published_evidence_accounting/v1",),
        role="practitioner",
    )
    definition = LoopDefinition.from_runtime(
        identity=identity,
        contract=contract,
        config=config,
        definition_id="practitioner.verify_published_harness_evidence",
        installed_executor_modes=("deterministic",),
    )
    event_log = LoopLedger()
    context = LoopRuntimeContext(
        custom_plugins=CustomPluginsPort(
            "published_harness_evidence",
            load_published_evidence,
            ("independent_verification",),
        ),
        internal=InternalRuntimeMechanics(
            bindings=(InternalRuntimeBinding(
                "loop_runtime", event_log,
                ("loop_spawn", "run_history_write")),),
            executor_modes=("deterministic",)),
    )
    loop = Loop(LoopStartRequest(
        goal="validate the published harness evidence catalog",
        definition=definition,
        relationship=LoopRelationship.starting(),
        runtime_context=context,
        event_log=event_log,
    ))
    output = {}

    def validate(_loop, _step, _state):
        catalog = load_published_evidence(default_published_catalog_path())
        output.update(catalog.accounting())
        return StepOutcome(
            output="published evidence catalog validated",
            mode="deterministic",
            confidence=1.0,
        )

    result = loop.run(handler=validate, max_steps=2)
    print(json.dumps({
        "loop_id": result.loop_id,
        "loop_definition": loop.definition_ref.to_dict(),
        "accounting": output,
    }, indent=2))


if __name__ == "__main__":
    main()
