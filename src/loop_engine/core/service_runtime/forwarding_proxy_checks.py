"""Checks for the trusted forwarding proxy of the failed-attempt limit (Cloudflare in front of the Fly proxy).

Run by `request_limit_checks.run_checks`, which `http_checks` runs, beside the checks of the version 1 limit; this
module holds the version 2 cases so that module stays under the size cap. The limiter is driven directly, and the
real service application is driven through ASGI with a chosen socket peer and chosen headers, as the version 1
checks do. The pinned range file is read from the package and changed copies are built in memory. No socket, no
network and no provider is used. Every guard is shown twice where it has one: the known-wrong case, and a
removed-guard control that patches the guard away and requires the check's own predicate to fail.

```text
Known-wrong cases
├── a forged CF-Connecting-IP from an address outside the pinned ranges          ignored; counted once
├── trusting CF-Connecting-IP from any address (a version 1 header mapping)       evades the limit
├── today's version 1 mapping behind the Cloudflare proxy                          every visitor shares one count
├── a missing, repeated, listed or malformed proxy header                          counted for the edge address
├── an inexact version 2 host mapping (unknown key or set, no proxy, wrong record) stops the host loader
└── a changed copy of the pinned ranges                                             refused when it is read
```
"""
from __future__ import annotations

from dataclasses import asdict
import json
from unittest.mock import patch

from . import forwarding_proxy
from .forwarding_proxy import (CLOUDFLARE, FORWARDING_PROXY_RECORD_TYPE, RANGES_RESOURCE, ServiceForwardingProxy,
                               parse_range_sets, pinned_range_sets, ranges_digest, read_range_sets)
from .request_limit_checks import (FIRST, HOST, ORIGIN, PROXY, PROXY_HEADER, SECOND, VICTIM, WRONG, _header, _peer,
                                   _refuses, _Service)
from .request_limits import (FORWARDED_REQUEST_LIMITS_RECORD_TYPE, HEADER_SOURCE, NOT_CONFIGURED_SOURCE,
                             REQUEST_LIMITS_RECORD_TYPE, SOCKET_PEER_SOURCE, FailedAttemptLimiter,
                             ForwardedRequestLimits, ServiceRequestLimits)

SET_ID = "cloudflare-2026-10-05"
CF_HEADER = "CF-Connecting-IP"
#: Addresses inside and just outside the pinned ranges. No request is sent to any of them.
EDGE, EDGE_V6 = "162.158.0.10", "2606:4700:10::6816:1"
#: The address Cloudflare gives a cross-zone Worker subrequest; it lies inside 2a06:98c0::/29.
WORKERS = "2a06:98c0:3600::103"
INSIDE_V4, OUTSIDE_V4 = "104.27.255.254", "104.28.0.1"  # the last address of 104.24.0.0/14 and the next one
INSIDE_V6, OUTSIDE_V6 = "2a06:98c7:ffff::1", "2a06:98c8::1"  # inside 2a06:98c0::/29 and the next /29
VISITOR_V6 = "2001:db8:5::1"


def _proxy(**changes):
    return ServiceForwardingProxy(**{"provider": CLOUDFLARE, "address_ranges": SET_ID,
                                     "client_address_header": CF_HEADER, **changes})


def _forwarded(source=HEADER_SOURCE, **changes):
    """Version 2 settings: the Fly header (or the socket peer) and the pinned Cloudflare ranges."""
    header = PROXY_HEADER if source == HEADER_SOURCE else ""
    return ForwardedRequestLimits(client_address_source=source, client_address_header=header,
                                  forwarding_proxy=_proxy(), **changes)


def _mapping(**changes):
    """The version 2 host file mapping the README gives, not enabled on any host."""
    return {"record_type": FORWARDED_REQUEST_LIMITS_RECORD_TYPE, "client_address_source": HEADER_SOURCE,
            "client_address_header": PROXY_HEADER,
            "forwarding_proxy": {"record_type": FORWARDING_PROXY_RECORD_TYPE, "provider": CLOUDFLARE,
                                 "address_ranges": SET_ID, "client_address_header": CF_HEADER}, **changes}


