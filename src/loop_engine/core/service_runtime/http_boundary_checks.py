"""Boundary counterexamples for HTTP limits, host setup, licence policy and signed billing.

These checks use temporary artifacts and loopback listeners. Identity and
billing signatures are local fixtures; no hosted identity, payment account,
model provider or public deployment is contacted.
"""
from __future__ import annotations

from dataclasses import asdict, replace
import hashlib
import hmac
import json
from pathlib import Path
import threading
import time

from .http import ServiceHttpConfiguration, PROVISIONING_REQUEST_VERSION
from .http_auth import ServiceHttpAuthentication
from .http_test_fixtures import HttpDomainFixture, running_http, running_key_set


def _request(operation="list", **fields):
    return {"record_type": PROVISIONING_REQUEST_VERSION, "operation": operation, **fields}


def run_checks(check, root):
    _host_setup(check, root / "host")
    _licence_policy(check, root / "licences")
    _limits(check, root / "limits")
    _key_endpoint(check, root / "keys")
    _billing(check, root / "billing")


def _host_setup(check, root):
    import httpx
    from ..harness_intelligence import HarnessIntelligenceDraft, item_from_body
    from .http_entrypoint import configure_host, load_host_application, load_host_manifest
    from .records import TenantKeyIssue, ServiceRuntimeError
    root.mkdir()
    artifacts = root / "artifacts"
    artifacts.mkdir()
    body = "Pinned host-reviewed instruction body"
    (artifacts / "instruction.txt").write_text(body)
    item = item_from_body(HarnessIntelligenceDraft("skill.host", "skill", "Host-reviewed source",
        "context_intelligence", "context:host/v1", "MIT"), body)
    manifest = {"record_type": "host_attested_intelligence_manifest/v1", "artifact_root": str(artifacts),
        "items": [{"reference": item.reference(), "body_path": "instruction.txt", "approval_ref": "host-review:fixture",
                   "grants": [{"tenant_id": "host", "body_allowed": True, "metering": "required"}]}]}
    manifest_path, config_path = root / "manifest.json", root / "service.json"
    manifest_path.write_text(json.dumps(manifest))
    def build(configuration):
        config_path.write_text(json.dumps({"record_type": "service_http_host_configuration/v1",
            "runtime": {"database_path": str(root / "state.db"), "writes_authorized": True},
            "http": asdict(configuration), "authentication": {"modes": ["host_key"]},
            "manifest_path": str(manifest_path), "tenants": [{"tenant_id": "host", "namespace": "host",
                "operator_entitlement": {"valid_until": int(time.time()) + 3600, "evidence_ref": "local-host-test"}}]}))
        configure_host(str(config_path))
        return load_host_application(str(config_path))[0]
    with running_http(None, application_factory=build) as (base, application):
        issued = application.runtime.issue_key(TenantKeyIssue("host", "host-loader-acceptance"))
        with httpx.Client(base_url=base, headers={"Authorization": "Bearer " + issued.key}, trust_env=False) as client:
            result = client.post("/api/v1/provisioning", json=_request("read", identity=item.identity,
                request_id="host-file", expected_digest=item.digest))
            check("host_configuration_entrypoint_serves_exact_reviewed_files_through_real_HTTP",
                  result.status_code == 200 and result.json()["result"]["body"] == body
                  and result.json()["result"]["qualification_basis"] == "host_attested")
            application.runtime.set_grants("host", ())
            reopened, _ = load_host_application(str(config_path))
            check("serving_restart_does_not_reinstall_manifest_grants_after_revocation",
                  reopened.provisioning.invoke(issued.key, "list")["items"] == [])
    changed = json.loads(json.dumps(manifest))
    changed["items"][0]["body_path"] = "../outside.txt"
    (root / "outside.txt").write_text(body)
    unsafe = root / "unsafe.json"
    unsafe.write_text(json.dumps(changed))
    try:
        load_host_manifest(str(unsafe))
    except ServiceRuntimeError as error:
        refused = error.code == "unsafe_artifact_path"
    else:
        refused = False
    check("host_manifest_cannot_escape_its_declared_artifact_root", refused)
    (artifacts / "instruction.txt").write_text("X" * len(body))
    try:
        load_host_manifest(str(manifest_path))
    except ServiceRuntimeError as error:
        refused = error.code == "artifact_digest_mismatch"
    else:
        refused = False
    check("host_review_is_bound_to_exact_bytes_not_only_an_item_name", refused)


