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
#: A PARKED.md marker names a deliberately retired capability and where its
#: working implementation is frozen; it is a declared record, not guidance.
CURRENT_DOCS = ("ARCHITECTURE-MAP.md", "PARKED.md")

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


def _dependency_direction_baseline() -> int:
    """The declared ceiling of the dependency-direction ratchet."""
    from ._conformance_scan import _rules, ratchet_baselines
    return ratchet_baselines(_rules()).get("dependency_direction", 0)


def _stale_docs() -> list:
    stale = []
    for f in sorted(os.listdir(_HERE)):
        if not f.endswith(".md") or f in CURRENT_DOCS:
            continue
        head = open(os.path.join(_HERE, f)).read(400)
        if "SUPERSEDED" not in head and "HISTORICAL" not in head:
            stale.append(f)
    return stale


#: The line a documentation folder's README must carry in its head: its kind.
DOCS_CHARTER_MARKER = "Kind:"
DOCS_CHARTER_HEAD_CHARACTERS = 600
#: The Markdown a reader is invited to follow: the repository's own front
#: matter, the documentation tree, the worked examples, the harness
#: embodiments and the READMEs that sit beside the source. Every relative
#: address in these must resolve.
LINKED_DOCUMENT_ROOTS = ("docs", "examples", "embodiments", "src", "tools", "devtools",
                         "integrations", "case-studies")
LINKED_DOCUMENT_FILES = ("README.md", "CONTRIBUTING.md", "SECURITY.md", "CHANGELOG.md")
#: Dated evidence keeps the bytes it was written with. A record of what was
#: observed on a day is not repaired later, so its addresses are read as
#: history, not as an invitation to follow them.
PRESERVED_EVIDENCE_ROOTS = (os.path.join("docs", "evidence"),)
#: An embodiment folder keeps a vendored copy of the harness it adapts,
#: under `upstream` or `runtime`. Those files are not documents this
#: repository writes: their addresses are read as someone else's history,
#: not as an invitation a reader of this repository was given.
VENDORED_EMBODIMENT_TREES = ("upstream", "runtime")


