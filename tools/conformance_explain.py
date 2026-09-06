#!/usr/bin/env python3
"""Report EVERY conformance violation at once, each with the exact fix.

Why this exists.  Adding one module to this package cost six iterations of a
150-second suite run, because the gates surface one violation at a time as a
post-hoc refusal with no suggested repair.  Every one of those violations was
statically detectable the moment the file was saved.

That is the same defect the runtime has: a correct constraint whose legal shape
is implicit, delivered only as a refusal, produces an agent that cannot
converge.  A model inside the solve loop hits it against the capability
contract; a developer hits it against the conformance contract.

This tool inverts the loop for the conformance half: all violations, at once,
each with the edit that resolves it.  Seconds, not minutes.  It lives outside
``src/loop_engine`` deliberately, so it adds no conformance surface of its own.

Usage:
    python3 tools/conformance_explain.py
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(HERE), "src")
sys.path.insert(0, SRC)

PACKAGE = os.path.join(SRC, "loop_engine")
RULES_PATH = os.path.join(PACKAGE, "forbidden_paths.json")

#: rule -> (what it protects, the exact edit that resolves a violation)
REPAIRS = {
    "dynamic_import_bypass": (
        "importing by name at runtime can load code the registry never saw",
        "Do not import importlib/__import__ in engine code. If you must load a "
        "generated artifact, run it in a separate process instead (see "
        "core/differential_verification.py), or add the file to "
        "'dynamic_import_allowed_modules' in forbidden_paths.json with a reason.",
    ),
    "subprocess_outside_declared": (
        "the allowlist IS the 'model output never reaches a shell' guarantee",
        "Add '<subpackage>/<module>.py' to 'subprocess_allowed_modules' in "
        "forbidden_paths.json. Keep the list short and auditable.",
    ),
    "uncollected_self_test": (
        "a self_test() the suite never runs is a test that does not exist",
        "Add 'core.<module>' to the collection list in _self_test.py.",
    ),
    "unmapped_module": (
        "an unmapped module is invisible to the architecture census",
        "Add '<module>' to the correct subpackage tuple in architecture_map.py, "
        "then regenerate ARCHITECTURE-MAP.md (see 'architecture_map_freshness').",
    ),
    "architecture_map_freshness": (
        "a committed map that disagrees with the live projection is drift",
        "Regenerate: python3 -c \"from loop_engine.architecture_map import "
        "render_map; import loop_engine, os; "
        "p=os.path.join(os.path.dirname(loop_engine.__file__),"
        "'ARCHITECTURE-MAP.md'); open(p,'w').write(render_map())\"",
    ),
    "retired_source_nomenclature": (
        "retired vocabulary (e.g. 'child') implies a node hierarchy that the "
        "Loop constitution forbids",
        "Reword the prose. 'child process' -> 'separate process'. This rule is "
        "vocabulary policing with real cost and little safety value; consider "
        "demoting it to a warning.",
    ),
    "eval_or_exec": (
        "dynamic execution of model output is the highest-severity escape",
        "Remove it. If genuinely required, add to 'eval_exec_allowed_modules'.",
    ),
    "network_outside_declared": (
        "undeclared egress is an SSRF and exfiltration surface",
        "Add the module to 'network_allowed_modules' in forbidden_paths.json.",
    ),
}


#: This tool runs the detector rules and the gates that are cheap to
#: evaluate. It does NOT run the whole conformance report, so a CLEAN here
#: is a strong signal and not a guarantee. Saying so is the point: an
#: earlier version of this tool reported CLEAN while the suite was failing
#: `architecture_map_freshness`, and a fast checker that can say CLEAN when
#: the suite is red is worse than no fast checker at all.
COVERAGE_CAVEAT = (
    "  note: detector rules + cheap gates only. The full report also "
    "computes\n        scan-dependent gates; run the suite before "
    "claiming green.")


def _cheap_gates() -> dict:
    """Evaluate the gates that cost nothing, so CLEAN means a little more."""
    failures = {}
    try:
        from loop_engine.conformance_report import _stale_architecture_map
        stale = _stale_architecture_map()
        if stale:
            failures["architecture_map_freshness"] = (
                stale,
                "ARCHITECTURE-MAP.md is generated -- do not hand-edit it. "
                "Regenerate: python3 -c \"from loop_engine.architecture_map "
                "import render_map; "
                "open('src/loop_engine/ARCHITECTURE-MAP.md','w')"
                ".write(render_map())\"")
    except Exception as exc:                           # noqa: BLE001
        failures["architecture_map_freshness"] = (
            -1, f"gate could not be evaluated: {exc!r}")
    return failures


def main() -> int:
    from loop_engine import _conformance_scan as scan

    with open(RULES_PATH, encoding="utf-8") as handle:
        rules = json.load(handle)

    violations = []
    for detector in scan.DETECTORS:
        try:
            violations.extend(detector(PACKAGE, rules) or [])
        except Exception as exc:                       # noqa: BLE001
            print(f"  ! detector {detector.__name__} errored: {exc!r}")

    gate_failures = _cheap_gates()

    if not violations and not gate_failures:
        print("conformance: CLEAN — detectors and cheap gates pass.")
        print(COVERAGE_CAVEAT)
        return 0

    if gate_failures:
        print(f"zero-tolerance gates: {len(gate_failures)} failing\n")
        for name, (count, repair) in sorted(gate_failures.items()):
            print(f"── {name}  ({count})")
            print(f"   FIX: {repair}\n")
        if not violations:
            print(COVERAGE_CAVEAT)
            return 1

    by_rule: dict[str, list] = {}
    for item in violations:
        by_rule.setdefault(item.get("rule", "unknown"), []).append(item)

    print(f"conformance: {len(violations)} violation(s) "
          f"across {len(by_rule)} rule(s)\n")
    for rule, items in sorted(by_rule.items()):
        protects, repair = REPAIRS.get(
            rule, ("(no repair recorded for this rule)", "See _conformance_scan.py."))
        print(f"── {rule}  ({len(items)})")
        print(f"   protects: {protects}")
        for item in items[:10]:
            where = item.get("file", "?")
            line = item.get("line") or 0
            detail = (item.get("detail") or "").strip()
            print(f"     {where}"
                  + (f":{line}" if line else "")
                  + (f"  — {detail}" if detail else ""))
        if len(items) > 10:
            print(f"     … and {len(items) - 10} more")
        print(f"   FIX: {repair}\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