def _licence_policy(check, root):
    """The host serves an item only when it accepts the exact licence that the item declares."""
    from types import SimpleNamespace
    from unittest.mock import patch
    from ..harness_intelligence import HarnessIntelligenceCatalogue, HarnessIntelligenceDraft, item_from_body
    from .http_entrypoint import (DEFAULT_ACCEPTED_LICENSES, HOST_CONFIGURATION_VERSION, LICENSE_POLICY_KEY,
        LICENSE_POLICY_VERSION, MANIFEST_VERSION, HostLicensePolicy, configure_host, load_host_application,
        load_host_manifest)
    from .records import TenantKeyIssue, ServiceRuntimeError
    root.mkdir()
    artifacts = root / "artifacts"
    artifacts.mkdir()
    body = "Pinned body that is served only under an accepted licence"
    (artifacts / "body.txt").write_text(body)
    numbers = iter(range(10_000))
    origin = "http://127.0.0.1:8000"
    # Characters that a person who reads a host file cannot see, or cannot tell
    # from an ordinary letter. They are built from code points, so that this
    # source file shows every character it holds. The variation selector and
    # the filler count as printable, and the last one is the Cyrillic letter
    # that looks like the first letter of MIT.
    zero_width, direction_override, no_break_space = chr(0x200B), chr(0x202E), chr(0xA0)
    variation_selector, hangul_filler, cyrillic_em = chr(0xFE0F), chr(0x3164), chr(0x41C)

    def row(identity, license_name, body_path="body.txt", granted=True):
        item = item_from_body(HarnessIntelligenceDraft(identity, "skill", "Licence policy fixture",
            "context_intelligence", "context:licence/v1", license_name), body)
        return {"reference": item.reference(), "body_path": body_path, "approval_ref": "host-review:fixture",
                "grants": [{"tenant_id": "host", "body_allowed": True, "metering": "required"}] if granted else []}

    def manifest(*rows):
        path = root / f"manifest-{next(numbers)}.json"
        path.write_text(json.dumps({"record_type": MANIFEST_VERSION, "artifact_root": str(artifacts), "items": list(rows)}))
        return str(path)

    def host(manifest_path, **settings):
        path = root / f"host-{next(numbers)}.json"
        path.write_text(json.dumps({"record_type": HOST_CONFIGURATION_VERSION,
            "runtime": {"database_path": str(path.with_suffix(".db")), "writes_authorized": True},
            "http": asdict(ServiceHttpConfiguration(origin, ("127.0.0.1:8000",), allow_loopback_http=True)),
            "authentication": {"modes": ["host_key"]}, "manifest_path": manifest_path,
            "tenants": [{"tenant_id": "host", "namespace": "host",
                "operator_entitlement": {"valid_until": int(time.time()) + 3600, "evidence_ref": "local-host-test"}}],
            **settings}))
        return path

    def outcome(action):
        """Return an empty code and text with the produced value, or the stable code and text of a refusal."""
        try:
            return "", "", action()
        except ServiceRuntimeError as error:
            return error.code, str(error), None
        except Exception as error:  # noqa: BLE001 - an untyped failure is never a stable refusal
            return "untyped_" + type(error).__name__, str(error), None

    def loaded(manifest_path, **options):
        return outcome(lambda: sorted(load_host_manifest(manifest_path, **options)[0].items))

    def started(configuration_path):
        return outcome(lambda: load_host_application(str(configuration_path)))

    def served(configuration_path, identity):
        def read():
            configure_host(str(configuration_path))
            application = load_host_application(str(configuration_path))[0]
            issued = application.runtime.issue_key(TenantKeyIssue("host", "licence-policy-acceptance"))
            return application.provisioning.invoke(issued.key, "read", identity=identity, request_id="licence-policy")["body"]
        return outcome(read)

    def refused(result, code, identity=""):
        return result[0] == code and identity in result[1] and result[2] is None

    accepted = manifest(row("skill.licensed", "MIT"))
    check("item_with_an_accepted_licence_loads_under_the_default_host_policy",
          loaded(accepted) == ("", "", ["skill.licensed"]))
    for name, code, values in (
            ("item_without_a_licence_is_refused_and_the_refusal_names_it", "item_license_missing", ("", "   ", None, 7)),
            ("item_with_an_unknown_licence_is_refused_and_the_refusal_names_it", "item_license_unknown",
             ("unknown", "UNKNOWN", "NOASSERTION", "NONE", " unknown ")),
            ("item_whose_licence_needs_review_is_refused_and_the_refusal_names_it", "item_license_needs_review",
             ("pending_review", "needs_review", "Needs Review", " pending_review ")),
            ("default_host_policy_refuses_a_licence_that_it_does_not_list", "item_license_not_accepted",
             ("Apache-2.0", "GPL-3.0-only"))):
        check(name, all(refused(loaded(manifest(row("skill.refused", value))), code, "skill.refused") for value in values))
    check("default_host_policy_accepts_only_the_licence_of_this_repository",
          DEFAULT_ACCEPTED_LICENSES == ("MIT",) and HostLicensePolicy().accepted_licenses == ("MIT",))
    # An item without any grant still reaches people. The starter catalogue of
    # the browser sign-in gives such an item to every new personal account, so
    # the licence decision cannot depend on the grants of a row.
    check("item_without_any_grant_is_still_refused_without_an_accepted_licence",
          all(refused(loaded(manifest(row("skill.ungranted", value, granted=False))), code, "skill.ungranted")
              for value, code in (("", "item_license_missing"), ("Apache-2.0", "item_license_not_accepted")))
          and loaded(manifest(row("skill.ungranted", "MIT", granted=False))) == ("", "", ["skill.ungranted"]))
    def starter_host(license_name):
        return host(manifest(row("skill.starter", license_name, granted=False)), browser_identity={
            "project_url": origin, "publishable_key_ref": "fixture:publishable", "namespace_prefix": "starters",
            "allow_loopback": True, "starter_identities": ["skill.starter"]})
    opened = started(starter_host("MIT"))
    check("host_does_not_start_when_its_starter_catalogue_holds_an_item_without_an_accepted_licence",
          opened[0] == "" and [binding.identity for binding in opened[2][0].browser_identity._starter_bindings] == ["skill.starter"]
          and all(refused(started(starter_host(value)), code, "skill.starter")
                  for value, code in (("", "item_license_missing"), ("Apache-2.0", "item_license_not_accepted"))))
    registered, register = [], HarnessIntelligenceCatalogue.register
    def recording(catalogue, item):
        registered.append(item.identity)
        return register(catalogue, item)
    # The refused row names a body that does not exist. The licence decides
    # first, so the loader never looks for that body.
    mixed = manifest(row("skill.licensed", "MIT"), row("skill.unlicensed", "", "never-opened.txt"))
    with patch.object(HarnessIntelligenceCatalogue, "register", recording):
        result = loaded(mixed)
    check("refused_item_is_never_registered_and_stops_the_whole_manifest",
          refused(result, "item_license_missing", "skill.unlicensed") and "skill.unlicensed" not in registered)
    stopped = host(mixed)
    check("host_with_one_unlicensed_item_neither_starts_nor_writes_tenant_state",
          refused(outcome(lambda: configure_host(str(stopped))), "item_license_missing", "skill.unlicensed")
          and refused(started(stopped), "item_license_missing", "skill.unlicensed")
          and not stopped.with_suffix(".db").exists())
    wider = manifest(row("skill.licensed", "MIT"), row("skill.apache", "Apache-2.0"))
    current = {"record_type": LICENSE_POLICY_VERSION, "accepted_licenses": ["MIT", "Apache-2.0"]}
    listed = host(wider, **{LICENSE_POLICY_KEY: current})
    check("host_that_lists_an_extra_licence_identifier_serves_that_item",
          served(listed, "skill.apache") == ("", "", body) and listed.with_suffix(".db").exists())
    check("same_manifest_is_refused_by_a_host_that_keeps_the_default_policy",
          refused(served(host(wider), "skill.apache"), "item_license_not_accepted", "skill.apache"))
    exact = HostLicensePolicy(("Apache-2.0",))
    check("licence_names_are_compared_exactly_and_a_host_list_replaces_the_default",
          exact.refusal("Apache-2.0") == "" and HostLicensePolicy(()).refusal("MIT") == "item_license_not_accepted"
          and all(exact.refusal(value) == "item_license_not_accepted" for value in (
              "apache-2.0", "APACHE-2.0", "Apache-2.0 ", " Apache-2.0", "Apache 2.0", "Apache-2.0+", "MIT"))
          and all(refused(loaded(manifest(row("skill.variant", value))), "item_license_not_accepted", "skill.variant")
                  for value in ("mit", "Mit", "MIT ", "MIT License", "MIT" + zero_width, "MIT\x7f")))
    # A state is decided before the list is read, so even a policy record that
    # was forced to hold a state still refuses it. An object that only imitates
    # the policy record is not a typed policy.
    forced = HostLicensePolicy(("MIT",))
    object.__setattr__(forced, "accepted_licenses", ("MIT", "unknown", ""))
    imitation = SimpleNamespace(accepted_licenses=("MIT",), record_type=LICENSE_POLICY_VERSION, refusal=lambda license_name: "")
    check("host_policy_cannot_list_a_missing_unknown_or_review_state_as_an_accepted_licence",
          all(refused(outcome(lambda names=names: HostLicensePolicy(names)), "invalid_license_policy") for names in (
              ("MIT", "unknown"), ("Unknown",), ("NOASSERTION",), ("pending_review",), ("needs-review",), ("",),
              (" MIT",), ("MIT", "MIT"), (7,), "MIT", None))
          and refused(outcome(lambda: HostLicensePolicy(("MIT",), "service_host_license_policy/v0")), "unsupported_license_policy")
          and [forced.refusal(value) for value in ("MIT", "unknown", "")] == ["", "item_license_unknown", "item_license_missing"]
          and all(refused(loaded(accepted, license_policy=untyped), "invalid_license_policy")
                  for untyped in ({"accepted_licenses": ["MIT"]}, ("MIT",), None, imitation)))
    absent = str(root / "absent-manifest.json")
    # A listed identifier is written in printable ASCII characters, so the
    # person who reviews the host file sees every character of it. A tab, a line
    # end, a delete character, a zero width space, a direction override, a
    # no-break space, a variation selector, a filler and a letter of another
    # script are refused, alone or beside the real name. An ordinary space
    # inside a name stays allowed.
    check("host_policy_cannot_list_a_name_with_a_hidden_or_look_alike_character",
          all(refused(outcome(lambda names=names: HostLicensePolicy(names)), "invalid_license_policy") for names in (
              ("MI\tT",), ("MI\nT",), ("MIT\x7f",), ("MIT\x85X",), ("MIT" + zero_width,), ("MIT", "MIT" + zero_width),
              (direction_override + "TIM",), ("MIT" + no_break_space + "License",), ("MIT", "MIT" + variation_selector),
              ("MIT" + hangul_filler,), ("MIT", cyrillic_em + "IT")))
          and refused(started(host(absent, **{LICENSE_POLICY_KEY: {**current, "accepted_licenses": ["MIT", "MIT" + zero_width]}})),
                      "invalid_license_policy")
          and outcome(lambda: HostLicensePolicy(("MIT", "CC BY 4.0")).refusal("CC BY 4.0")) == ("", "", ""))
    check("licence_policy_with_an_unknown_key_or_unsupported_version_is_refused_before_the_manifest_is_read",
          all(refused(started(host(absent, **{LICENSE_POLICY_KEY: value})), "unsupported_license_policy") for value in (
              None, [], {}, ["MIT"], {"accepted_licenses": ["MIT"]}, {**current, "accept_unknown": True},
              {**current, "record_type": "service_host_license_policy/v2"}))
          and refused(started(host(absent, **{LICENSE_POLICY_KEY: {**current, "accepted_licenses": ["MIT", "unknown"]}})),
                      "invalid_license_policy")
          and refused(started(host(absent, **{LICENSE_POLICY_KEY: current})), "invalid_configuration"))
    check("unknown_host_configuration_key_is_still_refused_beside_the_licence_policy",
          all(refused(started(host(accepted, **{key: current})), "unsupported_host_configuration")
              for key in ("licence_policy", "license_policies", "accepted_licenses"))
          and started(host(accepted, **{LICENSE_POLICY_KEY: current}))[0] == "")
    # An operator message stays short, whatever a manifest or a host list holds,
    # and it still names the refused item. An identity of 128 characters, the
    # longest tenant or namespace identity that the service supports, is shown
    # in full. A longer one is shown from its start.
    crowded = HostLicensePolicy(tuple(f"Licence-{number}" for number in range(5_000)))
    identities = ("skill.refused", "skill." + "n" * 122, "skill." + "x" * 5_000)
    messages = [loaded(manifest(row(identity, "L" * 5_000)), license_policy=crowded) for identity in identities]
    check("refusal_message_stays_short_and_still_names_the_refused_item",
          all(refused(result, "item_license_not_accepted") and len(result[1]) <= 480 for result in messages)
          and all(repr(identity) in result[1] for identity, result in zip(identities[:2], messages))
          and "'skill.xxxx" in messages[2][1] and all("5000" in result[1] for result in messages))
    # A declared licence can look like an accepted one. The message shows every
    # character outside printable ASCII by its code point, so the operator sees
    # why the item is refused.
    disguised = (("MIT" + variation_selector, "fe0f"), (cyrillic_em + "IT", "041c"), ("MIT" + zero_width, "200b"))
    check("refusal_message_shows_a_hidden_or_look_alike_character_by_its_code_point",
          all(refused(result, "item_license_not_accepted", "skill.disguised") and code_point in result[1]
              and value not in result[1] and "['MIT']" in result[1]
              for value, code_point in disguised for result in [loaded(manifest(row("skill.disguised", value)))]))
    # Control for the refusal checks above: with the policy decision patched
    # out, the same refused fixtures load. This shows that those fixtures are
    # refused for their licence and for no other reason. It does not detect a
    # removed guard by itself. The named detectors of a removed guard are the
    # refusal checks above, and this row follows the policy method that the
    # loader calls today.
    with patch.object(HostLicensePolicy, "refusal", lambda policy, license_name: ""):
        unguarded = [loaded(manifest(row("skill.refused", value, granted=granted)))[2]
                     for value in ("", "unknown", "pending_review", "Apache-2.0") for granted in (True, False)]
    check("refused_fixtures_load_once_the_licence_guard_is_patched_out", unguarded == [["skill.refused"]] * 8)


