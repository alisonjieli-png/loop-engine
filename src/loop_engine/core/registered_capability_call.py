"""One capability handle that reaches every registered code capability by name.

Code capabilities were reachable only by importing the package that defines
them, which made them libraries rather than parts of a run. This module adds
the general path: a Practitioner selects one handle, names the surface and
the operation it needs, and the call goes through the capability directory
the run was given. A new family becomes reachable by registering a surface,
never by adding a branch here, and the list a model sees is built from the
directory rather than written down twice.

Effects stay bound to the exact request. This handle carries no effect
authority, so a surface that declares anything beyond a pure effect is
refused here by name and needs a capability path that carries the matching
permission. A run with no directory installed is told so, and never
pretends the capability is missing from the world.
"""
from __future__ import annotations

CAPABILITY_REF = "core.capability.call"
RESULT_RECORD_TYPE = "registered_capability_call/v1"
#: The only effect this handle may carry, because it holds no permission.
PURE_EFFECT = "pure"
REQUIRED_ARGUMENTS = ("surface", "operation")
#: Argument names this handle consumes itself; everything else is forwarded.
RESERVED_ARGUMENTS = REQUIRED_ARGUMENTS + ("arguments",)


class RegisteredCapabilityError(ValueError):
    """The call names no directory, no surface, or an effect this handle cannot carry."""


def directory_of(services):
    """The capability directory the run was given, or None."""
    return getattr(getattr(services, "dependencies", None), "capability_directory", None)


def registered_capabilities(directory) -> tuple[dict, ...]:
    """What a model can select, built from the directory rather than written twice."""
    if directory is None:
        return ()
    rows = []
    for handshake in directory.available():
        rows.append({"surface": handshake.surface, "surface_kind": handshake.surface_kind,
                     "functionality": handshake.functionality,
                     "operations": list(handshake.operations),
                     "effects": list(handshake.effects),
                     "input_schema": handshake.input_schema,
                     "output_schema": handshake.output_schema,
                     "callable_through_this_handle": tuple(handshake.effects) == (PURE_EFFECT,)})
    return tuple(sorted(rows, key=lambda row: row["surface"]))


def _forwarded(arguments: dict) -> dict:
    supplied = arguments.get("arguments")
    if isinstance(supplied, dict):
        return dict(supplied)
    return {key: value for key, value in arguments.items() if key not in RESERVED_ARGUMENTS}


def registered_capability_operation(arguments: dict, services) -> dict:
    """Call one registered surface operation and return a typed record.

    The record names the surface, the operation, whether the call succeeded,
    and the value the surface returned. A refusal is a record too, with the
    reason and the surfaces that were available, so the next decision is made
    from what exists rather than from a guess.
    """
    arguments = dict(arguments or {})
    directory = directory_of(services)
    if directory is None:
        raise RegisteredCapabilityError(
            "no capability directory is installed for this run, so no registered "
            "code capability can be called; install one through the run's dependencies")
    missing = [name for name in REQUIRED_ARGUMENTS if not str(arguments.get(name, "")).strip()]
    if missing:
        raise RegisteredCapabilityError(
            f"name the {' and '.join(missing)} to call; available surfaces are "
            f"{[row['surface'] for row in registered_capabilities(directory)]}")
    surface = str(arguments["surface"])
    operation = str(arguments["operation"])
    try:
        handshake = directory.handshake(surface)
    except Exception as exc:  # noqa: BLE001 - the directory names what it has
        raise RegisteredCapabilityError(str(exc)) from None
    if not handshake.supports(operation):
        raise RegisteredCapabilityError(
            f"surface {surface!r} declares {list(handshake.operations)} and health "
            f"{handshake.health!r}, so it does not support {operation!r}")
    effects = tuple(handshake.effects)
    if effects != (PURE_EFFECT,):
        raise RegisteredCapabilityError(
            f"surface {surface!r} declares the effects {list(effects)}; this handle carries "
            "no effect authority, so it can call only a pure surface. Use a capability that "
            "declares the matching permission")
    result = directory.call(surface, operation, **_forwarded(arguments))
    return {"record_type": RESULT_RECORD_TYPE, "surface": surface, "operation": operation,
            "ok": bool(result.ok), "value": result.value,
            "used_fallback": bool(result.used_fallback), "note": result.note,
            "declared_effects": list(effects),
            "available_surfaces": [row["surface"] for row in registered_capabilities(directory)]}


