"""Checks for the capacity a request may take at the hosted service boundary.

Three controls share this module because each one bounds what one caller can
take from the whole service: the shares of the worker pool, the nesting depth
a request body may carry, and the statement a public binding must make before
it serves anyone. The failed-attempt limit for each client address is in
request_limit_checks.py, which also runs these. The real application is driven
through its ASGI interface with a chosen socket peer address; no socket is
opened here. A removed-guard control reruns a scenario with the guard patched
away and requires the scenario's own predicate to fail.
"""
from __future__ import annotations

import contextlib
import io
import json
import threading
from unittest.mock import patch

from .http import (
    EXTERNAL_PROVIDER_SHARE, MAXIMUM_JSON_NESTING_DEPTH, NESTING_LIMIT_CODE, ServiceHttpApplication,
    ServiceHttpConfiguration, ServiceHttpError, _json_nesting_depth, _parse_json,
)
from .http_auth import HttpAuthenticationError
from .request_limit_checks import (
    ACTIVATION, HEADER_SOURCE, LIMIT_REACHED_CODE, ORIGIN, HOST, PUBLIC_BINDING, WRONG, ServiceRequestLimits,
    _Service, _header, _peer, _refuses,
)


def run_checks(check, root):
    """Every capacity control, each with its own temporary directory."""
    root.mkdir()
    _binding_checks(check, root / "binding")
    _provider_share_checks(check, root / "provider")
    _depth_reader_checks(check)
    _deep_body_checks(check, root / "deep-body")


def _deep_body_checks(check, root):
    root.mkdir()
    # A body nested deeper than the parser can follow was an internal fault,
    # and an internal fault is not a refused attempt, so nothing counted it and
    # nothing stopped an anonymous caller from sending it again without end.
    #
    # How deep the parser can follow depends on the interpreter: near one
    # thousand containers on 3.10 and 3.11, near ten thousand on 3.12 and 3.13.
    # A body of five thousand faulted the known-wrong reader on the first two
    # and parsed on the service image's 3.12, so the removed-guard control
    # failed there and the release check with it. The scenario now sends the
    # deepest body a request may carry, and states that the plain parser
    # cannot follow it as a check of its own, so an interpreter or a size
    # limit that moves the fault fails by name rather than inside the control.
    depth = _deepest_body_depth()
    check("the_deepest_body_a_request_may_carry_exhausts_the_plain_parser",
          _exhausts_the_plain_parser(depth))
    check("a_body_nested_past_the_reader_is_a_counted_refusal_not_an_internal_fault",
          _deep_body_holds(_deep_body(root / "guarded", depth=depth)))
    with patch("loop_engine.core.service_runtime.http._parse_json", _unguarded_parse_json):
        unguarded = _deep_body(root / "unguarded", depth=depth)
    check("removed_nesting_limit_is_detected",
          not _deep_body_holds(unguarded)
          and unguarded == {"answers": [(500, "operation_failed")] * 6, "tracked": 0, "identity_calls": 0})


def _deepest_body_depth():
    """The deepest array a request body may carry under the transport's default size limit.

    Every container takes one byte to open and one to close, and the scenario
    service uses the same default settings as this one.
    """
    return ServiceHttpConfiguration(ORIGIN, (HOST,)).maximum_request_bytes // 2


def _exhausts_the_plain_parser(depth):
    """Whether this interpreter's own parser runs out of recursion on a body this deep."""
    try:
        json.loads(b"[" * depth + b"]" * depth)
    except RecursionError:
        return True
    return False


def _deep_body(root, *, depth):
    """A caller with no credential sends a body nested far deeper than any real request.

    The account activation route reads its body before any credential exists,
    so this is what an anonymous caller can send to the live service today.
    """
    service = _Service(root, _peer(failures_allowed=3), identity=True)
    try:
        nested = b"[" * depth + b"]" * depth
        answers = []
        for _attempt in range(6):
            status, _headers, body = service.send("POST", "/api/v1/account/activate", raw_body=nested)
            answers.append((status, (body or {}).get("error", {}).get("code")))
        return {"answers": answers, "tracked": len(service.application.request_limiter),
                "identity_calls": service.identity.calls}
    finally:
        service.close()


def _deep_body_holds(seen):
    """Three bounded refusals that are counted, then the wait, and no identity call."""
    return seen == {"answers": [(400, NESTING_LIMIT_CODE)] * 3 + [(429, LIMIT_REACHED_CODE)] * 3,
                    "tracked": 1, "identity_calls": 0}


def _unguarded_parse_json(body, *, maximum_depth=None):
    """The known-wrong reader: the reader as it stood before the depth limit.

    It hands the whole body to the parser, which opens one recursive call for
    each container. A deep body exhausts the interpreter's recursion allowance,
    which is not one of the service's own refusal types, so the caller gets an
    internal fault that the failed-attempt limit does not count.
    """
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("duplicate field")
            value[key] = item
        return value
    try:
        value = json.loads(body, object_pairs_hook=unique,
                           parse_constant=lambda _value: (_ for _ in ()).throw(ValueError("nonfinite value")))
    except (ValueError, UnicodeError):
        raise ServiceHttpError("invalid_json") from None
    if not isinstance(value, dict):
        raise ServiceHttpError("object_required")
    return value


