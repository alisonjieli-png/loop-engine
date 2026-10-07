"""A trusted forwarding proxy in front of the platform proxy, and the pinned address ranges it connects from.

Kind: internal service mechanics, read only by the failed-attempt limit (`request_limits.py`). It names a content
network proxy, today Cloudflare, that a host may place in front of the Fly proxy, and the exact address ranges that
proxy connects from, pinned in `data/forwarding_proxy_ranges.json` with their source, date and digest. It reads one
packaged data file, opens no connection, keeps no state and is not a graph vertex. Nothing here is switched on: a
host names a forwarding proxy only in the version 2 request limit record, and no host file does.

```text
visitor ──► Cloudflare edge ──────────► Fly edge ─────────────► Fly proxy ──► service process
            writes CF-Connecting-IP      writes Fly-Client-IP      socket peer: the Fly proxy
            (the visitor's address)      (the Cloudflare address)
```

Behind the Cloudflare proxy, the platform header `Fly-Client-IP` holds a Cloudflare address, so every visitor would
share one count. The limit therefore reads `CF-Connecting-IP`, and only for a request whose connecting address (the
address the platform proxy reports, or the socket peer) lies inside the pinned ranges. From anywhere else the header
is a caller's own text and is ignored. Cloudflare's header documentation (updated May 5, 2026) states that
`CF-Connecting-IP` carries the client address to the origin; that for a Worker subrequest to an origin outside
Cloudflare it reflects the actual client address and only `x-real-ip` can be altered; and that a cross-zone Worker
subrequest carries `2a06:98c0:3600::103`, which lies inside `2a06:98c0::/29`, so all such requests share one /64
key. A range check proves that a request came from Cloudflare's network, not that it passed through Baltor's own
zone; Authenticated Origin Pulls would lock the origin to the zone and is a recorded follow-up, not built here.

```text
forwarding_proxy_range_sets/v1          data/forwarding_proxy_ranges.json, read once and verified
└── forwarding_proxy_range_set/v1       one pinned set: set_id, provider, the header the provider writes,
                                        retrieved_at, sources (url, body digest, etag or last-modified),
                                        ipv4 and ipv6 ranges in the published order, ranges_sha256
service_forwarding_proxy/v1             the host's choice: provider, address_ranges (a pinned set id) and
                                        client_address_header, which must be the header the set names
```

A set is refused when its digest differs from its ranges, when a range is private, loopback, link-local,
unspecified, multicast or reserved, or wider than /8 (IPv4) or /16 (IPv6), and a host record is refused when it
names a set the image does not pin, another provider or another header. New ranges arrive only with a new image:
`tools/check_forwarding_proxy_ranges.py` reads Cloudflare's published lists and prints a candidate set on drift.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields
import functools
import hashlib
from importlib.resources import files
import ipaddress
import json
import re

FORWARDING_PROXY_RECORD_TYPE = "service_forwarding_proxy/v1"
RANGE_SETS_RECORD_TYPE = "forwarding_proxy_range_sets/v1"
RANGE_SET_RECORD_TYPE = "forwarding_proxy_range_set/v1"
CLOUDFLARE = "cloudflare"
#: The forwarding proxies this image knows. Each pinned set names one of them.
PROVIDERS = (CLOUDFLARE,)
RANGES_RESOURCE = ("data", "forwarding_proxy_ranges.json")
#: A pinned set names the documents it was read from; each is read over HTTPS only.
HTTPS_SCHEME = "https"
#: The widest range a pinned set may hold, by address family. Cloudflare's widest ranges are /13 and /29; a /0 in a
#: changed copy would trust every address on the internet.
WIDEST_PREFIX = {4: 8, 6: 16}
_SET_FIELDS = frozenset({"record_type", "set_id", "provider", "client_address_header", "retrieved_at", "sources",
                         "ipv4", "ipv6", "ranges_sha256"})
_SOURCE_FIELDS, _SOURCE_OPTIONAL = frozenset({"url", "body_sha256"}), frozenset({"etag", "last_modified"})
_SET_ID = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?")
_HEADER = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,62}[A-Za-z0-9])?")
_INSTANT = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
_DIGEST = re.compile(r"[0-9a-f]{64}")
#: A source address: a scheme, a host name, an optional port and an optional path, without spaces. The service never
#: requests it; it records where the ranges were read.
_ADDRESS = re.compile(r"(?P<scheme>[a-z][a-z0-9+.-]*)://[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?(?::[0-9]{1,5})?"
                      r"(?:/[^\s]*)?")


def ranges_digest(ipv4, ipv6):
    """SHA-256 of the canonical JSON of both range lists, in their published order."""
    payload = json.dumps({"ipv4": list(ipv4), "ipv6": list(ipv6)}, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True)
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def _unique_keys(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("a range set file names one key twice")
        value[key] = item
    return value


def parse_range_sets(text):
    """Parse a range-set file strictly: a key named twice is a changed file, not a choice between two values."""
    if not isinstance(text, str):
        raise ValueError("a range set file is text")
    return json.loads(text, object_pairs_hook=_unique_keys)


@dataclass(frozen=True)
class ForwardingProxyRangeSet:
    """One verified pinned set: the provider, the header it writes and the networks it connects from."""

    set_id: str
    provider: str
    client_address_header: str
    retrieved_at: str
    networks: tuple
    ranges_sha256: str

    def contains(self, address):
        """Whether one exact address (an ipaddress object) lies inside a range of this set."""
        return any(address.version == network.version and address in network for network in self.networks)


def _network(value, version):
    """One published range, refused unless it is an exact public network of the expected family and width."""
    if not isinstance(value, str):
        raise ValueError("a range is text")
    try:
        network = ipaddress.ip_network(value, strict=True)
    except ValueError:
        raise ValueError(f"not an exact network: {value!r}") from None
    if network.version != version or str(network) != value.lower():
        raise ValueError(f"a range is listed in its own family and canonical form: {value!r}")
    if network.prefixlen < WIDEST_PREFIX[version]:
        raise ValueError(f"a range wider than /{WIDEST_PREFIX[version]} is never trusted: {value!r}")
    if (network.is_private or network.is_loopback or network.is_link_local or network.is_unspecified
            or network.is_multicast or network.is_reserved):
        raise ValueError(f"a private, loopback, link-local, unspecified, multicast or reserved range: {value!r}")
    return network


def _source(value):
    if (not isinstance(value, Mapping) or not _SOURCE_FIELDS <= set(value)
            or set(value) - _SOURCE_FIELDS - _SOURCE_OPTIONAL):
        raise ValueError("a source names its address and body digest, with an optional etag or last-modified date")
    address = _ADDRESS.fullmatch(value["url"]) if isinstance(value["url"], str) else None
    if address is None or address.group("scheme") != HTTPS_SCHEME:
        raise ValueError("a source is an https address")
    if not isinstance(value["body_sha256"], str) or _DIGEST.fullmatch(value["body_sha256"]) is None:
        raise ValueError("a source body digest is 64 lowercase hexadecimal characters")
    if any(not isinstance(value[name], str) or not value[name] for name in _SOURCE_OPTIONAL & set(value)):
        raise ValueError("an etag or last-modified date is nonempty text")


def _ranges_match_digest(entry):
    """Whether a set's stated digest is the digest of its two range lists."""
    return entry["ranges_sha256"] == ranges_digest(entry["ipv4"], entry["ipv6"])


