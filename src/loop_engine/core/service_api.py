"""The hosted service surface: tenants, keys as digests, typed endpoints, metering.

Architectural role: a serving adapter, like the Studio server, over the
same boundaries a local run uses. It owns the HTTP surface (standard
library only, no new dependency), tenant records whose keys are stored as
digests and never as text, the metering ledger that counts the units the
packaging guide names (verified completions, avoided model calls, optimize
hours, judgment depth) with digests and never bodies, and three typed
endpoints: health, text conformance, and evaluation. It does not own model
routing, authority, or storage; the work inside each endpoint runs through
the existing modules, and a request without a valid key is refused before
any of them is touched.

Public entry points: ``serve(ServiceRequest)`` blocks; ``ServiceApplication``
handles requests without a socket so the checks run in process;
``new_tenant`` mints a key once and keeps only its digest.
"""
from __future__ import annotations

import hashlib
import json
import secrets
import threading
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

METERING_UNITS = ("verified_completion", "avoided_model_call", "optimize_hour", "judgment_depth")
ENDPOINTS = ("health", "conform", "evaluate", "usage", "memory_write", "memory_read")
KEY_HEADER = "X-Loop-Engine-Key"
TENANT_RECORD_TYPE = "service_tenant/v1"
METERING_RECORD_TYPE = "metering_record/v1"
MAX_BODY_BYTES = 8 * 1024 * 1024


class ServiceError(ValueError):
    """A tenant, request, or endpoint is invalid."""