def _setting_checks(check):
    v1, v2 = _header(), _forwarded()
    stored_v1, stored_v2 = (json.loads(json.dumps(asdict(value))) for value in (v1, v2))
    check("version_2_names_a_forwarding_proxy_and_version_1_keeps_its_exact_fields",
          v2.record_type == FORWARDED_REQUEST_LIMITS_RECORD_TYPE and v1.record_type == REQUEST_LIMITS_RECORD_TYPE
          and v1.forwarding_proxy is None and ServiceRequestLimits().forwarding_proxy is None
          and "forwarding_proxy" not in stored_v1 and stored_v2["forwarding_proxy"]["address_ranges"] == SET_ID
          and ServiceRequestLimits.from_host(stored_v1) == v1 and ServiceRequestLimits.from_host(stored_v2) == v2
          and type(ServiceRequestLimits.from_host(stored_v2)) is ForwardedRequestLimits and v1 != v2
          and v2.published() == v1.published() and v2.active)
    unusable = [
        lambda: ForwardedRequestLimits(client_address_source=HEADER_SOURCE, client_address_header=PROXY_HEADER),
        lambda: ForwardedRequestLimits(forwarding_proxy=_proxy()),
        lambda: ForwardedRequestLimits(client_address_source=HEADER_SOURCE, client_address_header=CF_HEADER,
                                       forwarding_proxy=_proxy()),
        lambda: ForwardedRequestLimits(client_address_source=HEADER_SOURCE, client_address_header="cf-connecting-ip",
                                       forwarding_proxy=_proxy()),
        lambda: ForwardedRequestLimits(client_address_source=HEADER_SOURCE, client_address_header=PROXY_HEADER,
                                       forwarding_proxy=asdict(_proxy())),
        lambda: ForwardedRequestLimits(client_address_source=HEADER_SOURCE, client_address_header=PROXY_HEADER,
                                       forwarding_proxy=_proxy(), record_type=REQUEST_LIMITS_RECORD_TYPE),
        lambda: ServiceRequestLimits(record_type=FORWARDED_REQUEST_LIMITS_RECORD_TYPE),
        lambda: _proxy(address_ranges="cloudflare-1999-01-01"), lambda: _proxy(provider="fastly"),
        lambda: _proxy(client_address_header="X-Forwarded-For"), lambda: _proxy(client_address_header="True-Client-IP"),
        lambda: _proxy(client_address_header="cf-connecting-ip"),
        lambda: _proxy(record_type="service_forwarding_proxy/v2")]
    check("version_2_settings_refuse_an_absent_unknown_or_caller_controlled_forwarding_proxy",
          all(_refuses(case) for case in unusable) and _forwarded(SOCKET_PEER_SOURCE).active)


def _load(root, name, http):
    """The real host loader over one host file whose http block holds `http`."""
    from .http_entrypoint import HOST_CONFIGURATION_VERSION, MANIFEST_VERSION, load_host_application
    folder = root / name
    folder.mkdir(parents=True)
    manifest = folder / "manifest.json"
    manifest.write_text(json.dumps({"record_type": MANIFEST_VERSION, "artifact_root": str(folder), "items": []}))
    path = folder / "host.json"
    path.write_text(json.dumps({"record_type": HOST_CONFIGURATION_VERSION, "manifest_path": str(manifest),
        "runtime": {"database_path": str(folder / "host.db"), "writes_authorized": True},
        "http": {"public_base_url": ORIGIN, "allowed_hosts": [HOST], **http}, "authentication": {}}))
    application = load_host_application(str(path))[0]
    application._workers.shutdown(wait=True)
    return (application.configuration.request_limits,
            application.capabilities()["limits"]["failed_attempts_per_address"])