def _limits(check, root):
    import httpx
    from ..provisioning_server import ProvisioningGrant, ProvisioningItemBinding
    from .records import TenantKeyIssue
    root.mkdir()
    fixture = HttpDomainFixture(root)
    with running_http(fixture, maximum_response_bytes=8192, maximum_inline_body_bytes=128) as (base, _service):
        limited = fixture.runtime.issue_key(TenantKeyIssue("alpha", "metadata only", scopes=("provisioning:metadata",)))
        with httpx.Client(base_url=base, headers={"Authorization": "Bearer " + limited.key}, trust_env=False) as client:
            listing = client.post("/api/v1/provisioning", json=_request()).json()["result"]
            denied = client.post("/api/v1/provisioning", json=_request("read", identity="skill.alpha", request_id="no-scope"))
            check("metadata_only_durable_key_neither_advertises_nor_performs_body_access",
                  not any(row["body_allowed"] for row in listing["items"])
                  and denied.status_code == 403 and not fixture.reads)
        updated = replace(fixture.catalogue.items["skill.alpha"], purpose="EXCESS_METADATA" * 1000)
        fixture.catalogue.items[updated.identity] = updated
        fixture.bindings[updated.identity] = ProvisioningItemBinding.from_item(updated)
        fixture.runtime.set_grants("alpha", (ProvisioningGrant("alpha", fixture.bindings[updated.identity], True),))
        with httpx.Client(base_url=base, headers=fixture.headers(), trust_env=False) as client:
            limited_response = client.post("/api/v1/provisioning", json=_request())
            check("response_limit_refuses_the_whole_payload_without_partial_metadata_disclosure",
                  limited_response.status_code == 413 and len(limited_response.content) < 8192
                  and "EXCESS_METADATA" not in limited_response.text)
    delayed_root = root / "delayed"
    delayed_root.mkdir()
    fixture = HttpDomainFixture(delayed_root)
    entered, release = threading.Event(), threading.Event()
    fixture.before_read = lambda _item: (entered.set(), release.wait(2))
    with running_http(fixture, request_timeout_seconds=0.1, maximum_concurrent_operations=1) as (base, _service):
        try:
            with httpx.Client(base_url=base, headers=fixture.headers(), trust_env=False, timeout=2) as client:
                late = client.post("/api/v1/provisioning", json=_request("read", identity="skill.alpha", request_id="late-once"))
                busy = client.get("/api/v1/session")
                check("expired_response_wait_is_not_success_and_running_work_keeps_its_capacity_slot",
                      entered.is_set() and late.status_code == 504 and busy.status_code == 503
                      and late.json()["effect_commitment"] == "not_asserted"
                      and late.json()["automatic_retry"] is False)
                release.set()
                deadline = time.monotonic() + 1
                while fixture.usage()["records"] == 0 and time.monotonic() < deadline:
                    time.sleep(0.005)
                check("timed_out_callback_can_commit_once_without_adapter_replay",
                      len(fixture.reads) == 1 and fixture.usage()["records"] == 1)
        finally:
            release.set()


