"""Prove the paid path of the hosted service end to end in Stripe test mode, with the service's own code.

Kind: operator check. It runs the real service on a loopback socket, composed by the same host loader the
deployment uses, against the real Stripe test environment, and records what a customer meets at each step:

```text
Paid path in Stripe test mode
├── part checkout
│   ├── sign up with an email address, confirm the link, choose a password, open the account
│   ├── the new account searches for free and is refused a download, over HTTP and over MCP, with the plan offer
│   ├── the plans record offers checkout; the service creates the account's one Stripe customer and a session
│   ├── a real browser pays on the Stripe-hosted page with a Stripe test card
│   ├── `stripe listen` forwards the signed events; the service reads the subscription and grants downloads
│   ├── the account downloads over HTTP and over MCP, and the download is recorded as usage
│   ├── the customer portal shows the paid invoice; the person cancels there, at the end of the paid month
│   ├── access continues until then, as the terms of service say
│   └── the operator refunds the payment and ends the subscription now; access ends with the deletion event
└── part renewal (a Stripe test clock moves the subscription's time; the service keeps its own clock)
    ├── a second account pays at checkout for a customer that lives on a test clock
    ├── the clock passes the end of the paid month: the renewal invoice waits as a draft for about an hour
    ├── access continues through that hour, and the paid renewal extends it to the next month
    ├── the payment method is replaced with a Stripe test card that is declined on renewal
    └── the next renewal fails, the subscription is past due, and access ends
```

What it needs, and what it refuses:

- A Stripe test key in `STRIPE_API_KEY`, for the account the `stripe-test` reference in
  `tools/operator_credentials.json` names. Run it through `tools/operator_credentials.py run --ref stripe-test`,
  so the key never reaches an argument, a file or the terminal. Any other key is refused before a request.
- The product, the monthly price and the portal configuration that `tools/setup_stripe_sandbox.py` creates, found
  by the price lookup key and the portal configuration's marker. The check creates none of them.
- The Stripe command line, for `stripe listen`, which forwards events to the loopback service and signs them with
  the session's own signing secret. That secret goes into this process's environment only, as the service's
  `STRIPE_WEBHOOK_SECRET`, and every line the listener prints is stored with any secret removed.
- Node and the Playwright browser the website checks use, through `tools/stripe_test_checkout.mjs`. A hosted page
  address carries a session secret, so it is handed to the browser on standard input and never stored.

Each part fits in the five minutes `tools/operator_credentials.py run` allows. Run them one at a time:

```bash
/usr/bin/python3 tools/operator_credentials.py run --ref stripe-test --timeout 300 -- \
  .venv/bin/python tools/check_stripe_test_journey.py --part checkout --report /new/path/journey-checkout.json
/usr/bin/python3 tools/operator_credentials.py run --ref stripe-test --timeout 300 -- \
  .venv/bin/python tools/check_stripe_test_journey.py --part renewal --report /new/path/journey-renewal.json
```

The identity provider is the stand-in project the website checks serve on loopback, because production sign-up
cannot be exercised without creating real accounts. Every other boundary is the real one: the host loader, the
billing adapters, the HTTP routes, the protocol endpoint, Stripe's test API, Stripe-hosted Checkout and the
customer portal. The check makes no model call and touches no live account. It removes the Stripe test customers
and the test clock it created unless `--keep-stripe-objects` is given; their identities stay in the report.

Exit codes: 0 every step passed, 1 a step failed (the report names it), 2 refused before any request.
"""
from __future__ import annotations