def self_test() -> dict:
    """The handle finds a surface, refuses an effect it cannot carry, and lists what exists."""
    from types import SimpleNamespace
    from .capability_directory import (CapabilityHandshake, CapabilityDirectory, Endpoint,
                                       SurfaceRegistration)
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    def refuses(action):
        try:
            action()
        except RegisteredCapabilityError:
            return True
        except Exception:  # noqa: BLE001  (a crash is not a typed refusal)
            return False
        return False

    calls = []

    def pure_endpoint(**kw):
        calls.append(kw)
        return {"seen": sorted(kw)}

    directory = CapabilityDirectory()
    pure = SurfaceRegistration(CapabilityHandshake(
        "fixture_pure", "code_node_registry", "a pure fixture surface",
        operations=("run", "validate"), accepts=("code",), returns=("code",)),
        (Endpoint("run", pure_endpoint),))
    writing = SurfaceRegistration(CapabilityHandshake(
        "fixture_writes", "code_node_registry", "a fixture surface that writes",
        operations=("run",), accepts=("code",), returns=("code",),
        effects=("reads_fs", "writes_fs")),
        (Endpoint("run", pure_endpoint),))
    for item in (pure, writing):
        directory.register(item.handshake, item.endpoints)
    services = SimpleNamespace(dependencies=SimpleNamespace(capability_directory=directory))
    empty = SimpleNamespace(dependencies=SimpleNamespace(capability_directory=None))

    record = registered_capability_operation(
        {"surface": "fixture_pure", "operation": "run", "rows": [{"a": 1}]}, services)
    nested = registered_capability_operation(
        {"surface": "fixture_pure", "operation": "run",
         "arguments": {"rows": [{"a": 1}], "columns": ["a"]}}, services)
    check("the_handle_calls_a_registered_pure_surface_and_forwards_its_arguments",
          record["ok"] and record["record_type"] == RESULT_RECORD_TYPE
          and record["value"]["seen"] == ["rows"]
          and nested["value"]["seen"] == ["columns", "rows"]
          and record["surface"] == "fixture_pure" and len(calls) == 2,
          str(record["value"]))
    check("a_surface_that_declares_an_effect_is_refused_because_this_handle_carries_none",
          refuses(lambda: registered_capability_operation(
              {"surface": "fixture_writes", "operation": "run"}, services))
          and len(calls) == 2)
    absent_directory = ""
    try:
        registered_capability_operation({"surface": "fixture_pure", "operation": "run"}, empty)
    except RegisteredCapabilityError as exc:
        absent_directory = str(exc)
    check("a_missing_directory_a_missing_name_and_an_undeclared_operation_are_refused_by_name",
          "no capability directory is installed" in absent_directory
          and "NoneType" not in absent_directory
          and refuses(lambda: registered_capability_operation({"operation": "run"}, services))
          and refuses(lambda: registered_capability_operation({"surface": "absent", "operation": "run"},
                                                             services))
          and refuses(lambda: registered_capability_operation(
              {"surface": "fixture_pure", "operation": "compose"}, services)),
          absent_directory[:90])
    listed = registered_capabilities(directory)
    check("the_list_a_model_sees_is_built_from_the_directory_and_says_which_are_callable_here",
          [row["surface"] for row in listed] == ["fixture_pure", "fixture_writes"]
          and listed[0]["callable_through_this_handle"] is True
          and listed[1]["callable_through_this_handle"] is False
          and listed[1]["effects"] == ["reads_fs", "writes_fs"]
          and registered_capabilities(None) == ()
          and directory_of(empty) is None and directory_of(services) is directory,
          str([row["surface"] for row in listed]))
    failing = CapabilityDirectory()

    def raiser(**kw):
        raise RuntimeError("the surface failed")

    broken = SurfaceRegistration(CapabilityHandshake(
        "fixture_broken", "code_node_registry", "a surface whose endpoint raises",
        operations=("run",), accepts=("code",), returns=("code",)),
        (Endpoint("run", raiser),))
    failing.register(broken.handshake, broken.endpoints)
    broken_services = SimpleNamespace(
        dependencies=SimpleNamespace(capability_directory=failing))
    outcome = registered_capability_operation(
        {"surface": "fixture_broken", "operation": "run"}, broken_services)
    check("a_surface_that_fails_returns_a_record_that_says_so_rather_than_raising",
          outcome["ok"] is False and outcome["record_type"] == RESULT_RECORD_TYPE
          and outcome["available_surfaces"] == ["fixture_broken"],
          str(outcome["note"])[:120])
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "registered_capability_call_test/v1", "tests": tests,
            "passed": passed, "total": len(tests), "all_passed": passed == len(tests)}
