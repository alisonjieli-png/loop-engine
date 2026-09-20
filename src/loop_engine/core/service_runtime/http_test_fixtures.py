"""Local fixtures for real HTTP and protocol acceptance.

Servers bind only loopback, service state uses temporary SQLite files, and
fixtures make no provider or external-network calls. They do not establish
live identity-provider, payment-provider, or hosting qualification.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
import json
from pathlib import Path
import socket
import threading
import time

from ..harness_intelligence import HarnessIntelligenceCatalogue, HarnessIntelligenceDraft, item_from_body
from ..provisioning_server import (
    ProvisioningGrant, ProvisioningItemBinding, ProvisioningQualification, ProvisioningQualificationResolver,
)
from .http import ServiceHttpApplication, ServiceHttpConfiguration
from .http_auth import ServiceHttpAuthentication
from .provisioning import DurableProvisioningBinding
from .records import ServiceRuntimeConfig, TenantRegistration, TenantKeyIssue
from .runtime import ServiceRuntime


@dataclass
class HttpDomainFixture:
    root: Path
    bodies: dict = field(default_factory=lambda: {
        "skill.alpha": "APPROVED_ALPHA_BODY", "skill.beta": "PRIVATE_BETA_BODY",
        "skill.candidate": "UNAPPROVED_CANDIDATE_BODY", "skill.large": "LARGE_BODY_" * 2048})
    reads: list = field(default_factory=list)
    before_read: object | None = None
    operator_access: bool = True

    def __post_init__(self):
        self.runtime = ServiceRuntime(ServiceRuntimeConfig(str(self.root / "service.db"), writes_authorized=True))
        self.keys = {}
        for tenant in ("alpha", "beta"):
            self.runtime.register_tenant(TenantRegistration(tenant, "tenant:" + tenant))
            self.keys[tenant] = self.runtime.issue_key(TenantKeyIssue(tenant, "local HTTP acceptance"))
            if self.operator_access:
                self.runtime.set_operator_entitlement(tenant, valid_until=int(time.time()) + 3600,
                                                     evidence_ref="local-acceptance-not-payment")
        self.catalogue = HarnessIntelligenceCatalogue()
        for identity, body in self.bodies.items():
            self.catalogue.register(item_from_body(HarnessIntelligenceDraft(
                identity, "skill", "Alpha reference " + identity, "context_intelligence",
                "fixture:" + identity + "/v1", "MIT"), body))
        self.bindings = {identity: ProvisioningItemBinding.from_item(item)
                         for identity, item in self.catalogue.items.items()}
        for tenant in ("alpha", "beta"):
            identities = ("skill.alpha", "skill.large", "skill.candidate") if tenant == "alpha" else ("skill.beta",)
            self.runtime.set_grants(tenant, tuple(ProvisioningGrant(tenant, self.bindings[identity], True)
                                                 for identity in identities))
        def qualify(binding):
            if binding.identity == "skill.candidate" or self.bindings.get(binding.identity) != binding:
                return ProvisioningQualification(binding, "unknown", "host_attested")
            return ProvisioningQualification(binding, "approved", "host_attested", "fixture-review:exact")
        def read(item):
            self.reads.append(item.identity)
            if self.before_read is not None:
                self.before_read(item)
            return self.bodies[item.identity]
        self.provisioning = DurableProvisioningBinding(self.runtime, self.catalogue,
            ProvisioningQualificationResolver("fixture-reviewed-sources", qualify), read)

    def headers(self, tenant="alpha"):
        return {"Authorization": "Bearer " + self.keys[tenant].key}

    def usage(self, tenant="alpha"):
        return self.runtime.usage_for(self.runtime.authenticate_key(self.keys[tenant].key))


@contextmanager
def running_http(fixture, *, authentication=None, application_factory=None, billing_processor=None, **changes):
    import uvicorn
    bound = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    bound.bind(("127.0.0.1", 0))
    port = bound.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    configuration = ServiceHttpConfiguration(base, (f"127.0.0.1:{port}",),
        allowed_origins=("http://127.0.0.1:5173",), allow_loopback_http=True, **changes)
    service = (application_factory(configuration) if application_factory is not None else
               ServiceHttpApplication(fixture.runtime, fixture.provisioning, configuration,
                   authentication(configuration) if callable(authentication) else
                   authentication or ServiceHttpAuthentication(), billing_processor=billing_processor))
    server = uvicorn.Server(uvicorn.Config(service.create_app(), log_level="error", access_log=False,
                                          proxy_headers=False, timeout_graceful_shutdown=2))
    worker = threading.Thread(target=lambda: server.run(sockets=[bound]), daemon=True)
    worker.start()
    deadline = time.monotonic() + 5
    while not server.started and worker.is_alive() and time.monotonic() < deadline:
        time.sleep(0.005)
    if not server.started:
        server.should_exit = True
        bound.close()
        raise RuntimeError("local HTTP fixture did not start")
    try:
        yield base, service
    finally:
        server.should_exit = True
        worker.join(5)
        bound.close()
        if worker.is_alive():
            raise RuntimeError("local HTTP fixture did not stop")


@contextmanager
def running_key_set():
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    state = {"keys": [], "requests": 0, "paths": [], "status": 200, "padding": ""}
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            state["requests"] += 1
            state["paths"].append(self.path)
            body = json.dumps({"keys": state["keys"], "padding": state["padding"]}).encode()
            self.send_response(state["status"])
            if state.get("location"):
                self.send_header("Location", state["location"])
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        def log_message(self, *_args):
            pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", state
    finally:
        server.shutdown()
        server.server_close()
        worker.join(3)