def _range_set(entry):
    if not isinstance(entry, Mapping) or set(entry) != _SET_FIELDS or entry["record_type"] != RANGE_SET_RECORD_TYPE:
        raise ValueError(f"each set is one {RANGE_SET_RECORD_TYPE} record with exactly its own fields")
    if not isinstance(entry["set_id"], str) or _SET_ID.fullmatch(entry["set_id"]) is None:
        raise ValueError("a set id is lowercase letters, digits and hyphens")
    if entry["provider"] not in PROVIDERS:
        raise ValueError(f"a set names one of the known providers {PROVIDERS}")
    if not isinstance(entry["client_address_header"], str) or _HEADER.fullmatch(entry["client_address_header"]) is None:
        raise ValueError("a set names the one exact header its provider writes")
    if not isinstance(entry["retrieved_at"], str) or _INSTANT.fullmatch(entry["retrieved_at"]) is None:
        raise ValueError("a set states when it was read, in UTC seconds")
    if not isinstance(entry["sources"], list) or not entry["sources"]:
        raise ValueError("a set names the documents it was read from")
    for source in entry["sources"]:
        _source(source)
    if not isinstance(entry["ipv4"], list) or not isinstance(entry["ipv6"], list) or not entry["ipv4"] + entry["ipv6"]:
        raise ValueError("a set lists its IPv4 and IPv6 ranges")
    networks = tuple(_network(value, 4) for value in entry["ipv4"]) + tuple(_network(value, 6) for value in entry["ipv6"])
    if len(set(networks)) != len(networks):
        raise ValueError("a set lists each range once")
    if not isinstance(entry["ranges_sha256"], str) or not _ranges_match_digest(entry):
        raise ValueError("the ranges differ from the digest the set states")
    return ForwardingProxyRangeSet(entry["set_id"], entry["provider"], entry["client_address_header"],
                                   entry["retrieved_at"], networks, entry["ranges_sha256"])