import argparse
import asyncio
from contextlib import ExitStack, contextmanager
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
for entry in (ROOT / "src", ROOT / "tools"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

import setup_stripe_sandbox as sandbox  # noqa: E402  (the owner of the sandbox plan and the key rules)
from loop_engine.core.service_runtime.stripe_sessions import CHECKOUT_HOST, PORTAL_HOST  # noqa: E402

REPORT_RECORD_TYPE = "stripe_test_journey_report/v1"
PARTS = ("checkout", "renewal", "failed_renewal")
PAGE_HELPER = ROOT / "tools" / "stripe_test_checkout.mjs"
PLAYWRIGHT_MODULE = ROOT / "showcase" / "node_modules" / "playwright-core" / "index.mjs"
STARTER_MANIFEST = ROOT / "examples" / "29_intelligence_service" / "starter-catalogue" / "host-release" / "manifest.json"
#: Stripe's published test cards (https://docs.stripe.com/testing). The first pays. The second, "Always authenticate",
#: needs the cardholder on every charge: the Checkout page authenticates the first payment, and the renewal Stripe
#: charges with nobody present fails, which is how a failed renewal is produced.
PAYING_CARD, AUTHENTICATION_EVERY_TIME_CARD = "4242424242424242", "4000002760003184"
#: The listener prints the session's signing secret on its first line; it is removed from every stored line.
_SIGNING_SECRET = re.compile(r"whsec_[A-Za-z0-9+/=_-]+")
_LISTENER_VERSION = re.compile(r"Stripe API Version \[([0-9]{4}-[0-9]{2}-[0-9]{2}\.[a-z]+)\]")
_FORWARDED = re.compile(r"-->\s+([a-z_.]+)\s+\[(evt_[A-Za-z0-9]+)\]")
_ANSWERED = re.compile(r"<--\s+\[(\d{3})\]\s+POST\s+\S+\s+\[(evt_[A-Za-z0-9]+)\]")
SERVICE_SECRET_ENVIRONMENT = sandbox.SERVICE_WEBHOOK_SECRET_ENVIRONMENT
PUBLISHABLE_KEY_ENVIRONMENT = "BALTOR_JOURNEY_IDENTITY_PUBLISHABLE_KEY"
#: How long a step waits for Stripe and the forwarded events before it is recorded as failed.
EVENT_WAIT_SECONDS, CLOCK_WAIT_SECONDS = 60, 90


class Refusal(Exception):
    """Refused before any request left the machine."""


def redact(line):
    """A listener line with any signing secret removed."""
    return _SIGNING_SECRET.sub("whsec_[removed]", line)


def require_test_key(environment, manifest):
    """The test key of the account the stripe-test reference names, or a refusal before any request."""
    try:
        binding = sandbox.credential_binding(sandbox.DEFAULT_CREDENTIAL_REFERENCE, manifest)
        key = sandbox.resolve_credential(binding, environment)
    except sandbox.Refusal as refusal:
        raise Refusal(str(refusal)) from None
    return binding, key


def reserve_report(path):
    target = Path(path)
    if target.exists() or target.is_symlink():
        raise Refusal("report_path_exists")
    if not target.parent.is_dir():
        raise Refusal("report_folder_missing")
    return target


class StripeTestApi:
    """The few test-mode calls the check itself makes: lookups, the operator's refund and cancellation, test clocks."""

    def __init__(self, key, account_id, api_version):
        import httpx
        self.account_id = account_id
        self._client = httpx.Client(base_url=sandbox.STRIPE_ORIGIN, auth=(key, ""), timeout=30,
                                    follow_redirects=False, trust_env=False,
                                    headers={"Stripe-Version": api_version})
        # What this run made at Stripe, removed at the end unless the operator keeps it.
        self.customers, self.test_clocks = [], []

    def call(self, method, path, data=None, params=None):
        response = self._client.request(method, path, data=data, params=params,
                                        headers={"Idempotency-Key": "baltor-journey-" + uuid.uuid4().hex}
                                        if method == "POST" else None)
        value = response.json()
        if response.status_code >= 400:
            error = value.get("error", {}) if isinstance(value, dict) else {}
            raise RuntimeError("stripe_test_api_refused:" + method + " " + path.split("?")[0] + ":"
                               + str(error.get("code") or error.get("type") or response.status_code) + ":"
                               + redact(str(error.get("message", "")))[:200])
        if isinstance(value, dict) and value.get("livemode") is True:
            raise RuntimeError("stripe_answered_with_a_live_object")
        return value

    def sandbox_objects(self):
        """The price and the portal configuration the setup command made, or a refusal naming what is missing."""
        account = self.call("GET", "/v1/account")
        if account.get("id") != self.account_id:
            raise Refusal("stripe_account_mismatch")
        plan = sandbox.SandboxPlan()
        prices = self.call("GET", "/v1/prices", params={"lookup_keys[0]": plan.price_lookup_key, "active": "true"})["data"]
        portals = [row for row in self.call("GET", "/v1/billing_portal/configurations",
                                            params={"active": "true", "limit": "100"})["data"]
                   if (row.get("metadata") or {}).get(plan.marker_key) == plan.marker_value]
        if len(prices) != 1 or len(portals) != 1:
            raise Refusal("sandbox_objects_missing_run_tools_setup_stripe_sandbox")
        return {"price_id": prices[0]["id"], "unit_amount": prices[0]["unit_amount"], "currency": prices[0]["currency"],
                "portal_configuration_id": portals[0]["id"], "plan_ref": plan.plan_ref, "plan_label": plan.product_name}

    def close(self):
        self._client.close()


class ListenerLog:
    """What `stripe listen` printed, kept without its signing secret: version, forwarded events, the service's answers."""

    def __init__(self):
        self.lines, self.forwarded, self.answered = [], {}, {}
        self.version, self.secret = None, None

    def consume(self, line):
        """Read one printed line. The first line that carries the signing secret also names the API version."""
        if self.secret is None:
            found = _SIGNING_SECRET.search(line)
            if found:
                self.secret = found.group(0)
                version = _LISTENER_VERSION.search(line)
                self.version = version.group(1) if version else None
        forwarded, answered = _FORWARDED.search(line), _ANSWERED.search(line)
        if forwarded:
            self.forwarded[forwarded.group(2)] = forwarded.group(1)
        if answered:
            self.answered.setdefault(answered.group(2), []).append(int(answered.group(1)))
        self.lines.append(redact(line)[:300])

    def deliveries(self):
        return [{"event_id": event, "type": self.forwarded.get(event, ""), "statuses": statuses}
                for event, statuses in self.answered.items()]

    def delivered(self, kind):
        """Event identities of one type that the service answered with a success."""
        return [event for event, statuses in self.answered.items()
                if self.forwarded.get(event) == kind and any(200 <= status < 300 for status in statuses)]


class Listener(ListenerLog):
    """`stripe listen`, forwarding the service's five event types to the loopback webhook address."""

    def __init__(self, executable, forward_to, events, environment):
        super().__init__()
        self._ready = threading.Event()
        self._process = subprocess.Popen(
            [executable, "listen", "--forward-to", forward_to, "--events", ",".join(events)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, text=True,
            env=environment)
        self._reader = threading.Thread(target=self._read, daemon=True)
        self._reader.start()

    def _read(self):
        for raw in self._process.stdout:
            self.consume(raw.rstrip("\n"))
            if self.secret is not None:
                self._ready.set()
        self._ready.set()

    def wait_ready(self, seconds=45):
        return self._ready.wait(seconds) and self.secret is not None

    def stop(self):
        if self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(10)
            except subprocess.TimeoutExpired:
                self._process.kill()


@contextmanager
def identity_project():
    """The stand-in identity project of the website checks, served on loopback, signing real RS256 sessions."""
    from cryptography.hazmat.primitives.asymmetric import rsa
    import jwt
    from loop_engine.core.service_runtime.account_email_checks import serving_identity_project
    from loop_engine.core.service_runtime.account_origin_checks import MarkingIdentityProjectStandIn
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    def session(project, user):
        now = int(time.time())
        return jwt.encode({"iss": project.issuer, "aud": "authenticated", "sub": user["id"], "exp": now + 1800,
                           "iat": now, "role": "authenticated", "is_anonymous": False, "email": user["email"],
                           "session_id": str(uuid.uuid4())}, key, algorithm="RS256", headers={"kid": "journey"})
    project = MarkingIdentityProjectStandIn(session_factory=session)
    public = {**json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key())), "kid": "journey", "alg": "RS256",
              "use": "sig"}
    with serving_identity_project(project, [public]) as origin:
        yield project, origin