def _host_file_checks(check, root):
    settings, published = _load(root, "v2", {"request_limits": _mapping()})
    v1_settings, v1_published = _load(root, "v1", {"request_limits": {
        "record_type": REQUEST_LIMITS_RECORD_TYPE, "client_address_source": HEADER_SOURCE,
        "client_address_header": PROXY_HEADER}})
    check("the_version_2_host_file_mapping_activates_the_forwarding_proxy_through_the_real_host_loader",
          settings == _forwarded() and v1_settings == _header() and published == v1_published
          and (published["active"], published["client_address_source"]) == (True, HEADER_SOURCE))
    proxy = _mapping()["forwarding_proxy"]
    inexact = [_mapping(trust_forwarded_for=True), _mapping(forwarding_proxy=None), _mapping(forwarding_proxy=[proxy]),
               _mapping(forwarding_proxy=SET_ID), _mapping(record_type="service_request_limits/v9"),
               _mapping(client_address_source=NOT_CONFIGURED_SOURCE, client_address_header=""),
               _mapping(forwarding_proxy={**proxy, "address_ranges": "cloudflare-1999-01-01"}),
               _mapping(forwarding_proxy={**proxy, "record_type": "service_forwarding_proxy/v2"}),
               _mapping(forwarding_proxy={**proxy, "ranges": ["0.0.0.0/0"]}),
               _mapping(forwarding_proxy={**proxy, "provider": "fastly"}),
               _mapping(forwarding_proxy={**proxy, "client_address_header": "X-Forwarded-For"}),
               {key: value for key, value in _mapping().items() if key != "forwarding_proxy"},
               {**_mapping(), "record_type": REQUEST_LIMITS_RECORD_TYPE}]
    check("an_inexact_version_2_host_file_mapping_stops_the_host_loader_before_it_serves",
          all(_refuses(lambda row=row, index=index: _load(root, f"inexact-{index}", {"request_limits": row}))
              for index, row in enumerate(inexact)))


def _packaged_text():
    from importlib.resources import files
    return files("loop_engine").joinpath(*RANGES_RESOURCE).read_text("utf-8")


def _changed_copies():
    """Changed copies of the pinned file, each paired with whether it restates its digest to match."""
    original = parse_range_sets(_packaged_text())

    def changed(edit, restate):
        payload = json.loads(json.dumps(original))
        entry = payload["sets"][0]
        edit(entry, payload)
        if restate:
            entry["ranges_sha256"] = ranges_digest(entry["ipv4"], entry["ipv6"])
        return payload
    return [changed(lambda entry, _p: entry["ipv4"].append("8.8.8.0/24"), False),
            changed(lambda entry, _p: entry["ipv4"].append("10.0.0.0/8"), True),
            changed(lambda entry, _p: entry["ipv4"].append("0.0.0.0/0"), True),
            changed(lambda entry, _p: entry["ipv6"].append("fe80::/64"), True),
            changed(lambda entry, _p: entry["ipv4"].append("2606:4700::/32"), True),
            changed(lambda entry, _p: entry["ipv6"].__setitem__(1, "2606:4700:0::/32"), True),
            changed(lambda entry, _p: entry["ipv4"].append(entry["ipv4"][0]), True),
            changed(lambda entry, _p: entry.__setitem__("provider", "fastly"), False),
            changed(lambda entry, _p: entry.__setitem__("client_address_header", "X Forwarded"), False),
            changed(lambda entry, _p: entry["sources"][0].__setitem__("url", "http://api.cloudflare.com/ips"), False),
            changed(lambda entry, _p: entry.__setitem__("note", "extra"), False),
            changed(lambda entry, payload: payload["sets"].append(json.loads(json.dumps(entry))), False)]


def _changed_copies_refused():
    first = _changed_copies()[0]
    return (all(_refuses(lambda payload=payload: read_range_sets(payload)) for payload in _changed_copies())
            and _refuses(lambda: read_range_sets(first)))


def _pinned_file_checks(check):
    text = _packaged_text()
    pinned = pinned_range_sets()[SET_ID]
    entry = parse_range_sets(text)["sets"][0]
    check("the_pinned_cloudflare_ranges_verify_against_their_stated_digest_and_sources",
          set(pinned_range_sets()) == {SET_ID} and pinned.provider == CLOUDFLARE
          and pinned.client_address_header == CF_HEADER and pinned.retrieved_at == "2026-10-05T22:50:04Z"
          and [network.version for network in pinned.networks] == [4] * 15 + [6] * 7
          and pinned.ranges_sha256 == ranges_digest(entry["ipv4"], entry["ipv6"])
          and [source["url"].startswith("https://") for source in entry["sources"]] == [True] * 3)
    duplicated = text.replace(f'"set_id": "{SET_ID}"', f'"set_id": "first", "set_id": "{SET_ID}"', 1)
    check("a_changed_copy_of_the_pinned_ranges_is_refused_when_it_is_read",
          _changed_copies_refused() and duplicated != text and _refuses(lambda: parse_range_sets(duplicated)))
    with patch.object(forwarding_proxy, "_ranges_match_digest", lambda entry: True):
        check("removed_range_digest_rule_is_detected", not _changed_copies_refused())


