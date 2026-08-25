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
    default_loop_engine_catalog_path,
    default_published_catalog_path,
    load_native_evidence,
    load_published_evidence,
    match_loop_engine_to_published,
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
        output_roles=("complex_task_comparison_audit/v1",),
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
        published = load_published_evidence(default_published_catalog_path())
        native = load_native_evidence(default_loop_engine_catalog_path())
        accounting = published.accounting()
        match_report = match_loop_engine_to_published(native, published)
        output.update({
            "published": {
                "numeric_records": accounting["numeric_records"],
                "qualitative_findings": accounting["findings"],
                "exact_cross_harness_groups": accounting["comparable_groups"],
            },
            "loop_engine": [{
                "record_id": record.record_id,
                "benchmark": record.benchmark_name,
                "tasks": record.population_count,
                "score": record.score_value,
                "metric": record.score_metric,
                "selected_model_calls": record.selected_model_calls,
                "packet_model_calls": record.packet_model_calls,
                "token_accounting_complete": (
                    record.token_accounting_complete),
                "cost_state": record.cost_state,
            } for record in native.records],
            "match_report": {
                "comparison_ready": match_report.comparison_ready,
                "exclusions": [{
                    "loop_engine_record_id": item.loop_engine_record_id,
                    "reason": item.exclusion_reason,
                } for item in match_report.matches
                if not item.comparison_ready],
            },
        })
        return StepOutcome(
            output="published and Loop Engine evidence catalogs validated",
            mode="deterministic",
            confidence=1.0,
        )

    result = loop.run(handler=validate, max_steps=2)
    print(json.dumps({
        "loop_id": result.loop_id,
        "loop_definition": loop.definition_ref.to_dict(),
        "comparison_audit": output,
    }, indent=2))


if __name__ == "__main__":
    main()