def loopback_origin(bound):
    """The origin of the bound loopback socket, with the scheme the service's own address owner accepts for loopback.

    The container journey drill reads that scheme from `validate_public_url`; this check takes the same answer
    instead of stating one of its own."""
    from check_client_journey_in_containers import PLAIN_SCHEME
    host, port = bound.getsockname()[:2]
    return PLAIN_SCHEME + "%s:%d" % (host, port)


def write_host(folder, base, port, identity_origin, objects, api_version, account_id, key_reference):
    """The host file of a deployment, with loopback addresses: the billing block is what the setup command emits."""
    from loop_engine.core.service_runtime.http_entrypoint import HOST_CONFIGURATION_VERSION
    from loop_engine.core.service_runtime.account_policy import ACCOUNT_POLICY_VERSION
    from loop_engine.core.service_runtime.records import BILLING_MANAGE_SCOPE, DEFAULT_SCOPES
    from loop_engine.core.service_runtime.request_limits import REQUEST_LIMITS_RECORD_TYPE, SOCKET_PEER_SOURCE
    manifest = json.loads(STARTER_MANIFEST.read_text())
    manifest["artifact_root"] = str(STARTER_MANIFEST.parent.resolve())
    for row in manifest["items"]:
        row["grants"] = []
    (folder / "manifest.json").write_text(json.dumps(manifest))
    starters = [row["reference"]["identity"] for row in manifest["items"]]
    application_address = base + "/app"
    common = {"account_id": account_id, "api_version": api_version, "livemode": False}
    host = {"record_type": HOST_CONFIGURATION_VERSION,
            "runtime": {"database_path": str(folder / "service.db"), "writes_authorized": True},
            "http": {"public_base_url": base, "allowed_hosts": [f"127.0.0.1:{port}"], "allow_loopback_http": True,
                     "display_name": "Baltor",
                     "request_limits": {"record_type": REQUEST_LIMITS_RECORD_TYPE,
                                        "client_address_source": SOCKET_PEER_SOURCE,
                                        "failures_allowed": 100, "window_seconds": 600}},
            "authentication": {"modes": ["host_key"]},
            "manifest_path": str(folder / "manifest.json"),
            "accounts": {"record_type": ACCOUNT_POLICY_VERSION, "founding_free_monthly_accounts": 0},
            "browser_identity": {"project_url": identity_origin, "publishable_key_ref": "env:" + PUBLISHABLE_KEY_ENVIRONMENT,
                                 "namespace_prefix": "journey-customers",
                                 "allowed_scopes": [*DEFAULT_SCOPES, BILLING_MANAGE_SCOPE],
                                 "registration_enabled": True, "email_signup_enabled": True, "allow_network": True,
                                 "allow_loopback": True, "starter_identities": starters},
            "client_access": {"writes_authorized": True},
            "billing": {
                "webhook": {**common, "signing_secret_refs": ["env:" + SERVICE_SECRET_ENVIRONMENT]},
                "policy": {"allowed_price_ids": [objects["price_id"]]},
                "provider": {**common, "api_key_ref": key_reference, "allow_network": True},
                "sessions": {**common, "api_key_ref": key_reference,
                             "plans": [{"plan_ref": objects["plan_ref"], "label": objects["plan_label"],
                                        "price_id": objects["price_id"]}],
                             "checkout_success_url": application_address, "checkout_cancel_url": application_address,
                             "portal_return_url": application_address,
                             "portal_configuration_id": objects["portal_configuration_id"],
                             "allow_network": True, "allow_session_creation": True,
                             "allow_loopback_return_urls": True}}}
    path = folder / "host.json"
    path.write_text(json.dumps(host, indent=1))
    return path


def serve(host_path, project, identity_origin, bound):
    """Configure the host as `loop-engine service configure` does, then serve it as the deployment does."""
    import uvicorn
    from loop_engine.core.service_runtime.account_email import AccountEmailAdapter
    from loop_engine.core.service_runtime.account_email_checks import _secrets as account_secrets
    from loop_engine.core.service_runtime.account_email_checks import _settings as account_settings
    from loop_engine.core.service_runtime.account_origin import AccountOrigins, SupabaseIdentityAdministration
    from loop_engine.core.service_runtime.http_entrypoint import configure_host, load_host_application
    configure_host(host_path)
    application, _configuration = load_host_application(host_path)
    config = application.configuration
    origins = AccountOrigins(application.runtime, identity_origin + "/auth/v1",
                             SupabaseIdentityAdministration(identity_origin, allow_network=True, transport=project.admin))
    email = AccountEmailAdapter(account_settings(identity_origin=identity_origin, mail_origin=identity_origin,
                                                 allow_loopback=True, attempts_for_each_address=50,
                                                 attempts_for_each_email=10),
                                account_secrets, public_base_url=config.public_base_url,
                                address_limits=config.request_limits, display_name=config.display_name,
                                identity_transport=project.generate_link, mail_transport=project.send_mail,
                                account_origins=origins)
    application = replace(application, account_email=email)
    server = uvicorn.Server(uvicorn.Config(application.create_app(), log_level="error", access_log=False,
                                          proxy_headers=False, timeout_graceful_shutdown=2,
                                          limit_concurrency=config.maximum_transport_concurrency))
    worker = threading.Thread(target=lambda: server.run(sockets=[bound]), daemon=True)
    worker.start()
    deadline = time.monotonic() + 20
    while not server.started and worker.is_alive() and time.monotonic() < deadline:
        time.sleep(0.02)
    if not server.started:
        raise RuntimeError("the service did not start")
    return application, server, worker


