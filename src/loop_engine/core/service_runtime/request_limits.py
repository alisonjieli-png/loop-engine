"""Failed-attempt limits for each client address at the hosted service boundary.

Kind: internal service mechanics. One immutable settings record and one table
in process memory. The HTTP transport asks two questions: may this address
try to sign in now, and was its attempt refused. This module reads no request,
opens no connection, stores no credential and is not a graph vertex. The
table belongs to one service process. It is not shared between machines and
it is empty again after a restart. The limit is active only when the host
states where the client address comes from; it never guesses, because behind
a proxy the socket peer is the proxy and every caller would share one count.
"""
from __future__ import annotations

from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass, fields
import ipaddress
import math
import re
import threading
import time

REQUEST_LIMITS_RECORD_TYPE = "service_request_limits/v1"
PUBLISHED_LIMIT_RECORD_TYPE = "service_failed_attempt_limit/v1"
REFUSAL_RECORD_TYPE = "service_request_limit_refusal/v1"
LIMIT_REACHED_CODE = "failed_attempt_limit_reached"
NOT_CONFIGURED_SOURCE, SOCKET_PEER_SOURCE, HEADER_SOURCE = "not_configured", "socket_peer", "header"
CLIENT_ADDRESS_SOURCES = (NOT_CONFIGURED_SOURCE, SOCKET_PEER_SOURCE, HEADER_SOURCE)
UNKNOWN_PEER_KEY = "unknown-peer"
# The table holds at most this many failure times over all addresses together.
MAXIMUM_REMEMBERED_FAILURES = 1_000_000
_HEADER_NAME = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,62}[A-Za-z0-9])?")
_LONGEST_ADDRESS_TEXT = 64


@dataclass(frozen=True)
class ServiceRequestLimits:
    """Host settings for refused sign-in attempts from one client address.

    The host states the source of the client address. `socket_peer` is right
    only when callers connect to this process directly. `header` needs the
    exact name of a header that the host's own trusted proxy overwrites on
    every request. Until the host states a source the limit stays inactive.
    """

    client_address_source: str = NOT_CONFIGURED_SOURCE
    client_address_header: str = ""
    failures_allowed: int = 30
    window_seconds: float = 60
    maximum_tracked_addresses: int = 4096
    ipv6_prefix_bits: int = 64
    record_type: str = REQUEST_LIMITS_RECORD_TYPE

    def __post_init__(self):
        if self.record_type != REQUEST_LIMITS_RECORD_TYPE:
            raise ValueError("unsupported request limit settings")
        for name, lowest, highest in (("failures_allowed", 1, 1000), ("maximum_tracked_addresses", 1, 65_536),
                                      ("ipv6_prefix_bits", 32, 128)):
            number = getattr(self, name)
            if type(number) is not int or not lowest <= number <= highest:
                raise ValueError(f"{name} must be a whole number from {lowest} to {highest}")
        if self.failures_allowed * self.maximum_tracked_addresses > MAXIMUM_REMEMBERED_FAILURES:
            raise ValueError("failures allowed multiplied by tracked addresses exceeds the memory allowance")
        window = self.window_seconds
        if type(window) not in (int, float) or not math.isfinite(window) or not 1 <= window <= 86_400:
            raise ValueError("the failure window must be from one second to one day")
        header = self.client_address_header
        if not isinstance(header, str) or (header and _HEADER_NAME.fullmatch(header) is None):
            raise ValueError("the client address header must be empty or one exact header name")
        if self.client_address_source not in CLIENT_ADDRESS_SOURCES:
            raise ValueError("the client address source must be one of the supported sources")
        if (self.client_address_source == HEADER_SOURCE) != bool(header):
            raise ValueError("a header name is required exactly when the client address source is the header")

    @classmethod
    def from_host(cls, value):
        """Accept the typed record, or the exact versioned mapping from a host file."""
        if isinstance(value, cls):
            return value
        names = {item.name for item in fields(cls)}
        if (not isinstance(value, Mapping) or set(value) - names
                or value.get("record_type") != REQUEST_LIMITS_RECORD_TYPE):
            raise ValueError("request limits need the typed record or its exact versioned fields")
        return cls(**value)

    @property
    def active(self):
        return self.client_address_source != NOT_CONFIGURED_SOURCE

    def published(self):
        """The projection published under the `limits` key of the capabilities record.

        Anyone can read that record without signing in. The projection has its
        own record type because it is not the settings record. It says what a
        caller can observe: whether the limit is active, the address source,
        the allowance and the window. It leaves out the name of the trusted
        header and the size of the table. No client needs them, and they would
        tell a caller which header to forge and how many addresses empty the table.
        """
        return {"record_type": PUBLISHED_LIMIT_RECORD_TYPE, "active": self.active,
                "counted": ["refused_authentication", "refused_account_activation",
                            "refused_promotion_redemption"],
                "failures_allowed": self.failures_allowed, "window_seconds": self.window_seconds,
                "client_address_source": self.client_address_source,
                "ipv6_prefix_bits": self.ipv6_prefix_bits,
                "refusal_code": LIMIT_REACHED_CODE,
                "state": "memory_of_one_service_process"}


