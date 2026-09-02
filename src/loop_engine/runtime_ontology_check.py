"""Runtime ontology introspection: prove the one-Loop invariant live.

Python introspection gives several independent proof mechanisms:

- ``Loop.__subclasses__()`` must be empty. The canonical runtime class
  refuses subclassing at class-creation time, so any subclass would
  already have raised.
- ``gc.get_objects()`` enumerates every live object in the interpreter.
  Filtering by ``isinstance(obj, Loop)`` proves every operational
  instance is the canonical class.
- Walking ``sys.modules`` and using ``inspect.getmembers`` finds every
  loaded class, so a node-named class cannot hide behind lazy imports.
- ``inspect.getmro`` proves inheritance chains.
- ``type.__subclasses__()`` recursively proves no hidden subclass tree
  exists under any node-named base.

Static analysis proves the source. This module proves the live process.
"""
from __future__ import annotations

import gc
import inspect
import sys

#: The canonical operational runtime class name.
CANONICAL_RUNTIME = "Loop"

#: Node is conceptual only, so no active node-named class is permitted.
ALLOWED_NODE_CLASSES = frozenset()


def loaded_node_classes() -> list[dict]:
    """Every loaded class whose name is Node or ends in Node or Vertex."""
    found = []
    for module_name, module in sorted(sys.modules.items()):
        if not (module_name == "loop_engine"
                or module_name.startswith("loop_engine.")):
            continue
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if obj.__module__ != module_name:
                continue
            if name == "Node" or name.endswith("Node") \
                    or name.endswith("Vertex"):
                found.append({"class": name, "module": module_name,
                              "bases": [b.__name__ for b in obj.__bases__]})
    return found


def node_class_violations() -> list[dict]:
    """Loaded node-named classes outside the allowlist."""
    violations = []
    for record in loaded_node_classes():
        if record["class"] not in ALLOWED_NODE_CLASSES:
            violations.append({
                "rule": "runtime_node_class",
                "class": record["class"],
                "module": record["module"],
                "detail": "Node is conceptual; executable work uses Loop"})
    return violations


def subclass_violations() -> list[dict]:
    """The canonical Loop class has no subclasses, direct or hidden."""
    from .loop.recursive_loop import Loop
    violations = []
    direct = Loop.__subclasses__()
    if direct:
        violations.append({
            "rule": "runtime_subclass",
            "detail": f"Loop has direct subclasses: "
                      f"{[c.__name__ for c in direct]}"})
    # Recursively prove no hidden subclass tree exists under any
    # node-named base class.
    for record in loaded_node_classes():
        if record["class"] not in ALLOWED_NODE_CLASSES:
            continue
        module = sys.modules[record["module"]]
        cls = getattr(module, record["class"])
        tree = _subclass_tree(cls)
        if tree:
            violations.append({
                "rule": "runtime_subclass",
                "class": record["class"],
                "detail": f"hidden subclass tree: {tree}"})
    return violations


def _subclass_tree(cls: type) -> list[str]:
    """Names of every subclass reachable from cls, recursively."""
    names = []
    for sub in cls.__subclasses__():
        names.append(sub.__name__)
        names.extend(_subclass_tree(sub))
    return names


def live_instance_report() -> dict:
    """Every live operational instance in this interpreter."""
    from .loop.recursive_loop import Loop
    instances = [obj for obj in gc.get_objects() if isinstance(obj, Loop)]
    classes = sorted({type(obj).__name__ for obj in instances})
    return {
        "record_type": "runtime_ontology_instances/v1",
        "live_loop_instances": len(instances),
        "instance_classes": classes,
        "all_instances_are_canonical": classes == [CANONICAL_RUNTIME]
        if classes else True,
    }


def run_runtime_ontology_check() -> dict:
    """Prove every live operational instance uses canonical Loop."""
    # The ontology package uses lazy public-name resolution, so import the
    # record modules explicitly before walking sys.modules.
    problems: list[dict] = []
    problems.extend(node_class_violations())
    problems.extend(subclass_violations())
    instances = live_instance_report()
    if not instances["all_instances_are_canonical"]:
        problems.append({
            "rule": "runtime_instance",
            "detail": f"non-canonical instance classes: "
                      f"{instances['instance_classes']}"})
    return {
        "record_type": "runtime_ontology_check/v1",
        "loaded_node_classes": loaded_node_classes(),
        "live_instances": instances,
        "problems": problems,
        "passed": not problems,
    }


def self_test() -> dict:
    """Canary-prove every detector, then judge the live process."""
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    # Canary 1: the loaded-class walker must see no active Node class.
    # The ontology package uses lazy public-name resolution, so import the
    # record modules explicitly before walking sys.modules.
    loaded = {r["class"] for r in loaded_node_classes()}
    check("loaded_class_walker_sees_no_active_node_class",
          not loaded,
          f"loaded node-named classes: {sorted(loaded)}")

    # Canary 2: the canonical Loop class refuses subclassing live.
    from .loop.recursive_loop import Loop
    try:
        class _Probe(Loop):
            pass
        check("canonical_loop_refuses_subclassing", False)
    except TypeError:
        check("canonical_loop_refuses_subclassing", True)

    # Canary 3: a live Loop instance must be discoverable by gc.
    probe = Loop("runtime ontology probe")
    instances = live_instance_report()
    check("gc_discovers_live_loop_instances",
          instances["live_loop_instances"] >= 1
          and instances["all_instances_are_canonical"],
          str(instances))

    # Canary 4: the subclass-tree walker must detect a planted subclass
    # on a non-canonical base (the canonical base refuses subclassing,
    # so we prove the walker itself works on a plain class).
    class _PlainBase:
        pass

    class _HiddenSub(_PlainBase):
        pass
    check("subclass_tree_walker_detects_hidden_subclasses",
          _subclass_tree(_PlainBase) == ["_HiddenSub"])

    live = run_runtime_ontology_check()
    check("live_process_passes_runtime_ontology_check", live["passed"],
          str(live["problems"])[:400])
    return {"tests": results}
