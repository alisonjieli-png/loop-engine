"""Checks for the failed-attempt limit of each client address.

The limiter is driven directly with an injected clock. The real service
application is driven through its ASGI interface with a chosen socket peer
address, which a loopback socket cannot vary. No socket is opened here; the
loopback transport checks for the same limit are in http_checks.py. Identity
outcomes at the activation route are injected, because identity verification
has its own checks. A removed-guard control reruns a scenario with the guard
patched away and requires the scenario's own predicate to fail. Not every
guard has one; the README names the guards that do.
"""
from __future__ import annotations

import asyncio
from dataclasses import asdict
from email.message import Message
import json
import threading
from unittest.mock import patch

from .http import MAXIMUM_JSON_NESTING_DEPTH, ServiceHttpApplication, ServiceHttpConfiguration
from .http_auth import HttpAuthenticationError
from .http_test_fixtures import HttpDomainFixture
from .request_limits import (
    HEADER_SOURCE, LIMIT_REACHED_CODE, NOT_CONFIGURED_SOURCE, PUBLISHED_LIMIT_RECORD_TYPE, REFUSAL_RECORD_TYPE,
    REQUEST_LIMITS_RECORD_TYPE, SOCKET_PEER_SOURCE, UNKNOWN_PEER_KEY, FailedAttemptLimiter, ServiceRequestLimits,
)

HOST, ORIGIN = "service.test", "https://service.test"
PROXY_HEADER = "Fly-Client-IP"
# Every address of this machine: the binding a hosted service uses.
PUBLIC_BINDING = "0.0.0.0"
# Documentation address ranges: no check can name a real machine.
FIRST, SECOND, VICTIM, PROXY = "198.51.100.10", "198.51.100.20", "203.0.113.9", "192.0.2.2"
WRONG = {"Authorization": "Bearer WRONG_FIXTURE_TOKEN"}
ACTIVATION = {"record_type": "service_account_activation_request/v1"}


def _peer(**changes):
    """Settings of a host whose callers connect to the service process directly."""
    return ServiceRequestLimits(client_address_source=SOCKET_PEER_SOURCE, **changes)


def _header(name=PROXY_HEADER, **changes):
    """Settings of a host behind a proxy that overwrites the named header."""
    return ServiceRequestLimits(client_address_source=HEADER_SOURCE, client_address_header=name, **changes)


class _Clock:
    def __init__(self, now=1000.0):
        self.now = now

    def __call__(self):
        return self.now


class _IdentityStandIn:
    """Injected activation outcomes behind the browser_identity/v1 boundary.

    Both entry points read the identity provider, a machine the service does
    not control and cannot hurry. `hold` lets a check keep those reads in
    flight, the way a slow or flooded provider does. It is set by default, so
    a read returns at once unless a check asks for otherwise.
    """

    protocol_version = "browser_identity/v1"

    def __init__(self, runtime):
        self.runtime, self.outcome, self.calls = runtime, "refused", 0
        self.hold, self.arrived = threading.Event(), threading.Semaphore(0)
        self.hold.set()

    def _provider_read(self):
        self.arrived.release()
        self.hold.wait(timeout=20)

    def activate(self, _credential):
        self.calls += 1
        self._provider_read()
        if self.outcome == "outage":
            raise HttpAuthenticationError("identity_provider_unavailable")
        if self.outcome == "refused":
            raise HttpAuthenticationError()
        return {"record_type": "fixture_account_activation/v1", "created": True}

    def authenticate(self, _credential):
        self._provider_read()
        raise HttpAuthenticationError()


PRIVATE_VALUE = "PRIVATE_FIXTURE_VALUE"
CARRIED_HEADERS = {"Set-Cookie": "provider_session=" + PRIVATE_VALUE, "X-Provider-Internal": PRIVATE_VALUE,
                   "Retry-After": "86400"}


class _OutsideFailure(RuntimeError):
    """A failure that is not the service's own refusal type and carries response headers.

    A provider client can raise such a failure: the transport failure of the
    standard library carries the provider's response headers in a message
    object under the same attribute name.
    """

    def __init__(self):
        super().__init__("outside failure")
        self.headers = Message()
        for name, value in CARRIED_HEADERS.items():
            self.headers[name] = value


