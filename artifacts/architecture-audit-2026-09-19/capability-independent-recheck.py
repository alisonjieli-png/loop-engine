"""Independent, offline public-path recheck of the three capability findings.

Only local trace callbacks execute. The model callback probe is not a model
call. Runtime source is never patched. No network or filesystem effect is
performed by an endpoint, and no provider integration is claimed.
"""
from __future__ import annotations

import hashlib
import importlib
import json
from dataclasses import replace
from pathlib import Path

from loop_engine.core.capability_directory import (
    CapabilityDirectory, CapabilityHandshake, Endpoint, default_directory)
from loop_engine.core.capability_invocation import CapabilityInvocationPolicy
from loop_engine.loop.capability_loops import run_capability_as_loop, run_capability_ref_as_loop
from loop_engine.loop.recursive_loop import LoopLedger


def main():
    probes, suites = [], []

    def record(name, passed, observation):
        probes.append({"name": name, "passed": bool(passed), "observation": observation})

    for name in ("loop_engine.core.capability_directory", "loop_engine.loop.capability_loops",
                 "loop_engine.core.host_runtime"):
        module = importlib.import_module(name)
        result = module.self_test()
        rows = result["tests"]
        suites.append({"module": name, "total": len(rows),
                       "failed": [row for row in rows if row.get("passed") is not True],
                       "not_tested": [row for row in rows if row.get("not_tested")]})

    for event, declaration_change in (("spec", True), ("tool_invocation_started", False)):
        calls = []
        directory = CapabilityDirectory()
        handshake = CapabilityHandshake("race", "static_component", "pure fixture", ("run",))
        directory.register(handshake, (Endpoint("run", lambda **_: calls.append("original") or {"ok": True}),))
        reference = directory.search_core("pure fixture")[0]

        class ReplacingLedger(LoopLedger):
            def record(self, **values):
                super().record(**values)
                if values.get("event") == event:
                    changed = (replace(handshake, effects=("writes_fs",), functionality="changed implementation")
                               if declaration_change else handshake)
                    directory.register(changed, (Endpoint("run", lambda **_: calls.append("replacement")
                                                          or {"ok": True}),), replace=True)

        try:
            result = run_capability_ref_as_loop(directory, reference, "run", ledger=ReplacingLedger())
            observation = {"calls": calls, "ok": result["ok"], "reported_effects": result["effects"]}
            refused = False
        except ValueError as error:
            observation = {"calls": calls, "error": type(error).__name__ + ": " + str(error)}
            refused = True
        record("replacement_after_selection_" + event, refused and not calls, observation)

    privacy = ["internal"]
    try:
        handshake = CapabilityHandshake("mutable", "static_component", "fixture", ("run",), privacy_class=privacy)
        privacy.append("public")
        record("mutable_scalar_declaration", False, {"accepted": True, "held": handshake.privacy_class})
    except ValueError as error:
        record("mutable_scalar_declaration", True, {"accepted": False, "error": str(error)})

    calls = []
    try:
        directory = default_directory(llm_invoke=lambda **_: calls.append("model_adapter") or {"ok": True})
        result = run_capability_as_loop(directory, "llm_pipeline", "invoke")
        record("obsolete_arbitrary_model_callback", False,
               {"calls": calls, "effects": result["effects"], "model_calls": result["model_calls"]})
    except TypeError as error:
        record("obsolete_arbitrary_model_callback", not calls, {"calls": calls, "error": str(error)})

    for value in (float("inf"), float("nan"), True):
        try:
            CapabilityHandshake("limits", "static_component", "fixture", ("run",), timeout_seconds=value)
            refused = False
        except ValueError:
            refused = True
        record("invalid_timeout_" + str(value), refused, {"value": str(value), "refused": refused})

    calls = []
    directory = CapabilityDirectory()
    handshake = CapabilityHandshake("future", "static_component", "fixture", ("run",), protocol_version="future/v9")
    directory.register(handshake, (Endpoint("run", lambda **_: calls.append("ran")),))
    try:
        run_capability_as_loop(directory, "future", "run")
        refused = False
    except ValueError:
        refused = True
    record("governed_unsupported_version", refused and not calls, {"refused": refused, "calls": calls})

    for versions, expected in ((("version-A",), ["a"]), (("version-A", "version-B"), ["a", "b"])):
        calls = []
        directory = CapabilityDirectory()
        handshake = CapabilityHandshake("a", "static_component", "fixture", ("run",), protocol_version="version-A")

        def failing_endpoint():
            calls.append("a")
            raise RuntimeError("fixture failure")

        directory.register(handshake, (Endpoint("run", failing_endpoint, ("b", "run")),))
        directory.register(replace(handshake, surface="b", protocol_version="version-B"),
                           (Endpoint("run", lambda: calls.append("b")),))
        try:
            result = directory.call("a", "run", policy=CapabilityInvocationPolicy(supported_protocol_versions=versions))
            observation = {"ok": result.ok, "calls": calls, "used_fallback": result.used_fallback}
            expected_outcome = len(versions) == 2 and result.ok and result.used_fallback
        except ValueError as error:
            observation = {"error": str(error), "calls": calls}
            expected_outcome = len(versions) == 1
        record("fallback_versions_" + ",".join(versions), expected_outcome and calls == expected, observation)

    calls = []
    directory = CapabilityDirectory()
    for source, target in (("a", "b"), ("b", "a")):
        def fail(source=source):
            calls.append(source)
            raise ValueError(source)
        directory.register(CapabilityHandshake(source, "static_component", "cycle fixture", ("run",)),
                           (Endpoint("run", fail, (target, "run")),))
    try:
        directory.call("a", "run")
        refused = False
    except RuntimeError:
        refused = True
    record("two_surface_cycle", refused and calls == ["a", "b"], {"refused": refused, "calls": calls})

    calls = []
    directory = CapabilityDirectory()
    handshake = CapabilityHandshake("x", "static_component", "fixture", ("run", "get"))
    directory.register(handshake, (Endpoint("run", lambda: calls.append("old-run")),
                                   Endpoint("get", lambda: calls.append("old-get"))),
                       default_fallback=("x", "get"))
    current = replace(handshake, operations=("run",))
    directory.register(current, (Endpoint("run", lambda: calls.append("new-run")),), replace=True)
    missing = directory.call("x", "get")
    record("replacement_cleanup", not missing.ok and not calls and "x" not in directory._default_fallback,
           {"ok": missing.ok, "calls": calls, "fallback": directory._default_fallback.get("x")})
    try:
        directory.register(current, (Endpoint("get", lambda: calls.append("invalid")),), replace=True)
        refused = False
    except RuntimeError:
        refused = True
    record("invalid_replacement_preserves_registration", refused and directory.handshake("x") == current
           and set(directory._ep) == {("x", "run")}, {"refused": refused, "calls": calls})

    result = run_capability_as_loop(default_directory(), "llm_pipeline", "invoke")
    record("missing_model_executor", not result["ok"] and result["value"]["error_code"] == "model_executor_unavailable"
           and result["value"]["asked_model"] is False and result["attempts"] == 1,
           {key: result[key] for key in ("ok", "value", "attempts", "model_calls", "capability_terminal_code")})

    paths = [Path(importlib.import_module(name).__file__) for name in (
        "loop_engine.core.capability_directory", "loop_engine.core.capability_directory_checks",
        "loop_engine.core.capability_invocation", "loop_engine.loop.capability_loops",
        "loop_engine.core.host_runtime", "loop_engine.core.host_completion_checks")]
    result = {"record_type": "capability_independent_recheck/v1", "suites": suites, "probes": probes,
              "passed": all(row["passed"] for row in probes)
              and not any(row["failed"] or row["not_tested"] for row in suites),
              "source_sha256": {str(path.relative_to(Path.cwd())):
                                hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(paths)},
              "limitations": ["Local callback and declaration tests only; no provider or model call occurred.",
                              "Reentrant replacement is deterministic concurrency scheduling, not a multi-process stress test.",
                              "Registration remains trusted host configuration, not an operating-system sandbox.",
                              "This is not full repository conformance, installation, or production qualification."]}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
