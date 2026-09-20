"""Read-only runtime mutation controls for the September 19 capability patch.

Each mutation replaces a live function only inside this owned Python process.
No endpoint opens a network connection, writes a file, or calls a model. The
runner prints its report; the invoking agent saves that report with apply_patch.
A setup failure or an unexplained exception is not a killed mutant. A kill
requires an independently observed bad behavior and an explicit failed owning
regression record named in that mutation's expected test set.
"""
from __future__ import annotations

from contextlib import ExitStack
from dataclasses import replace
import hashlib
import inspect
import json
from pathlib import Path
import sys
import textwrap
from unittest.mock import patch

from loop_engine.core import capability_directory as directory_module
from loop_engine.core import capability_directory_checks as directory_checks
from loop_engine.core import capability_invocation as invocation_module
from loop_engine.loop import capability_loops as loops


def source_hashes():
    paths = [Path(module.__file__) for module in (
        directory_module, directory_checks, invocation_module, loops)]
    paths.append(Path(__file__).with_name("capability-independent-recheck.py"))
    return {str(path.relative_to(Path.cwd())): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(paths)}


def suites():
    captured, reports, errors = [], [], []
    watched = {directory_checks.registration_checks.__code__, directory_checks.run_checks.__code__,
               loops._invocation_policy_checks.__code__, loops.self_test.__code__}

    def trace(frame, event, argument):
        if event == "return" and frame.f_code in watched:
            for name in ("tests", "results"):
                rows = frame.f_locals.get(name)
                if isinstance(rows, list):
                    captured.extend(dict(row) for row in rows if isinstance(row, dict))
        return trace

    previous = sys.gettrace()
    sys.settrace(trace)
    try:
        for name, run in ((directory_module.__name__, directory_module.self_test),
                          (loops.__name__, loops.self_test)):
            try:
                result = run()
                rows = result["tests"]
                captured.extend(rows)
                reports.append({"module": name, "executed": len(rows),
                                "passed": sum(row["passed"] is True for row in rows)})
            except Exception as error:
                errors.append({"module": name, "type": type(error).__name__, "message": str(error)})
    finally:
        sys.settrace(previous)
    failures = {}
    for row in captured:
        if row.get("passed") is False:
            failures[row.get("test") or row.get("name")] = row
    return {"suites": reports, "failed_records": list(failures.values()), "runtime_errors": errors}