class _Service:
    """One real application driven through ASGI, with counted sign-in and worker entries."""

    def __init__(self, root, limits, *, identity=False, **configuration):
        root.mkdir()
        self.fixture, self.clock = HttpDomainFixture(root), _Clock()
        self.identity = _IdentityStandIn(self.fixture.runtime) if identity else None
        self.application = ServiceHttpApplication(self.fixture.runtime, self.fixture.provisioning,
            ServiceHttpConfiguration(ORIGIN, (HOST,), request_limits=limits, **configuration),
            browser_identity=self.identity)
        self.application.request_limiter = FailedAttemptLimiter(limits, clock=self.clock)
        self.authentications = self.worker_entries = 0
        # The counted seam is the credential resolution that runs inside a
        # worker, not the transport method around it. The transport now
        # decides which share of the pool an attempt may take before it takes
        # any, so an attempt that is refused for want of capacity never
        # reaches this seam, which is the fact these checks measure.
        resolve, work = self.application.authenticator.host_key, self.application._work

        def counted_resolution(authorization, **fields):
            self.authentications += 1
            return resolve(authorization, **fields)

        async def counted_work(function, **reservation):
            self.worker_entries += 1
            return await work(function, **reservation)

        self.application.authenticator.host_key, self.application._work = counted_resolution, counted_work
        self.app = self.application.create_app()

    def close(self):
        self.application._workers.shutdown(wait=True)

    @property
    def valid(self):
        return self.fixture.headers()

    async def _exchange(self, method, path, *, peer=FIRST, headers=(), body=None, raw_body=None):
        pairs = list(headers.items()) if isinstance(headers, dict) else list(headers)
        raw = [(b"host", HOST.encode())] + [(name.lower().encode(), value.encode()) for name, value in pairs]
        # `raw_body` sends exact bytes, for a shape that a JSON writer in this
        # process could not produce without failing here instead of there.
        content = raw_body if raw_body is not None else (b"" if body is None else json.dumps(body).encode())
        if body is not None or raw_body is not None:
            raw.append((b"content-type", b"application/json"))
        scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": method,
                 "scheme": "https", "path": path, "raw_path": path.encode(), "query_string": b"", "root_path": "",
                 "headers": raw, "client": (peer, 40_000) if peer else None, "server": (HOST, 443)}
        sent, delivered = [], []

        async def receive():
            if delivered:
                return {"type": "http.disconnect"}
            delivered.append(True)
            return {"type": "http.request", "body": content, "more_body": False}

        async def send(message):
            sent.append(message)

        await self.app(scope, receive, send)
        start = next(message for message in sent if message["type"] == "http.response.start")
        payload = b"".join(message.get("body", b"") for message in sent if message["type"] == "http.response.body")
        try:
            decoded = json.loads(payload)
        except ValueError:
            decoded = None
        return start["status"], {key.decode(): value.decode() for key, value in start["headers"]}, decoded

    def send(self, method, path, **request):
        """Return (status, response headers, decoded JSON or None) for one request."""
        return asyncio.run(self._exchange(method, path, **request))

    def status(self, method, path, **request):
        return self.send(method, path, **request)[0]

    def statuses_together(self, count, method, path, **request):
        """Send `count` equal requests on one event loop, so that they overlap."""
        return sorted(row[0] for row in self.answers_together(count, method, path, **request))

    def answers_together(self, count, method, path, **request):
        """Send `count` equal requests on one event loop and keep every answer.

        The status alone cannot tell a typed refusal from a failure the
        service did not plan for, so a check about what happens under load
        needs the refusal codes as well.
        """
        async def together():
            return await asyncio.gather(*(self._exchange(method, path, **request) for _each in range(count)))
        return asyncio.run(together())


def _refuses(function):
    try:
        function()
    except (AttributeError, TypeError, ValueError):  # a frozen record refuses with AttributeError
        return True
    return False


def _setting_checks(check):
    check("request_limit_settings_are_an_immutable_versioned_record",
          ServiceRequestLimits().record_type == REQUEST_LIMITS_RECORD_TYPE
          and _refuses(lambda: setattr(ServiceRequestLimits(), "failures_allowed", 1))
          and _refuses(lambda: ServiceRequestLimits(record_type="service_request_limits/v0"))
          and _refuses(lambda: FailedAttemptLimiter({"failures_allowed": 3})))
    unsafe = [{"failures_allowed": value} for value in (True, 0, -1, 1.5, 1001, "3")]
    unsafe += [{"window_seconds": value} for value in (True, 0, 0.5, 86_401, float("inf"), float("nan"), "60")]
    unsafe += [{"maximum_tracked_addresses": value} for value in (True, 0, 65_537, 8.0)]
    unsafe += [{"ipv6_prefix_bits": value} for value in (True, 31, 129, 64.0)]
    unsafe += [{"failures_allowed": 1000, "maximum_tracked_addresses": 1001}]
    unsafe += [{"client_address_source": HEADER_SOURCE, "client_address_header": value} for value in (
        5, None, "", " ", "Fly Client IP", "Fly-Client-IP:", "Fly-Client-IP\r\nX-Other", "-Leading", "Trailing-", "X" * 65)]
    # A header name and the header source are valid only together, and no other source exists.
    unsafe += [{"client_address_header": PROXY_HEADER},
               {"client_address_source": SOCKET_PEER_SOURCE, "client_address_header": PROXY_HEADER},
               {"client_address_source": "x-forwarded-for"}, {"client_address_source": None}]
    check("request_limit_settings_refuse_unsafe_values_and_inexact_header_names",
          all(_refuses(lambda row=row: ServiceRequestLimits(**row)) for row in unsafe)
          and _header().client_address_header == PROXY_HEADER and _header().active and _peer().active
          and ServiceRequestLimits().client_address_source == NOT_CONFIGURED_SOURCE
          and not ServiceRequestLimits().active)
    chosen = _header(failures_allowed=5, window_seconds=30)
    stored = json.loads(json.dumps(asdict(ServiceHttpConfiguration(ORIGIN, (HOST,), request_limits=chosen))))
    inexact = ({key: value for key, value in asdict(chosen).items() if key != "record_type"},
               {**asdict(chosen), "record_type": "service_request_limits/v2"},
               {**asdict(chosen), "trust_forwarded_for": True}, [3, 60], "30 per minute", None)
    check("host_file_limits_need_the_exact_versioned_fields",
          ServiceHttpConfiguration(**stored).request_limits == chosen
          and ServiceHttpConfiguration(ORIGIN, (HOST,)).request_limits == ServiceRequestLimits()
          and all(_refuses(lambda row=row: ServiceHttpConfiguration(ORIGIN, (HOST,), request_limits=row))
                  for row in inexact))