async def _unshared_authentication(self, request):
    """The known-wrong transport: authentication as it stood before the share.

    One submission for every credential, whatever confirms it. A read at the
    identity provider could then take any worker in the pool, so callers
    holding signed browser tokens could hold every worker while that provider
    answered, and a paying customer's host key found none left.
    """
    if len(request.headers.getlist("authorization")) != 1:
        raise HttpAuthenticationError()
    return await self._work(lambda: self.authenticator.authenticate(
        request.headers["authorization"],
        purpose="website" if request.url.path.startswith("/api/") else "service"))


SETTLED_SECONDS = 3.0


def _provider_flood(root):
    """Hold the identity provider's reads, then ask what a host key can still do.

    The flood sends credentials that only the identity provider can confirm.
    Each read stays in flight until this check releases it, which is what a
    slow or flooded provider looks like from here. The flood is counted until
    it settles, so the answer is the number of reads the service allowed at
    once and not the number this check happened to observe first.
    """
    service = _Service(root, _peer(), identity=True, maximum_concurrent_operations=4)
    slots = service.application.configuration.maximum_concurrent_operations
    service.identity.hold.clear()
    answers = []
    flooding = [threading.Thread(daemon=True, target=lambda: answers.append(
        service.status("GET", "/api/v1/session", headers=WRONG))) for _each in range(slots)]
    try:
        for worker in flooding:
            worker.start()
        held = 0
        if service.identity.arrived.acquire(timeout=20):
            held = 1
            while service.identity.arrived.acquire(timeout=SETTLED_SECONDS):
                held += 1
        customer = service.send("GET", "/api/v1/session", headers=service.valid)
        listing = service.send("POST", "/api/v1/provisioning", headers=service.valid,
                               body={"record_type": "service_provisioning_request/v1", "operation": "list"})
        return {"reads_held_at_once": held, "pool": slots,
                "share": service.application.configuration.maximum_concurrent_operations_for_each_tenant,
                "customer": (customer[0], (customer[2] or {}).get("error", {}).get("code")),
                "listing": (listing[0], (listing[2] or {}).get("error", {}).get("code"))}
    finally:
        service.identity.hold.set()
        for worker in flooding:
            worker.join(30)
        service.close()


def _provider_flood_holds(seen):
    """The share holds: the reads stop at it, and the host key is served normally."""
    return (seen["reads_held_at_once"] == seen["share"] < seen["pool"]
            and seen["customer"] == (200, None) and seen["listing"] == (200, None))


def _provider_flood_takes_the_pool(seen):
    """The known-wrong outcome: the reads take the pool and the host key finds none."""
    return (seen["reads_held_at_once"] == seen["pool"]
            and seen["customer"] == (503, "service_busy") and seen["listing"] == (503, "service_busy"))


def _activation_flood(root):
    """Hold the identity provider's activation reads, then ask what a host key can still do.

    Account activation confirms a signed token at the identity provider, the
    same slow outside read that sign-in makes. The flood sends activations
    whose reads stay in flight until this check releases them, and is counted
    until it settles, exactly as `_provider_flood` counts sign-in reads.
    """
    service = _Service(root, _peer(), identity=True, maximum_concurrent_operations=4)
    slots = service.application.configuration.maximum_concurrent_operations
    service.identity.hold.clear()
    answers = []
    flooding = [threading.Thread(daemon=True, target=lambda: answers.append(
        service.status("POST", "/api/v1/account/activate", headers=WRONG, body=ACTIVATION)))
        for _each in range(slots)]
    try:
        for worker in flooding:
            worker.start()
        held = 0
        if service.identity.arrived.acquire(timeout=20):
            held = 1
            while service.identity.arrived.acquire(timeout=SETTLED_SECONDS):
                held += 1
        customer = service.send("GET", "/api/v1/session", headers=service.valid)
        return {"reads_held_at_once": held, "pool": slots,
                "share": service.application.configuration.maximum_concurrent_operations_for_each_tenant,
                "customer": (customer[0], (customer[2] or {}).get("error", {}).get("code")),
                "listing": (200, None)}
    finally:
        service.identity.hold.set()
        for worker in flooding:
            worker.join(30)
        service.close()


def _unshared_work(original):
    """The known-wrong worker entry: every submission ignores the share it names."""
    async def work(self, function, *, shares=()):
        return await original(self, function)
    return work


