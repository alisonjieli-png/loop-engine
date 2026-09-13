"""Score one run's history against the full-spectrum aspect list.

Offline, stdlib-only. Each aspect reports PASS (observed), ABSENT (never
fired — a coverage gap, not a failure), or FAIL (fired and went wrong).
Usage: python tools/spectrum_score.py <events.jsonl> [events2.jsonl ...]
"""
from __future__ import annotations

import json
import sys
from collections import Counter

KERNEL = ("orient", "standardize_task", "frame_alternatives",
          "reconcile_horizon", "assess_prepare", "decide_next", "how",
          "forecast_outcome", "act", "verify", "calibrate",
          "integrate_commit", "route")
RECOVERY = ("diagnose_stall", "propose_recovery", "adjudicate_recovery")


def load(path: str) -> list:
    events = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            try:
                events.append(json.loads(line))
            except ValueError:
                pass
    return events


def score(events: list) -> dict:
    steps = Counter(e.get("step") or "" for e in events)
    inits = [e for e in events if e.get("event_type") == "loop_init"]
    profs = Counter()
    rels = Counter()
    for e in inits:
        d = e.get("detail") or {}
        profs[d.get("profile_id") or "?"] += 1
        rels[d.get("relationship_kind") or "?"] += 1
    blob = "\n".join(json.dumps(e.get("detail") or {}) for e in events)
    invocations = [e for e in events
                   if e.get("event_type") == "model_invocation"]
    aspects = {}
    aspects["harness_processes"] = (
        "PASS" if "run_external_harness" in steps else "ABSENT")
    aspects["cognitive_steps"] = {
        node: ("PASS" if steps.get(node) else "ABSENT") for node in KERNEL}
    aspects["recovery_ladder"] = {
        node: ("PASS" if steps.get(node) else "ABSENT")
        for node in RECOVERY}
    intel = {p: profs.get(p, 0) for p in
             ("intelligence.context.serve", "intelligence.code.resolve",
              "intelligence.code.invoke", "intelligence.code.package",
              "intelligence.runtime_history_solution.search",
              "intelligence.runtime_history_solution.replay",
              "intelligence.user_feedback.interpret")}
    aspects["intelligence_layers"] = {
        k: ("PASS" if v else "ABSENT") for k, v in intel.items()}
    aspects["fingerprinting"] = (
        "PASS" if "fingerprint" in blob.lower() else "ABSENT")
    aspects["memory_artifacts"] = (
        "PASS" if "artifact" in blob.lower() else "ABSENT")
    aspects["canvas_pipeline"] = (
        "PASS" if profs.get("solution.pipeline") else "ABSENT")
    aspects["canvas_atomic"] = (
        "PASS" if profs.get("solution.atomic_component") else "ABSENT")
    aspects["connected_loops"] = (
        "PASS" if rels.get("connected_from") else "ABSENT")
    aspects["validators"] = (
        "PASS" if profs.get("solution.validator") else "ABSENT")
    aspects["model_calls"] = len(invocations)
    aspects["spawned_loops"] = rels.get("spawned_by", 0)
    aspects["retrieved_loops"] = rels.get("retrieved_by", 0)
    return {"aspects": aspects, "loops": len(
        {e.get("loop_id") for e in events if e.get("loop_id")}),
        "events": len(events)}


def main(argv=None) -> int:
    paths = (argv or sys.argv)[1:]
    if not paths:
        print("usage: spectrum_score.py <events.jsonl> [...]")
        return 2
    for path in paths:
        result = score(load(path))
        print("=" * 20, path.split("/")[-2][:50])
        print(f"loops={result['loops']} events={result['events']} "
              f"calls={result['aspects']['model_calls']} "
              f"spawned={result['aspects']['spawned_loops']} "
              f"retrieved={result['aspects']['retrieved_loops']}")
        for key, value in result["aspects"].items():
            if isinstance(value, dict):
                missing = sorted(k for k, v in value.items() if v != "PASS")
                print(f"  {key}: "
                      f"{'ALL' if not missing else 'MISSING ' + ','.join(missing)}")
            elif key not in ("model_calls", "spawned_loops",
                             "retrieved_loops"):
                print(f"  {key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