def _inside_and_outside():
    """(connecting address, proxy header values, expected key) under the version 2 header settings."""
    return [(EDGE, [FIRST], FIRST), (EDGE_V6, [VISITOR_V6], "2001:db8:5::/64"),
            ("::ffff:" + EDGE, [FIRST], FIRST), (EDGE, ["::ffff:" + FIRST], FIRST),
            (INSIDE_V4, [FIRST], FIRST), (OUTSIDE_V4, [FIRST], OUTSIDE_V4),
            (INSIDE_V6, [FIRST], FIRST), (OUTSIDE_V6, [FIRST], "2a06:98c8::/64"),
            (WORKERS, [FIRST], FIRST), (EDGE, [WORKERS], "2a06:98c0:3600::/64"),
            (SECOND, [VICTIM], SECOND), ("2001:db8:7::9", [VICTIM], "2001:db8:7::/64")]


def _membership_holds():
    limiter, peer_limiter = FailedAttemptLimiter(_forwarded()), FailedAttemptLimiter(_forwarded(SOCKET_PEER_SOURCE))
    return (all(limiter.address_key(PROXY, [connecting], forwarded) == expected
                for connecting, forwarded, expected in _inside_and_outside())
            and peer_limiter.address_key(EDGE, [], [FIRST]) == FIRST
            and peer_limiter.address_key(SECOND, [EDGE], [VICTIM]) == SECOND
            and limiter.address_key(EDGE, [], [FIRST]) == FIRST)


def _limiter_checks(check):
    check("a_forwarding_proxy_header_names_the_visitor_only_for_a_connecting_address_inside_the_pinned_ranges",
          _membership_holds())
    with patch.object(ServiceForwardingProxy, "trusts", lambda self, address: True):
        check("removed_pinned_range_rule_is_detected", not _membership_holds())
    limiter = FailedAttemptLimiter(_forwarded())
    unusable = ([], [FIRST, SECOND], [FIRST + ", " + SECOND], ["not-an-address"], [" " + FIRST], [""],
                [FIRST + ":443"], ["2001:db8::" + "1" * 80], [None])
    check("a_missing_repeated_listed_or_malformed_proxy_header_counts_the_connecting_address",
          all(limiter.address_key(PROXY, [EDGE], values) == EDGE for values in unusable)
          and limiter.address_key(PROXY, [EDGE, EDGE_V6], [FIRST]) == PROXY)
    check("version_1_settings_never_read_the_forwarding_proxy_header",
          FailedAttemptLimiter(_header()).address_key(PROXY, [EDGE], [VICTIM]) == EDGE
          and FailedAttemptLimiter(_peer()).address_key(EDGE, [], [VICTIM]) == EDGE
          and FailedAttemptLimiter(ServiceRequestLimits()).address_key(EDGE, [EDGE], [VICTIM]) == "")


def _forged(root, limits, attempts=32):
    """One caller outside the ranges rotates a forged CF-Connecting-IP on every refused attempt."""
    service = _Service(root, limits)
    try:
        statuses = [service.status("GET", "/api/v1/session", peer=PROXY, headers=[
            *WRONG.items(), (PROXY_HEADER, FIRST), (CF_HEADER, f"203.0.113.{attempt + 1}")])
            for attempt in range(attempts)]
        return {"statuses": statuses, "counted": list(service.application.request_limiter._failures),
                "victim": service.status("GET", "/api/v1/session", peer=PROXY, headers=[
                    *service.valid.items(), (PROXY_HEADER, EDGE), (CF_HEADER, VICTIM)])}
    finally:
        service.close()


def _forged_holds(seen):
    return seen == {"statuses": [401] * 30 + [429] * 2, "counted": [FIRST], "victim": 200}


