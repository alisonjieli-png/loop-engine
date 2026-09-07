"""Offline evidence for admitted serial dependency values and references.

Exercises the public adaptive path, exact producer identities, schema
validation, scoped materialization, and blocked prerequisites without providers.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile


def assignment(task_id, *, dependencies=(), inputs=(), output=True):
    from .adaptive_practitioner_bindings import ASSIGNMENT_RECORD_TYPE
    return {
        "record_type": ASSIGNMENT_RECORD_TYPE, "task_id": task_id,
        "objective": "Resolve " + task_id, "constraints": [],
        "success_criteria": ["Return the exact declared result."],
        "depends_on": list(dependencies), "inputs": list(inputs),
        "output_contract": ({"role": "values/v1", "value_contract_ref": "integer_sequence/v1",
            "schema": {"type": "array", "items": {"type": "integer"}}, "result_path": ["value"]}
            if output is True else output),
    }


def input_binding(source="source", *, delivery="value"):
    return {"role": "values/v1", "source_task_id": source, "source_role": "values/v1",
            "value_contract_ref": "integer_sequence/v1", "delivery": delivery}


def spec_from(value):
    from ..loop.kernel import ProblemSpec
    from .adaptive_practitioner_bindings import ASSIGNMENT_KEY, SpawnedAssignment
    return ProblemSpec(value["objective"], constraints=tuple(value["constraints"]),
        success_criteria=tuple(value["success_criteria"]),
        seed_facts={ASSIGNMENT_KEY: SpawnedAssignment.from_mapping(value)})


def public_run(assignments, *, source_value=None, parent_finishes=False):
    from ..code_nodes.solution_model_port import FixtureModelExecutionRequest, fixture_model_execution
    from .adaptive_practitioner import run_adaptive_practitioner
    from .adaptive_practitioner_acceptance_checks import _decision, _decision_id, _orientation, _success_answers
    from .adaptive_practitioner_records import AdaptivePractitionerDependencies, AdaptivePractitionerRequest
    from .adaptive_host_runtime_checks import _answers, _fixture

    observed = []
    original = [2, 3] if source_value is None else source_value

    class ExactDependencyResolver:
        resolver_id = "fixture.dependency_values"

        def supports(self, task):
            try:
                return json.loads(task).get("record_type") == "delegated_problem/v1"
            except (ValueError, AttributeError):
                return False

        def execute(self, task):
            packet = json.loads(task)
            observed.append(packet)
            if packet["task_id"] == "source":
                return {"verified": True, "value": deepcopy(original)}
            inputs = packet["dependency_inputs"]
            if not inputs:
                return {"verified": True, "value": "barrier complete"}
            if inputs[0]["delivery"] == "reference":
                return {"verified": True, "value": inputs[0]["value_ref"]}
            return {"verified": True, "value": sum(inputs[0]["value"])}

    decision = _decision("SPAWN_LOOP", required_capabilities=[], permissions=[],
                         goal="Resolve declared dependent subproblems.")
    plan = {"action_id": _decision_id(decision), "how_mode": "delegate", "act_mode": "spawn_practitioners",
            "capability_ref": "", "arguments": {}, "steps": ["resolve dependencies"],
            "spawned_tasks": assignments, "rationale": "Use exact typed prerequisite outputs."}
    verification = json.loads(_success_answers()[-2])
    verification["scores"] = [1.0] * len(assignments)
    answers = tuple(json.dumps(item) for item in (
        _orientation(candidate_capabilities=[]), {"actions": [decision]}, plan, verification,
        {"route": "continue" if parent_finishes else "stop_success", "reason": "The subproblems returned."}))
    host = _fixture() if parent_finishes else None
    if host is not None:
        answers += _answers(host)
    with tempfile.TemporaryDirectory(prefix="adaptive-dependency-public-") as root:
        output = run_adaptive_practitioner(
            AdaptivePractitionerRequest("Resolve the root with independently accepted dependent work.",
                runs_dir=root, mode="hybrid", max_passes=2 if parent_finishes else 1, quiet_model_io=True),
            AdaptivePractitionerDependencies(
                fixture_model_execution(FixtureModelExecutionRequest(answers=answers, max_model_calls=len(answers))),
                deterministic_resolvers=(ExactDependencyResolver(),),
                host_runtime=host.binding if host is not None else None))
        from .run_history import RunHistory
        history = output["run_history"]
        from ..loop.intelligence_loops import serve_historical_intelligence
        saved = serve_historical_intelligence("Dependency fixture history", lambda:
            RunHistory.load(str(Path(history["path"]).parent), output["run_id"]))["value"]
        chain_intact = saved.verify_chain()["intact"]
        kinds = [event.detail.get("custom_kind") for event in saved.event_log]
    return output, observed, chain_intact, kinds


def frame_fixture(*, failed=False, issue=True):
    from ..loop.recursive_loop import Loop, LoopConfig, StepOutcome
    from .adaptive_practitioner_bindings import SpawnedAssignment, SpawnedDependencyFrame, _digest

    producer = SpawnedAssignment.from_mapping(assignment("source"))
    consumer = SpawnedAssignment.from_mapping(assignment("consumer", dependencies=("source",),
        inputs=(input_binding(),), output=None))
    owner = Loop("dependency fixture owner", LoopConfig(allowable_modes=("deterministic",),
        preferred_modes=("deterministic",), delegated_modes=("deterministic",)))
    frame = SpawnedDependencyFrame(owner, "fixture-run", "b" * 64,
                                   {"source": producer, "consumer": consumer})
    produced = owner.spawn("fixture producer")
    frame.start(producer, produced)
    produced.run(handler=lambda _owner, step, _context: StepOutcome(step, "deterministic", 1.0),
                 max_steps=len(produced.steps()) + 1)
    summary = {"record_type": "spawned_practitioner_result/v1", "loop_id": produced.loop_id,
               "definition_id": produced.definition_ref.definition_id,
               "definition_version": produced.definition_ref.version,
               "definition_digest": produced.definition_ref.content_digest,
               "spawned_by_loop_id": owner.loop_id, "dependency_plan_digest": frame.plan_digest,
               "task_id": "source", "task_complete": not failed,
               "verification_record_digest": "a" * 64,
               "accepted_result": {"result": {"verified": True, "value": [2, 3]}}}
    frame.register(producer, summary)
    if issue:
        owner.ledger.record(loop_id=owner.loop_id, event="custom",
            custom_kind="adaptive_spawned_result_returned", spawned_loop_id=produced.loop_id,
            result_digest=_digest(summary), spawned_task_complete=not failed)
    return frame, producer, consumer, summary


def run_checks():
    from ..loop.kernel import ProblemSpec
    from .adaptive_practitioner_records import AdaptivePractitionerRequest
    from .adaptive_practitioner_scope import delegated_task_text
    from .adaptive_practitioner_bindings import (
        ASSIGNMENT_KEY, DependencyBindingError, SpawnedAssignment, SpawnedOutputContract,
        assignment_for, compile_assignments)
    from .information_access import InformationAccessError, InformationAccessRequest

    tests = []

    def check(name, passed, detail="offline fixture; zero real provider calls"):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    def refused(function):
        try:
            function()
            return False
        except (ValueError, RuntimeError, TypeError):
            return True

    producer = assignment("source")
    consumer = assignment("consumer", dependencies=("source",), inputs=(input_binding(),), output=None)
    specs = (spec_from(consumer), spec_from(producer))
    order, plan_digest = compile_assignments(specs, "root task")
    check("dependency_plan_orders_producer_before_consumer_without_declared_order_guessing",
          order == (1, 0) and len(plan_digest) == 64)
    independent = (spec_from(assignment("z")), spec_from(assignment("a")))
    check("independent_named_assignments_preserve_declared_order",
          compile_assignments(independent, "root")[0] == (0, 1))
    other = deepcopy(consumer)
    other["inputs"][0]["delivery"] = "reference"
    check("reference_delivery_is_refused_at_admission_until_a_consumer_can_materialize",
          refused(lambda: compile_assignments((spec_from(other), specs[1]), "root task")))
    unknown_delivery = deepcopy(consumer)
    unknown_delivery["inputs"][0]["delivery"] = "stream"
    check("unknown_delivery_kinds_are_refused_at_admission",
          refused(lambda: compile_assignments((spec_from(unknown_delivery), specs[1]), "root task")))
    legacy = ProblemSpec("legacy", constraints=("constraint",), success_criteria=("criterion",))
    check("legacy_independent_assignment_and_task_packet_stay_unchanged",
          compile_assignments((legacy,), "root") == ((0,), "")
          and json.loads(delegated_task_text(legacy)) == {
              "record_type": "delegated_problem/v1", "objective": "legacy",
              "constraints": ["constraint"], "success_criteria": ["criterion"]})
    for label, raw in (("mapping", producer), ("null", None), ("text", "authorized")):
        check("reserved_seed_metadata_refuses_raw_" + label, refused(lambda raw=raw:
            assignment_for(replace(legacy, seed_facts={ASSIGNMENT_KEY: raw}))))
    check("reserved_seed_key_collision_is_refused", refused(lambda:
        assignment_for(replace(legacy, seed_facts={ASSIGNMENT_KEY + "_forged": producer}))))

    for label, change in (
            ("unknown_dependency", lambda values: values[0].update(depends_on=["absent"])),
            ("cycle", lambda values: values[1].update(depends_on=["consumer"])),
            ("duplicate_task", lambda values: values[0].update(task_id="source")),
            ("undeclared_input_dependency", lambda values: values[0].update(depends_on=[])),
            ("wrong_source_role", lambda values: values[0]["inputs"][0].update(source_role="other/v1")),
            ("wrong_target_role", lambda values: values[0]["inputs"][0].update(role="other/v1")),
            ("wrong_schema_ref", lambda values: values[0]["inputs"][0].update(value_contract_ref="text/v1")),
            ("duplicate_input_role", lambda values: values[0]["inputs"].append(deepcopy(values[0]["inputs"][0]))),
            ("unversioned_schema", lambda values: values[1]["output_contract"].update(value_contract_ref="integer_sequence")),
            ("external_schema", lambda values: values[1]["output_contract"].update(schema={"$ref": "https://invalid.invalid/schema"})),
            ("recursive_schema_ref", lambda values: values[1]["output_contract"].update(schema={"$ref": "#"})),
            ("unqualified_regex_schema", lambda values: values[1]["output_contract"].update(schema={"type": "string", "pattern": "(a+)+$"})),
            ("invented_schema_keyword", lambda values: values[1]["output_contract"].update(schema={"type": "array", "x-grants-authority": True})),
            ("malformed_schema", lambda values: values[1]["output_contract"].update(schema={"type": "not-a-type"})),
            ("unsafe_selector_type", lambda values: values[1]["output_contract"].update(result_path=[True])),
            ("unsupported_delivery", lambda values: values[0]["inputs"][0].update(delivery="shared_connection")),
            ("extra_authority_field", lambda values: values[0].update(permissions=["all"]))):
        values = deepcopy([consumer, producer])
        change(values)
        check("whole_plan_refuses_" + label,
              refused(lambda values=values: compile_assignments(tuple(spec_from(item) for item in values), "root")))
    different_schema = deepcopy(producer)
    different_schema.update(task_id="other")
    different_schema["output_contract"]["schema"] = {"type": "string"}
    check("one_schema_reference_cannot_bind_different_schema_bytes", refused(lambda:
        compile_assignments((spec_from(producer), spec_from(different_schema)), "root")))

    request = AdaptivePractitionerRequest("consumer", mode="deterministic")
    frame, _producer, input_assignment, summary = frame_fixture()
    consumer_loop = frame.owner.spawn("consumer")
    bound, delegation, resolver = frame.resolve(input_assignment, consumer_loop, request=request,
                                                spec=ProblemSpec("consumer"))
    reference = bound[0].reference
    check("named_value_port_has_exact_schema_digest_and_actual_producer_identity",
          bound[0].port.value == [2, 3] and bound[0].port.role == "values/v1"
          and reference.producer_loop_id == summary["loop_id"]
          and reference.value_contract_ref.endswith(bound[0].schema_digest)
          and json.loads(reference.producer_definition_ref)["content_digest"] == summary["definition_digest"]
          and delegation.inputs == tuple(item.port for item in bound))
    bound[0].port.value.append(99)
    again = resolver.materialize(InformationAccessRequest(value_ref=reference, requester_loop_id=consumer_loop.loop_id,
        purpose="verify detached input", requester_run_id=frame.run_id))
    check("consumer_mutation_does_not_change_source_or_later_materialization",
          summary["accepted_result"]["result"]["value"] == [2, 3] and again.value == [2, 3])
    check("same_run_sibling_cannot_dereference_consumer_grant", refused(lambda:
        resolver.materialize(InformationAccessRequest(value_ref=reference, requester_loop_id="sibling",
            purpose="forged access", requester_run_id=frame.run_id))))
    check("forged_reference_contract_and_digest_are_refused", all(refused(lambda ref=ref:
        resolver.materialize(InformationAccessRequest(value_ref=ref, requester_loop_id=consumer_loop.loop_id,
            purpose="changed identity", requester_run_id=frame.run_id)))
        for ref in (replace(reference, content_digest="0" * 64),
                    replace(reference, value_contract_ref="other/v1"),
                    replace(reference, producer_loop_id="other"))))
    check("dependency_delegation_does_not_add_call_or_iteration_ceilings",
          delegation.budget.max_model_calls is None and delegation.budget.max_iterations is None)
    from .adaptive_practitioner_bindings import DependencyValuePolicy
    check("bound_dependency_input_measures_its_delivered_bytes",
          bound[0].value_bytes == len(json.dumps([2, 3], separators=(",", ":")).encode("utf-8"))
          and bound[0].to_dict()["value_bytes"] == bound[0].value_bytes)
    bounded_frame, bounded_producer, _bounded_consumer, bounded_summary = frame_fixture()
    bounded_frame.policy = DependencyValuePolicy(maximum_value_bytes=4)
    check("dependency_value_over_the_delivery_bound_is_refused_as_incompatible",
          refused(lambda: bounded_frame.register(bounded_producer, bounded_summary))
          and DependencyValuePolicy().maximum_value_bytes == 262144
          and refused(lambda: DependencyValuePolicy(0))
          and refused(lambda: DependencyValuePolicy(True)))

    for label, mutate in (
            ("stale_source", lambda f, s: s["accepted_result"]["result"]["value"].append(4)),
            ("cross_scope_source", lambda f, s: s.update(spawned_by_loop_id="other-scope")),
            ("changed_definition", lambda f, s: s.update(definition_digest="c" * 64)),
            ("changed_schema", lambda f, s: f.assignments.__setitem__("source", replace(f.assignments["source"],
                output_contract=SpawnedOutputContract("values/v1", "integer_sequence/v1", '{"type":"string"}', ("value",))))),
            ("changed_stored_value", lambda f, s: f.outputs["source"][0].value.append(4))):
        damaged, _p, target, source = frame_fixture()
        mutate(damaged, source)
        target_loop = damaged.owner.spawn("consumer")
        check("binding_refuses_" + label, refused(lambda:
            damaged.resolve(target, target_loop, request=request, spec=ProblemSpec("consumer"))))
    for label, options in (("failed_prerequisite", {"failed": True}), ("unissued_prerequisite", {"issue": False})):
        damaged, _p, target, _source = frame_fixture(**options)
        target_loop = damaged.owner.spawn("consumer")
        check("binding_refuses_" + label, refused(lambda:
            damaged.resolve(target, target_loop, request=request, spec=ProblemSpec("consumer"))))

    output, observed, intact, kinds = public_run([consumer, producer])
    summaries = {item.get("task_id"): item for item in output.get("spawned_results", [])}
    check("public_adaptive_dependency_flow_executes_actual_bound_values",
          [item["task_id"] for item in observed] == ["source", "consumer"]
          and summaries.get("consumer", {}).get("accepted_result", {}).get("result", {}).get("value") == 5
          and summaries["source"]["task_complete"] and summaries["consumer"]["task_complete"],
          json.dumps({"observed": observed, "summaries": summaries, "failures": output.get("failures")}, default=str)[:1800])
    check("dependency_completion_does_not_certify_parent_or_add_model_calls",
          output.get("solved") is False and output.get("model_calls") == 5
          and not output.get("task_results") and all(item.get("model_calls") == 0 for item in summaries.values()))
    check("dependency_plan_and_handoff_stay_in_canonical_intact_history",
          intact and "adaptive_dependency_plan_admitted" in kinds and "adaptive_dependency_inputs_bound" in kinds)
    finished, _observed, finished_intact, _kinds = public_run([consumer, producer], parent_finishes=True)
    check("parent_can_complete_after_its_own_independent_verification",
          finished.get("solved") is True and len(finished.get("task_results", [])) == 1
          and finished.get("model_calls") == 10 and finished_intact)
    another = deepcopy(consumer)
    another.update(task_id="second_consumer", objective="Resolve another consumer")
    multiple, observed, _intact, _kinds = public_run([producer, consumer, another])
    consumers = [item for item in multiple.get("spawned_results", []) if item.get("task_id") != "source"]
    check("separate_consumers_receive_independent_scoped_grants_for_one_output",
          len(consumers) == 2 and all(item.get("task_complete") is True for item in consumers)
          and all(item["accepted_result"]["result"]["value"] == 5 for item in consumers))
    barrier = assignment("barrier", dependencies=("source",), output=None)
    root_only = deepcopy(producer)
    root_only["output_contract"] = None
    blocked_barrier, observed, _intact, _kinds = public_run([barrier, root_only])
    check("verified_barrier_dependency_needs_no_fabricated_value_port",
          [item["task_id"] for item in observed] == ["source", "barrier"]
          and all(item.get("task_complete") is True for item in blocked_barrier.get("spawned_results", [])))
    reference_consumer = deepcopy(consumer)
    reference_consumer["inputs"][0]["delivery"] = "reference"
    output, observed, _intact, _kinds = public_run([producer, reference_consumer])
    check("public_reference_delivery_is_refused_before_any_consumer_dispatch",
          not any(item.get("task_id") == "consumer" for item in observed)
          and not any(item.get("task_id") == "consumer" and item.get("task_complete") is True
                      for item in output.get("spawned_results", [])))
    unicode_source = deepcopy(producer)
    unicode_source["objective"] = "Préparer les valeurs de 東京"
    unicode_output, _observed, unicode_intact, _kinds = public_run([unicode_source, consumer])
    check("unicode_source_identity_matches_the_canonical_issued_result",
          unicode_intact and all(item.get("task_complete") is True
                                 for item in unicode_output.get("spawned_results", []))
          and unicode_output["spawned_results"][1]["accepted_result"]["result"]["value"] == 5)
    output, observed, _intact, _kinds = public_run([producer, consumer], source_value=[True, 3])
    summaries = {item.get("task_id"): item for item in output.get("spawned_results", [])}
    check("bad_output_type_blocks_consumer_before_execution",
          [item["task_id"] for item in observed] == ["source"]
          and summaries.get("source", {}).get("task_complete") is False
          and summaries.get("consumer", {}).get("binding_disposition") == "blocked"
          and output.get("solved") is False,
          json.dumps({"summaries": summaries, "failures": output.get("failures")}, default=str)[:1800])
    return {"record_type": "adaptive_dependency_binding_checks/v1", "tests": tests,
            "passed": sum(item["passed"] for item in tests), "total": len(tests),
            "all_passed": all(item["passed"] for item in tests)}
