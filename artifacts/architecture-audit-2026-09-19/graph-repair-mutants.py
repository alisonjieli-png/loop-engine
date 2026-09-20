"""In-memory mutants for graph dataflow and implementation identity repairs.

Every fixture is local and deterministic. No provider, native harness, or
external effect is used. Source files are never rewritten by this script.
"""

from dataclasses import replace
import inspect
import json
import re
import textwrap

from loop_engine.code_nodes import (
    solution_canvas, solution_compiler, solution_graph_checks,
    solution_graph_execution, solution_graph_validation,
)


def changed_function(function, module, before, after):
    source = textwrap.dedent(inspect.getsource(function))
    if source.count(before) != 1:
        raise RuntimeError("mutation target is not unique")
    namespace = dict(vars(module))
    exec(compile(source.replace(before, after), "<graph-audit-mutant>", "exec"), namespace)
    return namespace[function.__name__]


def observe(name, bindings):
    originals = [(owner, attribute, getattr(owner, attribute))
                 for owner, attribute, _ in bindings]
    for owner, attribute, value in bindings:
        setattr(owner, attribute, value)
    try:
        result = solution_graph_checks.self_test()
        failed = [item["name"] for item in result["tests"] if not item["passed"]]
        return {"mutant": name, "detected": bool(failed), "failed_checks": failed}
    except Exception as exc:
        return {"mutant": name, "detected": True,
                "detection": "exception on a valid fixture after the targeted mutation",
                "error_type": type(exc).__name__, "error": str(exc)}
    finally:
        for owner, attribute, original in originals:
            setattr(owner, attribute, original)


if __name__ == "__main__":
    baseline = solution_graph_checks.self_test()
    if not baseline["all_passed"]:
        raise RuntimeError("the unchanged graph checks must pass before mutation")
    values = solution_graph_execution._SolutionGraphValues
    original_input = values.input_for

    def sequential_input(self, vertex_id):
        for group in self.graph.groups:
            for index, stage in enumerate(group.stages):
                if index and vertex_id in stage.attempt_vertex_ids:
                    previous = group.stages[index - 1].result_vertex_id
                    role = self.graph.resolved_definition(previous).contract.output_roles[-1]
                    if (previous, role) in self.values:
                        return self.values[(previous, role)]
        return original_input(self, vertex_id)

    original_identity = solution_compiler.operation_identity

    def ignore_code(operation_ref, operation):
        return replace(original_identity(operation_ref, operation), implementation_digest="0" * 64)

    pipeline = solution_graph_execution._run_pipeline
    source = textwrap.dedent(inspect.getsource(pipeline))
    target = re.search(r"        ready = next\([\s\S]+?\n        if ready is None:", source)
    if target is None:
        raise RuntimeError("dependency scheduler mutation target is absent")
    ordered_pipeline = changed_function(pipeline, solution_graph_execution,
        target.group(0), "        ready = 0\n        if ready is None:")
    unguarded_binding = changed_function(solution_compiler.bind_solution_operations,
        solution_compiler, "if prior != current:", "if False:")
    unguarded_inputs = changed_function(solution_graph_validation.validate_loop_graph,
        solution_graph_validation,
        '            if target_key in bound_inputs:\n                violations.append(f"input {target_key} is bound more than once")',
        '            if False:\n                violations.append(f"input {target_key} is bound more than once")')
    observations = [
        observe("restore_sequential_value_handoff", [(values, "input_for", sequential_input)]),
        observe("restore_stage_list_scheduling", [
            (solution_graph_execution, "_run_pipeline", ordered_pipeline),
            (solution_canvas, "_run_pipeline", ordered_pipeline)]),
        observe("ignore_declared_output_ports", [
            (values, "public_output", lambda self: list(self.values.values())[-1])]),
        observe("ignore_implementation_code_identity", [
            (solution_compiler, "operation_identity", ignore_code)]),
        observe("skip_use_time_implementation_validation", [
            (solution_compiler, "validate_operation_binding", lambda *args: None)]),
        observe("silently_rebind_compiled_implementations", [
            (solution_compiler, "bind_solution_operations", unguarded_binding)]),
        observe("allow_duplicate_external_input_bindings", [
            (solution_graph_validation, "validate_loop_graph", unguarded_inputs)]),
        observe("omit_execution_control_topology_validation", [
            (solution_graph_validation, "_execution_topology_violations", lambda *args: [])]),
    ]
    print(json.dumps({"record_type": "graph_repair_mutants/v1", "provider_calls": 0,
                      "baseline_checks": baseline["total"], "mutants": observations,
                      "all_detected": all(item["detected"] for item in observations)}, indent=2))
    raise SystemExit(0 if all(item["detected"] for item in observations) else 1)
