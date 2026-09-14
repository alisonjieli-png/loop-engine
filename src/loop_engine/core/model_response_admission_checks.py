"""Contract checks for stalled repair: shapes ride with the exception.

The repair loop refuses repeated invalid outputs; when it gives up, the
raised ModelResponseRepairStalled must carry the rejected shapes so a
recovery panel can forbid them instead of re-deriving the failure.
"""
from __future__ import annotations

from .model_response_admission import ModelResponseRepairStalled


def self_test() -> dict:
    results = []

    def check(name, ok, detail=""):
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    stalled = ModelResponseRepairStalled(
        "cycle stalled", step_id="orient", attempts=3,
        failure_code="repeated_invalid_output",
        rejected_digests=("aaa", "bbb"))
    check("repair_stall_carries_shapes_for_recovery",
          isinstance(stalled, RuntimeError)
          and stalled.step_id == "orient" and stalled.attempts == 3
          and stalled.failure_code == "repeated_invalid_output"
          and stalled.rejected_digests == ("aaa", "bbb")
          and str(stalled) == "cycle stalled",
          "message unchanged; shapes ride as attributes for the "
          "recovery panel")
    bare = ModelResponseRepairStalled("stalled")
    check("stall_defaults_stay_empty_not_none",
          bare.step_id == "" and bare.attempts == 0
          and bare.failure_code == "" and bare.rejected_digests == (),
          "old raise sites without keywords keep working")

    # The schema's own path to a failed constraint is disclosed only by
    # policy, names what the trusted contract declared, and never a
    # candidate's keys; a contract's digest moves only when the policy is on.
    import hashlib
    import json
    from ..loop.recursive_loop import LoopLedger
    from .model_response_admission import (
        ModelResponseAdmissionPolicy, ModelResponseAdmissionRequest, ModelResponseContract,
        admit_model_response_as_loop)
    secret = "PRIVATE_CANDIDATE_KEY"
    digest = hashlib.sha256(b"schema-path-contract").hexdigest()
    ledger = LoopLedger()
    steps_schema = {"type": "object", "properties": {"steps": {"type": "array", "minItems": 1}}}
    quiet = admit_model_response_as_loop(ModelResponseAdmissionRequest(
        json.dumps({"steps": []}), "fixture.schema/v1", digest, schema=steps_schema), ledger=ledger)
    disclosed = admit_model_response_as_loop(ModelResponseAdmissionRequest(
        json.dumps({"steps": [], secret: 1}), "fixture.schema/v1", digest,
        schema={**steps_schema, "additionalProperties": False},
        policy=ModelResponseAdmissionPolicy(report_constraint_paths=True)), ledger=ledger)
    check("constraint_paths_are_disclosed_only_by_policy_and_name_the_schema_not_the_candidate",
          quiet.schema_errors == ("schema_constraint_failed:minItems",)
          and "schema_constraint_at:properties/steps/minItems" in disclosed.schema_errors
          and "schema_constraint_at:additionalProperties" in disclosed.schema_errors
          and "schema_constraint_failed:minItems" in disclosed.schema_errors
          and secret not in json.dumps(disclosed.to_dict())
          and secret not in json.dumps(ledger.events),
          str(disclosed.schema_errors)[:160])
    schema_json = json.dumps(steps_schema)
    off = ModelResponseContract("fixture.schema/v1", schema_json, ModelResponseAdmissionPolicy())
    on = ModelResponseContract("fixture.schema/v1", schema_json,
                               ModelResponseAdmissionPolicy(report_constraint_paths=True))
    check("a_contract_digest_moves_only_when_path_disclosure_is_on",
          "report_constraint_paths" not in off.to_dict()["normalization"]
          and on.to_dict()["normalization"]["report_constraint_paths"] is True
          and off.content_digest != on.content_digest)
    try:
        ModelResponseAdmissionPolicy(report_constraint_paths="yes")
        check("path_disclosure_must_be_a_boolean", False, "accepted text")
    except TypeError:
        check("path_disclosure_must_be_a_boolean", True)

    passed = sum(1 for item in results if item["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
