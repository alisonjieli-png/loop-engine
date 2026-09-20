"""Restore each repaired failure in memory and require a discriminating check.

No files, native harnesses, providers, or external effects are used. Run in a
fresh Python process with PYTHONPATH=src and PYTHONDONTWRITEBYTECODE=1.
"""

import inspect
import json
import textwrap

from loop_engine.loop import loop_definition_checks, recursive_loop, runtime_context


def run_mutant(name, owner, method_name, module, before, after, expected_checks):
    original = getattr(owner, method_name)
    source = textwrap.dedent(inspect.getsource(original))
    if source.count(before) != 1:
        raise RuntimeError(f"{name}: mutation target is not unique")
    namespace = dict(vars(module))
    exec(compile(source.replace(before, after), f"<audit-mutant:{name}>", "exec"),
         namespace)
    setattr(owner, method_name, namespace[method_name])
    try:
        result = loop_definition_checks.self_test()
        failed = [item["test"] for item in result["tests"] if not item["passed"]]
        detected = bool(set(expected_checks) & set(failed))
        return {"mutant": name, "detected": detected, "failed_checks": failed}
    finally:
        setattr(owner, method_name, original)


if __name__ == "__main__":
    observations = [
        run_mutant(
            "restore_implicit_deterministic_executor",
            runtime_context.LoopRuntimeContext, "derive", runtime_context,
            "executor_modes=requested_executors,",
            "executor_modes=requested_executors or ('deterministic',),",
            ("empty_context_derivation_does_not_add_an_executor",),
        ),
        run_mutant(
            "remove_compatibility_permission_check",
            recursive_loop.Loop, "spawn", recursive_loop,
            "self.runtime_context.require(permissions=definition.permissions)",
            "pass",
            ("compatibility_spawn_refuses_permissions_absent_from_its_owner",),
        ),
        run_mutant(
            "reset_supervision_during_mode_restriction",
            recursive_loop.Loop, "spawn", recursive_loop,
            "config = replace(\n                config,",
            "config = replace(\n                config,\n"
            "                supervision=DEFAULT_SUPERVISION_POLICY,",
            ("spawn_mode_restriction_preserves_every_independent_config_field",),
        ),
        run_mutant(
            "reset_output_obligation_during_mode_restriction",
            recursive_loop.Loop, "spawn", recursive_loop,
            "config = replace(\n                config,",
            "config = replace(\n                config,\n"
            "                output_type='single', max_outputs=None,",
            ("spawn_mode_restriction_preserves_every_independent_config_field",
             "spawn_mode_restriction_preserves_executed_output_quota"),
        ),
    ]
    print(json.dumps({"record_type": "runtime_repair_mutants/v1",
                      "mutants": observations,
                      "all_detected": all(item["detected"] for item in observations)},
                     indent=2))
    raise SystemExit(0 if all(item["detected"] for item in observations) else 1)
