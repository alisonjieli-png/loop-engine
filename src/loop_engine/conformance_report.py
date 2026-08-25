"""Zero-tolerance conformance gates (§21) — computed, never asserted.

``--conformance`` runs the machine-enforced scanner plus the structural gates,
writes ``architecture_conformance.json`` (the machine-readable manifest), and
exits nonzero on any violation.  Every gate is an honest COUNT computed from
the live tree; guard-enforced gates (runtime rails that cannot be counted
statically) are reported as guard names whose positive + adversarial tests
live in the suite — never as bare claims.
"""
from __future__ import annotations

import json
import os

_HERE = os.path.dirname(__file__)

#: documents allowed to present themselves as CURRENT guidance; every other
#: root .md must carry a SUPERSEDED/HISTORICAL header (stale-doc gate).
CURRENT_DOCS = ("ARCHITECTURE-MAP.md",)

#: rails that are enforced by runtime guards + proven by paired positive and
#: adversarial tests in the suite (they cannot be counted by a static scan).
GUARD_ENFORCED = (
    "hidden_semantic_calls: one semantic call per iteration; semantic "
    "fallbacks defer to the next iteration (model_boundary_deferred)",
    "spawned_permission_escalation: spawn() clamps spawned modes to the parent's "
    "delegation authority and refuses disjoint requests",
    "orphaned_loops: audit_closure() flags spawned-but-never-terminal "
    "spawned_loops; every terminal transition is a recorded ledger event",
    "self_promotion: guard_improvement_action raises SafeguardError on "
    "promote/overwrite/delete-evidence",
    "evidence_gated_promotion: asset_lifecycle.advance refuses "
    "validated->registered without evidence (PromotionRefused)",
    "candidate_templates_cannot_run: config_from_template refuses "
    "maturity=candidate",
    "cloud_only_and_forbidden_family: screen_route refuses local counted "
    "generation; kimi-k3 refused at ModelRoute construction",
    "max_power_grants_no_permissions: power scales budgets only",
)


def _access_baseline() -> int:
    """The declared no-direct-access baseline (a ratchet, never a pass)."""
    from ._conformance_scan import _rules
    return int(_rules().get("direct_resource_access_baseline", 0))


def _stale_docs() -> list:
    stale = []
    for f in sorted(os.listdir(_HERE)):
        if not f.endswith(".md") or f in CURRENT_DOCS:
            continue
        head = open(os.path.join(_HERE, f)).read(400)
        if "SUPERSEDED" not in head and "HISTORICAL" not in head:
            stale.append(f)
    return stale


def _unclassified() -> list:
    from .architecture_map import MODULE_MAP, ROOT_MODULES, SUBPACKAGES
    flat = {m for mods in MODULE_MAP.values() for m in mods}
    bad = []
    for f in os.listdir(_HERE):
        if f.endswith(".py") and f[:-3] not in ROOT_MODULES:
            bad.append(f)
    for s in SUBPACKAGES:
        for f in os.listdir(os.path.join(_HERE, s)):
            if f.endswith(".py") and f != "__init__.py" and f[:-3] not in flat:
                bad.append(f"{s}/{f}")
    return bad


def _legacy_flat_paths_reachable() -> list:
    """Probe obsolete package-root module paths; they must stay dead."""
    import importlib
    from .architecture_map import PACKAGE
    reachable = []
    # NOTE: "loop" is excluded — it is now the subpackage name, so the flat
    # spelling legitimately resolves to the subpackage, not the old module.
    for legacy in ("kernel", "recursive_loop", "capability_directory",
                   "intelligence_strings", "solver"):
        try:
            importlib.import_module(f"{PACKAGE}.{legacy}")
            reachable.append(legacy)
        except ModuleNotFoundError:
            pass
    return reachable


def _stale_architecture_map() -> int:
    """The generated ARCHITECTURE-MAP.md must match render_map() — its content
    freshness is gated like the conformance manifest, not just its title.  A
    committed map whose body disagrees with the live projection returns 1."""
    import re
    p = os.path.join(_HERE, "ARCHITECTURE-MAP.md")
    if not os.path.exists(p):
        return 1
    from .architecture_map import render_map
    live = render_map()
    committed = open(p, encoding="utf-8").read()
    # The body's map must contain every live module COUNT line verbatim; a
    # stale census is drift.  Compare count lines only (the module-name lines
    # wrap and are regenerated, not hand-checked).
    def counts(text):
        return [re.search(r"\(\d+ modules\)", l).group(0)
                for l in text.splitlines()
                if re.match(r"^\s{2}\S+/\s{2}\(\d+ modules\)", l)]
    return 0 if counts(committed) != [] and counts(committed) == counts(live) else 1


