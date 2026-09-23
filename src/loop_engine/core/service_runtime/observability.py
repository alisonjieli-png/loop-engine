"""Operator observability for the hosted service: request identity, a durable
failure journal, and a readiness answer that can fail.

Three separate facts live here and they are not merged.

1. A request reference is an unguessable name for one request. It is issued
   from the operating system random source and from nothing else, so it can
   never be derived from a credential. The customer sees it in the refusal and
   the operator searches for it.
2. A failure record is metadata about a refused request: its reference, its
   route, the typed refusal code, the tenant, the time and the version of the
   service. It never holds a credential, a header that carries authority, or
   the body of a private payload. A host that wants the request body must
   choose that in its configuration; the default records metadata only.
3. Readiness is a measured answer. Alive means the process answers. Ready
   means every required dependency answered just now. They are different
   fields with different meanings, and readiness can report not ready.

This module holds internal runtime mechanics. It is not an executable graph
vertex and it does not create another runtime type or another intelligence
layer. The transport Loop that already owns the request owns these records.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass, field
import secrets
import threading
import time

from .records import ServiceRuntimeError, identifier
from .storage import ServiceCatalogBinding

FAILURE_RECORD_VERSION = "service_request_failure/v1"
FAILURE_LIST_VERSION = "service_request_failure_list/v1"
OBSERVABILITY_POLICY_VERSION = "service_observability_policy/v1"
HEALTH_RECORD_VERSION = "service_health/v2"
#: The durable artifact kind of one failure record. It lives in the same
#: service collection and namespace as every other service record, so no
#: parallel store is created.
FAILURE_KIND = "service_request_failure"
#: The reference that names one request. Four characters of prefix and
#: twenty-six characters of lower case RFC 4648 base32, which holds the whole
#: of one hundred and twenty-eight random bits. That alphabet has no zero, no
#: one, no eight and no nine, so a person reading a reference out of a refusal
#: cannot confuse a zero with a letter O or a one with a letter I.
REFERENCE_PREFIX = "ref_"
REFERENCE_BODY_BYTES = 16
REFERENCE_BODY_CHARACTERS = 26
REFERENCE_ALPHABET = frozenset("abcdefghijklmnopqrstuvwxyz234567")
REFERENCE_CHARACTERS = len(REFERENCE_PREFIX) + REFERENCE_BODY_CHARACTERS
#: The route recorded when the request did not match a declared route. The raw
#: path is never recorded, because a path outside the declared set can carry
#: anything a stranger chose to send, including something private.
UNMATCHED_ROUTE = "unmatched"
#: The exact request methods this service answers, and one name for anything
#: else. A stranger can send any method text, so the text itself is not stored.
OTHER_METHOD = "other"
HTTP_METHODS = ("GET", "POST", "OPTIONS", "HEAD", "PUT", "PATCH", "DELETE")
RECORDED_METHODS = (*HTTP_METHODS, OTHER_METHOD)
#: The largest number of failure records one read may return. It bounds the
#: answer an operator command prints; it is not the number the service keeps.
MAXIMUM_FAILURE_LISTING = 1000
#: What a failure record may hold about the request itself.
METADATA_ONLY, METADATA_AND_REQUEST_BODY = "metadata_only", "metadata_and_request_body"
PAYLOAD_CAPTURE_CHOICES = (METADATA_ONLY, METADATA_AND_REQUEST_BODY)
#: The ASGI scope key that carries the captured request body of one request
#: when, and only when, the host has chosen to capture request bodies.
CAPTURED_BODY_KEY = "service_observability_request_body"
SCOPE_REFERENCE_KEY = "service_observability_request_reference"

_REFERENCE_ISSUER = object()


@dataclass(frozen=True)
class RequestReference:
    """One issued request reference; it cannot be built from a credential.

    Only `new_request_reference` can build one, because only this module holds
    the issuer object that the journal checks. A caller that computes a value
    from a credential, from an address or from anything else cannot present it
    as a reference: the journal refuses it with `unissued_request_reference`.
    """

    value: str
    _issuer: object = field(repr=False, compare=False, default=None)

    def __post_init__(self):
        if not valid_reference(self.value):
            raise ServiceRuntimeError("invalid_request_reference")


def valid_reference(value):
    """Return whether a value has the exact shape of an issued reference."""
    return (isinstance(value, str) and len(value) == REFERENCE_CHARACTERS
            and value.startswith(REFERENCE_PREFIX)
            and all(character in REFERENCE_ALPHABET for character in value[len(REFERENCE_PREFIX):]))


def new_request_reference():
    """Issue one request reference from the operating system random source.

    This function takes no argument. There is nothing for a credential, an
    address, a tenant or a request body to enter through, so a reference can
    carry no information about the caller. A check reads this signature and
    fails when an argument is added.
    """
    body = base64.b32encode(secrets.token_bytes(REFERENCE_BODY_BYTES)).decode("ascii").rstrip("=").lower()
    return RequestReference(REFERENCE_PREFIX + body, _REFERENCE_ISSUER)


@dataclass(frozen=True)
class ServiceObservabilityPolicy:
    """What one host records about a refused request, and how much it keeps.

    `retained_failures` bounds the durable cost. The journal keeps that many
    records and no more, so a stranger who sends refused requests for a day
    cannot fill the volume the service runs on.
    """

    record_failures: bool = True
    retained_failures: int = 500
    payload_capture: str = METADATA_ONLY
    #: The free space the volume must still have for the service to call itself
    #: ready. Sixteen mebibytes is the default: enough room for the durable
    #: store to finish a transaction and for an operator to act, and small
    #: enough that an ordinarily busy volume does not report a false alarm.
    #: A host with a different volume size names its own figure.
    minimum_free_bytes: int = 16 * 1024 * 1024
    #: The exact release the operator deployed, when the host knows it. The
    #: distribution version is always recorded; this names the build on top of
    #: it. Empty text means the host did not state one, which is recorded as
    #: unknown rather than guessed.
    release_reference: str = ""
    record_type: str = OBSERVABILITY_POLICY_VERSION

    def __post_init__(self):
        if self.record_type != OBSERVABILITY_POLICY_VERSION:
            raise ServiceRuntimeError("unsupported_observability_policy")
        if type(self.record_failures) is not bool:
            raise ServiceRuntimeError("invalid_observability_policy",
                                      "failure recording must be an explicit Boolean")
        if type(self.retained_failures) is not int or not 1 <= self.retained_failures <= 100_000:
            raise ServiceRuntimeError("invalid_observability_policy",
                                      "retained failures must be a positive bounded count")
        if self.payload_capture not in PAYLOAD_CAPTURE_CHOICES:
            raise ServiceRuntimeError("invalid_observability_policy",
                                      "payload capture must name a declared choice")
        if type(self.minimum_free_bytes) is not int or not 0 < self.minimum_free_bytes <= 2**40:
            raise ServiceRuntimeError("invalid_observability_policy",
                                      "the required free space is a positive bounded number of bytes")
        if not isinstance(self.release_reference, str) or len(self.release_reference) > 200:
            raise ServiceRuntimeError("invalid_observability_policy", "a release reference is bounded text")
        if self.release_reference and (not self.release_reference.isascii()
                                       or not self.release_reference.isprintable()):
            raise ServiceRuntimeError("invalid_observability_policy",
                                      "a release reference is printable ASCII text")

    @property
    def captures_request_body(self):
        return self.payload_capture == METADATA_AND_REQUEST_BODY


def service_version():
    """Return the installed distribution version, or explicit unknown text."""
    from importlib.metadata import PackageNotFoundError, version
    try:
        return version("loop-engine")
    except PackageNotFoundError:
        return "unknown"


@dataclass(frozen=True)
class ServiceFailureJournal:
    """A bounded durable ring of refused-request records over the service store.

    Each record occupies one slot. The slot of a record is its sequence number
    modulo the retained count, so the newest records replace the oldest and the
    number of stored records never passes the retained count. Two requests
    never choose the same slot at the same time, because the sequence comes
    from one counter under one lock.
    """

    config: object
    declared_routes: tuple[str, ...]
    policy: ServiceObservabilityPolicy = ServiceObservabilityPolicy()
    clock: object = field(default=time.time, repr=False)

    def __post_init__(self):
        from .records import ServiceRuntimeConfig
        if not isinstance(self.config, ServiceRuntimeConfig):
            raise ServiceRuntimeError("invalid_configuration")
        if not isinstance(self.policy, ServiceObservabilityPolicy):
            raise ServiceRuntimeError("invalid_observability_policy")
        routes = tuple(self.declared_routes)
        if not routes or any(not isinstance(route, str) or not route.startswith("/") for route in routes):
            raise ServiceRuntimeError("invalid_observability_policy",
                                      "declared routes are absolute paths")
        if not callable(self.clock):
            raise ServiceRuntimeError("invalid_configuration")
        object.__setattr__(self, "declared_routes", tuple(dict.fromkeys(routes)))
        object.__setattr__(self, "_binding", ServiceCatalogBinding(self.config))
        object.__setattr__(self, "_lock", threading.Lock())
        object.__setattr__(self, "_next", None)

    @staticmethod
    def method_of(value):
        """Return a declared method name, or the name for anything else."""
        return value if value in HTTP_METHODS else OTHER_METHOD

    def route_of(self, path):
        """Return the declared route of a path, or the unmatched name.

        A path the service does not declare is never recorded as written. A
        stranger chooses that text and it can hold anything.
        """
        return path if isinstance(path, str) and path in self.declared_routes else UNMATCHED_ROUTE

    def _sequence(self):
        """Reserve the next sequence number, continuing after a restart."""
        with self._lock:
            if self._next is None:
                object.__setattr__(self, "_next", self._highest_sequence() + 1)
            value = self._next
            object.__setattr__(self, "_next", value + 1)
            return value

    def _highest_sequence(self):
        try:
            with self._binding.store() as store:
                rows = self._stored_rows(store)
        except Exception:
            return 0
        numbers = [row["payload"]["sequence"] for row in rows
                   if type(row.get("payload", {}).get("sequence")) is int]
        return max(numbers, default=0)

    def _stored_rows(self, store, *, tenant_id=None):
        from ...catalog.query import IntelligenceQuery
        from .records import SERVICE_COLLECTION
        attributes = {} if tenant_id is None else {"tenant_id": {"equals": tenant_id}}
        rows = store.query(IntelligenceQuery(namespaces=(self.config.namespace,),
            source_collections=(SERVICE_COLLECTION,), artifact_kinds=(FAILURE_KIND,),
            attributes=attributes))
        kept = []
        for row in rows:
            payload = row.get("payload")
            if (row.get("namespace") != self.config.namespace
                    or row.get("source_collection") != SERVICE_COLLECTION
                    or row.get("artifact_kind") != FAILURE_KIND
                    or not isinstance(payload, dict)
                    or payload.get("record_type") != FAILURE_RECORD_VERSION):
                continue
            if tenant_id is not None and payload.get("tenant_id") != tenant_id:
                continue
            kept.append(row)
        return kept

    def build(self, reference, *, route, method, refusal_code, status, tenant_id, sequence,
              request_body=None):
        """Build one failure record, refusing anything outside the declared shape.

        The reference must be one this process issued. The route must be a
        declared route or the unmatched name. A request body is kept only when
        the host configuration chose to capture request bodies; otherwise the
        argument is refused, so a future caller cannot quietly start storing
        one against the host's choice.
        """
        if not isinstance(reference, RequestReference) or reference._issuer is not _REFERENCE_ISSUER:
            raise ServiceRuntimeError("unissued_request_reference")
        if route not in self.declared_routes and route != UNMATCHED_ROUTE:
            raise ServiceRuntimeError("undeclared_failure_route")
        if method not in RECORDED_METHODS:
            raise ServiceRuntimeError("unsupported_failure_method")
        identifier(refusal_code, "refusal code")
        if type(status) is not int or not 100 <= status <= 599:
            raise ServiceRuntimeError("invalid_failure_status")
        if tenant_id:
            identifier(tenant_id, "tenant identity")
        elif tenant_id != "":
            raise ServiceRuntimeError("invalid_request", "an unauthenticated failure records empty tenant text")
        if type(sequence) is not int or sequence < 1:
            raise ServiceRuntimeError("invalid_failure_sequence")
        payload = {"record_type": FAILURE_RECORD_VERSION, "request_reference": reference.value,
                   "route": route, "method": method, "refusal_code": refusal_code, "status": status,
                   "tenant_id": tenant_id, "at": int(self.clock()), "sequence": sequence,
                   "service_version": service_version(),
                   "release_reference": self.policy.release_reference,
                   "payload_capture": self.policy.payload_capture}
        if request_body is not None:
            if not self.policy.captures_request_body:
                raise ServiceRuntimeError("payload_capture_not_authorized")
            payload["request_body"] = _excerpt(request_body)
        return payload

    def record(self, reference, *, route, method, refusal_code, status, tenant_id, request_body=None):
        """Record one refused request. A recording failure never raises.

        The customer is already being refused. A journal that could turn a
        refusal into a different failure would make the service worse, so every
        failure of this write is caught and reported as a typed outcome.
        """
        if not self.policy.record_failures:
            return {"recorded": False, "reason": "recording_disabled"}
        try:
            sequence = self._sequence()
            payload = self.build(reference, route=route, method=method, refusal_code=refusal_code,
                                 status=status, tenant_id=tenant_id, sequence=sequence,
                                 request_body=request_body)
            slot = str(sequence % self.policy.retained_failures)
            with self._binding.store(write=True) as store:
                held = self._binding.read(store, FAILURE_KIND, slot)
                row = self._binding.record(FAILURE_KIND, slot, payload, tenant_id=tenant_id)
                self._binding.commit(store, (row,), (self._binding.guard(held, row["record_id"]),))
            return {"recorded": True, "sequence": sequence}
        except Exception as error:
            return {"recorded": False, "reason": getattr(error, "code", "failure_not_recorded")}

    def recent(self, *, limit=20, tenant_id=None):
        """Return the newest failure records, newest first. This never writes."""
        # The retained count bounds what is stored, not what may be asked for.
        # A request for more than exists returns what exists.
        if type(limit) is not int or not 1 <= limit <= MAXIMUM_FAILURE_LISTING:
            raise ServiceRuntimeError("invalid_failure_limit")
        if tenant_id is not None:
            identifier(tenant_id, "tenant identity")
        with self._binding.store() as store:
            rows = self._stored_rows(store, tenant_id=tenant_id)
        records = sorted((row["payload"] for row in rows), key=lambda value: value.get("sequence", 0), reverse=True)
        return {"record_type": FAILURE_LIST_VERSION, "failures": records[:limit],
                "returned": min(limit, len(records)), "stored": len(records),
                "retained_failures": self.policy.retained_failures,
                "tenant_id": tenant_id, "request_reference": None}

    def detail(self, request_reference):
        """Return the one record of a reference, or an empty list. This never writes."""
        if not valid_reference(request_reference):
            raise ServiceRuntimeError("invalid_request_reference")
        with self._binding.store() as store:
            rows = self._stored_rows(store)
        found = [row["payload"] for row in rows
                 if row["payload"].get("request_reference") == request_reference]
        return {"record_type": FAILURE_LIST_VERSION, "failures": found, "returned": len(found),
                "stored": len(rows), "retained_failures": self.policy.retained_failures,
                "tenant_id": None, "request_reference": request_reference}


def _excerpt(value, *, maximum_bytes=2048):
    """Return a bounded text excerpt of a captured request body."""
    if isinstance(value, str):
        value = value.encode("utf-8", "replace")
    if not isinstance(value, (bytes, bytearray)):
        raise ServiceRuntimeError("invalid_request", "a captured request body is bytes or text")
    kept = bytes(value[:maximum_bytes])
    return {"truncated": len(value) > maximum_bytes, "bytes": len(value),
            "text": kept.decode("utf-8", "replace")}


@dataclass(frozen=True)
class ReadinessCheck:
    """One named dependency answer. A required check that fails means not ready."""

    name: str
    required: bool
    passed: bool
    code: str = ""

    def to_dict(self):
        return {"name": self.name, "required": self.required, "passed": self.passed, "code": self.code}


def store_readiness(config):
    """Ask the durable store to answer now. This reads; it never writes."""
    try:
        binding = ServiceCatalogBinding(config)
        with binding.store() as store:
            store.get(binding.identity("service_readiness_probe", "absent"))
        return ReadinessCheck("durable_store_answers", True, True)
    except ServiceRuntimeError as error:
        return ReadinessCheck("durable_store_answers", True, False, error.code)
    except Exception:
        return ReadinessCheck("durable_store_answers", True, False, "store_unavailable")


def volume_readiness(config, policy):
    """Measure the free space left on the volume the durable store sits on.

    This is the failure the store check cannot see. When the volume fills, a
    read still answers and only writes fail, so a service that only reads on
    its health route would report itself perfectly healthy while every usage
    record, account record and failure record was being lost. Free space is
    read with one system call and nothing is written, so asking the question
    does not itself consume the space it is measuring.
    """
    import shutil
    try:
        from pathlib import Path
        # `shutil.disk_usage` answers on every platform this can run on, and
        # reports the space available to this process rather than the space a
        # privileged user could still reach.
        free = shutil.disk_usage(Path(config.database_path).parent).free
    except Exception:
        return ReadinessCheck("volume_has_write_headroom", True, False, "volume_unavailable")
    return ReadinessCheck("volume_has_write_headroom", True, free >= policy.minimum_free_bytes,
                          "" if free >= policy.minimum_free_bytes else "volume_nearly_full")


def catalogue_readiness(provisioning):
    """Report how much the service has to serve, without removing the machine.

    An empty catalogue is reported and does not make the service unready. It is
    a configuration state, not a dependency that failed: the service still
    authenticates, still answers its capabilities and still returns an accurate
    empty list. Treating it as required would turn a correct empty answer into
    a total outage, and it would take a freshly deployed machine out of service
    before its catalogue had been loaded.
    """
    try:
        count = len(provisioning.catalogue.items)
    except Exception:
        return ReadinessCheck("catalogue_registered", False, False, "catalogue_unavailable")
    return ReadinessCheck("catalogue_registered", False, count > 0,
                          "" if count > 0 else "catalogue_empty")


def catalogue_view_readiness(provisioning):
    """Report the catalogue view being served and its last refresh. Not required; it only reads.

    A failed refresh keeps the previous view serving, so it is reported and it
    does not take the machine out of service. The summary names the source,
    the release identity, the item count and the catalogue state revision.
    """
    try:
        view = provisioning.current_view()
        summary = view.summary()
    except Exception:
        return ReadinessCheck("catalogue_view_current", False, False, "catalogue_view_unavailable"), None
    refresher = getattr(provisioning, "catalogue_refresher", None)
    status = refresher.status() if refresher is not None else None
    failure = (status or {}).get("last_failure_code") or ""
    return ReadinessCheck("catalogue_view_current", False, not failure, failure), {**summary, "refresher": status}


def web_asset_readiness():
    """Report whether the packaged interface page can be read. Not required.

    A missing page stops a person signing in through a browser and stops
    nothing else: every API route the customer harnesses use still answers
    correctly. The service runs on one machine, so reporting not ready here
    would take the working API down as well, and restarting cannot put a file
    back into an image. An operator sees it and rolls the release back.
    """
    try:
        from importlib.resources import files
        body = files("loop_engine").joinpath("core", "service_runtime", "web_assets", "index.html").read_bytes()
    except Exception:
        return ReadinessCheck("interface_page_readable", False, False, "web_asset_unavailable")
    return ReadinessCheck("interface_page_readable", False, bool(body),
                          "" if body else "web_asset_empty")


#: The check that compares the stored billing policies with the running
#: configuration. `billing_sessions_installed` says an adapter exists; only
#: this check says whether the policy it enforces is the one stored.
BILLING_POLICY_CHECK = "billing_policy_current"


def billing_policy_readiness(measure):
    """Report whether the stored billing policies serve the running configuration. Not required.

    `measure` returns empty text when they do, or the code that names why not,
    such as `session_policy_changed`; it is None when the host installs no
    billing. The answer carries that code and never a digest.

    Release 13 kept serving with checkout and the portal unavailable, because
    the stored session policy held the digest an older release computed, and
    `billing_sessions_installed` still passed. This check fails in that state.

    It is not required, for three reasons. Every other route, including paid
    access for accounts that already have it, still answers correctly, so by
    the rule of `readiness_report` the machine must stay in service. Restarting
    cannot repair it; only the operator command `apply-billing-policy` can. And
    the release checks readiness right after the deploy and runs that command
    after the check, so a required check would stop every release before the
    step that repairs it. The release instead requires the capabilities record
    to report checkout as the host file offers it once the command has run.
    """
    if measure is None:
        return ReadinessCheck(BILLING_POLICY_CHECK, False, False, "billing_not_installed")
    try:
        code = measure()
    except ServiceRuntimeError as error:
        code = error.code
    except Exception:
        code = "billing_policy_unreadable"
    if not isinstance(code, str):
        code = "billing_policy_unreadable"
    return ReadinessCheck(BILLING_POLICY_CHECK, False, not code, code)


def readiness_report(*, config, provisioning, authentication_modes, policy,
                     browser_identity_installed, billing_sessions_installed, billing_webhook_installed,
                     billing_policy=None, retention=None):
    """Measure every dependency now and separate alive from ready.

    Alive is what the process can say about itself: this code is running and
    answering. Ready is measured. A required check that fails makes the whole
    answer not ready, and the route answers 503 so that a load balancer stops
    sending customers to a machine that cannot serve them.

    A check is required when the machine cannot give any correct answer without
    it, so that taking it out of service or restarting it is the right response.
    Three qualify: the durable store must answer, the volume must still have
    room to write, and some way to authenticate a customer must be installed.

    Everything else is reported and not required. The catalogue, the interface
    page, the identity, payment and browser adapters and the retention task
    each change what the service can offer, but a machine missing one of them
    still answers its other routes correctly. `retention` is the retention
    task's own reported check, read from memory; measuring health never runs
    a removal. Reporting not ready for those would take a working
    service down and could not repair any of them, so an operator reads them in
    the health record and decides. That difference is the whole point of
    separating alive from ready.
    """
    checks = [store_readiness(config), volume_readiness(config, policy),
              ReadinessCheck("authentication_mode_installed", True, bool(authentication_modes),
                             "" if authentication_modes else "no_authentication_mode"),
              catalogue_readiness(provisioning), web_asset_readiness(),
              ReadinessCheck("browser_identity_installed", False, bool(browser_identity_installed)),
              ReadinessCheck("billing_sessions_installed", False, bool(billing_sessions_installed)),
              ReadinessCheck("billing_webhook_installed", False, bool(billing_webhook_installed)),
              billing_policy_readiness(billing_policy)]
    if retention is not None:
        if not isinstance(retention, ReadinessCheck) or retention.required:
            raise ServiceRuntimeError("invalid_readiness_check")
        checks.append(retention)
    view_check, catalogue_release = catalogue_view_readiness(provisioning)
    checks.append(view_check)
    return health_record(checks, policy, catalogue_release=catalogue_release)


def health_record(checks, policy, *, catalogue_release=None):
    """Build the one health answer from a list of checks.

    Ready is true only when every required check passed. The measured answer
    and the answer given when measuring ran out of time are both built here,
    so the deployment gate and an operator never meet two shapes of it.
    """
    ready = all(check.passed for check in checks if check.required)
    return {"record_type": HEALTH_RECORD_VERSION, "alive": True, "ready": ready,
            "readiness_checked": True, "checks": [check.to_dict() for check in checks],
            "service_version": service_version(),
            "release_reference": policy.release_reference,
            "failure_records_enabled": policy.record_failures,
            "payload_capture": policy.payload_capture,
            "deployed_provider_qualification": False,
            # The served catalogue view, or None when it was not measured. The
            # key is always present, so every health answer has one shape.
            "catalogue_release": catalogue_release}


def readiness_deadline_report(policy):
    """Return the health answer for a measurement that did not finish in time.

    A dependency that does not answer inside the request deadline is a
    dependency that failed. The process is still answering, so it is alive,
    and it is not ready, with the one failed check that names why.
    """
    return health_record([ReadinessCheck("readiness_within_deadline", True, False,
                                         "readiness_deadline_exceeded")], policy)
