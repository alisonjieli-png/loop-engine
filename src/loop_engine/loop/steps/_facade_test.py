"""Facade conformance test for the nine per-step facades.

Owns: asserting every steps/ facade imports, re-exports its kernel default,
and matches the step registry.  Belongs to: loop runtime plumbing."""
from __future__ import annotations
import importlib


def self_test() -> dict:
    results: list[dict] = []

    def check(name, ok, detail=""):
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    from ...loop.kernel import KERNEL_NODES
    from ...architecture_map import PACKAGE
    pkg = PACKAGE + ".loop.steps."
    step_files = ["s1_orient", "s2_reconcile", "s3_assess", "s4_decide",
                  "s5_how", "s6_act", "s7_verify", "s8_integrate", "s9_route"]

    # 1. there is exactly one step file per kernel node, in order.
    check("one_step_file_per_kernel_node_in_order",
          len(step_files) == len(KERNEL_NODES) == 9,
          f"{len(step_files)} step files for {len(KERNEL_NODES)} nodes")

    # 2. every step facade imports and every __all__ symbol resolves (no
    # dangling re-exports — the reading surface can't lie).
    dangling = {}
    for f in step_files:
        m = importlib.import_module(pkg + f)
        bad = [s for s in getattr(m, "__all__", []) if not hasattr(m, s)]
        if bad:
            dangling[f] = bad
    check("every_step_facade_re_exports_real_symbols",
          not dangling, f"dangling: {dangling}")

    # 3. every step facade carries its CONTRACT + WAYS + EXTEND in the docstring
    # (the human/LLM reading surface is documented, not just code).
    undocumented = []
    for f in step_files:
        m = importlib.import_module(pkg + f)
        doc = (m.__doc__ or "")
        if not ("CONTRACT" in doc and "WAYS" in doc and "EXTEND" in doc):
            undocumented.append(f)
    check("every_step_facade_documents_contract_ways_and_extend",
          not undocumented, f"undocumented: {undocumented}")

    # 4. each facade re-exports its kernel default (the step's baseline).
    defaults = {"s1_orient": "default_orient",
                "s2_reconcile": "default_reconcile_horizon",
                "s3_assess": "default_assess_prepare",
                "s4_decide": "default_decide_next", "s5_how": "default_how",
                "s6_act": "default_act", "s7_verify": "default_verify",
                "s8_integrate": "default_integrate_commit",
                "s9_route": "default_route"}
    missing = []
    for f, d in defaults.items():
        m = importlib.import_module(pkg + f)
        if not hasattr(m, d):
            missing.append((f, d))
    check("each_step_facade_exposes_its_kernel_default",
          not missing, f"missing defaults: {missing}")

    # 5. the subpackage __init__ imports all nine.
    steps = importlib.import_module(PACKAGE + ".loop.steps")
    check("the_steps_subpackage_exposes_all_nine",
          all(hasattr(steps, f) for f in step_files),
          "import loop_engine.loop.steps -> all nine files")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "steps_facade_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
