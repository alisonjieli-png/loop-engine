"""Verify a release decision through one versioned typed Loop profile."""

import json

from loop_engine import (
    Loop,
    LoopConnectionSpec,
    LoopContract,
    LoopProfileBindingRequest,
    LoopProfileRef,
    StepOutcome,
    bind_profile,
    validate_loop_connection,
)


def main():
    metrics_contract = LoopContract(
        name="collect-deployment-metrics",
        execution_mode="code_only",
        input_roles=("deployment_metrics/v1",),
        output_roles=("release_evidence/v1",),
    )
    verifier_contract = LoopContract(
        name="verify-deployment",
        execution_mode="code_only",
        input_roles=("release_evidence/v1",),
        output_roles=("release_decision/v1",),
    )
    connection = validate_loop_connection(LoopConnectionSpec(
        producer=metrics_contract,
        consumer=verifier_contract,
    ))
    if not connection.compatible:
        raise RuntimeError(connection.explain())

    bound = bind_profile(LoopProfileBindingRequest(
        profile=LoopProfileRef("practitioner.verifier"),
        goal="verify the deployment decision",
        contract=verifier_contract,
        available_fields=("claim_set", "acceptance_rule"),
        capabilities=(
            "loop_spawn",
            "chronicle_write",
            "independent_verification",
        ),
        modes=("deterministic",),
        preferred_modes=("deterministic",),
    ))

    metrics = {
        "observed_error_rate": 0.031,
        "maximum_error_rate": 0.01,
        "observed_p95_ms": 420,
        "maximum_p95_ms": 500,
    }
    state = {"decision": "", "reason": ""}

    def handler(loop, step, context):
        if step == "collect_claims":
            output = "claim: deployment is safe to continue"
        elif step == "attack":
            failed = (metrics["observed_error_rate"]
                      > metrics["maximum_error_rate"])
            output = f"threshold_violation={failed}"
        elif step == "verify_survivors":
            state["decision"] = "rollback"
            state["reason"] = "error rate exceeds the release threshold"
            output = "continue claim rejected"
        else:
            output = json.dumps(state, sort_keys=True)
        return StepOutcome(
            output=output, mode="deterministic", confidence=1.0)

    loop = Loop(
        "verify the deployment decision",
        bound.config,
        contract=verifier_contract,
    )
    result = loop.run(handler=handler)
    print(json.dumps({
        "profile": bound.profile.spec.profile_id,
        "profile_version": bound.profile.spec.version,
        "connection_compatible": connection.compatible,
        "steps_run": result.steps_run,
        "model_calls": result.model_calls,
        "decision": state,
    }, indent=2))


if __name__ == "__main__":
    main()