def _key_endpoint(check, root):
    import httpx
    import jwt
    from cryptography.hazmat.primitives.asymmetric import rsa
    from .records import SubjectBindingRequest
    root.mkdir()
    fixture = HttpDomainFixture(root)
    with running_key_set() as (base, state):
        issuer = base + "/issuer"
        fixture.runtime.bind_subject(SubjectBindingRequest("alpha", issuer, "subject"))
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        state["keys"] = [{**json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key())), "kid": "key", "alg": "RS256"}]
        def credential(service):
            return jwt.encode({"iss": issuer, "aud": service + "/mcp", "sub": "subject", "exp": int(time.time()) + 60,
                               "scope": "provisioning:metadata"}, key, algorithm="RS256", headers={"kid": "key"})
        def auth(configuration):
            return ServiceHttpAuthentication(modes=("external_jwt",), issuer=issuer,
                audience=configuration.public_base_url + "/mcp",
                jwks_url=base + "/jwks", allow_loopback_issuer=True, maximum_key_set_bytes=1024)
        state.update(status=302, location=base + "/not-authorized")
        with running_http(fixture, authentication=auth) as (service, _application):
            refused = httpx.get(service + "/api/v1/session", headers={"Authorization": "Bearer " + credential(service)}, trust_env=False)
            check("configured_key_endpoint_cannot_redirect_authentication_to_another_resource",
                  refused.status_code == 401 and "/not-authorized" not in state["paths"])
        state.update(status=200, padding="X" * 2048)
        with running_http(fixture, authentication=auth) as (service, _application):
            refused = httpx.get(service + "/api/v1/session", headers={"Authorization": "Bearer " + credential(service)}, trust_env=False)
            check("external_key_set_respects_its_byte_allowance", refused.status_code == 401)