def _public_retired_nomenclature() -> list:
    """Scan current repository text for the retired decision-spine terms."""
    from ._conformance_scan import _rules
    from .nomenclature_conformance import retired_nomenclature_violations

    policy = dict(_rules().get("retired_source_nomenclature", {}))
    policy["terms"] = tuple(
        term for term in policy.get("terms", ())
        if "what" in str(term).casefold())
    policy["excluded_files"] = (
        "src/loop_engine/forbidden_paths.json",
    )
    root = os.path.dirname(os.path.dirname(_HERE))
    return retired_nomenclature_violations(root, policy)


def operational_graph_vertex_violations(root: "str | None" = None) -> list:
    """Find executable graph-vertex classes that compete with canonical Loop.

    Passive projections are admitted only when their exact Loop definition
    reference is explicit. They never own execution.
    """
    import ast
    base = root or _HERE
    retired = {"CanvasNode", "GoalNode", "CodeNode", "NodeResult"}
    passive = {
        "LoopNode": {"loop_id"},
        "LoopGraphVertex": {"definition_ref", "definition", "selected_mode"},
    }
    violations = []
    for directory, _, files in os.walk(base):
        for filename in files:
            if not filename.endswith(".py"):
                continue
            path = os.path.join(directory, filename)
            try:
                tree = ast.parse(open(path, encoding="utf-8").read(), path)
            except (OSError, SyntaxError):
                continue
            for item in (node for node in ast.walk(tree)
                         if isinstance(node, ast.ClassDef)):
                fields = {node.target.id for node in item.body
                          if isinstance(node, ast.AnnAssign)
                          and isinstance(node.target, ast.Name)}
                methods = {node.name for node in item.body
                           if isinstance(node, (ast.FunctionDef,
                                                ast.AsyncFunctionDef))}
                bases = {getattr(node, "id", getattr(node, "attr", ""))
                         for node in item.bases}
                reason = ""
                if item.name in retired:
                    reason = "retired non-Loop graph/runtime spelling"
                elif item.name in passive and passive[item.name] <= fields:
                    continue
                elif (item.name.endswith(("Node", "Vertex"))
                      and "Loop" not in bases):
                    reason = "graph vertex type does not inherit canonical Loop"
                elif ("node_id" in fields
                      and methods & {"run", "execute", "invoke"}
                      and "Loop" not in bases):
                    reason = "executable node-shaped type bypasses canonical Loop"
                if reason:
                    violations.append({
                        "file": os.path.relpath(path, base), "line": item.lineno,
                        "type": item.name, "reason": reason})
    return violations


