"""Route separation between the producer of work and the Loops that verify it.

An independent verifier that confirms on the very model route that produced
the work is only as independent as that route. When a verification policy
declares separation, every verifier call excludes the routes the producer's
own calls used, the gateway ends with no eligible route rather than reusing
one, and the report states the producer routes, the verifier routes, and
whether separation was achieved. This module owns that session wrapper, the
producer-route computation, the record shape, and the acceptance rule. It
grants no authority and calls no model; accounting stays on the one shared
session, because only the request gains the exclusion.
"""
from __future__ import annotations

from dataclasses import replace

#: How independent the verifier was from the producer, as the report states it.
INDEPENDENCE_SHARED_ROUTE = "isolated_context_shared_model_separate_controller"
INDEPENDENCE_SEPARATE_ROUTE = "isolated_context_separate_route_separate_controller"
ROUTE_SEPARATION_RECORD_TYPE = "route_separation/v1"
#: The profile every verifier-side Loop carries; its calls are not the producer's.
VERIFIER_PROFILE_ID = "practitioner.verifier"


class RouteSeparatedSession:
    """The shared model session with named routes excluded from every call.

    Only the request gains the exclusion, so the gateway refuses the excluded
    routes and the underlying session keeps charging calls and tokens once.
    """

    def __init__(self, session, excluded_routes: tuple[str, ...]):
        self._session = session
        self.excluded_routes = tuple(dict.fromkeys(excluded_routes))

    def invoke(self, request, parent_loop):
        merged = tuple(dict.fromkeys(tuple(request.excluded_routes) + self.excluded_routes))
        return self._session.invoke(replace(request, excluded_routes=merged), parent_loop)

    def __getattr__(self, name):
        return getattr(self._session, name)


def verifier_loop_ids(owner_loop) -> set:
    """Loops spawned under the verifier profile; their calls are not the producer's."""
    events = getattr(getattr(owner_loop, "ledger", None), "events", None) or ()
    return {event.get("loop_id") for event in events
            if event.get("profile_id") == VERIFIER_PROFILE_ID and event.get("loop_id")}


def producer_routes(session, owner_loop=None) -> tuple[str, ...]:
    """The routes the producer's own calls used, in first-use order.

    Calls owned by a verifier-profile Loop (an earlier verification or a
    failure review of this run) are the verifier's, so a nested review does
    not exclude the very routes separation reserved for it.
    """
    if session is None:
        return ()
    excluded_owners = verifier_loop_ids(owner_loop) if owner_loop is not None else set()
    return tuple(dict.fromkeys(
        result.route for result in getattr(session, "results", ())
        if getattr(result, "route", "")
        and getattr(result, "owner_loop_id", "") not in excluded_owners))


def routes_used_since(session, initial_results: int) -> tuple[str, ...]:
    """The routes the session used after the given result count, in first-use order."""
    if session is None:
        return ()
    return tuple(dict.fromkeys(
        result.route for result in list(getattr(session, "results", ()))[initial_results:]
        if getattr(result, "route", "")))


def route_separation_record(required: bool, producer: tuple[str, ...],
                            verifier: tuple[str, ...]) -> dict:
    """The record a report carries; achieved means the two route sets are disjoint."""
    return {"record_type": ROUTE_SEPARATION_RECORD_TYPE, "required": bool(required),
            "producer_routes": list(producer), "verifier_routes": list(verifier),
            "achieved": not (set(producer) & set(verifier))}


def independence_label(record: dict) -> str:
    """The independence a report may claim from its separation record."""
    if record.get("verifier_routes") and record.get("achieved"):
        return INDEPENDENCE_SEPARATE_ROUTE
    return INDEPENDENCE_SHARED_ROUTE


def require_route_separation(report: dict) -> None:
    """Refuse a report that required route separation and does not state it was achieved."""
    separation = report.get("route_separation") or {}
    if separation.get("required") and separation.get("achieved") is not True:
        raise ValueError("required route separation was not achieved by the independent report")


def self_test() -> dict:
    """Producer routes exclude verifier-owned calls; the record and the rule hold."""
    from types import SimpleNamespace
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    def refuses(action):
        try:
            action()
        except ValueError:
            return True
        return False

    results = [SimpleNamespace(route="cloud.a", owner_loop_id="producer"),
               SimpleNamespace(route="cloud.b", owner_loop_id="verifier-1"),
               SimpleNamespace(route="cloud.a", owner_loop_id="producer"),
               SimpleNamespace(route="", owner_loop_id="producer")]
    session = SimpleNamespace(results=results)
    owner = SimpleNamespace(ledger=SimpleNamespace(events=[
        {"loop_id": "verifier-1", "profile_id": VERIFIER_PROFILE_ID},
        {"loop_id": "producer", "profile_id": "practitioner.reference"}]))
    check("producer_routes_keep_first_use_order_and_skip_verifier_owned_and_empty_routes",
          producer_routes(session, owner) == ("cloud.a",)
          and producer_routes(session) == ("cloud.a", "cloud.b")
          and producer_routes(None) == () and routes_used_since(session, 1) == ("cloud.b", "cloud.a"))
    separated = route_separation_record(True, ("cloud.a",), ("cloud.b",))
    shared = route_separation_record(False, ("cloud.a",), ("cloud.a", "cloud.b"))
    check("a_record_is_achieved_only_when_the_route_sets_are_disjoint",
          separated["achieved"] is True and shared["achieved"] is False
          and route_separation_record(True, ("cloud.a",), ())["achieved"] is True
          and independence_label(separated) == INDEPENDENCE_SEPARATE_ROUTE
          and independence_label(shared) == INDEPENDENCE_SHARED_ROUTE
          and independence_label(route_separation_record(True, ("cloud.a",), ())) == INDEPENDENCE_SHARED_ROUTE)
    check("a_required_separation_that_was_not_achieved_is_refused",
          refuses(lambda: require_route_separation({"route_separation": {**separated, "achieved": False}}))
          and not refuses(lambda: require_route_separation({"route_separation": separated}))
          and not refuses(lambda: require_route_separation({"route_separation": shared}))
          and not refuses(lambda: require_route_separation({})))
    calls = []

    class Session:
        results = ()

        def invoke(self, request, parent_loop):
            calls.append(request.excluded_routes)
            return "ok"

    from dataclasses import dataclass

    @dataclass(frozen=True)
    class Request:
        """The one field the wrapper touches; the real request is the model port's."""
        excluded_routes: tuple = ()

    wrapped = RouteSeparatedSession(Session(), ("cloud.a", "cloud.a"))
    wrapped.invoke(Request(excluded_routes=("cloud.c",)), None)
    check("the_wrapped_session_merges_exclusions_without_duplicates_and_forwards_other_names",
          calls == [("cloud.c", "cloud.a")] and wrapped.excluded_routes == ("cloud.a",)
          and wrapped.results == ())
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "route_separation_test/v1", "tests": tests, "passed": passed,
            "total": len(tests), "all_passed": passed == len(tests)}