def _sliding_window():
    clock = _Clock(0.0)
    limiter = FailedAttemptLimiter(_peer(failures_allowed=3, window_seconds=60), clock=clock)
    observed = []
    for moment in (0.0, 10.0, 20.0):
        clock.now = moment
        observed.append(limiter.retry_after(FIRST))
        limiter.record_failure(FIRST)
    observed.append((limiter.retry_after(FIRST), limiter.refusal(FIRST), limiter.retry_after(SECOND)))
    clock.now = 59.9
    observed.append(limiter.retry_after(FIRST))
    clock.now = 60.0
    observed.append((limiter.retry_after(FIRST), limiter.refusal(FIRST)))
    limiter.record_failure(FIRST)
    observed.append(limiter.retry_after(FIRST))
    clock.now = 200.0
    observed.append((limiter.retry_after(FIRST), len(limiter)))
    return observed


def _sliding_window_holds(observed):
    return observed == [0, 0, 0, (40, {"record_type": REFUSAL_RECORD_TYPE, "retry_after_seconds": 40}, 0),
                        1, (0, None), 10, (0, 0)]


def _bounded_table():
    clock = _Clock(0.0)
    limiter = FailedAttemptLimiter(_peer(failures_allowed=2, maximum_tracked_addresses=8), clock=clock)
    for index in range(1000):
        clock.now = index / 100
        limiter.record_failure(f"198.51.{index // 250}.{index % 250}")
    for _repeat in range(10):
        limiter.record_failure(FIRST)
    newest = [f"198.51.3.{index}" for index in range(243, 250)] + [FIRST]
    return len(limiter), list(limiter._failures) == newest, max(len(times) for times in limiter._failures.values())