def _billing(check, root):
    import httpx
    from unittest.mock import patch
    from .billing import StripeEventProcessor
    from .billing_records import (StripeWebhookConfig, StripeEntitlementPolicy, StripeSubscriptionResolver,
                                 StripeCustomerSubscriptionSnapshot, StripeSubscriptionState)
    from .records import BillingCustomerBindingRequest, ServiceCommitUnknown
    root.mkdir()
    fixture = HttpDomainFixture(root, operator_access=False)
    fixture.runtime.bind_billing_customer(BillingCustomerBindingRequest("alpha", "cus_alpha", "acct_fixture"))
    policy = StripeEntitlementPolicy(("price_fixture",))
    fixture.runtime.configure_billing_policy(policy)
    configuration = StripeWebhookConfig("acct_fixture", "fixture_version", ("env:LOCAL_SIGNING_FIXTURE",))
    secret = "LOCAL_SIGNATURE_TEST_ONLY"
    status = {"subscriptions": ()}
    def snapshot(customer):
        return StripeCustomerSubscriptionSnapshot("acct_fixture", customer, "fixture_version", False,
            status["subscriptions"], hashlib.sha256(repr(status["subscriptions"]).encode()).hexdigest())
    processor = StripeEventProcessor(fixture.runtime, configuration, policy, lambda _ref: secret,
                                     StripeSubscriptionResolver("local-current-subscriptions", snapshot))
    def event(identity):
        timestamp = int(time.time())
        body = json.dumps({"id": identity, "object": "event", "api_version": "fixture_version", "livemode": False,
            "type": "customer.subscription.updated", "created": timestamp, "account": "acct_fixture",
            "data": {"object": {"id": "sub_fixture", "customer": "cus_alpha"}}}).encode()
        signature = hmac.new(secret.encode(), str(timestamp).encode() + b"." + body, hashlib.sha256).hexdigest()
        return body, "t=" + str(timestamp) + ",v1=" + signature
    with running_http(fixture, billing_processor=processor) as (base, _service):
        with httpx.Client(base_url=base, trust_env=False) as client:
            body, signature = event("evt_active")
            wrong = client.post("/api/v1/billing/webhook", content=body,
                headers={"Content-Type": "application/json", "Stripe-Signature": "t=0,v1=" + "0" * 64})
            check("webhook_does_not_accept_unsigned_or_wrongly_signed_subscription_authority",
                  wrong.status_code == 400 and fixture.runtime.authenticate_key(fixture.keys["alpha"].key).entitlement == "metadata")
            with patch.object(type(fixture.runtime._catalog), "commit", side_effect=ServiceCommitUnknown()):
                uncertain = client.post("/api/v1/billing/webhook", content=body,
                    headers={"Content-Type": "application/json", "Stripe-Signature": signature})
            check("unknown_billing_commit_is_a_retryable_HTTP_failure_not_a_success_acknowledgment",
                  uncertain.status_code == 503 and uncertain.json()["error"]["code"] == "billing_commit_unknown"
                  and uncertain.json()["error"]["details"]["committed"] is None)
            status["subscriptions"] = (StripeSubscriptionState("sub_fixture", "cus_alpha", "active",
                (("price_fixture", int(time.time()) + 3600),), True),)
            accepted = client.post("/api/v1/billing/webhook", content=body,
                headers={"Content-Type": "application/json", "Stripe-Signature": signature})
            duplicate = client.post("/api/v1/billing/webhook", content=body,
                headers={"Content-Type": "application/json", "Stripe-Signature": signature})
            check("actual_HTTP_signed_webhook_reconciles_current_state_and_deduplicates_delivery",
                  accepted.status_code == duplicate.status_code == 200
                  and accepted.json()["result"]["entitlement"] == "bodies"
                  and duplicate.json()["result"]["status"] == "duplicate")
    pending = StripeEventProcessor(fixture.runtime, configuration, policy, lambda _ref: secret)
    with running_http(fixture, billing_processor=pending) as (base, _service):
        body, signature = event("evt_pending")
        response = httpx.post(base + "/api/v1/billing/webhook", content=body,
            headers={"Content-Type": "application/json", "Stripe-Signature": signature}, trust_env=False)
        check("unreconciled_signed_webhook_retains_durable_pending_identity_without_false_activation",
              response.status_code == 503 and response.json()["effect_commitment"] == "durable_pending"
              and response.json()["error"]["details"]["event_id"] == "evt_pending"
              and fixture.runtime.authenticate_key(fixture.keys["alpha"].key).entitlement == "metadata")