def probe(kind):
    """Observe only local known-wrong behavior, independent of the owning suite."""
    Handshake = directory_module.CapabilityHandshake
    Directory = directory_module.CapabilityDirectory
    Endpoint = directory_module.Endpoint
    Policy = invocation_module.CapabilityInvocationPolicy
    calls = []
    if kind == "handshake_sequence":
        values = ["pure"]
        record = Handshake("fixture", "static_component", "fixture", ("run",), effects=values)
        values.append("writes_fs")
        return {"known_wrong_observed": tuple(record.effects) != ("pure",), "held": list(record.effects)}
    if kind == "policy_sequence":
        values = ["1.0.0"]
        record = Policy(supported_protocol_versions=values)
        values.append("future")
        return {"known_wrong_observed": tuple(record.supported_protocol_versions) != ("1.0.0",),
                "held": list(record.supported_protocol_versions)}
    if kind in ("scalar", "finite"):
        values = {"privacy_class": []} if kind == "scalar" else {"timeout_seconds": float("nan")}
        try:
            Handshake("fixture", "static_component", "fixture", ("run",), **values)
            accepted = True
        except ValueError:
            accepted = False
        return {"known_wrong_observed": accepted, "accepted_invalid_field": next(iter(values)) if accepted else None}
    if kind == "model_absence":
        result = directory_module.default_directory().call("llm_pipeline", "invoke")
        return {"known_wrong_observed": result.ok, "ok": result.ok, "value": result.value}
    directory = Directory()
    def original(**_):
        calls.append("original")
        return {"ok": True}
    def alternate(**_):
        calls.append("alternate")
        return {"ok": True}
    handshake = Handshake("fixture", "static_component", "fixture", ("run", "get"))
    endpoint = Endpoint("run", original)
    if kind in ("endpoint_cleanup", "fallback_cleanup"):
        directory.register(handshake, (endpoint, Endpoint("get", alternate)),
                           default_fallback=("fixture", "get"))
        directory.register(replace(handshake, operations=("run",)), (endpoint,), replace=True)
        stale_endpoint = ("fixture", "get") in directory._ep
        stale_fallback = "fixture" in directory._default_fallback
        return {"known_wrong_observed": stale_endpoint if kind == "endpoint_cleanup" else stale_fallback,
                "stale_endpoint": stale_endpoint, "stale_fallback": stale_fallback}
    if kind in ("version_negotiation", "version_dispatch"):
        handshake = replace(handshake, protocol_version="future/v99")
        directory.register(handshake, (endpoint,))
        if kind == "version_negotiation":
            result = directory.negotiate("fixture", ("run",))
            return {"known_wrong_observed": result["ok"], "negotiation": result}
        try:
            result = directory.call("fixture", "run")
            refused = False
        except ValueError:
            refused = True
        return {"known_wrong_observed": not refused and calls == ["original"],
                "refused": refused, "calls": calls}
    directory.register(handshake, (endpoint,))
    digest = invocation_module.capability_handshake_digest(handshake)
    policy = Policy(False, digest, original)
    if kind == "digest_pin":
        directory.register(replace(handshake, functionality="changed after selection"), (endpoint,), replace=True)
    if kind == "callable_pin":
        directory.register(handshake, (Endpoint("run", alternate),), replace=True)
    if kind == "local_callable":
        class ChangingEndpoint:
            fallback = None
            reads = 0
            @property
            def fn(self):
                self.reads += 1
                return original if self.reads == 1 else alternate
        endpoint = ChangingEndpoint()
        directory._ep[("fixture", "run")] = endpoint
    if kind in ("digest_pin", "callable_pin", "local_callable"):
        try:
            directory.call("fixture", "run", policy=policy)
            refused = False
        except ValueError:
            refused = True
        wrong = (calls == ["alternate"] if kind in ("callable_pin", "local_callable") else bool(calls))
        return {"known_wrong_observed": wrong, "refused": refused, "calls": calls}
    if kind in ("governed_policy_forwarding", "governed_explicit_fallback"):
        def fail(**_):
            calls.append("failed-primary")
            raise ValueError("local fixture failure")
        directory.register(handshake, (Endpoint("run", fail, ("fallback", "run")),), replace=True)
        directory.register(replace(handshake, surface="fallback"), (Endpoint("run", alternate),))
        kwargs = {"invocation_policy": Policy(True)} if kind == "governed_explicit_fallback" else {}
        try:
            result = loops.run_capability_as_loop(directory, "fixture", "run", **kwargs)
            refused = False
        except loops.CapabilityLoopError:
            refused = True
        return {"known_wrong_observed": "alternate" in calls, "refused": refused, "calls": calls}
    raise ValueError("unknown probe fixture")


def cases():
    H = directory_module.CapabilityHandshake
    D = directory_module.CapabilityDirectory
    P = invocation_module.CapabilityInvocationPolicy
    return [
        ("negotiation_version_guard", D, "negotiate", "version_supported = h.protocol_version in policy.supported_protocol_versions",
         "version_supported = True", "version_negotiation", ("unknown_protocol_version_refuses_negotiation_and_dispatch",)),
        ("dispatch_version_guard", P, "bind", "if handshake.protocol_version not in self.supported_protocol_versions:",
         "if False:", "version_dispatch", ("unknown_protocol_version_refuses_negotiation_and_dispatch",)),
        ("handshake_sequence_copy", H, "__post_init__", "object.__setattr__(self, name, tuple(values))",
         "pass", "handshake_sequence", ("handshake_copies_caller_owned_sequences",)),
        ("invocation_version_sequence_copy", P, "__post_init__", "object.__setattr__(self, \"supported_protocol_versions\", tuple(versions))",
         "pass", "policy_sequence", ("explicit_supported_version_is_required_and_immutable",)),
        ("scalar_text_validation", H, "__post_init__", "descriptor.type == \"str\" and",
         "False and", "scalar", ("all_scalar_handshake_fields_refuse_mutable_or_unbounded_values",)),
        ("finite_timeout_validation", H, "__post_init__", "not math.isfinite(self.timeout_seconds)",
         "False", "finite", ("all_scalar_handshake_fields_refuse_mutable_or_unbounded_values",)),
        ("stale_endpoint_cleanup", D, "register", "self._ep = {key: value for key, value in self._ep.items() if key[0] != handshake.surface}",
         "pass", "endpoint_cleanup", ("replacement_removes_old_endpoints_and_fallbacks",)),
        ("stale_fallback_cleanup", D, "register", "self._default_fallback.pop(handshake.surface, None)",
         "pass", "fallback_cleanup", ("replacement_removes_old_endpoints_and_fallbacks",)),
        ("dispatch_handshake_digest_pin", P, "bind", "if (self.expected_handshake_digest and self.expected_handshake_digest",
         "if (False and self.expected_handshake_digest", "digest_pin", ("handshake_drift_refuses_before_any_endpoint_or_fallback",)),
        ("dispatch_callable_pin", P, "bind", "if self.expected_callable is not None and function is not self.expected_callable:",
         "if False:", "callable_pin", ("callable_swap_refuses_before_any_endpoint_or_fallback",)),
        ("single_callable_lookup", D, "_call", "value = function(**kwargs)",
         "value = ep.fn(**kwargs)", "local_callable", ("directory_binds_the_callable_locally_only_once",)),
        ("model_absence_cannot_succeed", directory_module, "default_directory",
         '\"ok\": False, \"error_code\": \"model_executor_unavailable\"',
         '\"ok\": True, \"error_code\": \"model_executor_unavailable\"', "model_absence",
         ("an_absent_model_executor_is_unavailable_not_a_canned_success",)),
        ("governed_policy_forwarding", loops, "run_capability_as_loop",
         "ledger=_LoopScopedLedger(lp.ledger, lp.loop_id), policy=invocation_policy,",
         "ledger=_LoopScopedLedger(lp.ledger, lp.loop_id), policy=None,", "governed_policy_forwarding",
         ("canonical_capability_loop_forwards_pinned_no_fallback_policy", "a_governed_attempt_does_not_silently_select_a_fallback")),
        ("governed_explicit_auto_fallback_refusal", loops, "run_capability_as_loop",
         " or invocation_policy.allow_fallback", "", "governed_explicit_fallback",
         ("a_single_attempt_refuses_automatic_fallback_authority",)),
    ]