def _visitors(root, limits):
    """Two visitors behind one Cloudflare edge address, the first failing past its allowance of three."""
    service = _Service(root, limits)
    try:
        def through_edge(visitor, credential, extra=()):
            return service.status("GET", "/api/v1/session", peer=PROXY, headers=[
                *credential.items(), (PROXY_HEADER, EDGE), (CF_HEADER, visitor), *extra])
        seen = {"first": [through_edge(FIRST, WRONG) for _attempt in range(4)],
                "second": [through_edge(SECOND, service.valid), through_edge(SECOND, WRONG)]}
        seen["counted"] = list(service.application.request_limiter._failures)
        return seen
    finally:
        service.close()


def _visitors_hold(seen):
    return seen == {"first": [401, 401, 401, 429], "second": [200, 401], "counted": [FIRST, SECOND]}


def _repeated(root):
    """Through the edge, every refused attempt repeats the proxy header to name a victim beside itself."""
    service = _Service(root, _forwarded(failures_allowed=3))
    try:
        statuses = [service.status("GET", "/api/v1/session", peer=PROXY, headers=[
            *WRONG.items(), (PROXY_HEADER, EDGE), (CF_HEADER, VICTIM), (CF_HEADER, f"203.0.113.{attempt + 1}")])
            for attempt in range(4)]
        counted = list(service.application.request_limiter._failures)
        victim = service.status("GET", "/api/v1/session", peer=PROXY, headers=[
            *service.valid.items(), (PROXY_HEADER, EDGE), (CF_HEADER, VICTIM)])
        return {"statuses": statuses, "counted": counted, "victim": victim}
    finally:
        service.close()


def _published(root):
    service = _Service(root, _forwarded(failures_allowed=3))
    try:
        status, _headers, body = service.send("GET", "/api/v1/capabilities", peer=PROXY)
        return status, body
    finally:
        service.close()


def _transport_checks(check, root):
    check("a_forged_forwarding_proxy_header_from_outside_the_ranges_never_moves_the_count",
          _forged_holds(_forged(root / "forged", _forwarded())))
    with patch.object(ServiceForwardingProxy, "trusts", lambda self, address: True):
        trusting = _forged(root / "forged-trusting-every-address", _forwarded())
    check("removed_forwarding_proxy_range_rule_through_the_application_is_detected",
          not _forged_holds(trusting) and 429 not in trusting["statuses"] and len(trusting["counted"]) == 32)
    # Known-wrong configuration: CF-Connecting-IP named as the host's own header, read from any caller.
    naive = _forged(root / "forged-naive-header", _header(CF_HEADER))
    check("trusting_the_cloudflare_header_from_any_address_is_the_known_wrong_case",
          not _forged_holds(naive) and 429 not in naive["statuses"])
    check("visitors_behind_one_cloudflare_address_are_counted_separately",
          _visitors_hold(_visitors(root / "visitors", _forwarded(failures_allowed=3))))
    shared = _visitors(root / "visitors-version-1", _header(failures_allowed=3))
    check("version_1_behind_the_cloudflare_proxy_puts_every_visitor_in_one_count_the_known_wrong_case",
          not _visitors_hold(shared) and shared["second"][0] == 429 and shared["counted"] == [EDGE])
    with patch.object(ServiceForwardingProxy, "trusts", lambda self, address: False):
        check("removed_trust_of_the_pinned_ranges_is_detected",
              not _visitors_hold(_visitors(root / "visitors-never-trusted", _forwarded(failures_allowed=3))))
    check("a_repeated_proxy_header_through_the_application_counts_the_edge_and_cannot_name_a_victim",
          _repeated(root / "repeated") == {"statuses": [401, 401, 401, 429], "counted": [EDGE], "victim": 200})
    status, body = _published(root / "published")
    text = json.dumps(body).lower()
    check("capabilities_of_a_forwarded_host_name_no_proxy_header_provider_or_range_set",
          status == 200 and body["result"]["limits"]["failed_attempts_per_address"]
          == _header(failures_allowed=3).published()
          and not any(word in text for word in (CF_HEADER.lower(), "forwarding", CLOUDFLARE, SET_ID)))


def run_checks(check, root):
    root.mkdir(parents=True, exist_ok=True)
    _setting_checks(check)
    _pinned_file_checks(check)
    _limiter_checks(check)
    _host_file_checks(check, root / "host-file")
    _transport_checks(check, root)