def _provider_share_checks(check, root):
    root.mkdir()
    from .records import identifier
    # The two kinds of share live in one table, so an account must not be able
    # to name the provider share and take its capacity, or be refused by it.
    check("no_account_can_ever_name_the_share_held_by_provider_reads",
          _refuses(lambda: identifier(EXTERNAL_PROVIDER_SHARE, "tenant identity"))
          and EXTERNAL_PROVIDER_SHARE not in ("", None))
    # A browser session and an external token are confirmed by a read at the
    # identity provider. Those reads used to take workers from the same pool
    # as everything else, so one caller with valid signed tokens could hold
    # every worker and every paying customer was answered `service_busy`.
    check("a_held_identity_provider_cannot_take_the_workers_a_host_key_needs",
          _provider_flood_holds(_provider_flood(root / "provider-share")))
    with patch.object(ServiceHttpApplication, "_authenticate_request", _unshared_authentication):
        unshared = _provider_flood(root / "provider-share-unshared")
    check("removed_provider_share_is_detected",
          not _provider_flood_holds(unshared) and _provider_flood_takes_the_pool(unshared))
    # Account activation makes the same outside read. A merge on September 22,
    # 2026 dropped its share argument while its comment still promised it, and
    # no check noticed; these two close that gap.
    check("a_held_identity_provider_cannot_take_the_workers_through_account_activation",
          _provider_flood_holds(_activation_flood(root / "activation-share")))
    with patch.object(ServiceHttpApplication, "_work", _unshared_work(ServiceHttpApplication._work)):
        unshared_activation = _activation_flood(root / "activation-share-unshared")
    check("removed_activation_share_is_detected",
          not _provider_flood_holds(unshared_activation)
          and unshared_activation["reads_held_at_once"] == unshared_activation["pool"]
          and unshared_activation["customer"] == (503, "service_busy"))


def _depth_reader_checks(check):
    """The depth scan itself, against the shapes a caller can write."""
    limit = MAXIMUM_JSON_NESTING_DEPTH
    quoted = b'{"a":"[[[[[[[[ ]]]]]]]]","b":"\\\\","c":"\\""}'
    check("the_nesting_scan_counts_containers_and_reads_quoted_brackets_as_text",
          _json_nesting_depth(b"1", limit) == 0 and _json_nesting_depth(b"{}", limit) == 1
          and _json_nesting_depth(b'{"a":[{"b":[]}]}', limit) == 4
          and _json_nesting_depth(b'[{},{},{}]', limit) == 2
          and _json_nesting_depth(quoted, limit) == 1
          and _json_nesting_depth(b"[" * (limit + 5), limit) > limit)
    deepest = b'{"a":' * limit + b"1" + b"}" * limit
    over = b'{"a":' * (limit + 1) + b"1" + b"}" * (limit + 1)
    check("the_reader_accepts_the_deepest_allowed_body_and_refuses_one_container_more",
          _parse_json(deepest) is not None and _refuses(lambda: _parse_json(over))
          and _code(lambda: _parse_json(over)) == NESTING_LIMIT_CODE
          and _code(lambda: _parse_json(b"[" * 5000 + b"]" * 5000)) == NESTING_LIMIT_CODE)


def _code(function):
    """The refusal code of a bounded transport refusal, or the failure type name."""
    try:
        function()
    except ServiceHttpError as refusal:
        return refusal.code
    except BaseException as failure:
        return type(failure).__name__
    return ""


def _binding_checks(check, root):
    """A binding the public can reach must state where the client address comes from."""
    from .http_entrypoint import HOST_CONFIGURATION_VERSION, MANIFEST_VERSION, main, public_binding_refusal
    root.mkdir()
    artifacts = root / "artifacts"
    artifacts.mkdir()
    manifest = root / "manifest.json"
    manifest.write_text(json.dumps({"record_type": MANIFEST_VERSION,
                                    "artifact_root": str(artifacts), "items": []}))
    path = root / "host.json"
    path.write_text(json.dumps({"record_type": HOST_CONFIGURATION_VERSION, "manifest_path": str(manifest),
        "runtime": {"database_path": str(root / "host.db"), "writes_authorized": True},
        "http": {"public_base_url": ORIGIN, "allowed_hosts": [HOST]}, "authentication": {}}))
    check("a_public_binding_without_a_stated_client_address_source_is_refused",
          bool(public_binding_refusal(PUBLIC_BINDING, True, ServiceRequestLimits()))
          and bool(public_binding_refusal(PUBLIC_BINDING, True, _peer()))
          and bool(public_binding_refusal(PUBLIC_BINDING, False, _header()))
          and not public_binding_refusal(PUBLIC_BINDING, True, _header())
          and all(not public_binding_refusal(host, False, ServiceRequestLimits())
                  for host in ("127.0.0.1", "::1", "localhost")))
    stopped = None
    with contextlib.redirect_stderr(io.StringIO()) as complaint:
        try:
            main(["serve", "--config", str(path), "--host", PUBLIC_BINDING, "--behind-trusted-tls-proxy"])
        except SystemExit as chosen:
            stopped = chosen.code
    # The message must carry the repair, because an operator reads it instead
    # of the source when a release will not start.
    check("the_real_serve_command_stops_before_it_serves_the_public_without_the_limit",
          stopped == 2 and "request_limits" in complaint.getvalue()
          and HEADER_SOURCE in complaint.getvalue())