def key_digest(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class TenantRecord:
    """One tenant: its identity, namespace, allowed endpoints, and the digest of its key."""

    tenant_id: str
    key_digest: str
    namespace: str
    endpoints: tuple[str, ...] = ENDPOINTS

    def __post_init__(self):
        if not self.tenant_id or not self.namespace:
            raise ServiceError("a tenant needs an identifier and a namespace")
        if len(self.key_digest) != 64 or any(ch not in "0123456789abcdef" for ch in self.key_digest):
            raise ServiceError("key_digest is the SHA-256 hex digest of the key, never the key")
        endpoints = tuple(self.endpoints)
        if any(item not in ENDPOINTS for item in endpoints):
            raise ServiceError(f"endpoints must be drawn from {ENDPOINTS}")
        object.__setattr__(self, "endpoints", endpoints)

    def to_dict(self) -> dict:
        return {"record_type": TENANT_RECORD_TYPE, "tenant_id": self.tenant_id, "key_digest": self.key_digest,
                "namespace": self.namespace, "endpoints": list(self.endpoints)}

    @classmethod
    def from_dict(cls, value: dict) -> "TenantRecord":
        if value.get("record_type") != TENANT_RECORD_TYPE:
            raise ServiceError("not a service tenant record")
        endpoints = value.get("endpoints", ENDPOINTS)
        if not isinstance(endpoints, (list, tuple)):
            raise ServiceError("endpoints must be a list or tuple, including an explicit empty set")
        return cls(str(value["tenant_id"]), str(value["key_digest"]), str(value["namespace"]),
                   tuple(endpoints))


def new_tenant(tenant_id: str, namespace: str, endpoints: tuple[str, ...] = ENDPOINTS) -> tuple[TenantRecord, str]:
    """Mint one key; return the record (digest only) and the key text for the caller to hand over once."""
    key = "le_" + secrets.token_urlsafe(32)
    return TenantRecord(tenant_id, key_digest(key), namespace, endpoints), key


@dataclass(frozen=True)
class MeteringRecord:
    tenant_id: str
    unit: str
    quantity: float
    record_ref: str
    at: float

    def __post_init__(self):
        if self.unit not in METERING_UNITS:
            raise ServiceError(f"unit must be one of {METERING_UNITS}")
        if self.quantity < 0:
            raise ServiceError("quantity cannot be negative")

    def to_dict(self) -> dict:
        return {"record_type": METERING_RECORD_TYPE, "tenant_id": self.tenant_id, "unit": self.unit,
                "quantity": self.quantity, "record_ref": self.record_ref, "at": self.at}


class MeteringLedger:
    """Append-only metering; totals per tenant and unit."""

    def __init__(self):
        self._records: list[MeteringRecord] = []
        self._lock = threading.Lock()

    def add(self, record: MeteringRecord) -> None:
        with self._lock:
            self._records.append(record)

    def usage(self, tenant_id: str) -> dict:
        with self._lock:
            totals = {unit: 0.0 for unit in METERING_UNITS}
            count = 0
            for item in self._records:
                if item.tenant_id == tenant_id:
                    totals[item.unit] += item.quantity
                    count += 1
        return {"record_type": "tenant_usage/v1", "tenant_id": tenant_id, "records": count,
                "totals": {unit: round(value, 6) for unit, value in totals.items()}}

    @property
    def records(self) -> tuple[MeteringRecord, ...]:
        with self._lock:
            return tuple(self._records)


@dataclass
class ServiceApplication:
    """Request handling without a socket: authenticate, dispatch, meter.

    ``handlers`` maps a POST endpoint to a callable taking the tenant, the
    parsed payload, the ledger, and the clock; the code intelligence
    package supplies the real ones, so core never imports it.
    """

    tenants: tuple[TenantRecord, ...]
    handlers: dict = field(default_factory=dict)
    ledger: MeteringLedger = field(default_factory=MeteringLedger)
    clock: object = time.time

    def __post_init__(self):
        digests = [item.key_digest for item in self.tenants]
        if len(set(digests)) != len(digests):
            raise ServiceError("two tenants cannot share one key digest")
        if any(name not in ENDPOINTS or not callable(fn) for name, fn in self.handlers.items()):
            raise ServiceError(f"handlers are callables keyed by one of {ENDPOINTS}")

    def authenticate(self, key: str | None) -> "TenantRecord | None":
        if not key:
            return None
        digest = key_digest(key)
        for tenant in self.tenants:
            if secrets.compare_digest(tenant.key_digest, digest):
                return tenant
        return None

    def handle(self, method: str, path: str, key: str | None, body: bytes) -> tuple[int, dict]:
        """One request in, one status and JSON body out; nothing runs before the key is checked."""
        endpoint = path.strip("/").split("/")[-1] if path.strip("/") else ""
        if endpoint not in ENDPOINTS:
            return 404, {"error": "unknown endpoint", "endpoints": list(ENDPOINTS)}
        tenant = self.authenticate(key)
        if tenant is None:
            return 401, {"error": "a valid tenant key is required", "header": KEY_HEADER}
        if endpoint not in tenant.endpoints:
            return 403, {"error": f"tenant {tenant.tenant_id} may not use {endpoint}"}
        if endpoint == "health":
            return 200, {"record_type": "service_health/v1", "healthy": True, "tenant_id": tenant.tenant_id}
        if endpoint == "usage":
            return 200, self.ledger.usage(tenant.tenant_id)
        if method != "POST":
            return 405, {"error": f"{endpoint} takes POST"}
        if len(body) > MAX_BODY_BYTES:
            return 413, {"error": "request body too large"}
        try:
            payload = json.loads(body.decode("utf-8") or "{}")
        except (UnicodeDecodeError, ValueError):
            return 400, {"error": "the request body must be JSON"}
        if not isinstance(payload, dict):
            return 400, {"error": "the request body must be one JSON object"}
        handler = self.handlers.get(endpoint)
        if handler is None:
            return 501, {"error": f"{endpoint} has no handler in this deployment"}
        try:
            return 200, handler(tenant, payload, self.ledger, self.clock)
        except ValueError as exc:
            return 422, {"error": str(exc)[:500]}


@dataclass(frozen=True)
class ServiceRequest:
    """How to serve: bind address, port, and the tenants."""

    tenants: tuple[TenantRecord, ...]
    bind: str = "127.0.0.1"
    port: int = 0
    handlers: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.tenants:
            raise ServiceError("serving needs at least one tenant")
        if type(self.port) is not int or not 0 <= self.port <= 65535:
            raise ServiceError("port lies in [0, 65535]")


def _handler(application: ServiceApplication):
    class Handler(BaseHTTPRequestHandler):
        server_version = "LoopEngineService/1.0"

        def _respond(self, method: str) -> None:
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if 0 < length <= MAX_BODY_BYTES else b""
            if length > MAX_BODY_BYTES:
                status, payload = 413, {"error": "request body too large"}
            else:
                status, payload = application.handle(method, self.path, self.headers.get(KEY_HEADER), body)
            data = json.dumps(payload, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            self._respond("GET")

        def do_POST(self):
            self._respond("POST")

        def log_message(self, format, *args):
            return None

    return Handler


def serve(request: ServiceRequest, ready=None) -> None:
    """Serve until interrupted; ``ready(port)`` is called once the socket listens."""
    application = ServiceApplication(request.tenants, handlers=dict(request.handlers))
    httpd = ThreadingHTTPServer((request.bind, request.port), _handler(application))
    if ready is not None:
        ready(httpd.server_address[1])
    try:
        httpd.serve_forever()
    finally:
        httpd.server_close()


def load_tenants(path: str) -> tuple[TenantRecord, ...]:
    """Tenant records from a JSON file; the file holds digests, never keys."""
    data = json.loads(open(path, "r", encoding="utf-8").read())
    if not isinstance(data, list):
        raise ServiceError("the tenants file holds a list of tenant records")
    return tuple(TenantRecord.from_dict(item) for item in data)


def self_test() -> dict:
    """Keys are checked first, bodies never enter the ledger, endpoints answer in process and over a socket."""
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    def refuses(action) -> bool:
        try:
            action()
        except ServiceError:
            return True
        return False

    tenant, key = new_tenant("acme", "tenant:acme")
    limited, limited_key = new_tenant("guest", "tenant:guest", ("health",))
    check("a_new_tenant_keeps_only_the_key_digest",
          tenant.key_digest == key_digest(key) and key not in json.dumps(tenant.to_dict())
          and TenantRecord.from_dict(tenant.to_dict()) == tenant
          and refuses(lambda: TenantRecord("t", "short", "ns"))
          and refuses(lambda: TenantRecord("t", "0" * 64, "ns", ("oracle",))))
    denied = TenantRecord("denied", key_digest("denied-fixture-key"), "tenant:denied", ())
    restored = TenantRecord.from_dict(denied.to_dict())
    denied_application = ServiceApplication((restored,))
    omitted = tenant.to_dict()
    omitted.pop("endpoints")
    check("tenant_roundtrip_preserves_empty_endpoint_permissions_without_defaulting_them",
          restored.endpoints == ()
          and all(denied_application.handle("POST", "/v1/" + endpoint,
                                           "denied-fixture-key", b"{}")[0] == 403
                  for endpoint in ENDPOINTS)
          and TenantRecord.from_dict(omitted).endpoints == ENDPOINTS)
    check("serialized_endpoint_permissions_refuse_null_strings_and_unknown_values",
          all(refuses(lambda value=value: TenantRecord.from_dict(
              {**tenant.to_dict(), "endpoints": value}))
              for value in (None, "health", {}, ["unknown"])))
    ticks = iter(range(100))

    def echo_conform(tenant, payload, ledger, clock):
        rows = payload.get("rows")
        if not isinstance(rows, list):
            raise ServiceError("rows must be a list")
        ledger.add(MeteringRecord(tenant.tenant_id, METERING_UNITS[1], float(len(rows)), "fixture", clock()))
        return {"record_type": "fixture_conform/v1", "rows": len(rows), "metered": {"avoided_model_call": len(rows)}}

    application = ServiceApplication((tenant, limited), handlers={"conform": echo_conform},
                                     clock=lambda: 1000.0 + next(ticks))
    status, body = application.handle("GET", "/health", None, b"")
    wrong = application.handle("GET", "/health", "le_wrong", b"")
    unknown = application.handle("GET", "/nowhere", key, b"")
    forbidden = application.handle("POST", "/v1/conform", limited_key, b"{}")
    check("requests_without_a_valid_key_are_refused_before_any_work",
          status == 401 and wrong[0] == 401 and unknown[0] == 404 and forbidden[0] == 403
          and application.handle("GET", "/health", key, b"")[0] == 200
          and application.handle("GET", "/v1/conform", key, b"")[0] == 405
          and application.handle("POST", "/v1/conform", key, b"not json")[0] == 400
          and application.handle("POST", "/v1/evaluate", key, b"{}")[0] == 501)
    status, body = application.handle("POST", "/v1/conform", key, json.dumps({"rows": [1, 2]}).encode("utf-8"))
    usage = application.ledger.usage("acme")
    check("a_handler_runs_only_after_authentication_and_its_metering_lands_on_the_tenant",
          status == 200 and body["rows"] == 2 and usage["totals"]["avoided_model_call"] == 2.0
          and application.handle("GET", "/v1/usage", key, b"")[1]["totals"]["avoided_model_call"] == 2.0
          and application.handle("GET", "/v1/usage", limited_key, b"")[0] == 403
          and application.handle("POST", "/v1/conform", key, json.dumps({"rows": "x"}).encode("utf-8"))[0] == 422
          and all("fixture" == item.record_ref for item in application.ledger.records))
    listening = {}
    thread = threading.Thread(target=serve, args=(ServiceRequest((tenant,), port=0),),
                              kwargs={"ready": lambda port: listening.update(port=port) or ready_event.set()},
                              daemon=True)
    ready_event = threading.Event()
    thread.start()
    ready_event.wait(10)
    import http.client
    connection = http.client.HTTPConnection("127.0.0.1", listening.get("port", 0), timeout=10)
    connection.request("GET", "/health")
    unauthorized = connection.getresponse()
    unauthorized.read()
    connection.request("GET", "/health", headers={KEY_HEADER: key})
    authorized = connection.getresponse()
    answer = json.loads(authorized.read().decode("utf-8"))
    connection.close()
    check("the_socket_surface_answers_with_the_same_rules",
          unauthorized.status == 401 and authorized.status == 200 and answer["healthy"] is True)
    check("service_requests_and_metering_records_are_validated",
          refuses(lambda: ServiceRequest(()))
          and refuses(lambda: ServiceRequest((tenant,), port=70000))
          and refuses(lambda: MeteringRecord("t", "outcomes", 1, "r", 0))
          and refuses(lambda: MeteringRecord("t", "judgment_depth", -1, "r", 0))
          and refuses(lambda: ServiceApplication((tenant, tenant)))
          and refuses(lambda: ServiceApplication((tenant,), handlers={"oracle": lambda *a: None})))
    passed = sum(item["passed"] for item in results)
    return {"record_type": "service_api_test/v1", "tests": results, "passed": passed,
            "total": len(results), "all_passed": passed == len(results)}