class FailedAttemptLimiter:
    """Remember refused attempts for each address, inside one process only.

    An address is refused while it has `failures_allowed` refused attempts in
    the last `window_seconds`. An accepted attempt is never counted and never
    clears the count. The caller decides what a refused attempt is. With no
    stated address source nothing is counted and nobody is refused.
    """

    def __init__(self, settings: ServiceRequestLimits, *, clock=time.monotonic):
        if not isinstance(settings, ServiceRequestLimits) or not callable(clock):
            raise TypeError("typed request limit settings and a callable clock are required")
        self.settings, self.clock = settings, clock
        # Address key -> refused attempt times, oldest first. The table is
        # ordered by each address's latest refusal, oldest first.
        self._failures: OrderedDict[str, list[float]] = OrderedDict()
        self._lock = threading.Lock()

    def __len__(self):
        with self._lock:
            return len(self._failures)

    def address_key(self, peer_host, header_values=()):
        """Name the counted address. Only the host-configured header can replace the peer.

        The header counts only when it appears exactly once and holds exactly
        one address. A missing, repeated, listed or malformed value falls back
        to the socket peer, so a caller can never choose an arbitrary key.
        """
        values = tuple(header_values) if self.settings.client_address_source == HEADER_SOURCE else ()
        named = self._canonical(values[0]) if len(values) == 1 else ""
        return named or self._canonical(peer_host) or UNKNOWN_PEER_KEY

    def _canonical(self, value):
        if not isinstance(value, str) or not 0 < len(value) <= _LONGEST_ADDRESS_TEXT:
            return ""
        try:
            address = ipaddress.ip_address(value)
        except ValueError:
            return ""
        if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
            address = address.ipv4_mapped
        if isinstance(address, ipaddress.IPv4Address):
            return str(address)
        # One subscriber usually controls a whole IPv6 prefix, so the prefix is the address.
        unused = 128 - self.settings.ipv6_prefix_bits
        return str(ipaddress.IPv6Network((int(address) >> unused << unused, self.settings.ipv6_prefix_bits)))

    def retry_after(self, key):
        """Whole seconds this address must wait, or zero when it may try now."""
        if not self.settings.active:
            return 0
        with self._lock:
            times = self._failures.get(key)
            if times is None:
                return 0
            now = self.clock()
            self._forget_expired(times, now)
            if not times:
                del self._failures[key]
                return 0
            if len(times) < self.settings.failures_allowed:
                return 0
            return max(1, math.ceil(times[0] + self.settings.window_seconds - now))

    def refusal(self, key):
        """The versioned refusal record while this address is over its limit, else None."""
        wait = self.retry_after(key)
        return {"record_type": REFUSAL_RECORD_TYPE, "retry_after_seconds": wait} if wait else None

    def record_failure(self, key):
        """Count one refused attempt for this address."""
        if not self.settings.active:
            return
        with self._lock:
            now = self.clock()
            times = self._failures.pop(key, [])
            self._forget_expired(times, now)
            times.append(now)
            del times[:-self.settings.failures_allowed]
            self._make_room(now)
            self._failures[key] = times

    def _forget_expired(self, times, now):
        cutoff = now - self.settings.window_seconds
        kept = next((index for index, moment in enumerate(times) if moment > cutoff), len(times))
        del times[:kept]

    def _make_room(self, now):
        """Drop addresses whose window has passed, then the oldest while the table is full."""
        cutoff = now - self.settings.window_seconds
        while self._failures:
            oldest_key, oldest_times = next(iter(self._failures.items()))
            if oldest_times[-1] > cutoff and len(self._failures) < self.settings.maximum_tracked_addresses:
                return
            del self._failures[oldest_key]