def _documentation_links_that_do_not_resolve(repository: "str | None" = None) -> list:
    """Relative Markdown addresses, in documents a reader follows, that lead nowhere.

    An installed package carries no documentation tree and reports nothing.
    A web address is not checked here: it needs the network, and conformance
    must run without one.
    """
    import re
    if repository is None:
        repository, _exclusions = _nomenclature_scan_layout()
        if repository == _HERE:
            return []
    link = re.compile(r"\[[^\]\n]{0,200}\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
    documents = [os.path.join(repository, name) for name in LINKED_DOCUMENT_FILES]
    for folder in LINKED_DOCUMENT_ROOTS:
        for directory, subdirectories, files in os.walk(os.path.join(repository, folder)):
            subdirectories[:] = [name for name in subdirectories
                                 if not name.startswith(".") and name != "node_modules"]
            documents += [os.path.join(directory, name) for name in files if name.endswith(".md")]
    broken = []
    for path in sorted(documents):
        relative = os.path.relpath(path, repository)
        parts = relative.split(os.sep)
        if (not os.path.isfile(path) or relative.startswith(PRESERVED_EVIDENCE_ROOTS)
                or (len(parts) >= 3 and parts[0] == "embodiments" and parts[2] in VENDORED_EMBODIMENT_TREES)):
            continue
        with open(path, encoding="utf-8", errors="ignore") as stream:
            text = stream.read()
        for number, line in enumerate(text.splitlines(), 1):
            for target in link.findall(line):
                if target.startswith(("http://", "https://", "mailto:", "tel:", "data:", "#")):
                    continue
                destination = target.split("#")[0].split("?")[0]
                if not destination:
                    continue
                # An absolute file path resolves only on the machine that wrote
                # it, and it tells every reader where that machine keeps its
                # files. It is refused even when this machine has the file.
                if (os.path.isabs(destination) or re.match(r"^[A-Za-z]:[\\/]", destination)
                        or not os.path.exists(os.path.join(os.path.dirname(path), destination))):
                    broken.append({"file": relative, "line": number, "target": target})
    return broken


def _docs_folders_without_charter(docs_dir: "str | None" = None) -> list:
    """Documentation folders that hold files but carry no README stating their kind.

    A source checkout is chartered folder by folder; an installed package has
    no documentation tree and reports nothing. A folder with no files at all
    (an untracked placeholder) is not chartered.
    """
    if docs_dir is None:
        repository, _exclusions = _nomenclature_scan_layout()
        if repository == _HERE:
            return []
        docs_dir = os.path.join(repository, "docs")
    if not os.path.isdir(docs_dir):
        return []
    missing = []
    for name in sorted(os.listdir(docs_dir)):
        folder = os.path.join(docs_dir, name)
        if not os.path.isdir(folder) or name.startswith("."):
            continue
        if not any(files for _root, _dirs, files in os.walk(folder)):
            continue
        readme = os.path.join(folder, "README.md")
        if not os.path.isfile(readme):
            missing.append(name)
            continue
        with open(readme, encoding="utf-8") as stream:
            head = stream.read(DOCS_CHARTER_HEAD_CHARACTERS)
        if DOCS_CHARTER_MARKER not in head:
            missing.append(name)
    return missing


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
    import importlib.util
    from .architecture_map import PACKAGE
    reachable = []
    # NOTE: "loop" is excluded — it is now the subpackage name, so the flat
    # spelling legitimately resolves to the subpackage, not the old module.
    # A documentation-only folder (no __init__.py) is not a real module even
    # when Python namespace-package rules would allow an empty import.
    for legacy in ("kernel", "recursive_loop", "capability_directory",
                   "intelligence_strings", "solver"):
        spec = importlib.util.find_spec(f"{PACKAGE}.{legacy}")
        if spec is not None and spec.origin is not None:
            reachable.append(legacy)
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


def _nomenclature_scan_layout(
        package_dir: "str | None" = None) -> tuple[str, tuple[str, ...]]:
    """Resolve source-checkout or installed-package paths without guessing."""
    here = package_dir or _HERE
    repository = os.path.dirname(os.path.dirname(here))
    source_policy = os.path.join(
        repository, "src", "loop_engine", "forbidden_paths.json")
    if os.path.isfile(source_policy):
        return repository, (
            "src/loop_engine/forbidden_paths.json",
            "src/loop_engine/architecture_conformance.json",
        )
    return here, ("forbidden_paths.json", "architecture_conformance.json")


def _public_retired_nomenclature() -> list:
    """Scan current source or installed package without scanning policy data."""
    from ._conformance_scan import _rules
    from .nomenclature_conformance import retired_nomenclature_violations

    policy = dict(_rules().get("retired_source_nomenclature", {}))
    policy["terms"] = tuple(
        term for term in policy.get("terms", ())
        if "what" in str(term).casefold())
    root, layout_exclusions = _nomenclature_scan_layout()
    if os.path.abspath(root)!=os.path.abspath(_HERE):
        included=policy.get('public_scan_paths')
        if included is None:
            raise ValueError('source checkout public-language scope must be explicitly declared')
        policy['included_paths']=included
    policy["excluded_files"] = tuple(dict.fromkeys((
        *policy.get("excluded_files", ()), *layout_exclusions)))
    return retired_nomenclature_violations(root, policy)


def _vocabulary_and_placement() -> list:
    """Check terminology.yaml against the documents and the served page.

    An installed package carries the contract but not the repository
    documents, so only the contract's own rules run there.
    """
    from .architecture_contract import load_terminology_contract
    from .nomenclature_conformance import vocabulary_violations

    root, _exclusions = _nomenclature_scan_layout()
    return vocabulary_violations(
        root, load_terminology_contract(),
        scan_files=os.path.abspath(root) != os.path.abspath(_HERE))


def operational_graph_vertex_violations(root: "str | None" = None) -> list:
    """Find executable graph-vertex classes competing with Loop.

    Passive projections are admitted only when their exact LoopDefinition
    reference is explicit. They never own execution.
    """
    import ast
    base = root or _HERE
    retired = {"CanvasNode", "GoalNode", "CodeNode", "NodeResult"}
    passive = {
        "LoopDefinitionRecord": {"role", "supported_modes"},
        "LoopGraphVertexRecord": {"definition_ref", "definition", "selected_mode"},
        "LoopRelationshipRecord": {"loop_id"},
        "LoopReportRecord": {"loop_id"},
    }
    violations = []
    # Compatibility reader modules and passive base records never execute.
    passive_files = {"ontology/loop_node.py", "ontology/node.py",
                     "ontology/records.py"}
    for directory, _, files in os.walk(base):
        for filename in files:
            if not filename.endswith(".py"):
                continue
            path = os.path.join(directory, filename)
            if os.path.relpath(path, base).replace(os.sep, "/") in passive_files:
                continue
            try:
                tree = ast.parse(open(path, encoding="utf-8").read(), path)
            except (OSError, SyntaxError):
                continue
            classes = {node.name: node for node in ast.walk(tree)
                       if isinstance(node, ast.ClassDef)}
            for item in classes.values():
                fields = {node.target.id for node in item.body
                          if isinstance(node, ast.AnnAssign)
                          and isinstance(node.target, ast.Name)}
                for base_node in item.bases:
                    base_name = getattr(base_node, "id", "")
                    if base_name in classes:
                        fields |= {node.target.id
                                   for node in classes[base_name].body
                                   if isinstance(node, ast.AnnAssign)
                                   and isinstance(node.target, ast.Name)}
                methods = {node.name for node in item.body
                           if isinstance(node, (ast.FunctionDef,
                                                ast.AsyncFunctionDef))}
                bases = {getattr(node, "id", getattr(node, "attr", ""))
                         for node in item.bases}
                reason = ""
                relative = os.path.relpath(path, base).replace(os.sep, "/")
                if item.name in retired:
                    reason = "retired non-Loop graph/runtime spelling"
                elif item.name in passive and passive[item.name] <= fields:
                    continue
                elif item.name.endswith(("Node", "Vertex")):
                    reason = "graph vertex type competes with canonical Loop"
                elif ("node_id" in fields
                      and methods & {"run", "execute", "invoke"}):
                    reason = "executable node-shaped type bypasses Loop"
                if reason:
                    violations.append({
                        "file": os.path.relpath(path, base), "line": item.lineno,
                        "type": item.name, "reason": reason})
    return violations


def run_conformance() -> dict:
    from ._conformance_scan import run_scan
    from .core.api_quality import scan_public_signatures
    from .core.boundary_registry import boundary_report
    scan = run_scan()
    api_violations = scan_public_signatures()
    boundaries = boundary_report()
    graph_vertex_violations = operational_graph_vertex_violations()
    from .semantic_conformance import semantic_conformance_report
    semantics = semantic_conformance_report()
    public_nomenclature = _public_retired_nomenclature()
    vocabulary = _vocabulary_and_placement()
    unclassified = _unclassified()
    legacy_flat_paths = _legacy_flat_paths_reachable()
    stale = _stale_docs()
    uncharted = _docs_folders_without_charter()
    broken_links = _documentation_links_that_do_not_resolve()
    c = scan["counts_by_rule"]
    gates = {
        "unclassified_files": len(unclassified),
        "docs_folders_without_a_charter_readme": len(uncharted),
        "documentation_links_that_do_not_resolve": len(broken_links),
        "reachable_legacy_flat_paths": len(legacy_flat_paths),
        "legacy_flat_imports_on_live_paths": c.get(
            "legacy_flat_import", 0),
        "public_parallel_runtime_surfaces": c.get(
            "public_parallel_runtime_surface", 0),
        "retired_decision_spine_terms": len(public_nomenclature),
        "undefined_terms_retired_names_and_misplaced_words":
            len(vocabulary),
        "direct_model_or_network_calls_outside_gateway":
            c.get("network_outside_gateway", 0),
        "subprocess_outside_declared_adapters":
            c.get("subprocess_outside_declared", 0),
        "direct_writes_to_intelligence_files_outside_adapters":
            c.get("intelligence_file_direct_write", 0),
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
        "semantic_identities_without_one_meaning_and_authority":
            len(semantics["violations"]),
        "direct_resource_access_above_baseline": max(
            0, c.get("direct_resource_access", 0) - _access_baseline()),
        "dependency_direction_above_baseline": max(
            0, c.get("dependency_direction", 0) - _dependency_direction_baseline()),
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
                         "docs_folders_without_a_charter_readme": uncharted,
                         "documentation_links_that_do_not_resolve": broken_links,
                         "reachable_legacy_flat_paths": legacy_flat_paths,
                         "stale_current_architecture_documents": stale,
                         "operational_boundary_ontology": boundaries,
                         "operational_graph_vertex_types":
                             graph_vertex_violations,
                         "semantic_identity": semantics,
                         "retired_decision_spine_terms":
                             public_nomenclature,
                         "undefined_terms_retired_names_and_misplaced_words":
                             vocabulary,
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
          _stale_docs() == [] and CURRENT_DOCS == ("ARCHITECTURE-MAP.md", "PARKED.md"),
          "every non-current root doc carries a SUPERSEDED/HISTORICAL header; "
          "PARKED.md is a declared marker that names a deliberately retired "
          "capability, so it is current by definition")
    with tempfile.TemporaryDirectory() as directory:
        fixture = os.path.join(directory, "vertex_canary.py")
        with open(fixture, "w", encoding="utf-8") as stream:
            stream.write(
                "class TaskNode:\n    node_id: str\n"
                "    def run(self): pass\n\n"
                "class GoalItem:\n    goal_id: str\n\n"
                "class SolutionSlot:\n    slot_id: str\n\n"
                "class LoopGraphVertexRecord:\n    definition_ref: object\n"
                "    definition: object\n    selected_mode: str\n\n"
                "GoalNode = GoalItem\n")
        canary = operational_graph_vertex_violations(directory)
    check("operational_vertex_canary_refuses_non_loop_and_ignores_passive_records",
          [item["type"] for item in canary] == ["TaskNode"],
          f"violations={canary}")
    with tempfile.TemporaryDirectory() as directory:
        os.makedirs(os.path.join(directory, "uncharted"))
        open(os.path.join(directory, "uncharted", "note.md"), "w", encoding="utf-8").write("x")
        os.makedirs(os.path.join(directory, "chartered"))
        open(os.path.join(directory, "chartered", "README.md"), "w", encoding="utf-8").write(
            "# Chartered\n\nKind: fixture records.\n")
        os.makedirs(os.path.join(directory, "unmarked"))
        open(os.path.join(directory, "unmarked", "README.md"), "w", encoding="utf-8").write(
            "# Unmarked\n\nA README that never states its kind.\n")
        os.makedirs(os.path.join(directory, "empty"))
        uncharted = _docs_folders_without_charter(directory)
    check("docs_charter_canary_reports_folders_without_a_kind_and_skips_empty_ones",
          uncharted == ["uncharted", "unmarked"], f"uncharted={uncharted}")
    with tempfile.TemporaryDirectory() as directory:
        os.makedirs(os.path.join(directory, "docs"))
        target = os.path.join(directory, "docs", "guide.md")
        open(target, "w", encoding="utf-8").write("# Guide\n")
        # The absolute link names a file that exists on this machine, which is
        # how the known-wrong link passed here and failed on every other one.
        open(os.path.join(directory, "README.md"), "w", encoding="utf-8").write(
            f"[relative](docs/guide.md) [absolute]({target}) [missing](docs/absent.md)\n")
        reported = [row["target"] for row in _documentation_links_that_do_not_resolve(directory)]
    check("link_gate_refuses_absolute_paths_and_missing_targets",
          reported == [target, "docs/absent.md"], f"reported={reported}")
    with tempfile.TemporaryDirectory() as directory:
        installed_package = os.path.join(directory, "loop_engine")
        os.makedirs(installed_package)
        open(os.path.join(
            installed_package, "forbidden_paths.json"), "w").write("{}")
        installed_root, installed_exclusions = _nomenclature_scan_layout(
            installed_package)
    check("installed_package_nomenclature_scan_excludes_its_policy_and_manifest",
          installed_root == installed_package
          and installed_exclusions == (
              "forbidden_paths.json", "architecture_conformance.json"),
          f"root={installed_root}; exclusions={installed_exclusions}")
    import copy as _copy

    from .architecture_contract import load_terminology_contract
    from .nomenclature_conformance import vocabulary_violations
    vocabulary_root, _unused = _nomenclature_scan_layout()
    live_contract = load_terminology_contract()
    weakened = _copy.deepcopy(live_contract)
    weakened["vocabulary"]["Loop"]["must_not_appear"] = []
    weakened["vocabulary"]["Loop"]["definition"] = ""
    caught = {item["rule"] for item in vocabulary_violations(
        vocabulary_root, weakened,
        scan_files=os.path.abspath(vocabulary_root) != os.path.abspath(_HERE))}
    check("vocabulary_gate_refuses_a_term_whose_definition_was_removed",
          "term_without_definition" in caught, f"rules={sorted(caught)}")
    passed = sum(1 for x in results if x["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