class Journey:
    """The customer's side of the run: HTTP, the protocol endpoint and a real browser, recorded step by step."""

    def __init__(self, base, project, identity_origin, stripe, listener, evidence_prefix):
        import httpx
        self.base, self.project, self.identity_origin = base, project, identity_origin
        self.stripe, self.listener, self.evidence_prefix = stripe, listener, evidence_prefix
        self.http = httpx.Client(timeout=60, trust_env=False)
        self.steps, self.started = [], time.monotonic()

    def step(self, name, passed, **facts):
        row = {"step": name, "passed": bool(passed), "seconds": round(time.monotonic() - self.started, 1), **facts}
        self.steps.append(row)
        print(json.dumps({"step": name, "passed": bool(passed)}), flush=True)
        return bool(passed)

    def api(self, method, path, token=None, body=None, headers=None):
        sent = dict(headers or {})
        if token:
            sent["Authorization"] = "Bearer " + token
        response = self.http.request(method, self.base + path, json=body, headers=sent)
        try:
            value = response.json()
        except ValueError:
            value = None
        return response.status_code, value, response

    # Sign-up, as the website's Get started page drives it.
    def sign_up(self, address):
        status, value, _ = self.api("POST", "/api/v1/account/signup",
                                    body={"record_type": "service_account_signup_request/v2", "email": address})
        links = self.project.links_to(address)
        if status not in (200, 202) or not links:
            return None, {"signup_status": status, "links": len(links)}
        token_hash, action = links[-1]
        verified = self.http.post(self.identity_origin + "/auth/v1/verify", json={"token_hash": token_hash, "type": action})
        session = verified.json().get("access_token") if verified.status_code == 200 else None
        password = secrets.token_urlsafe(18)
        chosen = self.http.put(self.identity_origin + "/auth/v1/user", json={"password": password},
                               headers={"Authorization": "Bearer " + (session or "")})
        signed_in = self.http.post(self.identity_origin + "/auth/v1/token?grant_type=password",
                                   json={"email": address, "password": password})
        token = signed_in.json().get("access_token") if signed_in.status_code == 200 else None
        status_activate, activation, _ = self.api("POST", "/api/v1/account/activate", token,
                                                  {"record_type": "service_account_activation_request/v1"})
        tenant = ((activation or {}).get("result") or {}).get("tenant_id")
        return (token if status_activate == 200 and tenant else None), {
            "signup_status": status, "link_verified": verified.status_code, "password_set": chosen.status_code,
            "signed_in": signed_in.status_code, "activation_status": status_activate, "tenant_id": tenant,
            "founding_offer": ((activation or {}).get("result") or {}).get("founding_offer")}

    def session(self, token):
        status, value, _ = self.api("GET", "/api/v1/session", token)
        result = (value or {}).get("result") or {}
        return {"status": status, "access_source": result.get("access_source"),
                "entitlement": (result.get("principal") or {}).get("entitlement"),
                "tenant_id": (result.get("principal") or {}).get("tenant_id")}

    def wait_for_entitlement(self, token, wanted, seconds=EVENT_WAIT_SECONDS):
        deadline = time.monotonic() + seconds
        current = self.session(token)
        while current["entitlement"] != wanted and time.monotonic() < deadline:
            time.sleep(1)
            current = self.session(token)
        return current

    def wait_for_event(self, kind, before=(), seconds=EVENT_WAIT_SECONDS):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            fresh = [event for event in self.listener.delivered(kind) if event not in before]
            if fresh:
                return fresh
            time.sleep(1)
        return []

    def wait_for_forwarded(self, kind, before=(), seconds=EVENT_WAIT_SECONDS):
        """Event identities of one type the listener forwarded and the service answered, whatever the answer."""
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            fresh = [event for event, statuses in self.listener.answered.items()
                     if self.listener.forwarded.get(event) == kind and event not in before and statuses]
            if fresh:
                return fresh
            time.sleep(1)
        return []

    def search(self, token, query):
        status, value, _ = self.api("POST", "/api/v1/retrieval", token, {"record_type": "service_retrieval_request/v2",
                                                                         "query": query, "mode": "lexical", "top_n": 3})
        hits = ((value or {}).get("result") or {}).get("hits") or []
        return status, hits, ((value or {}).get("result") or {}).get("bodies_loaded")

    def download(self, token, identity, digest):
        status, value, response = self.api("POST", "/api/v1/download", token, {
            "record_type": "service_provisioning_request/v2", "operation": "read", "identity": identity,
            "expected_digest": digest, "request_id": "journey-" + uuid.uuid4().hex})
        if status == 200:
            return status, hashlib.sha256(response.content).hexdigest(), None
        error = (value or {}).get("error") or {}
        return status, None, {"code": error.get("code"), "details": error.get("details")}

    def mcp_read(self, key, identity, digest):
        """`provisioning_read` through the official protocol client, with a client key as a harness holds it."""
        async def run():
            import httpx2
            from mcp import Client
            from mcp.client.streamable_http import streamable_http_client
            async with httpx2.AsyncClient(headers={"Authorization": "Bearer " + key}, timeout=60) as http:
                async with Client(streamable_http_client(self.base + "/mcp", http_client=http), mode="legacy") as client:
                    result = await client.call_tool("provisioning_read", {"identity": identity, "expected_digest": digest,
                                                                          "request_id": "journey-mcp-" + uuid.uuid4().hex})
                    content = result.structured_content or {}
                    error = content.get("error") or {}
                    body = ((content.get("result") or {}).get("body")) if not result.is_error else None
                    return {"is_error": bool(result.is_error), "code": error.get("code"),
                            "offer": (error.get("details") or {}).get("record_type"),
                            "pricing_url_path": (error.get("details") or {}).get("pricing_url", "")[len(self.base):] or None,
                            "body_digest": hashlib.sha256(body.encode()).hexdigest() if isinstance(body, str) else None}
        return asyncio.run(run())

    def client_key(self, token):
        status, value, _ = self.api("POST", "/api/v1/account/access", token, {
            "record_type": "service_client_access_request/v1", "operation": "issue", "request_id": uuid.uuid4().hex,
            "label": "journey harness", "scopes": ["provisioning:metadata", "provisioning:read", "usage:read"],
            "lifetime_seconds": 3600})
        result = (value or {}).get("result") or {}
        return status, result.get("token")

    def page(self, operation, url, **settings):
        """One Stripe-hosted page in a real browser. The address goes over standard input and is never stored."""
        node = shutil.which("node")
        answer = subprocess.run([node, str(PAGE_HELPER)], input=json.dumps({
            "operation": operation, "url": url, "return_prefix": self.base + "/",
            "evidence_prefix": self.evidence_prefix + "-" + operation, **settings}),
            capture_output=True, text=True, timeout=200)
        try:
            return json.loads(answer.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            return {"ok": False, "error": "page_helper_gave_no_answer", "exit": answer.returncode,
                    "stderr": answer.stderr[-300:]}

    def billing_session(self, token, operation, options, plan_ref=None):
        body = {"record_type": "billing_session_request/v1", "request_id": "journey-" + uuid.uuid4().hex,
                "policy_digest": options["policy_digest"], **({"plan_ref": plan_ref} if plan_ref else {})}
        status, value, _ = self.api("POST", "/api/v1/billing/" + operation, token, body)
        return status, (value or {}).get("result") or (value or {}).get("error") or {}


def hosted_on(address, host):
    """True for an HTTPS address on exactly the Stripe host the service's session adapter accepts."""
    parts = urlsplit(address)
    return parts.scheme == "https" and parts.hostname == host and not parts.username and not parts.password


def _first_item(journey, token):
    status, hits, bodies_loaded = journey.search(token, "error analysis by segment")
    hit = hits[0]["reference"] if hits else {}
    return status, hits, bodies_loaded, hit.get("identity"), hit.get("body_digest") or hit.get("digest")


def subscription_of(stripe, customer):
    rows = stripe.call("GET", "/v1/subscriptions", params={"customer": customer, "status": "all", "limit": "3",
                                                         "expand[]": "data.latest_invoice"})["data"]
    return rows[0] if rows else None


def period_end(subscription):
    return max(item["current_period_end"] for item in subscription["items"]["data"])


def part_checkout(journey, application, objects):
    """Sign up, be refused, pay, download, cancel in the portal, and lose access when the subscription ends."""
    stripe = journey.stripe
    address = "journey-" + uuid.uuid4().hex[:10] + "@example.com"
    token, facts = journey.sign_up(address)
    if not journey.step("sign_up_with_email_link_and_password", token is not None, **facts):
        return
    tenant = facts["tenant_id"]
    state = journey.session(token)
    journey.step("new_account_holds_no_plan", state["access_source"] == "none" and state["entitlement"] == "metadata",
                 **state)
    status, hits, bodies_loaded, identity, digest = _first_item(journey, token)
    journey.step("search_is_free_without_a_plan", status == 200 and hits and bodies_loaded is False and identity,
                 hits=len(hits))
    status, _received, refusal = journey.download(token, identity, digest)
    journey.step("download_refused_with_the_plan_offer", status == 403 and (refusal or {}).get("code") == "plan_required"
                 and ((refusal or {}).get("details") or {}).get("record_type") == "service_plan_required/v1",
                 status=status, code=(refusal or {}).get("code"),
                 offer_paths=sorted(value[len(journey.base):] for key, value in
                                    ((refusal or {}).get("details") or {}).items() if key.endswith("_url")))
    status, key = journey.client_key(token)
    journey.step("client_key_issued_for_a_harness", status == 200 and bool(key), status=status)
    refused = journey.mcp_read(key, identity, digest) if key else {}
    journey.step("mcp_read_refused_with_the_plan_offer", refused.get("is_error") is True
                 and refused.get("code") == "plan_required" and refused.get("offer") == "service_plan_required/v1",
                 **{name: refused.get(name) for name in ("is_error", "code", "offer", "pricing_url_path")})
    status, value, _ = journey.api("GET", "/api/v1/billing/plans", token)
    options = (value or {}).get("result") or {}
    journey.step("plans_offer_checkout_and_no_portal_before_payment", status == 200
                 and options.get("checkout_available") is True and options.get("portal_available") is False
                 and [row.get("plan_ref") for row in options.get("plans", [])] == [objects["plan_ref"]],
                 plans=options.get("plans"), unavailable_reason=options.get("unavailable_reason"))
    status, result = journey.billing_session(token, "checkout", options, objects["plan_ref"])
    redirect = result.get("redirect_url", "")
    session_id = result.get("provider_session_id", "")
    try:
        customer = application.runtime.billing_customer_for(application.runtime.authenticate_subject(
            journey.identity_origin + "/auth/v1", journey.project.users[address]["id"]))["provider_customer_id"]
    except Exception:
        customer = ""
    if customer:
        stripe.customers.append(customer)
    at_stripe = stripe.call("GET", "/v1/customers/" + customer) if customer else {}
    journey.step("checkout_session_created_with_one_customer_for_the_account", status == 200
                 and hosted_on(redirect, CHECKOUT_HOST) and session_id.startswith("cs_test_")
                 and result.get("payment_confirmed") is False and result.get("entitlement_changed") is False
                 and (at_stripe.get("metadata") or {}).get("loop_engine_tenant_id") == tenant,
                 status=status, session=session_id, customer=customer)
    paid = journey.page("checkout", redirect, card=PAYING_CARD, email=address) if redirect else {}
    journey.step("paid_on_the_stripe_page_with_a_test_card", paid.get("ok") is True and paid.get("returned") is True,
                 **{name: paid.get(name) for name in ("returned_path", "total_due_text", "tax_lines", "page_terms",
                                                      "error", "screenshot")})
    state = journey.wait_for_entitlement(token, "bodies")
    subscription = subscription_of(stripe, customer) if customer else None
    journey.step("signed_events_grant_downloads", state["entitlement"] == "bodies"
                 and state["access_source"] == "subscription", **state,
                 subscription=(subscription or {}).get("id"), subscription_status=(subscription or {}).get("status"),
                 latest_invoice_status=((subscription or {}).get("latest_invoice") or {}).get("status"),
                 deliveries=journey.listener.deliveries())
    status, received, refusal = journey.download(token, identity, digest)
    journey.step("paid_account_downloads_over_http", status == 200 and received == digest, status=status,
                 refusal=refusal)
    read = journey.mcp_read(key, identity, digest) if key else {}
    journey.step("paid_account_reads_over_mcp", read.get("is_error") is False and read.get("body_digest") == digest,
                 is_error=read.get("is_error"), code=read.get("code"))
    status, value, _ = journey.api("GET", "/api/v1/usage", token)
    usage = (value or {}).get("result") or {}
    journey.step("downloads_are_recorded_as_usage", status == 200 and (usage.get("records") or 0) >= 1,
                 records=usage.get("records"), current_period_records=usage.get("current_period_records"))
    status, value, _ = journey.api("GET", "/api/v1/billing/plans", token)
    options = (value or {}).get("result") or {}
    status, portal = journey.billing_session(token, "portal", options)
    journey.step("portal_session_created_after_payment", options.get("portal_available") is True and status == 200
                 and hosted_on(portal.get("redirect_url", ""), PORTAL_HOST), status=status,
                 portal_available=options.get("portal_available"))
    before = journey.listener.delivered("customer.subscription.updated")
    shown = journey.page("portal", portal.get("redirect_url", ""), cancel=True) if portal.get("redirect_url") else {}
    journey.step("portal_lists_the_paid_invoice_and_cancels_at_the_period_end", shown.get("ok") is True
                 and shown.get("shows_paid_invoice") is True and shown.get("cancelled_in_portal") is True,
                 **{name: shown.get(name) for name in ("shows_invoice_history", "shows_paid_invoice", "price_lines",
                                                       "next_billing_line", "after_cancel_text", "error")})
    updated = journey.wait_for_event("customer.subscription.updated", before)
    subscription = subscription_of(stripe, customer) if customer else None
    state = journey.session(token)
    status, received, _ = journey.download(token, identity, digest)
    # The portal schedules the end with `cancel_at` at the period end on the flexible billing mode, and with
    # `cancel_at_period_end` on the classic one; either is a cancellation at the end of the paid month.
    scheduled = (subscription or {}).get("cancel_at_period_end") is True or (
        (subscription or {}).get("cancel_at") is not None
        and (subscription or {}).get("cancel_at") == period_end(subscription))
    journey.step("access_continues_until_the_paid_month_ends", bool(updated) and state["entitlement"] == "bodies"
                 and status == 200 and scheduled and (subscription or {}).get("status") == "active",
                 events=updated, entitlement=state["entitlement"], download_status=status,
                 cancel_at_period_end=(subscription or {}).get("cancel_at_period_end"),
                 cancel_at=(subscription or {}).get("cancel_at"),
                 period_end=period_end(subscription) if subscription else None)
    # The operator's refund and immediate cancellation: what a refund request ends with.
    refund = {}
    try:
        invoice = (subscription or {}).get("latest_invoice") or {}
        payments = stripe.call("GET", "/v1/invoice_payments", params={"invoice": invoice.get("id"), "limit": "3"})["data"]
        intent = ((payments[0].get("payment") or {}).get("payment_intent")) if payments else None
        made = stripe.call("POST", "/v1/refunds", data={"payment_intent": intent}) if intent else {}
        refund = {"refund": made.get("id"), "refund_status": made.get("status"), "amount": made.get("amount")}
    except RuntimeError as error:
        refund = {"refund_error": str(error)}
    before = journey.listener.delivered("customer.subscription.deleted")
    ended = stripe.call("DELETE", "/v1/subscriptions/" + subscription["id"]) if subscription else {}
    deleted = journey.wait_for_event("customer.subscription.deleted", before)
    state = journey.wait_for_entitlement(token, "metadata")
    status, _received, refusal = journey.download(token, identity, digest)
    after = journey.mcp_read(key, identity, digest) if key else {}
    journey.step("refund_and_cancellation_end_access", bool(deleted) and ended.get("status") == "canceled"
                 and state["entitlement"] == "metadata" and status == 403
                 and (refusal or {}).get("code") == "plan_required" and after.get("code") == "plan_required",
                 **refund, subscription_status=ended.get("status"), events=deleted, entitlement=state["entitlement"],
                 access_source=state["access_source"], download_status=status, mcp_code=after.get("code"))


def advance(stripe, clock, moment):
    stripe.call("POST", "/v1/test_helpers/test_clocks/" + clock + "/advance", data={"frozen_time": str(moment)})
    deadline = time.monotonic() + CLOCK_WAIT_SECONDS
    while time.monotonic() < deadline:
        value = stripe.call("GET", "/v1/test_helpers/test_clocks/" + clock)
        if value.get("status") == "ready" and value.get("frozen_time") == moment:
            return True
        time.sleep(2)
    return False


def _clock_checkout(journey, application, objects, address, card, *, authenticate=False):
    """Sign up, put the account's customer on a fresh test clock, and pay at checkout. Returns the run's handles."""
    from loop_engine.core.service_runtime.records import BillingCustomerBindingRequest
    stripe = journey.stripe
    token, facts = journey.sign_up(address)
    if not journey.step("sign_up_with_email_link_and_password", token is not None, **facts):
        return None
    tenant = facts["tenant_id"]
    clock = stripe.call("POST", "/v1/test_helpers/test_clocks", data={
        "frozen_time": str(int(time.time())), "name": "baltor-journey-" + tenant[-20:]})["id"]
    stripe.test_clocks.append(clock)
    customer = stripe.call("POST", "/v1/customers", data={"test_clock": clock,
                                                          "metadata[loop_engine_tenant_id]": tenant})["id"]
    # The host binding route of the subscription journey guide: a customer made outside checkout, bound by the host.
    # A test clock can only hold a customer created on it, so the service's own customer creation is not used here;
    # the checkout part covers it.
    application.runtime.bind_billing_customer(BillingCustomerBindingRequest(tenant, customer, stripe.account_id))
    journey.step("customer_on_a_test_clock_bound_by_the_host", True, clock=clock, customer=customer)
    _status, _hits, _loaded, identity, digest = _first_item(journey, token)
    _status, value, _ = journey.api("GET", "/api/v1/billing/plans", token)
    options = (value or {}).get("result") or {}
    status, result = journey.billing_session(token, "checkout", options, objects["plan_ref"])
    paid = journey.page("checkout", result.get("redirect_url", ""), card=card, email=address,
                        authenticate=authenticate) if result.get("redirect_url") else {}
    state = journey.wait_for_entitlement(token, "bodies")
    subscription = subscription_of(stripe, customer)
    journey.step("paid_at_checkout_for_the_clock_customer", paid.get("ok") is True and state["entitlement"] == "bodies",
                 checkout_status=status, subscription=(subscription or {}).get("id"), entitlement=state["entitlement"],
                 authentication_completed=paid.get("authentication_completed"), error=paid.get("error"))
    if subscription is None:
        return None
    return {"token": token, "clock": clock, "customer": customer, "identity": identity, "digest": digest,
            "subscription": subscription}


def part_renewal(journey, application, objects):
    """Pay on a test clock, keep access through the renewal draft hour, and renew to the next month."""
    stripe = journey.stripe
    held = _clock_checkout(journey, application, objects, "journey-renewal-" + uuid.uuid4().hex[:8] + "@example.com",
                           PAYING_CARD)
    if held is None:
        return
    token, clock, customer, identity, digest = (held[key] for key in ("token", "clock", "customer", "identity", "digest"))
    first_end = period_end(held["subscription"])
    before = set(journey.listener.answered)
    moved = advance(stripe, clock, first_end + 600)
    time.sleep(8)
    subscription = subscription_of(stripe, customer)
    state = journey.session(token)
    status, _received, refusal = journey.download(token, identity, digest)
    journey.step("access_continues_while_the_renewal_invoice_is_a_draft", moved and state["entitlement"] == "bodies"
                 and status == 200, clock_advanced=moved, subscription_status=subscription.get("status"),
                 latest_invoice_status=(subscription.get("latest_invoice") or {}).get("status"),
                 entitlement=state["entitlement"], download_status=status, refusal=refusal,
                 events=[row for row in journey.listener.deliveries() if row["event_id"] not in before])
    before_paid = journey.listener.delivered("invoice.paid")
    moved = advance(stripe, clock, first_end + 7200)
    renewed = journey.wait_for_event("invoice.paid", before_paid)
    subscription = subscription_of(stripe, customer)
    state = journey.session(token)
    status, _received, _ = journey.download(token, identity, digest)
    journey.step("paid_renewal_extends_access_to_the_next_month", moved and bool(renewed)
                 and period_end(subscription) > first_end and state["entitlement"] == "bodies" and status == 200,
                 events=renewed, latest_invoice_status=(subscription.get("latest_invoice") or {}).get("status"),
                 entitlement=state["entitlement"], download_status=status)


def part_failed_renewal(journey, application, objects):
    """Pay with a card that needs the cardholder for every charge; the unattended renewal fails and access ends.

    Stripe refuses to change the payment method of a subscription that Checkout created with Managed Payments, so a
    declined renewal is produced with Stripe's "Always authenticate" test card instead: the first payment is
    authenticated on the Checkout page, and the renewal, charged with nobody present, cannot be."""
    stripe = journey.stripe
    held = _clock_checkout(journey, application, objects, "journey-failed-" + uuid.uuid4().hex[:8] + "@example.com",
                           AUTHENTICATION_EVERY_TIME_CARD, authenticate=True)
    if held is None:
        return
    token, clock, customer, identity, digest = (held[key] for key in ("token", "clock", "customer", "identity", "digest"))
    before = set(journey.listener.answered)
    moved = advance(stripe, clock, period_end(held["subscription"]) + 7200)
    # The failure and the past-due update arrive within the same second; whichever reconciles last decides, and the
    # other may be answered as pending for the provider to retry. Both are forwarded, and access must end.
    failed = journey.wait_for_forwarded("invoice.payment_failed", before)
    state = journey.wait_for_entitlement(token, "metadata")
    subscription = subscription_of(stripe, customer)
    status, _received, refusal = journey.download(token, identity, digest)
    journey.step("failed_renewal_payment_ends_access", moved and bool(failed) and state["entitlement"] == "metadata"
                 and subscription.get("status") == "past_due" and status == 403
                 and (refusal or {}).get("code") == "plan_required",
                 events=[row for row in journey.listener.deliveries() if row["event_id"] not in before],
                 subscription_status=subscription.get("status"),
                 latest_invoice_status=(subscription.get("latest_invoice") or {}).get("status"),
                 entitlement=state["entitlement"], access_source=state["access_source"], download_status=status)
    _status, value, _ = journey.api("GET", "/api/v1/billing/plans", token)
    options = (value or {}).get("result") or {}
    journey.step("the_portal_stays_offered_to_fix_the_payment", options.get("portal_available") is True,
                 portal_available=options.get("portal_available"), checkout_available=options.get("checkout_available"))


def refusals(host_path):
    """The service's own failure journal for the run: route, status and code of each refused request, no bodies."""
    from loop_engine.core.service_runtime.http_entrypoint import read_failures
    try:
        rows = read_failures(host_path, limit=50)
    except Exception as error:
        return [{"journal_unreadable": type(error).__name__}]
    rows = rows.get("failures", []) if isinstance(rows, dict) else rows
    keep = ("route", "method", "status", "refusal_code", "at")
    return [{name: row.get(name) for name in keep if row.get(name) is not None}
            for row in (rows if isinstance(rows, list) else []) if isinstance(row, dict)]


def cleanup(stripe, keep):
    """Delete the test clocks (which takes their customers with them) and the customers this run created."""
    removed = []
    if keep:
        return removed
    for prefix, identities in (("/v1/test_helpers/test_clocks/", stripe.test_clocks), ("/v1/customers/", stripe.customers)):
        for identity in identities:
            try:
                stripe.call("DELETE", prefix + identity)
                removed.append(identity)
            except RuntimeError:
                pass
    return removed


def run(part, report_path, *, keep=False, environment=None):
    environment = dict(os.environ if environment is None else environment)
    manifest = sandbox.load_manifest()
    binding, key = require_test_key(environment, manifest)
    for need, present in (("stripe_command_line", shutil.which("stripe")), ("node", shutil.which("node")),
                          ("playwright", PLAYWRIGHT_MODULE.exists()), ("starter_catalogue", STARTER_MANIFEST.exists())):
        if not present:
            raise Refusal("missing_" + need)
    target = reserve_report(report_path)
    report = {"record_type": REPORT_RECORD_TYPE, "part": part, "observed_at": datetime.now(timezone.utc).isoformat(),
              "stripe_account": binding.account_id, "livemode": False, "steps": [],
              "limitations": [
                  "Stripe test mode only: no live account, card or money is involved.",
                  "The identity provider is the loopback stand-in the website checks use; production sign-up is not exercised.",
                  "A test clock moves Stripe's time only. The service keeps its own clock, so an access period that lapses "
                  "with no event at all is not observed here; the renewal steps observe the events Stripe sends.",
                  "Events reach the service through `stripe listen`, in the account's default API version, not through a "
                  "registered endpoint."]}
    stripe = None
    listener = None
    try:
        with ExitStack() as stack:
            folder = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="stripe-journey-")))
            bound = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            bound.bind(("127.0.0.1", 0))
            stack.callback(bound.close)
            port = bound.getsockname()[1]
            base = loopback_origin(bound)
            child = {**environment, binding.environment_name: key}
            listener = Listener(shutil.which("stripe"), base + "/api/v1/billing/webhook", sandbox.SERVICE_EVENT_TYPES, child)
            stack.callback(listener.stop)
            if not listener.wait_ready():
                raise RuntimeError("stripe_listen_did_not_start")
            report["listener_api_version"] = listener.version
            stripe = StripeTestApi(key, binding.account_id, listener.version)
            objects = stripe.sandbox_objects()
            report["sandbox_objects"] = objects
            os.environ[SERVICE_SECRET_ENVIRONMENT] = listener.secret
            os.environ[binding.environment_name] = key
            os.environ[PUBLISHABLE_KEY_ENVIRONMENT] = "sb_publishable_journey_stand_in"
            project, identity_origin = stack.enter_context(identity_project())
            host_path = write_host(folder, base, port, identity_origin, objects, listener.version, binding.account_id,
                                   binding.service_api_key_reference)
            application, server, worker = serve(host_path, project, identity_origin, bound)
            stack.callback(lambda: (setattr(server, "should_exit", True), worker.join(5)))
            journey = Journey(base, project, identity_origin, stripe, listener, str(target.with_suffix("")))
            status, health, _ = journey.api("GET", "/api/v1/health")
            checks = {row["name"]: row["passed"] for row in ((health or {}).get("result") or {}).get("checks", [])}
            journey.step("service_reports_billing_installed", status == 200 and all(
                checks.get(name) for name in ("billing_sessions_installed", "billing_webhook_installed",
                                              "billing_policy_current")), checks={key_: value for key_, value in
                                                                                  checks.items() if "billing" in key_})
            try:
                {"checkout": part_checkout, "renewal": part_renewal,
             "failed_renewal": part_failed_renewal}[part](journey, application, objects)
            finally:
                report["steps"] = journey.steps
                report["deliveries"] = listener.deliveries()
                report["service_refusals"] = refusals(host_path)
    except Refusal:
        raise
    except Exception as error:
        report["stopped"] = type(error).__name__ + ": " + str(error)[:300]
    finally:
        if listener is not None:
            listener.stop()
            report["listener_lines"] = listener.lines[-80:]
        if stripe is not None:
            report["stripe_objects_created"] = {"customers": list(stripe.customers), "test_clocks": list(stripe.test_clocks)}
            report["stripe_objects_removed"] = cleanup(stripe, keep)
            stripe.close()
        for name in (SERVICE_SECRET_ENVIRONMENT, PUBLISHABLE_KEY_ENVIRONMENT):
            os.environ.pop(name, None)
    report["passed"] = sum(1 for row in report["steps"] if row["passed"])
    report["total"] = len(report["steps"])
    report["all_passed"] = bool(report["steps"]) and report["passed"] == report["total"] and "stopped" not in report
    encoded = json.dumps(report, indent=1, sort_keys=True)
    for value in (key, listener.secret if listener else None):
        if value and value in encoded:
            raise RuntimeError("a credential reached the report; nothing was written")
    target.write_text(encoded + "\n")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--part", choices=PARTS, required=True)
    parser.add_argument("--report", required=True, help="a new file; an existing one is never overwritten")
    parser.add_argument("--keep-stripe-objects", action="store_true",
                        help="leave the test customers and the test clock in the Stripe test account")
    arguments = parser.parse_args(argv)
    try:
        report = run(arguments.part, arguments.report, keep=arguments.keep_stripe_objects)
    except Refusal as refusal:
        print(json.dumps({"refused": str(refusal)}))
        return 2
    print(json.dumps({"part": report["part"], "passed": report["passed"], "total": report["total"],
                      "all_passed": report["all_passed"], "stopped": report.get("stopped"),
                      "report": str(arguments.report)}))
    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