def read_range_sets(payload):
    """Every set of one parsed range-set file, verified, by set id; anything inexact is refused."""
    if (not isinstance(payload, Mapping) or set(payload) != {"record_type", "sets"}
            or payload["record_type"] != RANGE_SETS_RECORD_TYPE or not isinstance(payload["sets"], list)
            or not payload["sets"]):
        raise ValueError(f"a range set file is one {RANGE_SETS_RECORD_TYPE} record with its sets")
    sets = {}
    for entry in payload["sets"]:
        verified = _range_set(entry)
        if verified.set_id in sets:
            raise ValueError("a set id appears once")
        sets[verified.set_id] = verified
    return sets


@functools.lru_cache(maxsize=1)
def pinned_range_sets():
    """The sets this image pins, read from its own package data and verified once."""
    return read_range_sets(parse_range_sets(files("loop_engine").joinpath(*RANGES_RESOURCE).read_text("utf-8")))


def pinned_range_set(set_id):
    """One pinned set by its id, or a refusal naming the sets this image offers."""
    chosen = pinned_range_sets().get(set_id) if isinstance(set_id, str) else None
    if chosen is None:
        raise ValueError(f"this image pins no forwarding proxy range set {set_id!r}; "
                         f"it pins {sorted(pinned_range_sets())}")
    return chosen


@dataclass(frozen=True)
class ServiceForwardingProxy:
    """The host's statement that a known proxy forwards every request, and which pinned ranges it connects from.

    The header must be the one the pinned set says its provider writes; a host cannot name `X-Forwarded-For`,
    which a caller can extend, or any other header a caller controls.
    """

    provider: str
    address_ranges: str
    client_address_header: str
    record_type: str = FORWARDING_PROXY_RECORD_TYPE

    def __post_init__(self):
        if self.record_type != FORWARDING_PROXY_RECORD_TYPE:
            raise ValueError("unsupported forwarding proxy record")
        if self.provider not in PROVIDERS:
            raise ValueError(f"the forwarding proxy is one of {PROVIDERS}")
        chosen = pinned_range_set(self.address_ranges)
        if chosen.provider != self.provider:
            raise ValueError("the pinned range set belongs to another provider")
        if self.client_address_header != chosen.client_address_header:
            raise ValueError(f"the forwarding proxy's address header is {chosen.client_address_header}, the header "
                             f"its provider writes on every request")

    @classmethod
    def from_host(cls, value):
        """Accept the typed record, or its exact versioned mapping from a host file."""
        if isinstance(value, cls):
            return value
        names = {item.name for item in fields(cls)}
        if (not isinstance(value, Mapping) or set(value) - names
                or value.get("record_type") != FORWARDING_PROXY_RECORD_TYPE):
            raise ValueError("a forwarding proxy needs the typed record or its exact versioned fields")
        return cls(**value)

    @property
    def range_set(self):
        return pinned_range_set(self.address_ranges)

    def trusts(self, address):
        """Whether a request whose connecting address is `address` came from this proxy's pinned ranges."""
        return self.range_set.contains(address)