def _limiter_checks(check):
    check("an_address_waits_until_its_oldest_counted_failure_leaves_the_window",
          _sliding_window_holds(_sliding_window()))
    with patch.object(FailedAttemptLimiter, "_forget_expired", lambda self, times, now: None):
        check("removed_window_expiry_is_detected", not _sliding_window_holds(_sliding_window()))
    check("memory_stays_bounded_and_the_oldest_address_leaves_first", _bounded_table() == (8, True, 2))
    with patch.object(FailedAttemptLimiter, "_make_room", lambda self, now: None):
        check("removed_eviction_is_detected", _bounded_table()[0] > 8)
    clock = _Clock(0.0)
    limiter = FailedAttemptLimiter(_peer(failures_allowed=1, maximum_tracked_addresses=3), clock=clock)
    limiter.record_failure(FIRST)
    clock.now = 50.0
    limiter.record_failure(SECOND)
    limiter.record_failure(VICTIM)
    clock.now = 61.0
    limiter.record_failure(PROXY)
    check("an_expired_address_leaves_before_a_waiting_address_is_evicted",
          list(limiter._failures) == [SECOND, VICTIM, PROXY] and limiter.retry_after(SECOND) == 49)
    roomy = FailedAttemptLimiter(_peer(failures_allowed=1, maximum_tracked_addresses=3), clock=clock)
    roomy.record_failure(FIRST)
    clock.now += 61.0
    roomy.record_failure(SECOND)
    check("an_expired_address_is_forgotten_when_another_address_fails_in_a_table_with_room",
          list(roomy._failures) == [SECOND])
    shared = FailedAttemptLimiter(_peer(failures_allowed=4, maximum_tracked_addresses=16))
    errors = []

    def hammer(offset):
        try:
            for index in range(500):
                key = f"192.0.2.{(index + offset) % 64}"
                shared.record_failure(key)
                shared.retry_after(key)
        except Exception as error:  # a broken table must fail the check, not the thread
            errors.append(error)

    threads = [threading.Thread(target=hammer, args=(offset,)) for offset in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(30)
    check("concurrent_failures_keep_the_table_bounded_and_consistent",
          not errors and not any(thread.is_alive() for thread in threads) and len(shared) <= 16
          and all(len(times) <= 4 for times in shared._failures.values()))


def _unconfigured_header_is_ignored():
    limiter = FailedAttemptLimiter(_peer())
    return limiter.address_key(FIRST, [VICTIM]) == FIRST and limiter.address_key(FIRST, ()) == FIRST


def _trusting_address_key(self, peer_host, header_values=()):
    """The known-wrong rule: read an address header that the host never configured."""
    values = tuple(header_values)
    named = self._canonical(values[0]) if len(values) == 1 else ""
    return named or self._canonical(peer_host) or UNKNOWN_PEER_KEY


def _address_checks(check):
    check("an_address_header_the_host_did_not_configure_is_never_read", _unconfigured_header_is_ignored())
    with patch.object(FailedAttemptLimiter, "address_key", _trusting_address_key):
        check("removed_header_configuration_rule_is_detected", not _unconfigured_header_is_ignored())
    limiter = FailedAttemptLimiter(_header())
    unusable = ([], [VICTIM, SECOND], [VICTIM + ", " + SECOND], ["not-an-address"], [" " + VICTIM], [""],
                ["2001:db8::" + "1" * 80], [VICTIM + ":443"])
    check("a_configured_header_counts_only_when_it_holds_exactly_one_address",
          limiter.address_key(PROXY, [VICTIM]) == VICTIM
          and all(limiter.address_key(PROXY, values) == PROXY for values in unusable))
    exact = FailedAttemptLimiter(_peer(ipv6_prefix_bits=128))
    check("addresses_are_counted_in_one_canonical_form",
          limiter.address_key("::ffff:" + VICTIM) == VICTIM
          and limiter.address_key("2001:db8:1:2::1") == limiter.address_key("2001:DB8:1:2:ffff::9") == "2001:db8:1:2::/64"
          and limiter.address_key("2001:db8:1:3::1") == "2001:db8:1:3::/64"
          and exact.address_key("2001:db8:1:2::1") != exact.address_key("2001:db8:1:2::2")
          and limiter.address_key(None) == limiter.address_key("unix-socket") == UNKNOWN_PEER_KEY)


def _crossing(root):
    service = _Service(root, _peer(failures_allowed=3))
    try:
        refused = [service.status("GET", "/api/v1/session", headers=WRONG) for _attempt in range(3)]
        before = (service.authentications, service.worker_entries)
        status, headers, body = service.send("GET", "/api/v1/session", headers=WRONG)
        return {"refused": refused, "before": before, "status": status, "headers": headers, "body": body,
                "after": (service.authentications, service.worker_entries),
                "correct_key": service.status("GET", "/api/v1/session", headers=service.valid),
                "after_correct_key": service.authentications,
                "public": [service.status("GET", path) for path in ("/api/v1/health", "/api/v1/capabilities", "/app")],
                "other_address": [service.status("GET", "/api/v1/session", peer=SECOND, headers=chosen)
                                  for chosen in (service.valid, WRONG)]}
    finally:
        service.close()


def _crossing_holds(seen):
    error = (seen["body"] or {}).get("error", {})
    return (seen["refused"] == [401, 401, 401] and seen["before"] == (3, 3) and seen["status"] == 429
            and seen["after"] == (3, 3) and seen["headers"].get("retry-after") == "60"
            and seen["headers"].get("cache-control") == "no-store" and error.get("code") == LIMIT_REACHED_CODE
            and error.get("details") == {"record_type": REFUSAL_RECORD_TYPE, "retry_after_seconds": 60})


def _forged_header(root, limits):
    """One address rotates forged address headers and names a victim in them."""
    service = _Service(root, limits)
    try:
        statuses = []
        for attempt in range(6):
            forged = {**WRONG, PROXY_HEADER: VICTIM if attempt % 2 else f"203.0.113.{100 + attempt}",
                      "X-Forwarded-For": VICTIM if attempt % 2 else f"203.0.113.{100 + attempt}"}
            statuses.append(service.status("GET", "/api/v1/session", headers=forged))
        return {"statuses": statuses, "counted": list(service.application.request_limiter._failures),
                "victim": service.status("GET", "/api/v1/session", peer=VICTIM, headers=service.valid)}
    finally:
        service.close()


def _forged_header_holds(seen):
    return seen == {"statuses": [401, 401, 401, 429, 429, 429], "counted": [FIRST], "victim": 200}


def _unstated_source(root):
    """A host that states no address source, such as a host file written before this limit existed."""
    service = _Service(root, ServiceRequestLimits(failures_allowed=3))
    try:
        statuses = {service.status("GET", "/api/v1/session", headers=WRONG) for _attempt in range(12)}
        published = service.send("GET", "/api/v1/capabilities")[2]["result"]["limits"]["failed_attempts_per_address"]
        return {"statuses": statuses, "tracked": len(service.application.request_limiter),
                "published": (published["active"], published["client_address_source"])}
    finally:
        service.close()


def _unstated_source_holds(seen):
    return seen == {"statuses": {401}, "tracked": 0, "published": (False, NOT_CONFIGURED_SOURCE)}


def _waiting(root):
    """One address reaches its limit and keeps asking while the clock moves on."""
    service = _Service(root, _peer(failures_allowed=3))
    try:
        seen = {"refused": [service.status("GET", "/api/v1/session", headers=WRONG) for _attempt in range(3)],
                "waiting": []}
        for _attempt in range(10):
            service.clock.now += 5
            status, headers, _body = service.send("GET", "/api/v1/session", headers=WRONG)
            seen["waiting"].append((status, headers.get("retry-after")))
        service.clock.now += 9  # one second before the three counted failures leave the window
        early = [service.send("GET", "/api/v1/session", headers=chosen) for chosen in (WRONG, service.valid)]
        seen["one_second_early"] = [(status, headers.get("retry-after")) for status, headers, _body in early]
        seen["reached_while_waiting"] = service.authentications
        service.clock.now += 1  # the three counted failures leave the window at this instant
        seen["released"] = [service.status("GET", "/api/v1/session", headers=chosen)
                            for chosen in (service.valid, WRONG)]
        seen["reached"] = service.authentications
        return seen
    finally:
        service.close()


def _waiting_holds(seen):
    """The wait falls by exactly the time that passed, and it ends when the counted failures leave the window."""
    return seen == {"refused": [401, 401, 401], "waiting": [(429, str(wait)) for wait in range(55, 5, -5)],
                    "one_second_early": [(429, "1"), (429, "1")], "reached_while_waiting": 3,
                    "released": [200, 401], "reached": 5}


def _counting_refusal(self, key):
    """The known-wrong rule: a request that is refused with status 429 is counted as one more failure."""
    wait = self.retry_after(key)
    if wait:
        self.record_failure(key)
    return {"record_type": REFUSAL_RECORD_TYPE, "retry_after_seconds": wait} if wait else None


def _outside_failure(root):
    """Authentication raises a failure from outside the service that carries its own response headers."""
    service = _Service(root, _peer(failures_allowed=3))
    try:
        with patch.object(service.application.authenticator, "authenticate", side_effect=_OutsideFailure()):
            status, headers, body = service.send("GET", "/api/v1/session", headers=service.valid)
        own = service.send("GET", "/api/v1/unknown", headers=service.valid)
        return {"status": status, "carried": sorted(set(headers) & {name.lower() for name in CARRIED_HEADERS}),
                "private_value_sent": PRIVATE_VALUE in json.dumps([headers, body]),
                "code": (body or {}).get("error", {}).get("code"), "counted": len(service.application.request_limiter),
                "own_refusal": (own[0], (own[2] or {}).get("error", {}).get("code"))}
    finally:
        service.close()


def _outside_failure_holds(seen):
    return seen == {"status": 500, "carried": [], "private_value_sent": False, "code": "operation_failed",
                    "counted": 0, "own_refusal": (404, "route_unavailable")}


FOREIGN_ORIGIN = "https://foreign.invalid"


def _first_origin(sent_origins):
    """The known-wrong rule: read the first origin and ignore the rest."""
    return sent_origins[0] if sent_origins else None


def _two_origins(service):
    """One request naming the declared origin and a foreign one, and one naming each alone."""
    def sent(*origins):
        status, headers, _body = service.send("GET", "/api/v1/session", headers=[
            *service.valid.items(), *[("Origin", value) for value in origins]])
        return status, headers.get("access-control-allow-origin")
    return {"both": sent(ORIGIN, FOREIGN_ORIGIN), "reversed": sent(FOREIGN_ORIGIN, ORIGIN),
            "declared alone": sent(ORIGIN), "foreign alone": sent(FOREIGN_ORIGIN)}


def _two_origins_holds(seen):
    return seen == {"both": (403, None), "reversed": (403, None),
                    "declared alone": (200, ORIGIN), "foreign alone": (403, None)}


def _transport_checks(check, root):
    # Behind a proxy the socket peer is the proxy. A limit that guessed the
    # socket peer would put every caller in one count, so it must not guess.
    check("an_unstated_address_source_leaves_the_limit_inactive_and_says_so",
          _unstated_source_holds(_unstated_source(root / "unstated")))
    with patch.object(ServiceRequestLimits, "active", True):
        check("removed_unstated_source_rule_is_detected",
              not _unstated_source_holds(_unstated_source(root / "unstated-guessing")))
    seen = _crossing(root / "crossing")
    check("the_attempt_over_the_limit_is_refused_before_authentication_and_before_a_worker_slot", _crossing_holds(seen))
    check("a_correct_key_is_refused_too_while_its_address_waits",
          seen["correct_key"] == 429 and seen["after_correct_key"] == 3)
    check("public_routes_stay_open_to_a_waiting_address", seen["public"] == [200, 200, 200])
    check("a_different_address_is_unaffected", seen["other_address"] == [200, 401])
    with patch.object(FailedAttemptLimiter, "retry_after", lambda self, key: 0):
        mutant = _crossing(root / "crossing-without-limit")
    check("removed_failed_attempt_limit_is_detected",
          not _crossing_holds(mutant) and mutant["status"] == 401 and mutant["after"] == (4, 4))

    # The clock moves between the refused requests. With a clock that stands
    # still, a counted refusal would leave the same failure times and stay unseen.
    check("refusals_while_waiting_are_not_counted_and_the_window_expires", _waiting_holds(_waiting(root / "window")))
    with patch.object(FailedAttemptLimiter, "refusal", _counting_refusal):
        counted = _waiting(root / "window-counting-refusals")
    # The known-wrong rule never releases a caller that keeps asking: the wait
    # stops falling, and a correct key is still refused at the original expiry.
    check("removed_uncounted_refusal_rule_is_detected",
          not _waiting_holds(counted) and counted["waiting"][0] == (429, "55") and counted["released"][0] == 429)
    check("a_failure_from_outside_the_service_adds_no_response_header",
          _outside_failure_holds(_outside_failure(root / "outside-failure")))

    service = _Service(root / "success", _peer(failures_allowed=3))
    try:
        order = [WRONG, WRONG] + [service.valid] * 6 + [WRONG, service.valid]
        check("a_success_is_never_counted_and_never_clears_the_count",
              [service.status("GET", "/api/v1/session", headers=chosen) for chosen in order]
              == [401, 401, 200, 200, 200, 200, 200, 200, 401, 429])
    finally:
        service.close()

    service = _Service(root / "uncounted", _peer(failures_allowed=3))
    try:
        # The addresses answer differently on purpose. `/api/v1/session` is an
        # address this service serves, so a request without a credential is
        # refused for the credential. `/favicon.ico` and `/robots.txt` are
        # addresses it does not serve at all, so the answer is that the address
        # is missing; saying "unauthorized" to those sent the reader looking for
        # a credential fault that did not exist. Neither kind reaches a worker
        # slot, an authentication or the failed-attempt count, which is what
        # this check is for.
        anonymous = [service.status("GET", path) for path in ("/api/v1/session", "/favicon.ico", "/robots.txt") * 4]
        doubled = service.status("GET", "/api/v1/session", headers=[*WRONG.items(), *WRONG.items()])
        check("a_request_without_one_credential_uses_no_worker_slot_and_is_not_counted",
              anonymous == [401, 404, 404] * 4 and doubled == 401
              and (service.authentications, service.worker_entries) == (0, 0)
              and len(service.application.request_limiter) == 0)
        # A caller can pair the browser origin the host declared with another
        # one. Reading the first of them would answer that caller with the
        # declared origin's sharing headers, on the refusal as well.
        check("a_request_that_names_two_origins_is_refused_and_shares_with_neither",
              _two_origins_holds(_two_origins(service)))
        with patch("loop_engine.core.service_runtime.http.selected_origin", _first_origin):
            check("removed_single_origin_rule_is_detected",
                  not _two_origins_holds(_two_origins(_Service(root / "first-origin", _peer()))))
        signed_in = [service.status("GET", "/api/v1/unknown", headers=service.valid) for _attempt in range(5)]
        signed_in += [service.status("GET", "/api/v1/admin/access", headers=service.valid) for _attempt in range(5)]
        check("a_refusal_after_sign_in_is_not_counted",
              signed_in == [404] * 5 + [403] * 5 and len(service.application.request_limiter) == 0)
        with patch.object(service.application.authenticator, "authenticate",
                          side_effect=HttpAuthenticationError("identity_provider_unavailable")):
            outage = [service.status("GET", "/api/v1/session", headers=service.valid) for _attempt in range(5)]
        check("an_outage_answer_is_not_counted", outage == [503] * 5
              and len(service.application.request_limiter) == 0
              and service.status("GET", "/api/v1/session", headers=service.valid) == 200)
    finally:
        service.close()

    service = _Service(root / "overlap", _peer(failures_allowed=3))
    try:
        # Every worker slot is held inside authentication first, and only then
        # are the further attempts sent. Sending them all at once and reading
        # the order back left the result to the scheduler: when the held
        # attempts finished before the later ones asked for a slot, the later
        # ones got a slot too and the check measured nothing. Holding and
        # releasing explicitly measures the same property every time.
        slots = service.application.configuration.maximum_concurrent_operations
        # Hold every worker slot open until the check releases it, at the key
        # resolution inside the slot. Provider reads hold their own share of
        # the worker pool, so the hold sits where a slot is actually occupied;
        # holding the whole authentication step would hold requests before
        # they take a slot, and the check would measure nothing. An earlier
        # version used a barrier of `slots` parties. When the machine was
        # loaded, the first attempts finished and freed their slots before the
        # extra ones arrived, so the extras took a slot, waited alone at a
        # barrier that would never fill again and answered 500 after ten
        # seconds. The check then failed for a timing the service never
        # promised, roughly half the time, which is worse than no check: it
        # taught a reader to rerun rather than to look.
        arrived, holding = threading.Semaphore(0), threading.Event()
        resolve = service.application.authenticator.host_key

        def held_resolution(authorization, **fields):
            arrived.release()
            holding.wait(timeout=20)
            return resolve(authorization, **fields)

        service.application.authenticator.host_key = held_resolution
        answers = []
        occupying = [threading.Thread(daemon=True, target=lambda: answers.append(
            service.status("GET", "/api/v1/session", headers=WRONG))) for _each in range(slots)]
        for worker in occupying:
            worker.start()
        # Every worker slot is occupied, and stays occupied, until this check
        # says otherwise. Only then are the extra attempts sent, so what they
        # answer is a property of the full service and not of the order the
        # event loop happened to choose.
        inside = all(arrived.acquire(timeout=20) for _each in range(slots))
        extra = [service.send("GET", "/api/v1/session", headers=WRONG) for _attempt in range(4)]
        holding.set()
        for worker in occupying:
            worker.join(30)
        service.application.authenticator.host_key = resolve
        # Known limit, stated in the README: attempts already inside
        # authentication finish, and the worker slots bound how many there
        # are. The rest must be told the service is busy. An unplanned 500
        # would satisfy a status count alone, so the refusal code is checked.
        check("attempts_already_inside_authentication_finish_and_the_worker_slots_bound_them",
              inside and sorted(answers) == [401] * slots
              and [row[0] for row in extra] == [503] * 4
              and [row[2]["error"]["code"] for row in extra] == ["service_busy"] * 4
              and service.authentications == slots
              and service.status("GET", "/api/v1/session", headers=WRONG) == 429
              and service.authentications == slots)
    finally:
        service.close()

    service = _Service(root / "activation", _peer(failures_allowed=3), identity=True)
    try:
        def activate(peer, body=ACTIVATION):
            return service.status("POST", "/api/v1/account/activate", peer=peer, headers=WRONG, body=body)
        service.identity.outcome = "outage"
        outage = [activate(FIRST) for _attempt in range(4)]
        service.identity.outcome = "refused"
        refused = [activate(FIRST) for _attempt in range(3)]
        # The governed operation may run its work more than once for one
        # request, so compare the identity work before and after, not a total.
        reached = service.identity.calls
        over_limit = activate(FIRST)
        malformed = [activate(SECOND, {**ACTIVATION, "tenant_id": "alpha"}) for _attempt in range(4)]
        service.identity.outcome = "accepted"
        check("refused_account_activations_are_counted_and_an_identity_outage_is_not",
              outage == [503] * 4 and refused == [401, 401, 401] and over_limit == 429
              and malformed == [400, 400, 400, 429] and activate(FIRST) == 429
              and service.identity.calls == reached
              and activate(VICTIM) == 200 and service.identity.calls == reached + 1)
    finally:
        service.close()

    check("an_unconfigured_header_is_ignored_and_a_forged_one_cannot_move_the_count",
          _forged_header_holds(_forged_header(root / "forged", _peer(failures_allowed=3))))
    # Known-wrong configuration: a header that the caller controls. The same
    # scenario then shows both defects: the limit is evaded and a victim is named.
    wrong = _forged_header(root / "forged-known-wrong", _header("X-Forwarded-For", failures_allowed=3))
    check("a_caller_controlled_header_is_the_known_wrong_case",
          not _forged_header_holds(wrong) and 429 not in wrong["statuses"] and VICTIM in wrong["counted"])

    service = _Service(root / "proxy", _header(failures_allowed=3))
    try:
        def through_proxy(address, credential, extra=()):
            return service.status("GET", "/api/v1/session", peer=PROXY,
                                  headers=[*credential.items(), (PROXY_HEADER, address), *extra])
        first = [through_proxy(FIRST, WRONG) for _attempt in range(4)]
        check("a_configured_header_separates_addresses_behind_one_proxy",
              first == [401, 401, 401, 429] and through_proxy(SECOND, service.valid) == 200
              and through_proxy(SECOND, WRONG) == 401
              and through_proxy(SECOND, service.valid, [("X-Forwarded-For", FIRST)]) == 200
              and list(service.application.request_limiter._failures) == [FIRST, SECOND])
        repeated = [through_proxy(VICTIM, WRONG, [(PROXY_HEADER, f"203.0.113.{200 + attempt}")]) for attempt in range(4)]
        check("a_repeated_configured_header_is_counted_for_the_socket_peer_not_for_a_named_address",
              repeated == [401, 401, 401, 429] and through_proxy(VICTIM, service.valid) == 200
              and list(service.application.request_limiter._failures) == [FIRST, SECOND, PROXY])
        # The capabilities record is anonymous. It names the address source,
        # never the trusted header and never the size of the table.
        status, _headers, body = service.send("GET", "/api/v1/capabilities", peer=PROXY)
        check("capabilities_name_the_address_source_but_not_the_trusted_header_or_the_table_size",
              status == 200 and PROXY_HEADER.lower() not in json.dumps(body).lower()
              and body["result"]["limits"]["failed_attempts_per_address"] == {
                  "record_type": PUBLISHED_LIMIT_RECORD_TYPE, "active": True,
                  "counted": ["refused_authentication", "refused_account_activation",
                              "refused_promotion_redemption"],
                  "failures_allowed": 3, "window_seconds": 60, "client_address_source": HEADER_SOURCE,
                  "ipv6_prefix_bits": 64, "refusal_code": LIMIT_REACHED_CODE,
                  "state": "memory_of_one_service_process"})
    finally:
        service.close()

    service = _Service(root / "many", _peer(failures_allowed=3, maximum_tracked_addresses=4))
    try:
        statuses = {service.status("GET", "/api/v1/session", peer=f"198.51.100.{index}", headers=WRONG)
                    for index in range(1, 61)}
        check("many_addresses_cannot_grow_the_table_of_a_running_service",
              statuses == {401} and len(service.application.request_limiter) == 4)
        limits = service.send("GET", "/api/v1/capabilities")[2]["result"]["limits"]
        configuration = service.application.configuration
        from .http import MAXIMUM_JSON_NESTING_DEPTH
        check("capabilities_publish_the_limit_beside_the_unchanged_existing_limits",
              {key: limits[key] for key in ("request_bytes", "response_bytes", "search_results", "concurrent_operations",
                                            "concurrent_operations_for_each_account", "request_nesting_depth",
                                            "concurrent_operations_waiting_on_another_service")}
              == {"request_bytes": configuration.maximum_request_bytes,
                  "response_bytes": configuration.maximum_response_bytes,
                  "search_results": configuration.maximum_search_results,
                  "concurrent_operations": configuration.maximum_concurrent_operations,
                  "concurrent_operations_for_each_account":
                      configuration.maximum_concurrent_operations_for_each_tenant,
                  "concurrent_operations_waiting_on_another_service":
                      configuration.maximum_concurrent_operations_for_each_tenant,
                  "request_nesting_depth": MAXIMUM_JSON_NESTING_DEPTH}
              and limits["failed_attempts_per_address"] == configuration.request_limits.published()
              and limits["failed_attempts_per_address"]["failures_allowed"] == 3
              and limits["failed_attempts_per_address"]["active"] is True
              and limits["failed_attempts_per_address"]["client_address_source"] == SOCKET_PEER_SOURCE
              and set(limits) == {"request_bytes", "response_bytes", "search_results", "concurrent_operations",
                                  "concurrent_operations_for_each_account", "request_nesting_depth",
                                  "concurrent_operations_waiting_on_another_service",
                                  "failed_attempts_per_address"})
    finally:
        service.close()


def _host_file_checks(check, root):
    """The mapping that the README gives for Fly, through the real host loader."""
    from .http_entrypoint import HOST_CONFIGURATION_VERSION, MANIFEST_VERSION, load_host_application
    root.mkdir()
    manifest = root / "manifest.json"
    manifest.write_text(json.dumps({"record_type": MANIFEST_VERSION, "artifact_root": str(root), "items": []}))

    def load(http):
        path = root / "host.json"
        path.write_text(json.dumps({"record_type": HOST_CONFIGURATION_VERSION, "manifest_path": str(manifest),
            "runtime": {"database_path": str(root / "host.db"), "writes_authorized": True},
            "http": {"public_base_url": ORIGIN, "allowed_hosts": [HOST], **http}, "authentication": {}}))
        application = load_host_application(str(path))[0]
        application._workers.shutdown(wait=True)
        return (application.configuration.request_limits,
                application.capabilities()["limits"]["failed_attempts_per_address"])

    stated = {"record_type": REQUEST_LIMITS_RECORD_TYPE, "client_address_source": HEADER_SOURCE,
              "client_address_header": PROXY_HEADER}
    settings, published = load({"request_limits": stated})
    earlier_settings, earlier = load({})
    # The header name is read from the loaded settings: the public record does not carry it.
    check("the_documented_host_file_mapping_activates_the_limit_through_the_real_host_loader",
          settings == _header() and (published["active"], published["client_address_source"]) == (True, HEADER_SOURCE)
          and earlier_settings == ServiceRequestLimits()
          and (earlier["active"], earlier["client_address_source"]) == (False, NOT_CONFIGURED_SOURCE))
    inexact = ({"client_address_header": PROXY_HEADER}, {**stated, "record_type": "service_request_limits/v2"},
               {**stated, "client_address_source": SOCKET_PEER_SOURCE}, {**stated, "trust_forwarded_for": True})
    check("an_inexact_host_file_mapping_stops_the_host_loader_before_it_serves",
          all(_refuses(lambda row=row: load({"request_limits": row})) for row in inexact))


def run_checks(check, root):
    from .capacity_checks import run_checks as capacity_checks
    _setting_checks(check)
    _host_file_checks(check, root / "host-file")
    capacity_checks(check, root / "capacity")
    _limiter_checks(check)
    _address_checks(check)
    _transport_checks(check, root)