def main():
    before = source_hashes()
    baseline = suites()
    controls = []
    for name, target, attribute, old, new, kind, expected in cases():
        record = {"mutant": name, "target": target.__name__ + "." + attribute,
                  "removed": old, "replacement": new, "expected_regressions": list(expected)}
        try:
            original = getattr(target, attribute)
            source = inspect.getsource(original)
            occurrences = source.count(old)
            if occurrences != 1:
                raise ValueError(f"expected one mutation site, found {occurrences}")
            namespace = dict(original.__globals__)
            transformed = "from __future__ import annotations\n" + textwrap.dedent(source.replace(old, new))
            exec(compile(transformed, "<capability-mutant:" + name + ">", "exec"), namespace)
            mutant = namespace[attribute]
            record["setup"] = {"status": "installed", "sites": occurrences,
                               "mutated_function_sha256": hashlib.sha256(transformed.encode()).hexdigest()}
        except Exception as error:
            record.update(status="setup_failed", setup={"status": "failed", "type": type(error).__name__,
                                                        "message": str(error)})
            controls.append(record)
            continue
        with ExitStack() as stack:
            stack.enter_context(patch.object(target, attribute, mutant))
            if attribute == "default_directory":
                stack.enter_context(patch.object(directory_checks, attribute, mutant))
            try:
                record["independent_bad_behavior"] = probe(kind)
            except Exception as error:
                record["independent_bad_behavior"] = {"known_wrong_observed": False,
                    "probe_error": {"type": type(error).__name__, "message": str(error)}}
            record["owning_checks"] = suites()
        failed = {row.get("test") or row.get("name") for row in record["owning_checks"]["failed_records"]}
        killed = record["independent_bad_behavior"]["known_wrong_observed"] and bool(failed.intersection(expected))
        if killed:
            record["status"] = "killed_by_named_regression"
        elif record["owning_checks"]["runtime_errors"] or "probe_error" in record["independent_bad_behavior"]:
            record["status"] = "inconclusive_runtime_error"
        else:
            record["status"] = "survived"
        controls.append(record)
    restored = suites()
    after = source_hashes()
    clean = lambda report: not report["failed_records"] and not report["runtime_errors"]
    result = {"record_type": "capability_mutation_controls/v1", "baseline": baseline,
              "mutants": controls, "restored": restored, "source_sha256": before,
              "runtime_sources_unchanged": before == after,
              "setup_failures": sum(row["status"] == "setup_failed" for row in controls),
              "killed": sum(row["status"] == "killed_by_named_regression" for row in controls),
              "total_mutants": len(controls),
              "passed": clean(baseline) and clean(restored) and before == after
                        and all(row["status"] == "killed_by_named_regression" for row in controls),
              "limits": ["Deterministic local fixture callbacks only; no provider call or endpoint filesystem effect.",
                         "Mutation setup failures and unexplained exceptions are never counted as kills.",
                         "Trace capture preserves explicit failing regression rows when a later validation aborts a suite.",
                         "Not a concurrency stress test, sandbox qualification, or full release gate."]}
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