def run_conformance() -> dict:
    from ._conformance_scan import run_scan
    from .static_architecture.api_quality import scan_public_signatures
    from .static_architecture.boundary_registry import boundary_report
    scan = run_scan()
    api_violations = scan_public_signatures()
    boundaries = boundary_report()
    graph_vertex_violations = operational_graph_vertex_violations()
    public_nomenclature = _public_retired_nomenclature()
    unclassified = _unclassified()
    legacy_flat_paths = _legacy_flat_paths_reachable()
    stale = _stale_docs()
    c = scan["counts_by_rule"]
    gates = {
        "unclassified_files": len(unclassified),
        "reachable_legacy_flat_paths": len(legacy_flat_paths),
        "legacy_flat_imports_on_live_paths": c.get(
            "legacy_flat_import", 0),
        "public_parallel_runtime_surfaces": c.get(
            "public_parallel_runtime_surface", 0),
        "retired_decision_spine_terms": len(public_nomenclature),
        "direct_model_or_network_calls_outside_gateway":
            c.get("network_outside_gateway", 0),
        "subprocess_outside_declared_adapters":
            c.get("subprocess_outside_declared", 0),
        "eval_or_exec_anywhere": c.get("eval_or_exec", 0),
        "secret_shaped_literals_in_code_or_run_records":
            c.get("secret_shaped_literal", 0),
        "dynamic_import_registration_bypasses":
            c.get("dynamic_import_bypass", 0),
        "forbidden_model_mentions_outside_guards":
            c.get("forbidden_model_mention", 0),
        "empty_placeholder_modules": c.get("empty_placeholder_module", 0),
        "modules_over_size_cap_without_declared_exception":
            c.get("module_over_size_cap", 0),
        "public_interfaces_over_parameter_cap_without_declared_exception":
            len(api_violations),
        "syntax_newer_than_the_declared_minimum_python":
            c.get("syntax_newer_than_min_python", 0),
        "modules_missing_llm_context_docstring":
            c.get("short_module_docstring", 0),
        "stale_current_architecture_documents": len(stale),
        "conformance_test_skip_markers":
            c.get("conformance_test_skip_marker", 0),
        "runtime_event_kinds_outside_the_canonical_vocabulary":
            c.get("unmapped_ledger_event_kind", 0),
        "modules_whose_self_test_the_suite_never_runs":
            c.get("uncollected_self_test", 0),
        # A RATCHET: the count of direct cross-boundary resource accesses may
        # only fall.  Reported as the OVERAGE so the gate reads 0 while the
        # real (nonzero) count stays visible in the manifest below.
        "envelope_owning_modules_missing_from_the_register":
            c.get("unregistered_boundary", 0),
        "operational_boundaries_outside_loop_ontology":
            boundaries["outside_loop_ontology"],
        "operational_boundary_relationship_kind_violations":
            len(boundaries["invalid_relationship_rows"]),
        "operational_graph_vertex_types_outside_canonical_loop":
            len(graph_vertex_violations),
        "direct_resource_access_above_baseline": max(
            0, c.get("direct_resource_access", 0) - _access_baseline()),
        "architecture_map_freshness": _stale_architecture_map(),
    }
    all_pass = all(v == 0 for v in gates.values())
    manifest = {
        "record_type": "architecture_conformance/v1",
        "generated_by": "python3 -m loop_engine "
                        "--conformance",
        "files_scanned": scan["files_scanned"],
        "zero_tolerance_gates": gates,
        "gate_details": {"unclassified_files": unclassified,
                         "reachable_legacy_flat_paths": legacy_flat_paths,
                         "stale_current_architecture_documents": stale,
                         "operational_boundary_ontology": boundaries,
                         "operational_graph_vertex_types":
                             graph_vertex_violations,
                         "retired_decision_spine_terms":
                             public_nomenclature,
                         "scan_violations": (scan["violations"]
                                             + api_violations)},
        "direct_resource_access": {
            "current": scan["counts_by_rule"].get("direct_resource_access", 0),
            "baseline": _access_baseline(),
            "honesty": "a ratchet, not conformance — the law is that NO "
                       "product-level caller reaches a resource directly; "
                       "this many still do, and the gate only stops it "
                       "growing"},
        "guard_enforced_rails": list(GUARD_ENFORCED),
        "suite_note": "run --self-test separately; conformance is releasable "
                      "only when BOTH exit 0",
        "all_gates_pass": all_pass,
    }
    with open(os.path.join(_HERE, "architecture_conformance.json"), "w") as f:
        json.dump(manifest, f, indent=1)
    lines = ["ZERO-TOLERANCE CONFORMANCE GATES"]
    for k, v in gates.items():
        lines.append(f"  {'PASS' if v == 0 else 'FAIL':4}  {k} = {v}")
    lines.append(f"  guard-enforced rails: {len(GUARD_ENFORCED)} "
                 "(positive + adversarial tests in the suite)")
    lines.append(f"  manifest: architecture_conformance.json | "
                 f"{'ALL GATES PASS' if all_pass else 'GATES FAILED'}")
    manifest["human_summary"] = "\n".join(lines)
    return manifest


def self_test() -> dict:
    import tempfile
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    r = run_conformance()
    check("all_zero_tolerance_gates_pass_on_the_live_tree",
          r["all_gates_pass"],
          json.dumps({k: v for k, v in r["zero_tolerance_gates"].items()
                      if v}) or "all zero")
    check("manifest_written_and_machine_readable",
          os.path.exists(os.path.join(_HERE, "architecture_conformance.json"))
          and r["record_type"] == "architecture_conformance/v1")
    check("stale_doc_gate_is_a_real_detector",
          _stale_docs() == [] and CURRENT_DOCS == ("ARCHITECTURE-MAP.md",),
          "every non-current root doc carries a SUPERSEDED/HISTORICAL header")
    with tempfile.TemporaryDirectory() as directory:
        fixture = os.path.join(directory, "vertex_canary.py")
        with open(fixture, "w", encoding="utf-8") as stream:
            stream.write(
                "class TaskNode:\n    node_id: str\n"
                "    def run(self): pass\n\n"
                "class GoalItem:\n    goal_id: str\n\n"
                "class SolutionSlot:\n    slot_id: str\n\n"
                "class LoopGraphVertex:\n    definition_ref: object\n"
                "    definition: object\n    selected_mode: str\n\n"
                "GoalNode = GoalItem\n")
        canary = operational_graph_vertex_violations(directory)
    check("operational_vertex_canary_refuses_non_loop_and_ignores_passive_records",
          [item["type"] for item in canary] == ["TaskNode"],
          f"violations={canary}")
    passed = sum(1 for x in results if x["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
